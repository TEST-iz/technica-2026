"""Producer catalog, deterministic splits, eligibility, and train-only vocabulary."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re

from .io import ROOT, digest, file_hash, read_json, write_json
from .representation import Excluded, FEATURE_VERSION, Graph, TARGET, Vocabulary, convert

CATALOG_VERSION = "te01.catalog.v1"
SPLIT_SEED = 20261017


def builder_hash():
    return digest({name: file_hash(ROOT / name) for name in
                   ("src/te01/data.py", "src/te01/representation.py", "src/te01/assembly.py", "src/te01/weak_protocol.py", "fixtures/parser-record.schema.json")})


def load_catalog(path):
    path = Path(path).resolve()
    catalog = read_json(path)
    if catalog.get("version") != CATALOG_VERSION or type(catalog.get("synthetic")) is not bool:
        raise ValueError("Catalog version/synthetic declaration required")
    if catalog.get("target") != TARGET or catalog.get("compiler") != "clang" or catalog.get("optimization") != "-O0":
        raise ValueError("Only declared Clang -O0 and provisional TP01 target supported")
    if not catalog.get("compiler_version") or not catalog.get("provenance"):
        raise ValueError("Compiler version and producer provenance required")
    if len(catalog["items"]) > 100000:
        raise ValueError("Catalog exceeds 100000-item cap")
    items, seen = [], set()
    for row in catalog["items"]:
        required = ("id", "record", "record_sha256", "problem_id", "source_id", "source_sha256",
                    "lineage_id", "build_id", "provenance", "source_locator")
        if any(not isinstance(row.get(k), str) or not row[k] for k in required):
            raise ValueError("Missing catalog identity/provenance fields")
        if row["id"] in seen:
            raise ValueError("Duplicate sample ID")
        seen.add(row["id"])
        if any(not re.fullmatch(r"[0-9a-f]{64}", row[k]) for k in ("record_sha256", "source_sha256")):
            raise ValueError("Record and source hashes must be SHA256 hex")
        if row.get("independence_attested") is not True:
            raise ValueError("Producer must attest source lineage/independence")
        ranges = row.get("address_ranges")
        if not isinstance(ranges, list) or any(not isinstance(r, list) or len(r) != 2 or
                any(type(x) is not int for x in r) or r[0] < 0 or r[0] >= r[1] for r in ranges):
            raise ValueError("Explicit complete loaded-image address ranges required")
        if not catalog["synthetic"] and (not ranges or row.get("address_ranges_complete") is not True):
            raise ValueError("Real records require complete loaded-image address ranges")
        record_path = (path.parent / row["record"]).resolve()
        allowed = (ROOT, ROOT.parent / "parser", ROOT.parent / "inputs")
        if not any(record_path.is_relative_to(p) for p in allowed):
            raise ValueError("Record must be locally bound inside technica_work permitted roots")
        if record_path.stat().st_size > 16 * 2**20:
            raise ValueError("Record exceeds 16 MiB input cap")
        if file_hash(record_path) != row["record_sha256"]:
            raise ValueError("Record hash mismatch")
        record = read_json(record_path)
        if row.get("selected_function_id") != record.get("entry_function_id"):
            raise ValueError("Producer selected-function association does not match record")
        item = {k: row[k] for k in ("id", "problem_id", "source_id", "source_sha256", "lineage_id", "build_id", "provenance", "source_locator")}
        item.update(status=record.get("status", "INVALID"), record_hash=row["record_sha256"],
                    exclusion=None, graph=None, identity=None, helper_count=0, helpers=[], missing_helpers=0)
        try:
            bundle = convert(record, address_ranges=ranges)
            item.update(graph=bundle.entry.as_json(), identity=bundle.entry.identity(),
                        helper_count=len(bundle.helpers), helpers=[g.as_json() for g in bundle.helpers], missing_helpers=bundle.missing_helpers)
        except Excluded as e:
            item["exclusion"] = str(e)
        items.append(item)
    if not items:
        raise ValueError("Empty intended catalog")
    return catalog, items


def quarantine_duplicates(items):
    # Conflicts and producer lineage relationships are checked before any split.
    for field in ("source_sha256", "source_id", "lineage_id", "identity"):
        groups = defaultdict(list)
        for item in items:
            if item[field] is not None:
                groups[item[field]].append(item)
        for group in groups.values():
            if len({i["problem_id"] for i in group}) > 1:
                for i in group:
                    i["exclusion"] = "conflicting_labels:" + field
    seen_sources, seen_source_ids, seen_normalized = set(), set(), set()
    for item in sorted(items, key=lambda x: x["id"]):
        if item["exclusion"]:
            continue
        if item["source_sha256"] in seen_sources or item["source_id"] in seen_source_ids or item["identity"] in seen_normalized:
            item["exclusion"] = "duplicate_source_or_normalized"
        seen_sources.add(item["source_sha256"])
        seen_source_ids.add(item["source_id"])
        seen_normalized.add(item["identity"])


def make_split(items, synthetic=False):
    problems = sorted({i["problem_id"] for i in items}, key=lambda p: digest([SPLIT_SEED, p]))
    # Fixed minimum evaluation allocations, remaining problems go to training.
    known, unknown, min_train = (2, 2, 2) if synthetic else (10, 20, 8)
    if len(problems) < min_train + 2 * (known + unknown):
        return {"version": "te01.split.v1", "seed": SPLIT_SEED, "assignments": {},
                "blockers": [f"Need >= {min_train + 2 * (known + unknown)} distinct problems; singleton fallback is diagnostics only"]}
    ntrain = len(problems) - 2 * (known + unknown)
    assignments = {}
    by_problem = defaultdict(list)
    for item in items:
        by_problem[item["problem_id"]].append(item)
    for n, problem in enumerate(problems):
        rows = by_problem[problem]
        if n < ntrain:
            partition, category = "train", "train"
        else:
            index = n - ntrain
            partition = "val" if index < known + unknown else "test"
            category = "known" if index % (known + unknown) < known else "unknown"
        usable = [i for i in rows if not i["exclusion"]]
        lineages = sorted({i["lineage_id"] for i in usable}, key=lambda s: digest([SPLIT_SEED, s]))
        ref_lineage = lineages[0] if lineages else None
        for row in rows:
            role = category
            if category == "known":
                role = "reference" if row["lineage_id"] == ref_lineage else "query"
            assignments[row["id"]] = {"partition": partition, "role": role}
    result = {"version": "te01.split.v1", "seed": SPLIT_SEED, "assignments": assignments, "blockers": []}
    validate_split(items, result)
    return result


def validate_split(items, split):
    if split.get("version") == "te02.split.v1":
        from .weak_protocol import validate_split as validate_weak
        return validate_weak(items, split)
    assignments = split["assignments"]
    if set(assignments) != {i["id"] for i in items}:
        raise ValueError("Split must cover the entire intended set")
    for field in ("problem_id", "source_sha256", "source_id", "lineage_id", "identity"):
        seen = defaultdict(set)
        for i in items:
            if i[field] is not None and not i["exclusion"]:
                seen[i[field]].add(assignments[i["id"]]["partition"])
        if any(len(parts) > 1 for parts in seen.values()):
            raise ValueError("Split leakage:" + field)
    for i in items:
        a = assignments[i["id"]]
        if a["partition"] not in ("train", "val", "test") or a["role"] not in ("train", "reference", "query", "unknown"):
            raise ValueError("Unknown split/role")
        if (a["partition"] == "train") != (a["role"] == "train"):
            raise ValueError("Training role/partition mismatch")
    for part in ("val", "test"):
        refs = [i for i in items if assignments[i["id"]] == {"partition": part, "role": "reference"} and not i["exclusion"]]
        queries = [i for i in items if assignments[i["id"]]["partition"] == part and assignments[i["id"]]["role"] in ("query", "unknown") and not i["exclusion"]]
        for q in queries:
            for r in refs:
                if q["lineage_id"] == r["lineage_id"] or q["source_sha256"] == r["source_sha256"]:
                    raise ValueError("Query/reference lineage leakage")
                if assignments[q["id"]]["role"] == "unknown" and q["problem_id"] == r["problem_id"]:
                    raise ValueError("Unknown query has reference")


def eligible_groups(items, split):
    by_problem = defaultdict(lambda: defaultdict(list))
    for i in items:
        a = split["assignments"].get(i["id"])
        if not i["exclusion"] and a == {"partition": "train", "role": "train"}:
            group = i["variant_id"] if i.get("protocol") == "gcc_cross_variant_weak_v1" else i["lineage_id"]
            by_problem[i["problem_id"]][group].append(i)
    return {p: dict(lineages) for p, lineages in sorted(by_problem.items()) if len(lineages) >= 2}


def eligibility(items, split, synthetic=False):
    blockers = list(split["blockers"])
    if blockers:
        return blockers
    minimum = 2 if synthetic else 8
    if len(eligible_groups(items, split)) < minimum:
        blockers.append(f"Need {minimum} training problems with >=2 independent nonduplicate lineages")
    for part in ("val", "test"):
        refs = [i for i in items if split["assignments"][i["id"]] == {"partition": part, "role": "reference"} and not i["exclusion"]]
        known, unknown = set(), set()
        for i in items:
            a = split["assignments"][i["id"]]
            if i["exclusion"] or a["partition"] != part:
                continue
            if a["role"] == "unknown":
                unknown.add(i["problem_id"])
            elif a["role"] == "query" and any(can_pair(i, r) and i["problem_id"] == r["problem_id"] for r in refs):
                known.add(i["problem_id"])
        if len(known) < (2 if synthetic else 10) or len(unknown) < (2 if synthetic else 20):
            blockers.append(f"{part}: independent known queries={len(known)}, unknown problems={len(unknown)} below frozen minimum")
    return blockers


def can_pair(a, b):
    if a.get("protocol") or b.get("protocol"):
        from .weak_protocol import pair_allowed
        return pair_allowed(a, b)
    return all(a[k] != b[k] for k in ("id", "source_id", "source_sha256", "lineage_id", "identity"))


def prepare(catalog_path, output=None):
    catalog, items = load_catalog(catalog_path)
    identities = defaultdict(list)
    for item in items:
        if item["identity"] is not None:
            identities[item["identity"]].append(item)
    diagnostics = {"normalized_collision_groups": sum(len(v) > 1 for v in identities.values()),
                   "cross_label_collision_groups": sum(len({i["problem_id"] for i in v}) > 1 for v in identities.values()),
                   "interpretation": "Conservative WL fingerprints; collisions quarantined, not proofs of semantic identity"}
    quarantine_duplicates(items)
    split = make_split(items, catalog["synthetic"])
    blockers = eligibility(items, split, catalog["synthetic"])
    training = [Graph(**i["graph"]) for i in items if not i["exclusion"] and
                split["assignments"].get(i["id"], {}).get("partition") == "train"]
    vocab = Vocabulary.fit(training)
    result = {"version": "te01.prepared.v1", "feature_version": FEATURE_VERSION,
              "feature_builder_hash": builder_hash(),
              "synthetic": catalog["synthetic"], "catalog_hash": digest(catalog),
              "samples": items, "split": split, "split_hash": digest(split),
              "vocabulary": vocab.tokens, "vocabulary_hash": digest(vocab.tokens),
              "blockers": blockers, "diagnostics": diagnostics,
              "coverage": dict(Counter(i["exclusion"] or i["status"] for i in items))}
    result["prepared_hash"] = digest(result)
    if output:
        write_json(output, result)
    return result


def load_prepared(path):
    if Path(path).stat().st_size > 1024 * 2**20:
        raise ValueError("Prepared input exceeds 1024 MiB cap")
    data = read_json(path)
    if data.get("version") not in ("te01.prepared.v1", "te02.prepared.v1") or data.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Prepared data version mismatch")
    if data.get("feature_builder_hash") != builder_hash():
        raise ValueError("Prepared feature builder changed; regenerate deterministic inputs")
    if data["prepared_hash"] != digest({k: v for k, v in data.items() if k != "prepared_hash"}):
        raise ValueError("Prepared input modified")
    if data["split"]["assignments"]:
        validate_split(data["samples"], data["split"])
    return data
