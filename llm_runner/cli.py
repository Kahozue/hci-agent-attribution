"""Command line interface for LLM synthetic participants."""

from __future__ import annotations

import argparse
import os
import random
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .lib import (
    CONDITION_ORDERS,
    AnswerValidationError,
    build_visible_study,
    format_trial_prompt,
    load_json,
    parse_answer,
    raw_answer_record,
    score_answer_doc,
    write_json,
    write_study_pack,
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_pairs_path() -> Path:
    return project_root() / "data" / "pairs.json"


def default_out_path(participant_id: str) -> Path:
    return project_root() / f"responses-{participant_id}.json"


def make_child_env(pack_dir: Path, allow_env: list[str]) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "HOME": str(pack_dir),
        "TMPDIR": str(pack_dir),
        "LANG": os.environ.get("LANG", "zh_TW.UTF-8"),
    }
    for name in allow_env:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def run_model_command(command_text: str, prompt: str, *, pack_dir: Path, timeout: int, allow_env: list[str]) -> str:
    command = shlex.split(command_text)
    if not command:
        raise ValueError("--llm-cmd cannot be empty")
    proc = subprocess.run(
        command,
        input=prompt,
        cwd=pack_dir,
        env=make_child_env(pack_dir, allow_env),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"LLM command failed with exit code {proc.returncode}\nSTDERR:\n{proc.stderr.strip()}\nSTDOUT:\n{proc.stdout.strip()}"
        )
    return proc.stdout


def interactive_answer(prompt: str) -> str:
    print(prompt)
    print("\n請貼上一行 JSON 答案：", file=sys.stderr)
    return input()


def command_pack(args: argparse.Namespace) -> int:
    pairs_doc = load_json(args.pairs)
    study = build_visible_study(
        pairs_doc,
        participant_id=args.participant_id,
        condition_order=args.condition_order,
    )
    written = write_study_pack(study, args.out, repo_root=project_root())
    print(f"wrote sanitized study pack: {Path(args.out).resolve()}")
    print(f"files: {len(written)}")
    return 0


def command_score(args: argparse.Namespace) -> int:
    pairs_doc = load_json(args.pairs)
    answer_doc = load_json(args.answers)
    scored = score_answer_doc(pairs_doc, answer_doc)
    write_json(args.out, scored)
    print(f"wrote scored responses: {Path(args.out).resolve()}")
    print(f"accuracy: {scored['summary']['accuracy']:.3f} ({scored['summary']['correct']}/{scored['summary']['total']})")
    return 0


def command_run(args: argparse.Namespace) -> int:
    pairs_doc = load_json(args.pairs)
    condition_order = args.condition_order or random.choice(CONDITION_ORDERS)
    study = build_visible_study(
        pairs_doc,
        participant_id=args.participant_id,
        condition_order=condition_order,
    )

    started_at = iso_now()
    answers = []
    temp_context = tempfile.TemporaryDirectory(prefix="hci-llm-study-") if args.pack_dir is None else None
    try:
        pack_dir = Path(args.pack_dir or temp_context.name).resolve()
        write_study_pack(study, pack_dir, repo_root=project_root())
        for trial in study["trials"]:
            prompt = format_trial_prompt(trial)
            t0 = time.monotonic()
            if args.llm_cmd:
                raw = run_model_command(
                    args.llm_cmd,
                    prompt,
                    pack_dir=pack_dir,
                    timeout=args.timeout,
                    allow_env=args.allow_env,
                )
            else:
                raw = interactive_answer(prompt)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            answer = parse_answer(raw)
            answers.append(raw_answer_record(trial, answer, time_ms=elapsed_ms))
            print(f"trial {trial['order']:02d}/{len(study['trials'])}: {answer['choice']} confidence={answer['confidence']}", file=sys.stderr)

        raw_doc = {
            "schema_version": 1,
            "participant_id": args.participant_id,
            "started_at": started_at,
            "finished_at": iso_now(),
            "condition_order": condition_order,
            "llm_command_recorded": bool(args.record_command),
            "llm_command": args.llm_cmd if args.record_command else None,
            "study_pack_dir": str(pack_dir) if args.pack_dir else None,
            "answers": answers,
        }
        if args.raw_out:
            write_json(args.raw_out, raw_doc)

        scored = score_answer_doc(pairs_doc, raw_doc)
        out = Path(args.out or default_out_path(args.participant_id))
        write_json(out, scored)
        print(f"wrote scored responses: {out.resolve()}")
        print(f"accuracy: {scored['summary']['accuracy']:.3f} ({scored['summary']['correct']}/{scored['summary']['total']})")
        if args.pack_dir:
            print(f"sanitized pack kept at: {pack_dir}")
        return 0
    except AnswerValidationError as exc:
        print(f"answer validation failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LLMs as locked-down synthetic participants for the HCI attribution study.")
    sub = parser.add_subparsers(dest="command", required=True)

    pack = sub.add_parser("pack", help="write a sanitized study pack for manual LLM runs")
    pack.add_argument("--pairs", default=str(default_pairs_path()))
    pack.add_argument("--out", required=True)
    pack.add_argument("--participant-id", default="llm-pack")
    pack.add_argument("--condition-order", choices=CONDITION_ORDERS, default="A_then_B")
    pack.set_defaults(func=command_pack)

    run = sub.add_parser("run", help="run an LLM CLI command or interactive JSON answers")
    run.add_argument("--pairs", default=str(default_pairs_path()))
    run.add_argument("--participant-id", required=True)
    run.add_argument("--condition-order", choices=CONDITION_ORDERS)
    run.add_argument("--llm-cmd", help="command that reads the prompt from stdin and prints answer JSON to stdout")
    run.add_argument("--out", help="scored responses JSON path; defaults to responses-<participant-id>.json")
    run.add_argument("--raw-out", help="optional raw answer JSON without ground truth")
    run.add_argument("--pack-dir", help="optional directory to keep the sanitized study pack")
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--allow-env", action="append", default=[], help="environment variable name to pass to the child process")
    run.add_argument("--record-command", action="store_true", help="record --llm-cmd in raw output metadata")
    run.set_defaults(func=command_run)

    score = sub.add_parser("score", help="score a raw answer JSON with trusted ground truth")
    score.add_argument("--pairs", default=str(default_pairs_path()))
    score.add_argument("--answers", required=True)
    score.add_argument("--out", required=True)
    score.set_defaults(func=command_score)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
