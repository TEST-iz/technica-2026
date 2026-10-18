"""Named TE02 protocol; candidate class variants are weak positives, not sources."""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from .assembly import ASSEMBLY_VERSION, FUNCTION_RE, convert_assembly, rebase_path
from .io import ROOT, digest, file_hash, read_json, write_json
from .representation import Excluded, Graph, Vocabulary, FEATURE_VERSION

PROTOCOL = "gcc_cross_variant_weak_v1"
SEED = 20261018
KNOWN = 50
UNKNOWN = 50
GALLERY = 512


def pair_allowed(a, b):
    if a.get("protocol") != PROTOCOL or b.get("protocol") != PROTOCOL:
        raise ValueError("Cannot mix supervision protocols")
    if any(a[k] == b[k] for k in ("id", "assembly_sha256", "identity")):
        return False
    if a["problem_id"] == b["problem_id"]:
        return a["variant_id"] != b["variant_id"]
    return a["parent_family"] != b["parent_family"]


def convert_catalog(root, *, workers=2):
    root = Path(root).absolute()
    complete = read_json(root / "COMPLETE.json")
    index = root / "combined_ready.jsonl"
    index_sha = file_hash(index)
    if index_sha != complete["combined_ready_sha256"]:
        raise ValueError("COMPLETE index checksum mismatch")
    rows = [json.loads(line) for line in index.read_text().splitlines()]
    if len(rows) != complete["combined_positive_candidates"]:
        raise ValueError("COMPLETE/index count mismatch")
    seen, tasks = set(), []
    for row in rows:
        p, relative = rebase_path(row["asm_path"], root)
        if relative in seen:
            raise ValueError("Duplicate authoritative index path")
        seen.add(relative)
        sha = file_hash(p)
        declarations = FUNCTION_RE.findall(p.read_text())
        tasks.append((row, p, relative, sha, declarations))
    def process(task):
        row, path, relative, sha, declarations = task
        parent = row["source"]
        variant = row["entry_class"] if row["scope"] == "split_variant" else "original_single"
        result = {"id": digest(relative)[:24], "problem_id": row["problem_group"], "protocol": PROTOCOL,
                  "source_id": parent, "producer_source_filename": parent, "source_sha256": None,
                  "independence_attested": None, "judge_validated": row["quality_validated_against_judge"],
                  "parent_family": parent, "lineage_id": parent, "variant_id": variant,
                  "source_locator": relative, "assembly_sha256": sha, "record_hash": sha,
                  "build_id": "producer_GCC_O0_version_unknown", "compiler": "gcc", "compiler_version": None,
                  "optimization": "-O0", "entry_class": row["entry_class"], "declared_functions": declarations,
                  "provenance": "combined_ready.jsonl; candidate labels; independently authored and judge correctness unknown",
                  "status": "FAILED", "exclusion": None, "graph": None, "identity": None,
                  "helper_count": None, "missing_helpers": None, "reasons": []}
        if row.get("training_positive_eligible") is not True:
            result["exclusion"] = "producer_ineligible"
        elif len(declarations) != 1:
            result["exclusion"] = "ambiguous_entry_multiple_declared_functions" if declarations else "no_declared_function"
        elif not variant:
            result["exclusion"] = "missing_variant_identity"
        else:
            try:
                record = convert_assembly(path, sha)
                result.update(graph=record["graph"], identity=record["identity"], status=record["status"], reasons=record["reasons"],
                              selected_function_symbol=record["selected_symbol"], object_sha256=record["object_sha256"])
                write_json(ROOT / ".cache/te02-records" / (sha + ".json"), record)
            except Excluded as e:
                result["exclusion"] = str(e)
        return result
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        samples = list(pool.map(process, tasks))
    before = dict(Counter(i["exclusion"] or i["status"] for i in samples))
    # Any family crossing labels is ambiguous; retain its full exclusion evidence.
    for field in ("parent_family", "assembly_sha256", "identity"):
        groups = defaultdict(list)
        for item in samples:
            if item.get(field) is not None:
                groups[item[field]].append(item)
        for group in groups.values():
            if len({i["problem_id"] for i in group}) > 1:
                for item in group:
                    if not item["exclusion"]:
                        item["exclusion"] = "cross_label_collision:" + field
    seen_identity, seen_assembly, seen_variant = set(), set(), set()
    for item in sorted(samples, key=lambda i: i["id"]):
        if item["exclusion"]:
            continue
        v = (item["problem_id"], item["parent_family"], item["variant_id"])
        if item["identity"] in seen_identity or item["assembly_sha256"] in seen_assembly or v in seen_variant:
            item["exclusion"] = "duplicate_view"
        seen_identity.add(item["identity"]); seen_assembly.add(item["assembly_sha256"]); seen_variant.add(v)
    return {"samples": samples, "index_sha256": index_sha, "complete_sha256": file_hash(root/"COMPLETE.json"),
            "conversion_seconds": time.perf_counter()-started, "before_deduplication": before,
            "coverage": dict(Counter(i["exclusion"] or i["status"] for i in samples))}


def make_split(samples):
    usable = defaultdict(list)
    all_problem = defaultdict(list)
    for s in samples:
        all_problem[s["problem_id"]].append(s)
        if not s["exclusion"]:
            usable[s["problem_id"]].append(s)
    multis = [p for p, items in usable.items() if len({i["variant_id"] for i in items}) >= 2]
    multis.sort(key=lambda p: digest([SEED, "known", p]))
    if len(multis) < 2*KNOWN+16:
        raise ValueError("Insufficient usable multi-variant problems for frozen TE02 protocol")
    val_known, test_known = set(multis[:KNOWN]), set(multis[KNOWN:2*KNOWN])
    unknown_pool = sorted((p for p in usable if p not in val_known|test_known), key=lambda p: digest([SEED,"unknown",p]))
    # Prefer singleton unknowns, preserving scarce candidate positives for training.
    unknown_pool.sort(key=lambda p: len(usable[p]) >= 2)
    if len(unknown_pool) < 2*UNKNOWN+GALLERY-KNOWN:
        raise ValueError("Insufficient unknown/distractor problems")
    val_unknown, test_unknown = set(unknown_pool[:UNKNOWN]), set(unknown_pool[UNKNOWN:2*UNKNOWN])
    held = val_known | test_known | val_unknown | test_unknown
    train_problems = set(usable)-held
    distractors = sorted(train_problems, key=lambda p: digest([SEED,"gallery",p]))[:GALLERY-KNOWN]
    if len(distractors) != GALLERY-KNOWN:
        raise ValueError("Fixed 512-problem gallery unavailable")
    reference_by_problem = {p: min(usable[p], key=lambda r: digest([SEED,"reference",r["id"]]))["id"] for p in usable}
    assignments = {}
    for p, items in all_problem.items():
        part = "val" if p in val_known|val_unknown else "test" if p in test_known|test_unknown else "train"
        for s in items:
            role = "train" if part == "train" else "unknown" if p in val_unknown|test_unknown else "reference" if s["id"] == reference_by_problem[p] else "query"
            assignments[s["id"]] = {"partition": part, "role": role}
    galleries = {part: [reference_by_problem[p] for p in sorted(known)] + [reference_by_problem[p] for p in distractors]
                 for part, known in (("val",val_known),("test",test_known))}
    split = {"version":"te02.split.v1","seed":SEED,"assignments":assignments,"blockers":[],
             "known_problems":{"val":sorted(val_known),"test":sorted(test_known)},
             "unknown_problems":{"val":sorted(val_unknown),"test":sorted(test_unknown)},
             "reference_by_problem":reference_by_problem,"galleries":galleries}
    validate_split(samples, split)
    return split


def validate_split(samples, split):
    if set(split["assignments"]) != {s["id"] for s in samples}:
        raise ValueError("Incomplete intended-set assignments")
    by_id = {s["id"]:s for s in samples}
    for field in ("problem_id","parent_family","assembly_sha256","identity"):
        groups = defaultdict(set)
        for s in samples:
            if not s["exclusion"] and s.get(field) is not None:
                groups[s[field]].add(split["assignments"][s["id"]]["partition"])
        if any(len(g)>1 for g in groups.values()):
            raise ValueError("TE02 split leakage:"+field)
    unknown = set(split["unknown_problems"]["val"]+split["unknown_problems"]["test"])
    for part, ids in split["galleries"].items():
        if len(ids)!=GALLERY or len(set(ids))!=GALLERY or len({by_id[i]["problem_id"] for i in ids})!=GALLERY:
            raise ValueError("Gallery must contain 512 distinct problems/references")
        for sid in ids:
            s = by_id[sid]
            if s["exclusion"] or s["problem_id"] in unknown or split["assignments"][sid]["partition"] not in (part,"train"):
                raise ValueError("Gallery contains excluded, unknown or other evaluation partition")
    for part in ("val","test"):
        known = split["known_problems"][part]
        if len(known)!=KNOWN or len(split["unknown_problems"][part])!=UNKNOWN:
            raise ValueError("Wrong evaluation allocation")
        for p in known:
            ref = by_id[split["reference_by_problem"][p]]
            if not any(not s["exclusion"] and s["problem_id"]==p and pair_allowed(ref,s) for s in samples):
                raise ValueError("Known evaluation problem has no nonduplicate class-variant query")


def prepare(root, output, *, workers=2):
    from .data import builder_hash
    result = convert_catalog(root, workers=workers)
    write_json(ROOT/".cache/te02-converted-catalog.json", result)
    samples = result["samples"]
    split = make_split(samples)
    training = [Graph(**s["graph"]) for s in samples if not s["exclusion"] and split["assignments"][s["id"]]["partition"]=="train"]
    vocab = Vocabulary.fit(training)
    usable = [s for s in samples if not s["exclusion"]]
    result.update(version="te02.prepared.v1", protocol=PROTOCOL, binding_contract=ASSEMBLY_VERSION,
                  feature_version=FEATURE_VERSION, feature_builder_hash=builder_hash(), synthetic=False,
                  split=split, split_hash=digest(split), galleries=split["galleries"],
                  vocabulary=vocab.tokens, vocabulary_hash=digest(vocab.tokens), blockers=[],
                  catalog_hash=digest([{k:s[k] for k in ("id","record_hash","problem_id","parent_family","variant_id")} for s in samples]),
                  diagnostics={"full_manifest":len(samples),"eligible_slice":len(usable),
                               "eligible_fraction":len(usable)/len(samples),"quality_validated_against_judge":False,
                               "source_independence":"unknown","reference_gallery_problems":GALLERY},
                  claims="GCC -O0 cross-variant retrieval under candidate labels; no independent-source or judge-equivalence claim")
    result["prepared_hash"]=digest(result)
    write_json(output,result)
    write_json(ROOT/"evidence/te02/entry-mapping-needed.json", {"required_mapping":"assembly_sha256 + producer class/source -> exact emitted solution function symbol; validate bounds before admission",
              "rows":[{k:s[k] for k in ("id","source_locator","assembly_sha256","problem_id","entry_class","declared_functions")} for s in samples if s["exclusion"]=="ambiguous_entry_multiple_declared_functions"]})
    summary = {k:result[k] for k in ("protocol","index_sha256","complete_sha256","conversion_seconds","before_deduplication","coverage","diagnostics","split_hash","prepared_hash")}
    summary["partition_roles"]=dict(Counter(a["partition"]+"/"+a["role"] for a in split["assignments"].values()))
    summary["usable_multivariant_problems"]=sum(len({s["variant_id"] for s in usable if s["problem_id"]==p})>=2 for p in {s["problem_id"] for s in usable})
    write_json(ROOT/"evidence/te02/binding-summary.json",summary)
    return summary
