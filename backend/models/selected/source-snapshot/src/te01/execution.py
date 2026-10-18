"""Deadline-aware dry planning and a bounded, process-group local executor."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import torch

from .data import eligibility
from .io import ROOT, digest, file_hash, output_path, read_json, source_hash, write_json


def validate_plan(plan):
    runs = plan["runs"]
    by_id = {r["id"]: r for r in runs}
    if len(by_id) != len(runs):
        raise ValueError("Duplicate experiment IDs")
    done = set()
    while len(done) < len(runs):
        ready = [r for r in runs if r["id"] not in done and set(r["depends_on"]) <= done]
        if not ready:
            raise ValueError("Missing dependency or cycle")
        done.update(r["id"] for r in ready)
    for run in runs:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", run["id"]):
            raise ValueError("Unsafe experiment ID")
        if run["timeout_seconds"] <= 0 or run["steps"] < 0:
            raise ValueError("Invalid step/time cap")
        if run["kind"] not in ("encoder", "control", "scorer", "block_rerank", "selection", "confirmation", "decision", "scoring_decision"):
            raise ValueError("Unimplemented runnable kind")
    return by_id


def sizing(data, plan):
    if data.get("protocol") == "gcc_cross_variant_weak_v1":
        from .objectives import PairSampler
        cap = plan["sizing"]
        draw_counts = {}
        for run in plan["runs"]:
            if run["kind"] in ("encoder","confirmation","scorer"):
                draw_counts[run["seed"]] = max(draw_counts.get(run["seed"],0),run["steps"])
        for p in cap["problems_choices"]:
            maxima = {"blocks":0,"instructions":0,"block_attention_cells":0,"graph_attention_cells":0}
            for seed,steps in sorted(draw_counts.items()):
                sampler = PairSampler(data["samples"],data["split"],seed,p)
                for step in range(steps):
                    graphs = [r["graph"] for r in sampler.draw(step)]
                    counts = [len(g["blocks"]) for g in graphs]
                    blocks = sum(counts)
                    lengths = [len(b) for g in graphs for b in g["blocks"]]
                    stats = {"blocks":blocks,"instructions":sum(lengths),"block_attention_cells":blocks*max(lengths)**2,
                             "graph_attention_cells":len(graphs)*max(counts)**2}
                    for key,value in stats.items():
                        maxima[key]=max(maxima[key],value)
            if (maxima["blocks"]<=cap["max_batch_blocks"] and maxima["instructions"]<=cap["max_batch_instructions"] and
                maxima["block_attention_cells"]<=cap["max_block_attention_cells"] and maxima["graph_attention_cells"]<=cap["max_graph_attention_cells"]):
                return {"problems":p,"implementations":2*p,"measured_tensor_dimensions":maxima,"planned_draws":{str(k):v for k,v in draw_counts.items()},
                        "rule":"All planned deterministic draws/seeds; common FP32 batch for every variant; no OOM adaptation"}
        raise ValueError("Actual planned batches exceed frozen TE02 limits")
    graphs = [i["graph"] for i in data["samples"] if not i["exclusion"]]
    if not graphs:
        raise ValueError("No usable graphs")
    blocks = max(len(g["blocks"]) for g in graphs)
    ins = max(sum(map(len, g["blocks"])) for g in graphs)
    per_block = max(len(b) for g in graphs for b in g["blocks"])
    cap = plan["sizing"]
    for p in cap["problems_choices"]:
        if (2 * p * blocks <= cap["max_batch_blocks"] and 2 * p * ins <= cap["max_batch_instructions"]
                and 2 * p * blocks * per_block**2 <= cap["max_block_attention_cells"]
                and 2 * p * blocks**2 <= cap["max_graph_attention_cells"]):
            return {"problems": p, "implementations": 2 * p, "max_blocks": blocks,
                    "max_instructions": ins, "max_instructions_per_block": per_block,
                    "rule": "conservative maxima; fixed for every anchor, not measured memory/throughput"}
    raise ValueError("Corpus dimensions exceed fixed shared batch presets; no silent truncation/OOM adaptation")


def schedule(runs, concurrency):
    slots = [0.] * concurrency
    finished, result = {}, []
    pending = list(runs)
    while pending:
        ready = [r for r in pending if set(r["depends_on"]) <= finished.keys()]
        if not ready:
            raise ValueError("Unsatisfied scheduling dependency")
        run = min(ready, key=lambda r: (max([finished[d] for d in r["depends_on"]] or [0]), r["id"]))
        slot = min(range(concurrency), key=lambda i: slots[i])
        start = max(slots[slot], max([finished[d] for d in run["depends_on"]] or [0]))
        end = start + run["timeout_seconds"]
        slots[slot], finished[run["id"]] = end, end
        result.append({"id": run["id"], "slot": slot, "start_cap_seconds": start, "end_cap_seconds": end})
        pending.remove(run)
    return result, max(slots)


def dry_plan(plan, *, data=None, devices=("cpu",), concurrency=1, budget=None, now=None, smoke=False):
    validate_plan(plan)
    if concurrency < 1 or concurrency > plan["execution"]["max_concurrency"] or concurrency > len(devices):
        raise ValueError("Concurrency must be 1..4 and no greater than independent device slots")
    if len(set(devices)) != len(devices):
        raise ValueError("Duplicate devices would oversubscribe a GPU")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Dispatch time must include timezone")
    deadline = datetime.fromisoformat(plan["deadline"])
    remaining = (deadline - now).total_seconds()
    reserve = sum(plan["reserve_seconds"].values())
    available = max(0., remaining - reserve)
    if budget:
        for k in ("max_wall_seconds", "max_gpu_hours", "memory_gib", "gpu_memory_gib"):
            if type(budget.get(k)) not in (float, int) or not math.isfinite(budget[k]) or budget[k] <= 0:
                raise ValueError("Budget requires finite positive " + k)
        available = min(available, float(budget["max_wall_seconds"]))
    runs = [dict(r) for r in plan["runs"]]
    for r in runs:
        # Selection waits for every retained screen/scoring node, not only anchors.
        if r.get("optional_dependencies"):
            r["depends_on"] = r["depends_on"] + r.get("optional_dependencies", [])
    cut = []
    def caps():
        waves, wall = schedule(runs, concurrency)
        gpu_hours = sum(r["timeout_seconds"] for r in runs) / 3600
        return waves, wall, gpu_hours
    waves, wall, gpu_hours = caps()
    while not smoke and (wall > available or (budget and gpu_hours > budget["max_gpu_hours"])):
        optional = [r for r in runs if r.get("cut_priority", 0) > 0]
        if not optional:
            break
        victim = max(optional, key=lambda r: (r["cut_priority"], r["id"]))
        cut.append(victim["id"])
        runs.remove(victim)
        for r in runs:
            r["depends_on"] = [d for d in r["depends_on"] if d != victim["id"]]
        waves, wall, gpu_hours = caps()
    blockers = []
    shape = None
    if data is None:
        blockers.append("Bind local producer catalog and prepare immutable inputs")
    else:
        blockers.extend(eligibility(data["samples"], data["split"], data["synthetic"]))
        try:
            shape = sizing(data, plan)
        except ValueError as e:
            blockers.append(str(e))
        if len(data["samples"]) > plan["sizing"]["max_catalog_items"]:
            blockers.append("Catalog item cap exceeded")
        if not smoke and data["synthetic"]:
            blockers.append("Synthetic data cannot authorize scientific execution")
    if not smoke:
        if budget is None:
            blockers.append("Explicit hardware/resource budget file required")
        else:
            for k in ("max_wall_seconds", "max_gpu_hours", "memory_gib", "gpu_memory_gib"):
                if not isinstance(budget.get(k), (float, int)) or not math.isfinite(budget[k]) or budget[k] <= 0:
                    raise ValueError("Budget requires finite positive " + k)
            if budget.get("hardware_confirmed") is not True:
                blockers.append("Hardware capacity must be confirmed at binding")
            if budget["memory_gib"] < plan["sizing"]["min_ram_gib"] or budget["gpu_memory_gib"] < plan["sizing"]["min_gpu_memory_gib"]:
                blockers.append("Minimum RAM/VRAM budget not met")
        if wall > available:
            blockers.append("Remaining dispatch time cannot fit mandatory comparisons plus reserves")
        if budget and gpu_hours > budget["max_gpu_hours"]:
            blockers.append("GPU-hour cap cannot fit mandatory comparisons")
        if any(not d.startswith("cuda:") for d in devices):
            blockers.append("Scientific batch requires explicit independent CUDA device IDs")
    for d in devices:
        if d == "cpu":
            continue
        try:
            index = int(d.split(":")[1]) if d.startswith("cuda:") else -1
            if index < 0 or index >= torch.cuda.device_count():
                raise ValueError()
            if budget and torch.cuda.get_device_properties(index).total_memory < budget["gpu_memory_gib"] * 2**30:
                blockers.append("Declared VRAM budget exceeds visible device " + d)
        except (ValueError, IndexError):
            blockers.append("Unavailable device " + d)
    return {"version": "te01.dispatch.v1", "now": now.isoformat(), "deadline": plan["deadline"],
            "remaining_seconds": remaining, "reserved_seconds": reserve, "available_seconds": available,
            "wall_cap_seconds": wall, "gpu_hour_cap": gpu_hours, "caps_are_not_throughput_measurements": True,
            "runs": runs, "waves": waves, "cut": cut, "blockers": blockers,
            "devices": list(devices), "concurrency": concurrency, "sizing": shape,
            "plan_hash": digest(plan), "source_hash": source_hash(), "data_hash": data["prepared_hash"] if data else None,
            "budget_hash": digest(budget), "smoke": smoke}


def stop_group(process):
    # Kill descendants even if the direct child has already exited.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=.25)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def execute_jobs(jobs, directory, devices, concurrency, command_builder, *, max_seconds, resume=False, memory_gib=None, max_device_seconds=None, cpu_concurrency=0):
    """No shell, transport, service or cluster. command_builder is internal/test-only."""
    directory = output_path(directory / "summary.json").parent
    started = time.monotonic()
    slot_devices = list(devices[:concurrency]) + ["cpu"] * cpu_concurrency
    previous = read_json(directory / "summary.json") if resume and (directory / "summary.json").is_file() else {}
    previous_elapsed = previous.get("cumulative_elapsed_seconds", 0.)
    previous_device = previous.get("cumulative_device_seconds", 0.)
    device_seconds = 0.
    by_id = {j["id"]: j for j in jobs}
    if len(by_id) != len(jobs):
        raise ValueError("Duplicate jobs")
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", j["id"]) for j in jobs):
        raise ValueError("Unsafe job ID")
    if any(j.get("resource","gpu") not in ("cpu","gpu") for j in jobs):
        raise ValueError("Unknown worker resource")
    pending, running, results = list(jobs), {}, {}
    try:
        while pending or running:
            consumed_device = previous_device + device_seconds + sum(time.monotonic() - s[2] for s in running.values())
            batch_limit = time.monotonic() - started >= max_seconds or (max_device_seconds is not None and consumed_device >= max_device_seconds)
            if batch_limit:
                for j in pending:
                    results[j["id"]] = {"status": "blocked_batch_deadline"}
                    write_json(directory / j["id"] / "status.json", results[j["id"]])
                pending.clear()
            for rid, state in list(running.items()):
                p, job, start, slot, log = state
                timed_out = time.monotonic() - start >= job.get("remaining_timeout_seconds", job["timeout_seconds"]) or batch_limit
                rss = 0
                try:
                    for line in Path(f"/proc/{p.pid}/status").read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1]) * 1024
                except FileNotFoundError:
                    pass
                memory_limit = memory_gib is not None and rss > memory_gib * 2**30
                if p.poll() is None and not timed_out and not memory_limit:
                    continue
                stop_group(p)
                log.close()
                result_path = directory / rid / "result.json"
                try:
                    payload = read_json(result_path) if result_path.is_file() else {}
                except (ValueError, OSError):
                    payload = {"status": "malformed_result"}
                status = "memory_limit" if memory_limit else "timeout" if timed_out else "completed" if p.returncode == 0 and payload.get("status") == "completed" else "failed"
                duration = time.monotonic() - start
                device_seconds += duration
                result = {"status": status, "returncode": p.returncode, "elapsed_seconds": time.monotonic() - start,
                          "cumulative_elapsed_seconds": job.get("consumed_seconds", 0.) + duration,
                          "device": slot_devices[slot], "worker_status": payload.get("status"),
                          "result_sha256": file_hash(result_path) if result_path.is_file() else None}
                write_json(directory / rid / "status.json", result)
                results[rid] = result
                del running[rid]
            for job in list(pending):
                if any(d in results and results[d]["status"] != "completed" for d in job["depends_on"]):
                    results[job["id"]] = {"status": "blocked_dependency"}
                    write_json(directory / job["id"] / "status.json", results[job["id"]])
                    pending.remove(job)
            free = [s for s in range(len(slot_devices)) if s not in {state[3] for state in running.values()}]
            ready = [j for j in pending if all(d in results and results[d]["status"] == "completed" for d in j["depends_on"])]
            for slot in free:
                compatible = [j for j in ready if (j.get("resource","gpu")=="cpu" if slot>=concurrency else j.get("resource","gpu")!="cpu" or not cpu_concurrency)]
                if not compatible:
                    continue
                job = compatible[0]
                ready.remove(job)
                rid = job["id"]
                out = output_path(directory / rid / "worker.log").parent
                # A completed run is reused only when batch identity was validated by the caller.
                if resume and (out / "status.json").is_file() and read_json(out / "status.json").get("status") == "completed":
                    status = read_json(out / "status.json")
                    if not (out / "result.json").is_file() or file_hash(out / "result.json") != status["result_sha256"]:
                        raise ValueError("Incompatible resume: completed result missing or modified")
                    prior_result = read_json(out / "result.json")
                    if "checkpoint_sha256" in prior_result and (not (out / "checkpoint.pt").is_file() or file_hash(out / "checkpoint.pt") != prior_result["checkpoint_sha256"]):
                        raise ValueError("Incompatible resume: completed checkpoint missing or modified")
                    results[rid] = status
                    pending.remove(job)
                    continue
                (out / "result.json").unlink(missing_ok=True)
                log = output_path(out / "worker.log").open("ab")
                try:
                    proc = subprocess.Popen(command_builder(job, out, slot_devices[slot]), cwd=ROOT,
                                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                except OSError as e:
                    log.close()
                    results[rid] = {"status": "launch_failed", "message": str(e)}
                    write_json(out / "status.json", results[rid])
                    pending.remove(job)
                    continue
                running[rid] = (proc, job, time.monotonic(), slot, log)
                pending.remove(job)
            if pending and not running and not any(all(d in results for d in j["depends_on"]) for j in pending):
                raise ValueError("Unresolvable dependency graph")
            if pending or running:
                time.sleep(.05)
    finally:
        for p, job, start, slot, log in running.values():
            stop_group(p)
            log.close()
            results[job["id"]] = {"status": "terminated_parent_exit"}
            device_seconds += time.monotonic() - start
            write_json(directory / job["id"] / "status.json", results[job["id"]])
        for job in pending:
            if job["id"] not in results:
                results[job["id"]] = {"status": "blocked_parent_exit"}
                write_json(directory / job["id"] / "status.json", results[job["id"]])
        summary = {"elapsed_seconds": time.monotonic() - started, "jobs": results,
                   "cumulative_elapsed_seconds": previous_elapsed + time.monotonic() - started,
                   "cumulative_device_seconds": previous_device + device_seconds,
                   "status": "completed" if len(results) == len(jobs) and all(r["status"] == "completed" for r in results.values()) else "failed"}
        write_json(directory / "summary.json", summary)
    return summary
