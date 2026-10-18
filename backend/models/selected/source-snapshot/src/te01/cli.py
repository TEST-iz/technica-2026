"""Small local CLI. Plan by default; smoke never accepts real data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
import sys
import traceback

import torch

from .data import load_prepared, prepare
from .engine import evaluate_checkpoint, run_experiment
from .execution import dry_plan, execute_jobs
from .io import ROOT, digest, output_path, read_json, source_hash, write_json


def smoke(device, directory):
    data = prepare(ROOT / "fixtures/catalog.json")
    plan = read_json(ROOT / "experiment_plan.json")
    results = []
    for run in plan["runs"]:
        result = run_experiment(run, data, directory / run["id"], device=device,
                                smoke=True, batch_root=directory, plan=plan)
        results.append({"id": run["id"], "status": result["status"], "device": device,
                        "steps": result.get("steps", 0), "parameters": result.get("parameters"),
                        "cpu_peak_rss_bytes": result.get("cpu_peak_rss_bytes"),
                        "cuda_peak_allocated_bytes": result.get("cuda_peak_allocated_bytes"),
                        "elapsed_seconds": result.get("elapsed_seconds")})
    summary = {"status": "completed", "synthetic": True, "scientific_quality_claim": False,
               "source_hash": source_hash(), "results": results}
    write_json(directory / "smoke-summary.json", summary)
    return summary


def batch(args, plan):
    data = load_prepared(args.prepared)
    budget = read_json(args.budget)
    devices = args.devices.split(",")
    dispatch = dry_plan(plan, data=data, budget=budget, devices=devices, concurrency=args.concurrency)
    if not args.allow_real_run:
        raise ValueError("--allow-real-run required; default is plan/smoke")
    if dispatch["blockers"]:
        raise ValueError("Preflight blocked: " + "; ".join(dispatch["blockers"]))
    if not args.batch_name.isidentifier() or args.batch_name.startswith("_"):
        raise ValueError("Batch name must be a simple identifier")
    directory = output_path(ROOT / "runs" / args.batch_name / "dispatch.json").parent
    identity = {"runs": digest(dispatch["runs"]), "plan": digest(plan), "source": source_hash(),
                "data": data["prepared_hash"], "budget": digest(budget), "devices": devices,
                "concurrency": args.concurrency, "sizing": dispatch["sizing"]}
    identity_path = directory / "identity.json"
    if identity_path.exists():
        if not args.resume or read_json(identity_path) != identity:
            raise ValueError("Batch exists or incompatible resume (including changed cut list)")
    elif args.resume:
        raise ValueError("Cannot resume nonexistent batch")
    else:
        write_json(identity_path, identity)
    write_json(directory / "dispatch.json", dispatch)
    write_json(directory / "budget.json", budget)
    previous = read_json(directory / "summary.json") if args.resume and (directory / "summary.json").is_file() else {}
    max_seconds = min(dispatch["available_seconds"], budget["max_wall_seconds"] - previous.get("cumulative_elapsed_seconds", 0.))
    if max_seconds <= 0 or previous.get("cumulative_device_seconds", 0.) >= budget["max_gpu_hours"] * 3600:
        raise ValueError("Cumulative resume budget exhausted")
    jobs = [dict(r) for r in dispatch["runs"]]
    for job in jobs:
        status_path = directory / job["id"] / "status.json"
        if args.resume and status_path.is_file():
            status = read_json(status_path)
            job["consumed_seconds"] = status.get("cumulative_elapsed_seconds", 0.)
            job["remaining_timeout_seconds"] = max(0., job["timeout_seconds"] - job["consumed_seconds"])
    def command(job, out, device):
        cmd = [sys.executable, "-m", "te01", "--plan", str(args.plan.resolve()), "_worker", "--prepared", str(Path(args.prepared).resolve()),
               "--dispatch", str(directory / "dispatch.json"), "--budget", str(directory / "budget.json"),
               "--id", job["id"], "--device", device, "--out", str(out), "--allow-real-run"]
        if args.resume and (out / "checkpoint.pt").exists():
            cmd.append("--resume")
        return cmd
    return execute_jobs(jobs, directory, devices, args.concurrency, command,
                        max_seconds=max_seconds, resume=args.resume, memory_gib=budget["memory_gib"],
                        max_device_seconds=budget["max_gpu_hours"] * 3600,cpu_concurrency=plan["execution"].get("cpu_workers",0))


def evaluation_preflight(args, data, plan):
    if not args.allow_real_run or args.budget is None:
        raise ValueError("Real evaluation requires --allow-real-run and --budget")
    if data["blockers"]:
        raise ValueError("Evaluation data prerequisites are blocked")
    budget = read_json(args.budget)
    for key in ("max_wall_seconds", "max_gpu_hours", "memory_gib", "gpu_memory_gib"):
        if type(budget.get(key)) not in (float, int) or not math.isfinite(budget[key]) or budget[key] <= 0:
            raise ValueError("Finite positive evaluation budget required")
    if budget.get("hardware_confirmed") is not True or not args.device.startswith("cuda:"):
        raise ValueError("Confirmed CUDA hardware budget required for real evaluation")
    props = torch.cuda.get_device_properties(args.device)
    if props.total_memory < budget["gpu_memory_gib"] * 2**30:
        raise ValueError("Evaluation VRAM budget exceeds device")
    # Final evaluation belongs to the reserved integration window; it still may
    # not cross the absolute deadline or its own explicit resource budget.
    remaining = (datetime.fromisoformat(plan["deadline"]) - datetime.now(timezone.utc)).total_seconds()
    cap = min(remaining, budget["max_wall_seconds"], budget["max_gpu_hours"] * 3600)
    if cap <= 0:
        raise ValueError("Evaluation deadline exhausted")
    return budget, cap


def evaluation_command(args, data, plan):
    if not data["synthetic"] and args.command == "evaluate":
        budget, cap = evaluation_preflight(args, data, plan)
        directory = output_path(args.out / "summary.json").parent
        if (directory / "summary.json").exists():
            raise ValueError("Use a new evaluation directory")
        def command(job, out, device):
            cmd = [sys.executable, "-m", "te01", "--plan", str(args.plan.resolve()), "_evaluate_worker", "--prepared", str(args.prepared.resolve()),
                   "--checkpoint", str(args.checkpoint.resolve()), "--out", str(out), "--device", device,
                   "--partition", args.partition, "--budget", str(args.budget.resolve()), "--allow-real-run"]
            for field in ("selection", "validation_result"):
                if getattr(args, field):
                    cmd += ["--" + field.replace("_", "-"), str(getattr(args, field).resolve())]
            return cmd
        return execute_jobs([{"id": "evaluate", "depends_on": [], "timeout_seconds": cap}], directory,
                            [args.device], 1, command, max_seconds=cap, memory_gib=budget["memory_gib"], max_device_seconds=cap)
    if not data["synthetic"]:
        budget, _ = evaluation_preflight(args, data, plan)
        torch.cuda.set_per_process_memory_fraction(budget["gpu_memory_gib"] * 2**30 / torch.cuda.get_device_properties(args.device).total_memory, args.device)
    val = read_json(args.validation_result) if args.validation_result else None
    result = evaluate_checkpoint(args.checkpoint, data, partition=args.partition,
                                 frozen_selection=read_json(args.selection) if args.selection else None,
                                 threshold=val["threshold"] if val else None, validation_result=val, device=args.device)
    result["status"] = "completed"
    write_json(args.out / "result.json", result)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,default=ROOT/"experiment_plan.json")
    sub = p.add_subparsers(dest="command")
    for name in ("plan", "batch"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--prepared", type=Path, required=name == "batch")
        cmd.add_argument("--budget", type=Path, required=name == "batch")
        cmd.add_argument("--devices", default="cpu")
        cmd.add_argument("--concurrency", type=int, default=1)
        if name == "plan":
            cmd.add_argument("--out", type=Path)
        else:
            cmd.add_argument("--batch-name", required=True)
            cmd.add_argument("--allow-real-run", action="store_true")
            cmd.add_argument("--resume", action="store_true")
    cmd = sub.add_parser("prepare")
    cmd.add_argument("--catalog", required=True, type=Path)
    cmd.add_argument("--out", required=True, type=Path)
    cmd = sub.add_parser("smoke")
    cmd.add_argument("--device", default="cpu")
    cmd.add_argument("--out", required=True, type=Path)
    for name in ("evaluate", "_evaluate_worker"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--checkpoint", required=True, type=Path)
        cmd.add_argument("--prepared", required=True, type=Path)
        cmd.add_argument("--partition", choices=("val", "test"), default="val")
        cmd.add_argument("--selection", type=Path)
        cmd.add_argument("--validation-result", type=Path)
        cmd.add_argument("--budget", type=Path)
        cmd.add_argument("--device", default="cpu")
        cmd.add_argument("--allow-real-run", action="store_true")
        cmd.add_argument("--out", required=True, type=Path)
    cmd = sub.add_parser("_worker", help=argparse.SUPPRESS)
    for arg in ("prepared", "dispatch", "budget", "out"):
        cmd.add_argument("--" + arg, required=True, type=Path)
    cmd.add_argument("--id", required=True)
    cmd.add_argument("--device", required=True)
    cmd.add_argument("--allow-real-run", action="store_true")
    cmd.add_argument("--resume", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    plan = read_json(args.plan)
    try:
        if args.command in (None, "plan"):
            result = dry_plan(plan, data=load_prepared(args.prepared) if getattr(args, "prepared", None) else None,
                              budget=read_json(args.budget) if getattr(args, "budget", None) else None,
                              devices=getattr(args, "devices", "cpu").split(","), concurrency=getattr(args, "concurrency", 1))
            if getattr(args, "out", None):
                write_json(args.out, result)
            print({k: result[k] for k in ("remaining_seconds", "reserved_seconds", "wall_cap_seconds", "cut", "blockers")})
        elif args.command == "prepare":
            result = prepare(args.catalog, args.out)
            print({k: result[k] for k in ("coverage", "blockers", "prepared_hash")})
        elif args.command == "smoke":
            result = smoke(args.device, args.out)
            print(result)
        elif args.command == "batch":
            result = batch(args, plan)
            print(result)
            return 0 if result["status"] == "completed" else 2
        elif args.command in ("evaluate", "_evaluate_worker"):
            data = load_prepared(args.prepared)
            result = evaluation_command(args, data, plan)
            print(result.get("metrics", result.get("status")))
            return 0 if result["status"] == "completed" else 2
        else:
            data, dispatch, budget = load_prepared(args.prepared), read_json(args.dispatch), read_json(args.budget)
            if not args.allow_real_run or dispatch["blockers"] or dispatch["smoke"] or data["synthetic"]:
                raise ValueError("Worker requires successful real preflight and explicit opt-in")
            if dispatch["source_hash"] != source_hash() or dispatch["data_hash"] != data["prepared_hash"] or dispatch["plan_hash"] != digest(plan) or dispatch["budget_hash"] != digest(budget):
                raise ValueError("Worker input/preflight hash mismatch")
            # Recheck actual remaining time and hardware at every worker dispatch.
            fresh = dry_plan(plan, data=data, budget=budget, devices=dispatch["devices"], concurrency=dispatch["concurrency"])
            if fresh["available_seconds"] <= 0 or any("Unavailable device" in b for b in fresh["blockers"]):
                raise ValueError("Dispatch deadline/hardware no longer valid")
            if args.device.startswith("cuda:"):
                torch.cuda.set_per_process_memory_fraction(budget["gpu_memory_gib"] * 2**30 / torch.cuda.get_device_properties(args.device).total_memory, args.device)
            run = next(r for r in dispatch["runs"] if r["id"] == args.id)
            result = run_experiment(run, data, args.out, device=args.device, problems=dispatch["sizing"]["problems"],
                                    allow_real=True, resume=args.resume, batch_root=args.out.parent, plan=plan, memory_gib=budget["memory_gib"])
            return 0 if result["status"] == "completed" else 2
        return 0
    except Exception as exc:
        if args.command in ("_worker", "_evaluate_worker"):
            write_json(args.out / "failure.json", {"status": "failed", "type": type(exc).__name__, "message": str(exc)})
            traceback.print_exc()
        print(f"TE01: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
