"""TE03 inference adapter: multi-function GNU x86-64 assembly -> cosine top-k.

Files remain raw strings: .asm/.s/.txt extensions do not affect parsing. Assemble
once; encode functions separately with the frozen E0 model. Aggregate by maximum
per-function score per distinct problem and retain the supporting query symbol.
The model bundle and its source-hash-bound snapshot must remain unchanged.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import sys


from technica_assembly import AssemblyInputError, convert_functions


class InferenceInputError(ValueError):
    """User input cannot be represented under the frozen model contract."""


def _validate_top_k(top_k: int) -> None:
    if type(top_k) is not int or not 1 <= top_k <= 50:
        raise InferenceInputError("top_k must be an integer between 1 and 50")


def _merge_function_rankings(functions: list[dict], top_k: int) -> list[dict]:
    """Best local match per problem, NOT a learned whole-program similarity.

    Per-function top-k is sufficient: a candidate below k in every function
    cannot enter the file's top-k under max aggregation. Ties use problem IDs
    consistently with _rank, and then reference/function names for determinism.
    """
    _validate_top_k(top_k)
    best = {}
    for fn in functions:
        for match in fn["results"]:
            score = match["similarity_score"]
            if not math.isfinite(score):
                raise RuntimeError("Non-finite function similarity")
            candidate = dict(match, query_function=fn["function"],
                             query_function_aliases=fn.get("aliases", [fn["function"]]),
                             query_function_status=fn["status"])
            key = candidate["problem_id"]
            prior = best.get(key)
            ordering = lambda item: (-item["similarity_score"], item["reference_id"], item["query_function"])
            if prior is None or ordering(candidate) < ordering(prior):
                best[key] = candidate
    return sorted(best.values(), key=lambda r: (-r["similarity_score"], r["problem_id"]))[:top_k]



def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class RetrievalEngine:
    def __init__(self, bundle_dir: Path):
        self.bundle = Path(bundle_dir).resolve(strict=True)
        checksums = json.loads((self.bundle / "SHA256.json").read_text())
        for name, expected in checksums.items():
            file = self.bundle / name
            if not file.resolve().is_relative_to(self.bundle) or not file.is_file():
                raise RuntimeError(f"Missing or unsafe model artifact: {name}")
            if _sha256(file) != expected:
                raise RuntimeError(f"Model artifact hash mismatch: {name}")

        source = self.bundle / "source-snapshot"
        sys.path.insert(0, str(source / "src"))
        from te01.engine import load_export
        from te01.models import collate
        from te01.representation import Graph, Excluded
        import torch

        self.torch = torch
        self.collate = collate
        self.Graph = Graph
        self.Excluded = Excluded
        # TE03's exact source snapshot is mandatory: load_export checks source_hash.
        self.model, self.vocab, self.threshold = load_export(
            self.bundle / "encoder.pt", device="cpu"
        )
        self.config = self.model.config
        self.model_sha = _sha256(self.bundle / "encoder.pt")
        index = torch.load(self.bundle / "reference_index.pt", map_location="cpu", weights_only=True)
        if index.get("encoder_sha256") != self.model_sha:
            raise RuntimeError("Reference index was built for different encoder weights")
        if index.get("version") != "te02.frozen-index.v1":
            raise RuntimeError("Unexpected reference-index format")
        self.ids = index["reference_ids"]
        self.refs = index["embeddings"].to(dtype=torch.float32, device="cpu")
        if self.refs.ndim != 2 or self.refs.shape != (len(self.ids), 128):
            raise RuntimeError("Unexpected reference-index tensor dimensions")
        meta = json.loads((self.bundle / "reference-metadata.json").read_text())
        self.by_id = {r["id"]: r for r in meta}
        if len(self.by_id) != len(meta) or set(self.ids) != set(self.by_id):
            raise RuntimeError("Reference metadata does not match reference index")
        titles_path = Path(__file__).with_name("leetcode_titles.json")
        self.titles = json.loads(titles_path.read_text()) if titles_path.is_file() else {}

    def encode_graph(self, graph: dict):
        batch = self.collate(
            [self.Graph(**graph)], self.vocab,
            rich=self.config["rich"], typed=self.config["typed"],
            structural=self.config["structural"] and self.config["graph"] != "set",
        ).to("cpu")
        with self.torch.inference_mode():
            embedding = self.model(batch)[0].detach().cpu()
        if embedding.shape != (128,) or not self.torch.isfinite(embedding).all().item():
            raise RuntimeError("Non-finite or incorrect embedding returned by model")
        return embedding

    def _rank(self, z, top_k):
        _validate_top_k(top_k)
        with self.torch.inference_mode():
            similarities = (self.refs @ z).tolist()
        best = {}
        for index, score in enumerate(similarities):
            if not math.isfinite(score):
                raise RuntimeError("Non-finite reference similarity")
            ref = self.by_id[self.ids[index]]
            problem_id = ref["problem_id"]
            prior = best.get(problem_id)
            if prior is None or score > prior["similarity_score"] or (
                score == prior["similarity_score"] and ref["id"] < prior["reference_id"]
            ):
                fallback = Path(ref.get("source_id") or problem_id).stem.replace("-", " ").strip()
                best[problem_id] = {
                    "candidate_name": self.titles.get(problem_id) or fallback,
                    "problem_id": problem_id,
                    "similarity_score": float(score),
                    "reference_id": ref["id"],
                    "source_id": ref.get("source_id"),
                }
        return sorted(best.values(), key=lambda r: (-r["similarity_score"], r["problem_id"]))[:top_k]

    def predict(self, raw_assembly: str, top_k: int = 8, *, function_symbol: str | None = None):
        """Return top-k distinct problems across all supported query functions.

        Existing predict(text, top_k=...) callers and result name/score tuples
        stay compatible. `functions` adds individual rankings and call metadata.
        Optional function_symbol selects an exact body/alias; no main/f0 guess.
        """
        _validate_top_k(top_k)
        try:
            converted = convert_functions(raw_assembly, function_symbol=function_symbol)
        except (AssemblyInputError, self.Excluded) as exc:
            raise InferenceInputError(str(exc)) from exc
        functions, warnings, call_graph = [], [], []
        # Sequential forwards preserve the original singleton evaluation path
        # and bound peak memory. All functions share the single assembled object.
        for item in converted["functions"]:
            symbol = item["selected_symbol"]
            z = self.encode_graph(item["graph"])
            reasons = [r.get("code", str(r)) if isinstance(r, dict) else str(r)
                       for r in item["reasons"]]
            functions.append({
                "function": symbol, "aliases": item["aliases"],
                "section": item["section"], "offset": item["symbol_start"],
                "size": item["symbol_size"], "status": item["status"],
                "instruction_count": len(item["instructions"]),
                "block_count": len(item["graph"]["blocks"]),
                "warnings": list(dict.fromkeys(reasons)),
                "calls": item["calls"], "transfers": item["transfers"],
                "results": self._rank(z, top_k),
            })
            warnings.extend(f"{symbol}: {reason}" for reason in reasons)
            for transfer in item["transfers"]:
                target = transfer.get("callee_symbol")
                if transfer["kind"] == "call" or target is not None:
                    symbolic = transfer.get("symbolic") or {}
                    call_graph.append({
                        "caller": symbol, "callee": target,
                        "external_symbol": symbolic.get("symbol") if transfer["target_kind"] == "external_anonymous" else None,
                        "kind": transfer["kind"], "instruction_offset": transfer["instruction"],
                        "target_kind": transfer["target_kind"],
                        "callee_offset": transfer.get("callee_offset"),
                        "recursion": transfer["recursion"],
                    })
        excluded = converted["excluded_functions"]
        warnings.extend(f"{r['function']}: excluded ({r['reason']})" for r in excluded)
        if len(functions) > 1:
            warnings.append("Multi-function ranking uses the best individual function match per problem; it is not a whole-program equivalence score.")
        if any(c["target_kind"] == "other_function" for c in call_graph):
            warnings.append("Local helper calls are preserved as metadata; helper bodies are encoded separately, not inlined into callers.")
        partial = bool(excluded) or any(f["status"] != "OK" for f in functions)
        return {
            "status": "PARTIAL" if partial else "OK",
            "warnings": list(dict.fromkeys(warnings))[:32],
            "model_sha256": self.model_sha,
            "scores_are_probabilities": False,
            "aggregation": "max_per_problem_across_functions" if len(functions) > 1 else "single_function",
            "function_count": len(functions),
            "defined_function_count": converted["defined_function_count"],
            "excluded_function_count": len(excluded),
            "excluded_functions": excluded,
            "functions": functions, "call_graph": call_graph,
            "results": _merge_function_rankings(functions, top_k),
        }

    def self_test(self, with_assembler=False):
        regression = json.loads((self.bundle / "inference-regression.json").read_text())
        tol = float(regression["absolute_tolerance"])
        for case in regression["queries"]:
            expected = self.torch.tensor(case["expected_embedding"])
            actual = self.encode_graph(case["graph"])
            difference = (actual - expected).abs().max().item()
            if difference > tol:
                raise RuntimeError(f"Embedding regression failed: {case['id']} diff={difference}")
            actual_ids = [r["problem_id"] for r in self._rank(actual, top_k=5)]
            expected_ids = [r["problem_id"] for r in case["expected_top5"]]
            if actual_ids != expected_ids:
                raise RuntimeError(f"Ranking regression failed for {case['id']}")
            if with_assembler:
                assembly = (self.bundle / case["assembly_file"]).read_text()
                output = self.predict(assembly, top_k=5)
                # A full assembler round trip is a separate, stricter test.
                got = [r["problem_id"] for r in output["results"]]
                if got != expected_ids:
                    raise RuntimeError(f"Assembly round-trip mismatch for {case['id']}: {got}")
        return {"status": "passed", "regressions": len(regression["queries"]),
                "assembly_round_trip": with_assembler}


@lru_cache(maxsize=1)
def get_model() -> RetrievalEngine:
    configured = os.getenv("TECHNICA_MODEL_DIR")
    if configured:
        return RetrievalEngine(Path(configured))
    here = Path(__file__).resolve().parent
    for bundle_dir in (here / "models/selected", here / "models/te03/selected"):
        if (bundle_dir / "encoder.pt").is_file():
            return RetrievalEngine(bundle_dir)
    raise RuntimeError("Set TECHNICA_MODEL_DIR to the selected/ folder containing encoder.pt")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--file", type=Path, help="Predict from .asm, .s or .txt contents")
    parser.add_argument("--assembly", action="store_true", help="Include assembler round trips in self-test")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--function", dest="function_symbol", help="Optional exact function name; otherwise score all")
    args = parser.parse_args()
    try:
        engine = get_model()
        result = (engine.self_test(with_assembler=args.assembly) if args.self_test else
                  engine.predict(args.file.read_text(encoding="utf-8"), args.top_k,
                                 function_symbol=args.function_symbol))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (InferenceInputError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
