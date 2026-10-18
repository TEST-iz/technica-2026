"""Distinct-problem retrieval, transparent exclusions and validation calibration."""
from __future__ import annotations

from collections import Counter
import math
import time

import torch

from .data import can_pair
from .io import digest
from .models import block_alignment
from .representation import Graph


def control_features(graph, kind):
    if kind == "identity":
        return Counter({graph.identity(): 1})
    if kind == "ngram":
        out = Counter()
        for block in graph.blocks:
            ins = [tuple(t) for t in block]
            for n in (1, 2, 3):
                out.update((n, tuple(ins[i:i + n])) for i in range(len(ins) - n + 1))
        return out
    if kind == "wl":
        # Pure structural control: no instruction tokens.
        labels = [str(i == graph.entry) for i in range(len(graph.blocks))]
        out = Counter((0, label) for label in labels)
        for depth in (1, 2):
            labels = [digest([labels[i], sorted(("out", k, labels[v]) for u, v, k in graph.edges if u == i),
                              sorted(("in", k, labels[u]) for u, v, k in graph.edges if v == i)])
                      for i in range(len(labels))]
            out.update((depth, label) for label in labels)
        return out
    raise ValueError("Unknown control")


def counter_cosine(a, b):
    denom = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return sum(v * b.get(k, 0) for k, v in a.items()) / denom if denom else 0.


def rank_problems(reference_scores):
    best = {}
    for ref, score in reference_scores:
        if not math.isfinite(score):
            raise ValueError("Nonfinite retrieval score")
        p = ref["problem_id"]
        prior = best.get(p)
        if prior is None or score > prior["score"] or (score == prior["score"] and ref["id"] < prior["reference_id"]):
            best[p] = {"problem_id": p, "score": float(score), "reference_id": ref["id"],
                       "source_id": ref["source_id"], "source_locator": ref.get("source_locator")}
    return sorted(best.values(), key=lambda r: (-r["score"], r["problem_id"]))


def calibrate_threshold(query_rows, partition, false_accept_rate=.05):
    if partition != "val":
        raise ValueError("Rejection threshold can only be fitted on validation")
    scores = sorted(r["max_score"] for r in query_rows if r["role"] == "unknown" and not r["exclusion"])
    if not scores:
        raise ValueError("Unknown validation queries required for calibration")
    # Inclusive acceptance score >= threshold; nextafter resolves boundary ties.
    for threshold in sorted(set(scores + [math.nextafter(s, math.inf) for s in scores])):
        if sum(s >= threshold for s in scores) / len(scores) <= false_accept_rate:
            return {"value": threshold, "partition": "val", "unknown_queries": len(scores),
                    "target_false_accept_rate": false_accept_rate, "scores_are_probabilities": False}
    raise AssertionError("Finite scores must yield a rejecting threshold")


def evaluate(data, score_fn, *, partition="val", base_score_fn=None, shortlist=20, threshold=None):
    assignments = data["split"]["assignments"]
    samples = data["samples"]
    gallery_ids = set(data.get("galleries", {}).get(partition, []))
    refs = [i for i in samples if not i["exclusion"] and
            (i["id"] in gallery_ids if gallery_ids else assignments.get(i["id"]) == {"partition": partition, "role": "reference"})]
    queries = [i for i in samples if assignments.get(i["id"], {}).get("partition") == partition and assignments[i["id"]]["role"] in ("query", "unknown")]
    rows = []
    for query in sorted(queries, key=lambda i: i["id"]):
        role = assignments[query["id"]]["role"]
        row = {"id": query["id"], "problem_id": query["problem_id"], "status": query["status"], "role": role,
               "exclusion": query["exclusion"], "rank": None, "scores": [], "max_score": None, "latency_ms": 0.}
        candidates = [r for r in refs if can_pair(query, r)]
        if not row["exclusion"] and not candidates:
            row["exclusion"] = "no_eligible_references"
        if not row["exclusion"] and role == "query" and not any(r["problem_id"] == query["problem_id"] for r in candidates):
            row["exclusion"] = "no_independent_positive_reference"
        if not row["exclusion"]:
            start = time.perf_counter()
            if base_score_fn:
                candidates = sorted(candidates, key=lambda r: (-float(base_score_fn(query, r)), r["id"]))[:shortlist]
                row["positive_in_shortlist"] = any(r["problem_id"] == query["problem_id"] for r in candidates)
            ranked = rank_problems([(r, float(score_fn(query, r))) for r in candidates])
            row["latency_ms"] = (time.perf_counter() - start) * 1000
            row["scores"] = ranked
            row["max_score"] = ranked[0]["score"]
            row["rank"] = next((n + 1 for n, r in enumerate(ranked) if r["problem_id"] == query["problem_id"]), None)
            row["top_ties"] = sum(r["score"] == ranked[0]["score"] for r in ranked)
        rows.append(row)
    known = [r for r in rows if r["role"] == "query" and not r["exclusion"]]
    intended_known = [r for r in rows if r["role"] == "query"]
    unknown = [r for r in rows if r["role"] == "unknown" and not r["exclusion"]]
    if partition == "val" and unknown:
        threshold = calibrate_threshold(rows, "val")
    if threshold is not None:
        if threshold["partition"] != "val":
            raise ValueError("Invalid threshold provenance")
        for r in rows:
            r["accepted"] = not r["exclusion"] and r["max_score"] >= threshold["value"]
    def metrics(group):
        n = len(group)
        return {"queries": n, "recall1": sum(r["rank"] == 1 for r in group) / n if n else None,
                "recall5": sum(r["rank"] is not None and r["rank"] <= 5 for r in group) / n if n else None,
                "mrr": sum(1 / r["rank"] if r["rank"] else 0 for r in group) / n if n else None}
    timings = sorted(r["latency_ms"] for r in rows if not r["exclusion"])
    result = {"partition": partition, "synthetic": data["synthetic"], "metrics": metrics(known),
              "intended_known": metrics(intended_known), "status_strata": {s: metrics([r for r in known if r["status"] == s]) for s in ("OK", "PARTIAL")},
              "coverage": {"intended_queries": len(rows), "evaluated_queries": sum(not r["exclusion"] for r in rows),
                           "fraction": sum(not r["exclusion"] for r in rows) / len(rows) if rows else 0.,
                           "exclusions": dict(Counter(r["exclusion"] for r in rows if r["exclusion"]))},
              "reference_implementations": len(refs), "reference_problems": len({r["problem_id"] for r in refs}),
              "rank_horizon": f"top_{shortlist}_references" if base_score_fn else "all_distinct_problems",
              "ranking_latency_ms": {"median": timings[len(timings) // 2] if timings else None,
                                     "p95": timings[min(len(timings) - 1, int(.95 * len(timings)))] if timings else None},
              "threshold": threshold, "queries": rows}
    if data.get("protocol"):
        intended_eligible = sum(not q["exclusion"] for q in queries)
        result["eligible_slice_coverage"] = sum(not r["exclusion"] for r in rows) / intended_eligible if intended_eligible else 0.
        result.update(protocol=data["protocol"], claims=data["claims"], full_manifest_coverage=data["diagnostics"],
                      full_manifest_exclusions=data["coverage"])
    if threshold is not None:
        result["unknown_false_accept_rate"] = sum(r["accepted"] for r in unknown) / len(unknown) if unknown else None
        result["known_acceptance_rate"] = sum(r["accepted"] for r in known) / len(known) if known else None
    return result


def score_functions(embeddings, blocks=None, scorer=None, block_rerank=False):
    def cosine(a, b):
        return float((embeddings[a["id"]] * embeddings[b["id"]]).sum())
    if scorer is not None:
        def score(a, b):
            with torch.no_grad():
                return float(scorer(embeddings[a["id"]], embeddings[b["id"]]))
        return score, None
    if block_rerank:
        def score(a, b):
            return .5 * cosine(a, b) + .5 * float(block_alignment(blocks[a["id"]], blocks[b["id"]]))
        return score, cosine
    return cosine, None


def control_evaluation(data, kind, partition="val", threshold=None):
    gallery = set(data.get("galleries", {}).get(partition, []))
    features = {i["id"]: control_features(Graph(**i["graph"]), kind) for i in data["samples"]
                if not i["exclusion"] and (data["split"]["assignments"].get(i["id"], {}).get("partition") == partition or i["id"] in gallery)}
    result = evaluate(data, lambda a, b: counter_cosine(features[a["id"]], features[b["id"]]),
                      partition=partition, threshold=threshold)
    result["normalization_diagnostics"] = data.get("diagnostics", {})
    return result
