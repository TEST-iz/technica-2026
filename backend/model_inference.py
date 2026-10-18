"""Thin adapter for the verified TE03 `selected.zip` model bundle.

Inference: GCC/Clang GAS x86-64 `.s` containing exactly one `.type ..., @function`
           -> assemble/disassemble/normalize -> frozen E0 -> cosine top-k.
This does NOT accept arbitrary objdump text or ELF uploads.
No LLM, MiniLM, training code changes, or teacher labels are used at inference.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile


class InferenceInputError(ValueError):
    """User input cannot be represented under the frozen model contract."""


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
        from te01.assembly import convert_assembly
        from te01.engine import load_export
        from te01.models import collate
        from te01.representation import Graph, Excluded
        import torch

        self.torch = torch
        self.collate = collate
        self.Graph = Graph
        self.Excluded = Excluded
        self.convert_assembly = convert_assembly
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
        if not isinstance(top_k, int) or not 1 <= top_k <= 50:
            raise InferenceInputError("top_k must be an integer between 1 and 50")
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

    def predict(self, raw_assembly: str, top_k: int = 8):
        if not isinstance(raw_assembly, str) or not raw_assembly.strip():
            raise InferenceInputError("raw_assembly is empty")
        if len(raw_assembly.encode("utf-8")) > 1_000_000:
            raise InferenceInputError("Assembly input exceeds 1 MB limit")
        # The frozen TE02 frontend requires one emitted GAS function declaration.
        from te01.assembly import FUNCTION_RE
        n = len(FUNCTION_RE.findall(raw_assembly))
        if n != 1:
            raise InferenceInputError(
                "Expected GNU assembler .s text with exactly one '.type SYMBOL,@function' "
                "declaration (not objdump output or a multi-function binary)"
            )
        # Converter uses a constrained assembler; no submitted program is executed.
        with tempfile.TemporaryDirectory(prefix="technica-query-") as temp:
            path = Path(temp) / "query.s"
            path.write_text(raw_assembly, encoding="utf-8")
            try:
                converted = self.convert_assembly(path)
            except self.Excluded as e:
                raise InferenceInputError(str(e)) from e
        z = self.encode_graph(converted["graph"])
        return {
            "status": converted["status"],
            "warnings": [r.get("code", str(r)) if isinstance(r, dict) else str(r)
                         for r in converted["reasons"]][:32],
            "model_sha256": self.model_sha,
            "scores_are_probabilities": False,
            "results": self._rank(z, top_k),
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
    bundle_dir = Path(os.getenv("TECHNICA_MODEL_DIR", "/root/backend/models/te03/selected"))
    return RetrievalEngine(bundle_dir)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", required=True)
    parser.add_argument("--assembly", action="store_true",
                        help="Also verify the actual assembler->decoder->model path")
    args = parser.parse_args()
    print(json.dumps(get_model().self_test(with_assembler=args.assembly), indent=2))
