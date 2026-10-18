"""Multi-function GAS -> per-function TE03 graphs; no model-bundle modifications.

The function decoder follows the frozen te01.assembly converter, reusing its
operand decoder, instruction tokenizer and structural features. Only selection
and inter-function transfer metadata are extended. No code is linked or executed.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

FRONTEND_VERSION = "te03.inference-multifunction.v1"
MAX_INPUT_BYTES = 1_000_000
MAX_OBJECT_BYTES = 16 * 2**20
MAX_FUNCTIONS = 256
MAX_TOTAL_INSTRUCTIONS = 32768


class AssemblyInputError(ValueError):
    """Invalid, unsupported or over-budget submitted assembly."""


def _code_only(text: str) -> str:
    # Remove comments/string contents before scanning directives. Match anywhere
    # so '; .include' or 'label: .incbin' cannot bypass a line-start check.
    pattern = r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|\#[^\n]*'
    return re.sub(pattern, lambda m: "\n" * m.group().count("\n") or " ", text)


def _assemble_text(raw_assembly: str) -> bytes:
    if not isinstance(raw_assembly, str) or not raw_assembly.strip():
        raise AssemblyInputError("raw_assembly is empty")
    try:
        raw = raw_assembly.encode("utf-8")
    except UnicodeError as exc:
        raise AssemblyInputError("Assembly must be valid UTF-8 text") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise AssemblyInputError("Assembly input exceeds 1 MB limit")
    if "\0" in raw_assembly:
        raise AssemblyInputError("Assembly must be text, not binary data")
    code = _code_only(raw_assembly)
    unsafe = re.search(r"(?i)\.(include|incbin|macro|irp|irpc|rept|rep|altmacro|purgem)\b", code)
    if unsafe:
        raise AssemblyInputError("Unsupported assembly directive: ." + unsafe[1].lower())
    if not shutil.which("as") or not shutil.which("prlimit"):
        raise RuntimeError("GNU as and prlimit must be installed on the backend host")
    # Each request has private paths: no shared publication race and no writes
    # inside the hash-bound/read-only model bundle. Assembly is never executed.
    with tempfile.TemporaryDirectory(prefix="technica-query-") as temp:
        root = Path(temp)
        source, obj, log = root / "query.s", root / "query.o", root / "assembler.log"
        source.write_bytes(raw)
        command = ["prlimit", "--as=" + str(512 * 2**20),
                   "--fsize=" + str(MAX_OBJECT_BYTES), "--cpu=8", "--",
                   "as", "--64", "-o", str(obj), str(source)]
        try:
            with log.open("wb") as out:
                result = subprocess.run(command, cwd=root, stdout=out, stderr=out,
                                        timeout=10, check=False)
        except subprocess.TimeoutExpired as exc:
            raise AssemblyInputError("Assembler exceeded its 10-second timeout") from exc
        if result.returncode:
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 1600))
                detail = stream.read().decode("utf-8", errors="replace")
            detail = detail.replace(str(source), "uploaded assembly")
            raise AssemblyInputError("assembler_failed: " + detail.strip())
        if not obj.is_file() or obj.stat().st_size > MAX_OBJECT_BYTES:
            raise AssemblyInputError("Assembler object exceeds output budget")
        return obj.read_bytes()


def convert_functions(raw_assembly: str, *, function_symbol: str | None = None) -> dict:
    """Assemble once, extract all defined ELF function symbols, decode separately.

    An optional exact symbol/alias selector restricts scoring, not assembly. Bad
    individual functions are reported as excluded; they never disappear silently.
    No function-boundary guesses or concatenation of unrelated bodies are used.
    """
    from elftools.elf.elffile import ELFFile
    from elftools.common.exceptions import ELFError
    from te01.representation import Excluded

    if function_symbol is not None and (not isinstance(function_symbol, str) or not function_symbol):
        raise AssemblyInputError("function_symbol must be a nonempty exact symbol name")
    raw_object = _assemble_text(raw_assembly)
    sha = hashlib.sha256(raw_assembly.encode("utf-8")).hexdigest()
    object_sha = hashlib.sha256(raw_object).hexdigest()
    try:
        elf = ELFFile(io.BytesIO(raw_object))
        if (elf["e_type"] != "ET_REL" or elf["e_machine"] != "EM_X86_64"
                or elf.elfclass != 64 or not elf.little_endian):
            raise AssemblyInputError("Expected little-endian x86-64 relocatable assembly")
        symtab = elf.get_section_by_name(".symtab")
        if symtab is None:
            raise AssemblyInputError("Assembly has no symbol table")
        functions = [s for s in symtab.iter_symbols()
                     if s["st_info"]["type"] == "STT_FUNC"
                     and isinstance(s["st_shndx"], int)]
        if not functions:
            raise AssemblyInputError("No defined functions: use GNU .type SYMBOL,@function and .size directives")
        if len(functions) > MAX_FUNCTIONS:
            raise AssemblyInputError(f"Input exceeds the {MAX_FUNCTIONS}-function limit")
        # Exact aliases share one physical body and one prediction. Partial
        # overlap is ambiguous and is excluded instead of creating fake bodies.
        groups = {}
        for fn in functions:
            groups.setdefault((fn["st_shndx"], fn["st_value"], fn["st_size"]), []).append(fn)
        groups = {key: sorted(value, key=lambda s: s.name) for key, value in groups.items()}
        names = {s.name for s in functions}
        if function_symbol is not None and function_symbol not in names:
            raise AssemblyInputError(f"Function {function_symbol!r} is not defined in this assembly")
        exception_metadata = bool(re.search(r"(?m)^\s*\.cfi_(?:personality|lsda)\b", raw_assembly))
        converted, excluded, total_instructions = [], [], 0
        all_canonical = [value[0] for value in groups.values()]
        for key, aliases in sorted(groups.items()):
            if function_symbol is not None and function_symbol not in {s.name for s in aliases}:
                continue
            fn = aliases[0]
            info = {"function": fn.name, "aliases": [s.name for s in aliases],
                    "section": elf.get_section(key[0]).name, "offset": key[1], "size": key[2]}
            try:
                if any(other != key and other[0] == key[0]
                       and max(key[1], other[1]) < min(key[1] + key[2], other[1] + other[2])
                       for other in groups):
                    raise Excluded("overlapping_function_extents")
                item = _decode_function(elf, fn, all_canonical, sha, object_sha, exception_metadata)
                total_instructions += len(item["instructions"])
                if total_instructions > MAX_TOTAL_INSTRUCTIONS:
                    raise AssemblyInputError(f"Input exceeds {MAX_TOTAL_INSTRUCTIONS} decoded instructions")
                item["aliases"] = info["aliases"]
                converted.append(item)
            except Excluded as exc:
                excluded.append(dict(info, reason=str(exc), status="EXCLUDED"))
        if not converted:
            detail = "; ".join(f"{r['function']}: {r['reason']}" for r in excluded[:8])
            raise AssemblyInputError("No supported functions could be extracted. " + detail)
        return {"functions": converted, "excluded_functions": excluded,
                "defined_function_count": len(functions), "distinct_body_count": len(groups),
                "assembly_sha256": sha, "object_sha256": object_sha}
    except ELFError as exc:
        raise AssemblyInputError("Invalid assembled ELF object: " + str(exc)) from exc


def _decode_function(elf, fn, all_functions, sha, object_sha, exception_metadata):
    # This is the frozen TE02 decoder with explicit ELF symbol selection. The
    # representation helpers come from the verified checkpoint source snapshot.
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_GRP_CALL, CS_GRP_JUMP, CS_GRP_RET
    from elftools.elf.relocation import RelocationSection
    from te01.assembly import decode_operand
    from te01.representation import Graph, Excluded, EDGE_KINDS, LIMITS, instruction_tokens, structural
    started = time.perf_counter()
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
    if exception_metadata:
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
            callee_symbol, callee_offset = None, None
            target_section, resolved_target = section_index, target
            if symbolic and isinstance(symbolic["symbol_section"], int):
                target_section = symbolic["symbol_section"]
                rel = rels[0]
                resolved_target = (rel["symbol_value"] + rel["addend"]
                                   + ins.address + ins.size - rel["offset"])
            if target_kind != "external_anonymous" and resolved_target is not None:
                matches = [s for s in all_functions
                           if s["st_shndx"] == target_section
                           and s["st_value"] == resolved_target and s["st_size"] > 0]
                if matches:
                    callee = sorted(matches, key=lambda s: s.name)[0]
                    callee_symbol = callee.name
                    callee_offset = int(resolved_target - callee["st_value"])
                    if target_kind != "local":
                        target_kind = "other_function"
                        target = int(resolved_target)
            transfer = {"instruction": ins.address, "kind": "call" if is_call else "conditional" if conditional else "jump",
                        "target": target, "target_kind": target_kind, "symbolic": symbolic,
                        "recursion": is_call and target_kind == "local" and target == start,
                        "continuation_inferred": is_call, "callee_symbol": callee_symbol,
                        "callee_offset": callee_offset}
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
    return {"version": FRONTEND_VERSION, "graph": graph.as_json(), "identity": graph.identity(),
            "status": "PARTIAL" if reasons else "OK", "reasons": reasons, "assembly_sha256": sha,
            "object_sha256": object_sha, "selected_symbol": fn.name, "section": section.name,
            "symbol_start": start, "symbol_size": size, "instructions": [r for _, r, *_ in decoded],
            "block_instruction_offsets": [[i.address for i, *_ in b] for b in blocks], "calls": calls,
            "transfers": list(transfers.values()), "relocations": relocation_audit,
            "conversion_seconds": time.perf_counter()-started}
