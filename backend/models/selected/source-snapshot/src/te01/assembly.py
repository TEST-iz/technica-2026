"""TE02 GCC text -> ET_REL function CFG. Never link or execute corpus programs.

The ET_REL contract is distinct from TP01's linked-ELF schema. Relocations, not
their placeholder bytes, determine symbol-relative transfers/address operands.
"""
from __future__ import annotations

from collections import Counter
import io
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import time

from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET, CS_AC_READ, CS_AC_WRITE
from capstone.x86 import X86_OP_REG, X86_OP_IMM, X86_OP_MEM
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

from .io import ROOT, digest, file_hash, output_path
from .representation import Graph, Excluded, EDGE_KINDS, LIMITS, instruction_tokens, structural

ASSEMBLY_VERSION = "te02.gcc-et-rel.v1"
OLD_PREFIX = "/home/saraa/leetcode_dataset_v15/"
FUNCTION_RE = re.compile(r"(?m)^\s*\.type\s+([^,\s]+)\s*,\s*@function\s*(?:#.*)?$")


def rebase_path(value, root):
    root = Path(root).absolute()
    if root.resolve() != root:
        raise ValueError("Dataset root is redirected")
    if not isinstance(value, str) or not value.startswith(OLD_PREFIX):
        raise ValueError("Unknown or ambiguous assembly root")
    suffix = value[len(OLD_PREFIX):]
    rel = Path(suffix)
    if rel.is_absolute() or ".." in rel.parts or "\\" in suffix or not (suffix.startswith("asm/") or suffix.startswith("variants/asm/")):
        raise ValueError("Unsafe assembly path")
    p = root / rel
    if p.resolve() != p or not p.resolve().is_relative_to(root) or not p.is_file():
        raise ValueError("Missing or redirected assembly file")
    return p, suffix


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 2**20, 16 * 2**20))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))


def assemble(path, expected_sha256=None):
    raw = Path(path).read_bytes()
    sha = file_hash(path)
    if expected_sha256 is not None and sha != expected_sha256:
        raise Excluded("assembly_hash_changed")
    if len(raw) > 2**20:
        raise Excluded("assembly_input_size_limit")
    text = raw.decode("utf-8")
    if re.search(r"(?m)^\s*\.(?:include|incbin|macro|irp|irpc|rept)\b", text):
        raise Excluded("unsupported_assembly_directive")
    declarations = FUNCTION_RE.findall(text)
    if len(declarations) != 1:
        raise Excluded("ambiguous_entry_multiple_declared_functions" if declarations else "no_declared_function")
    obj = output_path(ROOT / ".cache/te02-objects" / (sha + ".o"))
    if not obj.exists():
        fd, temporary = tempfile.mkstemp(prefix="assemble-", suffix=".o", dir=obj.parent)
        os.close(fd)
        try:
            result = subprocess.run(["prlimit", "--as="+str(512*2**20), "--fsize="+str(16*2**20), "--cpu=8",
                                     "--", "as", "--64", "-o", temporary, str(path)], capture_output=True,
                                    timeout=10, check=False)
        except subprocess.TimeoutExpired as e:
            raise Excluded("assembler_timeout") from e
        else:
            if result.returncode:
                raise Excluded("assembler_failed:" + result.stderr.decode(errors="replace")[-1200:])
            os.replace(temporary, obj)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return obj, declarations[0], sha


def decode_operand(ins, op):
    value = {"width": op.size * 8 or None,
             "access": [s for f, s in ((CS_AC_READ, "read"), (CS_AC_WRITE, "write")) if op.access & f] or None}
    if op.type == X86_OP_REG:
        value.update(kind="register", register=ins.reg_name(op.reg))
    elif op.type == X86_OP_IMM:
        value.update(kind="immediate", immediate=int(op.imm))
    elif op.type == X86_OP_MEM:
        m = op.mem
        value.update(kind="memory", memory={"base": ins.reg_name(m.base) or None, "index": ins.reg_name(m.index) or None,
                                              "scale": m.scale, "displacement": int(m.disp), "segment": ins.reg_name(m.segment) or None})
    else:
        value.update(kind="unknown", capstone_type=op.type)
    return value


def convert_assembly(path, expected_sha256=None):
    started = time.perf_counter()
    obj, selected, sha = assemble(path, expected_sha256)
    elf = ELFFile(io.BytesIO(obj.read_bytes()))
    if elf["e_type"] != "ET_REL" or elf["e_machine"] != "EM_X86_64" or elf.elfclass != 64 or not elf.little_endian:
        raise Excluded("unsupported_relocatable_target")
    symtab = elf.get_section_by_name(".symtab")
    funcs = [s for s in symtab.iter_symbols() if s["st_info"]["type"] == "STT_FUNC" and isinstance(s["st_shndx"], int)]
    if len(funcs) != 1 or funcs[0].name != selected:
        raise Excluded("declared_symbol_bounds_mismatch")
    fn = funcs[0]
    section_index, start, size = fn["st_shndx"], fn["st_value"], fn["st_size"]
    section = elf.get_section(section_index)
    if not size or not section["sh_flags"] & 4 or start + size > section["sh_size"]:
        raise Excluded("invalid_symbol_extent")
    raw = section.data()[start:start+size]
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    instructions = list(decoder.disasm(raw, start))
    if not instructions or sum(i.size for i in instructions) != size:
        raise Excluded("decode_coverage")
    if len(instructions) > LIMITS["instructions"]:
        raise Excluded("oversize_function")
    relocations = []
    for relsec in elf.iter_sections():
        if isinstance(relsec, RelocationSection) and relsec["sh_info"] == section_index:
            table = elf.get_section(relsec["sh_link"])
            for rel in relsec.iter_relocations():
                offset = rel["r_offset"]
                if start <= offset < start + size:
                    if not rel.is_RELA():
                        raise Excluded("unsupported_REL_without_explicit_addend")
                    s = table.get_symbol(rel["r_info_sym"])
                    relocations.append({"offset": offset, "type": rel["r_info_type"], "addend": rel["r_addend"],
                                        "symbol": s.name, "symbol_value": s["st_value"], "symbol_section": s["st_shndx"],
                                        "symbol_type": s["st_info"]["type"]})
    addresses = {ins.address for ins in instructions}
    decoded, transfers, calls, reasons, relocation_audit = [], {}, [], [], []
    if re.search(r"(?m)^\s*\.cfi_(?:personality|lsda)\b", Path(path).read_text()):
        reasons.append({"code": "exception_metadata_present_ordinary_flow_only"})
    for ins in instructions:
        operands = [decode_operand(ins, op) for op in ins.operands]
        read, written = ins.regs_access()
        record = {"rva": ins.address, "size": ins.size, "bytes": ins.bytes.hex(), "mnemonic": ins.mnemonic,
                  "display": ins.mnemonic + " " + ins.op_str, "operands": operands,
                  "registers_read": [ins.reg_name(r) for r in read], "registers_written": [ins.reg_name(r) for r in written],
                  "groups": [ins.group_name(g) for g in ins.groups]}
        rels = [r for r in relocations if ins.address <= r["offset"] < ins.address+ins.size]
        for rel in rels:
            offset = rel["offset"] - ins.address
            # Decode field offsets are authoritative: never rewrite opcode bytes.
            if offset == ins.imm_offset and ins.imm_size:
                for op in operands:
                    if op["kind"] == "immediate":
                        op["is_address"] = True
            elif offset == ins.disp_offset and ins.disp_size:
                for op in operands:
                    if op["kind"] == "memory":
                        op["is_address"] = True
            else:
                raise Excluded("relocation_not_on_operand_field")
            if rel["type"] not in (1, 2, 4, 9, 10, 11, 41, 42):
                raise Excluded("unsupported_relocation_type:" + str(rel["type"]))
            relocation_audit.append(dict(rel, instruction=ins.address, decoded_field_offset=offset))
        is_call = CS_GRP_CALL in ins.groups
        is_jump = CS_GRP_JUMP in ins.groups or ins.mnemonic.startswith("loop")
        is_return = CS_GRP_RET in ins.groups
        terminal = ins.mnemonic in ("ud2", "hlt", "int", "int3", "syscall", "sysenter")
        if is_call or is_jump:
            conditional = is_jump and ins.mnemonic not in ("jmp", "ljmp")
            target, target_kind, symbolic = None, "unresolved", None
            if len(operands) == 1 and operands[0]["kind"] == "immediate":
                if rels:
                    if len(rels) != 1 or rels[0]["type"] not in (2, 4):
                        raise Excluded("unsupported_control_relocation")
                    rel = rels[0]
                    symbolic = {k: rel[k] for k in ("symbol", "addend", "symbol_section", "symbol_value", "type")}
                    if rel["symbol_section"] == section_index:
                        # R_X86_64_PC32/PLT32: S + A - P, then CPU adds next IP.
                        target = rel["symbol_value"] + rel["addend"] + (ins.address + ins.size - rel["offset"])
                        target_kind = "local" if target in addresses else "outside_selected_extent"
                    elif rel["symbol_section"] == "SHN_UNDEF":
                        target_kind = "external_anonymous"
                    else:
                        target_kind = "other_section"
                else:
                    target = int(ins.operands[0].imm)
                    target_kind = "local" if target in addresses else "outside_selected_extent"
            transfer = {"instruction": ins.address, "kind": "call" if is_call else "conditional" if conditional else "jump",
                        "target": target, "target_kind": target_kind, "symbolic": symbolic,
                        "recursion": is_call and target_kind == "local" and target == start,
                        "continuation_inferred": is_call}
            transfers[ins.address] = transfer
            if is_call:
                calls.append(transfer)
            if target_kind in ("unresolved", "outside_selected_extent"):
                reasons.append({"code": "unresolved_transfer", "instruction": ins.address, "kind": transfer["kind"]})
        if terminal:
            reasons.append({"code": "unsupported_terminal_semantics", "instruction": ins.address})
        decoded.append((ins, record, is_call, is_jump, is_return or terminal))
    leaders = {start}
    for ins, record, call, jump, stop in decoded:
        transfer = transfers.get(ins.address)
        if jump and transfer["target_kind"] == "local":
            leaders.add(transfer["target"])
        if call or jump or stop:
            if ins.address+ins.size in addresses:
                leaders.add(ins.address+ins.size)
    if len(leaders) > LIMITS["blocks"]:
        raise Excluded("oversize_graph")
    blocks, current = [], []
    for entry in decoded:
        if entry[0].address in leaders and current:
            blocks.append(current); current = []
        current.append(entry)
    if current:
        blocks.append(current)
    mapping = {b[0][0].address: i for i, b in enumerate(blocks)}
    edges = []
    for index, block in enumerate(blocks):
        if len(block) > LIMITS["instructions_per_block"]:
            raise Excluded("oversize_block")
        ins, record, call, jump, stop = block[-1]
        nxt = mapping.get(ins.address+ins.size)
        transfer = transfers.get(ins.address)
        def edge(dest, kind):
            if dest is not None:
                edges.append((index, dest, EDGE_KINDS.index(kind)))
        if call:
            edge(nxt, "call_continuation")
        elif jump:
            conditional = transfer["kind"] == "conditional"
            if transfer["target_kind"] == "local":
                edge(mapping[transfer["target"]], "conditional_taken" if conditional else "unconditional_jump")
            if conditional:
                edge(nxt, "conditional_fallthrough")
        elif not stop:
            edge(nxt, "fallthrough")
            if nxt is None:
                reasons.append({"code": "unexplained_function_falloff", "instruction": ins.address})
    reachable = {0}
    while True:
        new = reachable | {v for u, v, k in edges if u in reachable}
        if new == reachable:
            break
        reachable = new
    if len(reachable) < len(blocks):
        reasons.append({"code": "unreachable_blocks", "count": len(blocks)-len(reachable)})
    encoded = [[instruction_tokens(record) for ins, record, *_ in b] for b in blocks]
    graph = Graph(encoded, sorted(set(edges)), structural(len(blocks), edges, 0), 0)
    return {"version": ASSEMBLY_VERSION, "graph": graph.as_json(), "identity": graph.identity(),
            "status": "PARTIAL" if reasons else "OK", "reasons": reasons, "assembly_sha256": sha,
            "object_sha256": file_hash(obj), "selected_symbol": selected, "section": section.name,
            "symbol_start": start, "symbol_size": size, "instructions": [r for _, r, *_ in decoded],
            "block_instruction_offsets": [[i.address for i, *_ in b] for b in blocks], "calls": calls,
            "transfers": list(transfers.values()), "relocations": relocation_audit,
            "conversion_seconds": time.perf_counter()-started, "object_path": str(obj)}
