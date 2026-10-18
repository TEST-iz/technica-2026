"""Strict input and workspace-confined, atomic output helpers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).absolute().parents[2]


def output_path(path):
    p = Path(os.path.abspath(ROOT / path))
    if not p.is_relative_to(ROOT) or p == ROOT or p.resolve() != p:
        raise ValueError(f"Output must be unredirected and inside {ROOT}: {p}")
    if any(x.startswith(".") for x in p.relative_to(ROOT).parts) and not p.is_relative_to(ROOT / ".cache") and not p.is_relative_to(ROOT / ".tmp"):
        raise ValueError("Reserved hidden output path")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f"Duplicate JSON key: {k}")
            out[k] = v
        return out
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def atomic_bytes(path, value):
    p = output_path(path)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".atomic-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return p


def write_json(path, value):
    return atomic_bytes(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())


def source_hash():
    paths = list((ROOT / "src").rglob("*.py")) + [ROOT / "fixtures/parser-record.schema.json", ROOT / "requirements-local.txt"]
    return digest({str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)})
