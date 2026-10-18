"""Schema 1.0.1 -> identity-free structured entry-function features.

Addresses are used only to check structure/order and to mask address operands.
No bytes, display text, symbols, IDs, provenance or labels become tokens.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass
import re

from jsonschema import Draft202012Validator

from .io import ROOT, digest, read_json

EDGE_KINDS = ("fallthrough", "conditional_taken", "conditional_fallthrough",
              "unconditional_jump", "indirect_resolved", "call_continuation", "unknown")
LIMITS = {"blocks": 256, "instructions_per_block": 256, "instructions": 4096,
          "fields_per_instruction": 96, "edges": 4096}
TARGET = {"format": "ELF", "isa": "x86_64", "bits": 64, "endianness": "little"}
VALIDATOR = Draft202012Validator(read_json(ROOT / "fixtures/parser-record.schema.json"))
FEATURE_VERSION = "te01.features.v1"


class Excluded(ValueError):
    pass


@dataclass
class Graph:
    blocks: list[list[list[str]]]
    edges: list[tuple[int, int, int]]
    structure: list[list[float]]
    entry: int

    def identity(self):
        # Conservative, permutation-invariant WL fingerprint, not an isomorphism proof.
        labels = [digest(b) for b in self.blocks]
        initial = sorted(labels)
        for _ in range(3):
            labels = [digest([labels[i], sorted(("out", k, labels[v]) for u, v, k in self.edges if u == i),
                              sorted(("in", k, labels[u]) for u, v, k in self.edges if v == i)])
                      for i in range(len(labels))]
        return digest([initial, sorted(labels), labels[self.entry], len(self.edges)])

    def as_json(self):
        return asdict(self)


@dataclass
class Bundle:
    status: str
    entry: Graph
    helpers: list[Graph]
    missing_helpers: int


def reg(name):
    if not name:
        return "NONE"
    name = name.lower()
    families = {"ax": ("rax", "eax", "ax", "al", "ah"), "bx": ("rbx", "ebx", "bx", "bl", "bh"),
                "cx": ("rcx", "ecx", "cx", "cl", "ch"), "dx": ("rdx", "edx", "dx", "dl", "dh"),
                "sp": ("rsp", "esp", "sp", "spl"), "bp": ("rbp", "ebp", "bp", "bpl"),
                "si": ("rsi", "esi", "si", "sil"), "di": ("rdi", "edi", "di", "dil"),
                "ip": ("rip", "eip", "ip"), "flags": ("rflags", "eflags", "flags")}
    for family, aliases in families.items():
        if name in aliases:
            return family
    m = re.fullmatch(r"r(\d+)[dwb]?", name)
    if m and 8 <= int(m[1]) <= 15:
        return "r" + m[1]
    if re.fullmatch(r"(?:[xyz]mm|st|mm)\d+", name) or name in {"cs", "ds", "es", "fs", "gs", "ss"}:
        return name
    return "UNK_REG"


def constant(value):
    # Called only after explicit address/transfer masking. Keep a fixed small
    # semantic vocabulary; unclassified large values expose no magnitude/sign.
    if -256 <= value <= 256:
        return str(value)
    if abs(value) in (1000000007, 1000000009):
        return "MODULUS:" + str(value)
    for bits in range(9, 65):
        if abs(value) == 2**bits:
            return f"POWER2:{'-' if value < 0 else '+'}:{bits}"
        if abs(value) == 2**bits - 1:
            return f"BITMASK:{'-' if value < 0 else '+'}:{bits}"
    return "OTHER"


def instruction_tokens(ins, address_ranges=(), rich=True):
    mnemonic = ins["mnemonic"].lower()
    if not re.fullmatch(r"[a-z][a-z0-9]*(?: [a-z][a-z0-9]*)?", mnemonic):
        raise Excluded("invalid_mnemonic")
    tokens = ["mn:" + mnemonic]
    if not rich:
        return tokens
    transfer = (mnemonic.startswith(("j", "call", "loop")) or
                any(g in {"jump", "call", "branch_relative"} for g in ins["groups"]))
    for n, op in enumerate(ins["operands"]):
        prefix = f"o{n}:"
        tokens.extend([prefix + "kind:" + op["kind"], prefix + "width:" + str(op["width"]),
                       prefix + "access:" + "+".join(sorted(op["access"] or ["unknown"]))])
        if op["kind"] == "register":
            tokens.append(prefix + "reg:" + reg(op["register"]))
        elif op["kind"] == "immediate":
            v = op["immediate"]
            value = "ADDRESS" if op.get("is_address") or transfer or any(a <= v < b for a, b in address_ranges) else constant(v)
            tokens.append(prefix + "imm:" + value)
        elif op["kind"] == "memory":
            m = op["memory"]
            tokens.extend(prefix + k + ":" + reg(m[k]) for k in ("base", "index", "segment"))
            tokens.append(prefix + "scale:" + str(m["scale"]))
            address = op.get("is_address") or m["base"] in (None, "rip", "eip") or any(a <= m["displacement"] < b for a, b in address_ranges)
            tokens.append(prefix + "disp:" + ("ADDRESS" if address else constant(m["displacement"])))
    for key in ("registers_read", "registers_written"):
        tokens.extend(key + ":" + r for r in sorted({reg(r) for r in ins[key]}))
    if len(tokens) > LIMITS["fields_per_instruction"]:
        raise Excluded("oversize_instruction_fields")
    return tokens


def structural(n, edges, entry):
    import numpy as np
    adjacency = np.zeros((n, n), dtype=np.float64)
    for u, v, _ in edges:
        adjacency[u, v] = 1
    indeg, outdeg = adjacency.sum(0), adjacency.sum(1)
    distance = [n + 1] * n
    distance[entry] = 0
    q = deque([entry])
    while q:
        u = q.popleft()
        for v in np.flatnonzero(adjacency[u]):
            if distance[v] == n + 1:
                distance[v] = distance[u] + 1
                q.append(int(v))
    transition = adjacency / np.maximum(outdeg[:, None], 1)
    power = np.eye(n)
    returns = []
    for _ in range(3):
        power = power @ transition
        returns.append(power.diagonal().copy())
    return [[float(i == entry), float(min(indeg[i], 16) / 16), float(min(outdeg[i], 16) / 16),
             float(min(distance[i], 32) / 32), *[float(r[i]) for r in returns]] for i in range(n)]


def convert(record, *, rich=True, address_ranges=()):
    errors = sorted(VALIDATOR.iter_errors(record), key=lambda e: str(e.path))
    if errors:
        raise Excluded("schema:" + errors[0].json_path)
    if record["status"] == "FAILED":
        raise Excluded("parser_failed")
    if not isinstance(record["target"], dict) or any(record["target"].get(k) != v for k, v in TARGET.items()) or record["target"].get("elf_type") not in ("ET_EXEC", "ET_DYN"):
        raise Excluded("unqualified_target")
    functions = record["functions"]
    fids = {f["id"] for f in functions}
    if len(fids) != len(functions) or record["entry_function_id"] not in fids:
        raise Excluded("entry_membership")
    # Mask known absolute addresses even for old records without producer ranges.
    ranges = list(address_ranges)
    for f in functions:
        for b in f["blocks"]:
            for base in (record["run"].get("mapped_base", 0), record["run"].get("linked_base", 0), 0):
                ranges.append((base + b["rva"], base + b["rva"] + b["size"]))
    graphs, missing = {}, 0
    for f in functions:
        blocks = f["blocks"]
        ids = {b["id"]: i for i, b in enumerate(blocks)}
        if not blocks or len(ids) != len(blocks) or f["entry_block_id"] not in ids:
            raise Excluded("block_membership")
        if len(blocks) > LIMITS["blocks"] or len(f["edges"]) > LIMITS["edges"]:
            raise Excluded("oversize_graph")
        if sum(len(b["instructions"]) for b in blocks) > LIMITS["instructions"]:
            raise Excluded("oversize_function")
        encoded = []
        for b in blocks:
            if len(b["instructions"]) > LIMITS["instructions_per_block"]:
                raise Excluded("oversize_block")
            # Serialization order may change; RVA establishes instruction order ONLY.
            instructions = sorted(b["instructions"], key=lambda x: x["rva"])
            pos = b["rva"]
            for ins in instructions:
                if ins["rva"] != pos or len(bytes.fromhex(ins["bytes"])) != ins["size"]:
                    raise Excluded("decode_coverage")
                pos += ins["size"]
            if pos != b["rva"] + b["size"]:
                raise Excluded("decode_coverage")
            encoded.append([instruction_tokens(i, ranges, rich) for i in instructions])
        edges = set()
        for e in f["edges"]:
            if e["source"] not in ids or e["destination"] not in ids:
                raise Excluded("edge_endpoint")
            edges.add((ids[e["source"]], ids[e["destination"]], EDGE_KINDS.index(e["kind"])))
        for call in f["calls"]:
            if call["block_id"] not in ids or call["callsite_rva"] not in {i["rva"] for i in blocks[ids[call["block_id"]]]["instructions"]}:
                raise Excluded("callsite_membership")
            for c in call["continuations"]:
                if c["block_id"] not in ids or blocks[ids[c["block_id"]]]["rva"] != c["rva"]:
                    raise Excluded("continuation_membership")
            for t in call["targets"]:
                if t["kind"] == "local" and t["function_id"] not in fids:
                    raise Excluded("dangling_helper")
                missing += t["kind"] == "internal_unavailable"
        for t in f["cross_function_transfers"]:
            if t["target"]["kind"] == "local" and t["target"]["function_id"] not in fids:
                raise Excluded("dangling_helper")
        edges = sorted(edges)
        entry = ids[f["entry_block_id"]]
        graphs[f["id"]] = Graph(encoded, edges, structural(len(blocks), edges, entry), entry)
    # Reasons also capture requested helpers without any reachable callsite.
    missing = max(missing, sum(r["code"] == "helper_recovery_failed" for r in record["reasons"]))
    return Bundle(record["status"], graphs[record["entry_function_id"]],
                  [g for fid, g in graphs.items() if fid != record["entry_function_id"]], missing)


class Vocabulary:
    def __init__(self, tokens=None):
        self.tokens = tokens or ["<PAD>", "<UNK>"]
        if self.tokens[:2] != ["<PAD>", "<UNK>"] or len(set(self.tokens)) != len(self.tokens):
            raise ValueError("Invalid vocabulary")
        self.index = {t: i for i, t in enumerate(self.tokens)}

    @classmethod
    def fit(cls, graphs, max_tokens=8192):
        counts = Counter(t for g in graphs for b in g.blocks for ins in b for t in ins)
        chosen = sorted(counts, key=lambda t: (-counts[t], t))[:max_tokens - 2]
        return cls(["<PAD>", "<UNK>"] + chosen)

    def encode(self, tokens):
        return [self.index.get(t, 1) for t in tokens]
