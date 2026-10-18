"""Bounded training, frozen scoring, checkpoint/resume, and inference export."""
from __future__ import annotations

import copy
import io
import importlib.metadata
import random
import resource
import time

import numpy as np
import torch

from .data import eligible_groups
from .evaluation import control_evaluation, evaluate, score_functions
from .io import ROOT, atomic_bytes, digest, file_hash, output_path, read_json, source_hash, write_json
from .models import FunctionEncoder, SymmetricMLP, collate
from .objectives import PairSampler, contrastive_loss, scorer_loss
from .representation import FEATURE_VERSION, Graph, Vocabulary


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def rng_state():
    ns = np.random.get_state()
    return {"python": random.getstate(), "numpy": [ns[0], ns[1].tolist(), ns[2], ns[3], ns[4]],
            "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def restore_rng(state):
    random.setstate(state["python"])
    ns = state["numpy"]
    np.random.set_state((ns[0], np.array(ns[1], dtype=np.uint32), ns[2], ns[3], ns[4]))
    torch.set_rng_state(state["torch"].cpu())
    if state["cuda"]:
        if not torch.cuda.is_available() or len(state["cuda"]) != torch.cuda.device_count():
            raise ValueError("CUDA RNG/device topology changed")
        torch.cuda.set_rng_state_all([x.cpu() for x in state["cuda"]])


def save_torch(path, value):
    buf = io.BytesIO()
    torch.save(value, buf)
    atomic_bytes(path, buf.getvalue())


def load_checkpoint(path, expected=None, device="cpu"):
    value = torch.load(path, map_location=device, weights_only=True)
    if value.get("version") != "te01.checkpoint.v1":
        raise ValueError("Unsupported checkpoint")
    if expected is not None and value["identity"] != expected:
        raise ValueError("Incompatible resume: config/source/split/data/vocabulary/device/exposure changed")
    return value


def make_batch(rows, vocabulary, config, device):
    return collate([Graph(**i["graph"]) for i in rows], vocabulary, rich=config["rich"], typed=config["typed"],
                   structural=config["structural"] and config["graph"] != "set").to(device)


def encode_rows(model, data, vocabulary, device, partition, with_blocks=False, memory_gib=8):
    embeddings, blocks = {}, {}
    model.eval()
    started = time.perf_counter()
    bytes_stored, query_times = 0, {}
    with torch.no_grad():
        gallery = set(data.get("galleries", {}).get(partition, []))
        # One graph per inference batch bounds evaluation memory independently of corpus size.
        for row in data["samples"]:
            if row["exclusion"] or (data["split"]["assignments"][row["id"]]["partition"] != partition and row["id"] not in gallery):
                continue
            tick = time.perf_counter()
            z, bs = model(make_batch([row], vocabulary, model.config, device), return_blocks=True)
            # Evaluation intermediates are temporary CPU tensors, never disk caches.
            embeddings[row["id"]] = z[0].cpu()
            if with_blocks:
                blocks[row["id"]] = bs[0].cpu()
            bytes_stored += z[0].numel() * z.element_size() + (bs[0].numel() * bs[0].element_size() if with_blocks else 0)
            if bytes_stored > min(2, memory_gib / 2) * 2**30:
                raise MemoryError("Bounded evaluation embedding storage exceeded")
            query_times[row["id"]] = (time.perf_counter() - tick) * 1000
    if str(device).startswith("cuda"):
        torch.cuda.synchronize(device)
    return embeddings, blocks, (time.perf_counter() - started) * 1000, query_times


def export_encoder(path, model, vocabulary, threshold=None, binding_contract=None, protocol=None):
    save_torch(path, {"version": "te01.export.v1", "feature_version": FEATURE_VERSION,
                      "parser_schema": None if binding_contract else "1.0.1", "binding_contract": binding_contract,
                      "supervision_protocol": protocol,
                      "source_hash": source_hash(), "config": model.config, "vocabulary": vocabulary.tokens,
                      "state_dict": model.state_dict(), "threshold": threshold,
                      "output": "unit-normalized selected-function embedding; uncalibrated similarity"})


def load_export(path, device="cpu"):
    artifact = torch.load(path, map_location=device, weights_only=True)
    if artifact.get("version") != "te01.export.v1" or artifact["feature_version"] != FEATURE_VERSION or artifact["source_hash"] != source_hash():
        raise ValueError("Incompatible export")
    vocab = Vocabulary(artifact["vocabulary"])
    model = FunctionEncoder(len(vocab.tokens), artifact["config"]).to(device)
    model.load_state_dict(artifact["state_dict"])
    return model.eval(), vocab, artifact["threshold"]


def resolve_run(run, plan, batch_root):
    result = copy.deepcopy(run)
    if run["kind"] == "confirmation":
        selected = read_json(batch_root / "SELECT/result.json")
        template = selected["selected"] if run["template"] == "selected" else run["template"]
        result["config"] = copy.deepcopy(next(r["config"] for r in plan["runs"] if r["id"] == template))
        result["selected_template"] = template
    return result


def run_experiment(run, data, directory, *, device="cpu", problems=8, smoke=False,
                   allow_real=False, resume=False, batch_root=None, plan=None, memory_gib=8):
    if not smoke and not allow_real:
        raise ValueError("Substantive execution requires explicit opt-in and batch preflight")
    if smoke and not data["synthetic"]:
        raise ValueError("Smoke accepts only explicitly synthetic fixtures")
    if data["blockers"]:
        raise ValueError("Data prerequisites blocked: " + "; ".join(data["blockers"]))
    plan = plan or read_json(ROOT / "experiment_plan.json")
    directory = output_path(directory / "result.json").parent
    batch_root = batch_root or directory.parent
    run = resolve_run(run, plan, batch_root)
    if run["kind"] == "selection":
        return select_candidate(plan, batch_root, directory, synthetic=data["synthetic"])
    if run["kind"] == "decision":
        return confirmation_decision(plan, batch_root, directory, synthetic=data["synthetic"])
    if run["kind"] == "scoring_decision":
        return scoring_decision(plan, batch_root, directory, synthetic=data["synthetic"])
    torch.set_num_threads(plan["execution"]["cpu_threads_per_worker"])
    seed_all(run["seed"])
    steps = min(run["steps"], 1) if smoke else run["steps"]
    problems = min(2, len(eligible_groups(data["samples"], data["split"]))) if smoke else problems
    identity = {"run": digest(run), "source": source_hash(), "split": data["split_hash"], "data": data["prepared_hash"],
                "vocabulary": data["vocabulary_hash"], "device": str(device), "steps": steps, "problems": problems,
                "smoke": smoke, "plan": digest(plan), "memory_gib": memory_gib,
                "runtime": {name: importlib.metadata.version(name) for name in ("torch", "torch-geometric", "numpy", "jsonschema")}}
    if (directory / "checkpoint.pt").exists() and not resume:
        raise ValueError("Existing checkpoint: use compatible resume or a new batch directory")
    start = time.perf_counter()
    if run["kind"] == "control":
        result = control_evaluation(data, run["control"])
        result.update(status="completed", id=run["id"], steps=0, parameters=0, elapsed_seconds=time.perf_counter() - start, identity=identity)
        write_json(directory / "result.json", result)
        return result
    vocabulary = Vocabulary(data["vocabulary"])
    model = FunctionEncoder(len(vocabulary.tokens), run["config"]).to(device)
    scorer = None
    frozen = run["kind"] in ("scorer", "block_rerank")
    if frozen:
        dependency_id = run.get("encoder_dependency", "E1")
        dependency = load_checkpoint(batch_root / dependency_id / "checkpoint.pt", device=device)
        if any(dependency["identity"][k] != identity[k] for k in ("source", "split", "data", "vocabulary", "smoke", "device", "problems", "plan", "runtime")):
            raise ValueError("Incompatible encoder dependency")
        if dependency["step"] != dependency["identity"]["steps"] or dependency["config"] != run["config"]:
            raise ValueError("Incomplete or incompatible encoder dependency")
        model.load_state_dict(dependency["model"])
        model.eval().requires_grad_(False)
        if run["kind"] == "scorer":
            scorer = SymmetricMLP(run["config"]["dim"]).to(device)
    trainable = scorer if scorer is not None else model
    optimizer = torch.optim.AdamW(trainable.parameters(), lr=plan["training"]["lr"], weight_decay=plan["training"]["weight_decay"])
    sampler = PairSampler(data["samples"], data["split"], run["seed"], problems)
    step, elapsed, losses, draws = 0, 0., [], []
    if resume:
        checkpoint = load_checkpoint(directory / "checkpoint.pt", expected=identity, device=device)
        model.load_state_dict(checkpoint["model"])
        if scorer is not None:
            scorer.load_state_dict(checkpoint["scorer"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        step, elapsed, losses, draws = checkpoint["step"], checkpoint["elapsed_seconds"], checkpoint["losses"], checkpoint["draw_hashes"]
        restore_rng(checkpoint["rng"])
    def save():
        save_torch(directory / "checkpoint.pt", {"version": "te01.checkpoint.v1", "identity": identity,
                   "config": run["config"], "kind": run["kind"], "vocabulary": vocabulary.tokens, "model": model.state_dict(),
                   "scorer": scorer.state_dict() if scorer is not None else None, "optimizer": optimizer.state_dict(),
                   "rng": rng_state(), "step": step, "elapsed_seconds": elapsed + time.perf_counter() - start,
                   "losses": losses, "draw_hashes": draws})
    if str(device).startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    model.train(not frozen)
    while step < steps:
        if elapsed + time.perf_counter() - start >= run["timeout_seconds"]:
            break
        rows = sampler.draw(step)
        batch = make_batch(rows, vocabulary, run["config"], device)
        optimizer.zero_grad(set_to_none=True)
        if frozen:
            with torch.no_grad():
                z = model(batch)
            loss = scorer_loss(scorer, z, rows)
        else:
            loss = contrastive_loss(model(batch), rows, plan["training"]["temperature"])
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite loss")
        loss.backward()
        grad = torch.nn.utils.clip_grad_norm_(trainable.parameters(), plan["training"]["gradient_clip"])
        if not torch.isfinite(grad) or float(grad) <= 0:
            raise RuntimeError("Nonfinite or zero gradient")
        optimizer.step()
        step += 1
        losses.append(float(loss.detach()))
        draws.append(digest([i["id"] for i in rows]))
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > memory_gib * 2**30:
            raise MemoryError("Worker host-memory cap exceeded")
        if step % plan["training"]["checkpoint_every"] == 0:
            save()
    save()
    if step != steps:
        result = {"id": run["id"], "status": "incomplete_time_cap", "steps": step, "identity": identity}
        write_json(directory / "result.json", result)
        return result
    model.eval()
    if scorer is not None:
        scorer.eval()
    embeddings, blocks, encode_ms, query_times = encode_rows(model, data, vocabulary, device, "val",
                                                           with_blocks=run["kind"] == "block_rerank", memory_gib=memory_gib)
    if scorer is not None:
        scorer.cpu()  # One explicit ranking device for controls and learned scorers.
    scoring, base = score_functions(embeddings, blocks, scorer, run["kind"] == "block_rerank")
    with torch.no_grad():
        result = evaluate(data, scoring, base_score_fn=base)
    add_encoding_latency(result, query_times)
    result.update(id=run["id"], seed=run["seed"], status="completed", steps=step, identity=identity, config=run["config"],
                  checkpoint_sha256=file_hash(directory / "checkpoint.pt"),
                  parameters=sum(p.numel() for p in model.parameters()),
                  scorer_parameters=sum(p.numel() for p in scorer.parameters()) if scorer else 0,
                  loss_first=losses[0] if losses else None, loss_last=losses[-1] if losses else None,
                  draw_hashes=draws, encoding_ms=encode_ms, elapsed_seconds=elapsed + time.perf_counter() - start,
                  cpu_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                  cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(device) if str(device).startswith("cuda") else None)
    export_encoder(directory / "encoder.pt", model, vocabulary, result["threshold"] if not frozen else None,
                   data.get("binding_contract"), data.get("protocol"))
    write_json(directory / "result.json", result)
    return result


def select_candidate(plan, batch_root, directory, synthetic=False):
    selection = plan["selection"]
    candidates = []
    for rid in selection["candidates"]:
        path = batch_root / rid / "result.json"
        if not path.is_file():
            continue
        result = read_json(path)
        spec = next(r for r in plan["runs"] if r["id"] == rid)
        if result.get("identity", {}).get("source") != source_hash() or result.get("config") != spec["config"]:
            raise ValueError("Selection artifact source/config mismatch")
        if not synthetic and result.get("steps") != spec["steps"]:
            continue
        if result.get("status") != "completed" or result["steps"] != result["identity"]["steps"]:
            continue
        coverage = result.get("eligible_slice_coverage",result["coverage"]["fraction"])
        if coverage < selection["minimum_coverage"] or result["metrics"]["mrr"] is None:
            continue
        if result["query_latency_ms"]["p95"] > selection["maximum_query_p95_ms"]:
            continue
        candidates.append(result)
    if not candidates:
        raise ValueError("No complete eligible candidate; no defensible architecture selection")
    if len({(r["identity"]["data"], r["identity"]["split"], r["identity"]["steps"], tuple(r["draw_hashes"])) for r in candidates}) != 1:
        raise ValueError("Selection requires identical inputs and training exposure")
    best = max(r["metrics"]["mrr"] for r in candidates)
    near = [r for r in candidates if r["metrics"]["mrr"] >= best - selection["near_tie_mrr"]]
    selected = min(near, key=lambda r: (r["parameters"], r["id"]))
    controls = [read_json(batch_root / rid / "result.json") for rid in ("C0", "C1")]
    learned_gain = selected["metrics"]["mrr"] > max(r["metrics"]["mrr"] for r in controls) + selection["near_tie_mrr"]
    result = {"id": "SELECT", "status": "completed", "selected": selected["id"], "synthetic": synthetic,
              "learned_gain_over_controls": learned_gain, "partition": "val", "architecture_winner": None,
              "decision": "mechanics_only" if synthetic else "await_paired_confirmation" if learned_gain else "no_evidence_of_learned_gain",
              "data_hash": selected["identity"]["data"], "source_hash": source_hash(),
              "candidate_results": {r["id"]: digest(r) for r in candidates}}
    write_json(directory / "result.json", result)
    return result


def add_encoding_latency(result, query_times):
    timings = []
    for row in result["queries"]:
        if not row["exclusion"]:
            row["encoding_ms"] = query_times[row["id"]]
            row["query_latency_ms"] = row["encoding_ms"] + row["latency_ms"]
            timings.append(row["query_latency_ms"])
    timings.sort()
    result["query_latency_ms"] = {"median": timings[len(timings) // 2] if timings else None,
                                  "p95": timings[min(len(timings) - 1, int(.95 * len(timings)))] if timings else None,
                                  "scope": "query encoding + CPU ranking; reference index construction reported separately"}


def confirmation_decision(plan, batch_root, directory, synthetic=False):
    screen = read_json(batch_root / "SELECT/result.json")
    pairs = []
    for seed in (29, 43):
        a = read_json(batch_root / f"CONF_E1_{seed}/result.json")
        b = read_json(batch_root / f"CONF_selected_{seed}/result.json")
        for r in (a, b):
            if r["status"] != "completed" or r["steps"] != r["identity"]["steps"] or r["identity"]["data"] != screen["data_hash"] or r["seed"] != seed or r["identity"]["source"] != source_hash():
                raise ValueError("Confirmation incomplete or input/seed mismatch")
        if a["draw_hashes"] != b["draw_hashes"]:
            raise ValueError("Confirmation exposure differs")
        pairs.append((a, b))
    delta = sum(b["metrics"]["mrr"] - a["metrics"]["mrr"] for a, b in pairs) / len(pairs)
    epsilon = plan["selection"]["near_tie_mrr"]
    stable = all(b["metrics"]["mrr"] >= a["metrics"]["mrr"] - epsilon for a, b in pairs)
    prefer_candidate = stable and (delta > epsilon or (abs(delta) <= epsilon and pairs[0][1]["parameters"] < pairs[0][0]["parameters"]))
    selected = screen["selected"] if prefer_candidate else "E1"
    config = next(r["config"] for r in plan["runs"] if r["id"] == selected)
    chosen_results = [b if prefer_candidate else a for a, b in pairs]
    controls = [read_json(batch_root / rid / "result.json")["metrics"]["mrr"] for rid in ("C0", "C1")]
    gain = sum(r["metrics"]["mrr"] for r in chosen_results) / len(chosen_results) > max(controls) + epsilon
    qualified = all(r.get("eligible_slice_coverage",r["coverage"]["fraction"]) >= plan["selection"]["minimum_coverage"] and
                    r["query_latency_ms"]["p95"] <= plan["selection"]["maximum_query_p95_ms"] for r in chosen_results)
    weak = plan.get("protocol") == "gcc_cross_variant_weak_v1"
    # TE02 locks a provisional evaluated candidate even when cheap controls win;
    # empirical advantage remains a separate, explicit claim.
    locked = not synthetic and qualified and (weak or (screen["learned_gain_over_controls"] and gain))
    result = {"id": "DECIDE", "status": "completed", "partition": "val", "synthetic": synthetic,
              "selected": selected, "architecture_config_hash": digest(config), "architecture_locked": locked,
              "larger_run_candidate": selected if locked else None, "paired_mean_mrr_delta": delta,
              "confirmation_gain_over_controls": gain, "confirmation_coverage_latency_qualified": qualified,
              "data_hash": screen["data_hash"], "source_hash": source_hash(),
              "protocol": plan.get("protocol", "independent_solutions"),
              "learned_advantage_established": bool(screen["learned_gain_over_controls"] and gain and qualified),
              "decision": "mechanics_only" if synthetic else "provisional_weak_label_candidate_locked" if weak and locked else "architecture_selected_for_larger_run" if locked else "no_evidence_of_learned_gain"}
    write_json(directory / "result.json", result)
    return result


def scoring_decision(plan, batch_root, directory, synthetic=False):
    decision = read_json(batch_root/"DECIDE/result.json")
    candidates=[]
    evidence={}
    for rid,kind in (("S1","mlp"),("S2","block")):
        if not all((batch_root/f"{rid}_CONF_{s}/result.json").is_file() for s in (29,43)):
            evidence[kind]={"confirmed":False,"reason":"confirmation omitted by declared budget cut"}
            continue
        delta=[]
        for seed in (29,43):
            anchor=read_json(batch_root/f"CONF_E1_{seed}/result.json")
            scored=read_json(batch_root/f"{rid}_CONF_{seed}/result.json")
            if scored["status"]!="completed" or scored["identity"]["data"]!=anchor["identity"]["data"] or scored["seed"]!=seed:
                raise ValueError("Scoring confirmation incomplete or mismatched")
            delta.append(scored["metrics"]["mrr"]-anchor["metrics"]["mrr"])
        evidence[kind]={"anchor":"E1 cosine only", "paired_mrr_deltas":delta,"mean_delta":sum(delta)/2,
                        "confirmed":min(delta)>=0 and sum(delta)/2>plan["selection"]["near_tie_mrr"]}
        if evidence[kind]["confirmed"]:
            candidates.append((sum(delta)/2,kind,rid))
    chosen=max(candidates,default=(0.,"cosine",None))
    mode=chosen[1] if decision["selected"]=="E1" else "cosine"
    result={**decision,"id":"SCORER_DECIDE","scorer_kind":mode,"scoring_evidence":evidence,
            "scorer_scope":"E1; no claim of improvement for other encoders", "synthetic":synthetic,
            "selected_checkpoint_run":chosen[2] if mode!="cosine" else decision["selected"]}
    write_json(directory/"result.json",result)
    return result


def evaluate_checkpoint(checkpoint_path, data, *, partition="val", frozen_selection=None, threshold=None,
                        validation_result=None, device="cpu"):
    if partition == "test":
        if not frozen_selection or frozen_selection.get("partition") != "val" or frozen_selection.get("data_hash") != data["prepared_hash"] or not frozen_selection.get("architecture_locked") or frozen_selection.get("source_hash") != source_hash():
            raise ValueError("Final test requires frozen validation selection bound to this data")
        if threshold is None:
            raise ValueError("Final test requires the saved validation threshold")
    checkpoint = load_checkpoint(checkpoint_path, device=device)
    if checkpoint["identity"]["data"] != data["prepared_hash"] or checkpoint["identity"]["source"] != source_hash():
        raise ValueError("Checkpoint/data/source mismatch")
    if checkpoint["step"] != checkpoint["identity"]["steps"]:
        raise ValueError("Incomplete checkpoint cannot be evaluated for selection")
    if partition == "test":
        if digest(checkpoint["config"]) != frozen_selection["architecture_config_hash"]:
            raise ValueError("Final test checkpoint is not the frozen architecture")
        kind="mlp" if checkpoint["kind"]=="scorer" else "block" if checkpoint["kind"]=="block_rerank" else "cosine"
        if "scorer_kind" in frozen_selection and frozen_selection["scorer_kind"]!=kind:
            raise ValueError("Final test checkpoint is not the frozen scoring rule")
        if not validation_result or validation_result.get("checkpoint_sha256") != file_hash(checkpoint_path) or validation_result.get("partition") != "val" or validation_result.get("threshold") != threshold:
            raise ValueError("Validation threshold must belong to this exact checkpoint")
    vocabulary = Vocabulary(checkpoint["vocabulary"])
    model = FunctionEncoder(len(vocabulary.tokens), checkpoint["config"]).to(device)
    model.load_state_dict(checkpoint["model"])
    scorer = None
    if checkpoint["scorer"] is not None:
        scorer = SymmetricMLP(checkpoint["config"]["dim"]).to(device)
        scorer.load_state_dict(checkpoint["scorer"])
        scorer.eval()
    embeddings, blocks, _, query_times = encode_rows(model, data, vocabulary, device, partition,
                                                   with_blocks=checkpoint["kind"] == "block_rerank")
    if scorer is not None:
        scorer.cpu()
    scoring, base = score_functions(embeddings, blocks, scorer, checkpoint["kind"] == "block_rerank")
    with torch.no_grad():
        result = evaluate(data, scoring, partition=partition, threshold=threshold, base_score_fn=base)
    add_encoding_latency(result, query_times)
    result["checkpoint_sha256"] = file_hash(checkpoint_path)
    return result
