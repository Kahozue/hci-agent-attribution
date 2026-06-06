"""Trusted helpers for running LLMs as synthetic study participants.

This module deliberately separates raw study materials from visible trial
payloads. Raw pairs include answer fields used for scoring; visible payloads
are the only data an LLM participant should receive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TYPES = ["harness", "model", "interaction", "noise"]
SCENARIOS = ["switch_after", "high_risk_review", "onboarding"]
CONDITIONS = ["A", "B"]
CONDITION_ORDERS = ["A_then_B", "B_then_A"]

STUDY_NAME = "HCI agent attribution pair study"

SCENARIO_COPY = {
    "switch_after": ("切換後", "同一任務已有前次執行紀錄，現在呈現另一份同任務執行摘要供檢視。"),
    "high_risk_review": ("高風險覆核", "此題來自錯誤成本較高的程式變更情境，請先閱讀兩份執行摘要。"),
    "onboarding": ("Onboarding", "此題來自熟悉任務的試用情境，請先閱讀兩份執行摘要。"),
}

CATEGORY_COPY = {
    "bug_fix": ("Bug 修復", "修正既有錯誤並讓測試通過"),
    "add_tests": ("補測試", "增加測試覆蓋以驗證既有功能"),
    "add_logging": ("加入 logging", "補上觀測與紀錄，降低後續除錯成本"),
    "benchmark": ("Benchmark", "在固定任務中檢查流程執行結果"),
}

DECISION_KIND_COPY = {
    "initial_tool_strategy": "初始工具策略",
    "semantic_output_convention": "輸出慣例（語意）差異",
    "task_success_gap": "任務成敗落差",
    "noise": "重跑變異",
}

CHOICE_COPY = {
    "harness": "提示、工具、skill 或流程框架造成差異",
    "model": "底層模型本身造成差異",
    "interaction": "特定 model 與 harness 組合才出現的差異",
    "noise": "同設定重跑時的隨機變異",
}

ANSWER_SCHEMA = {
    "choice": TYPES,
    "confidence": "integer 1..5",
    "rationale": "one concise sentence",
}

FORBIDDEN_VISIBLE_KEYS = {
    "ground_truth",
    "pair_type",
    "set",
    "config",
    "source",
}

FORBIDDEN_VISIBLE_SNIPPETS = [
    "analysis/phase",
    "data/pairs",
    "/Users/",
    "traces/",
    "hci-ground-truth",
    "metrics-summary",
]


class AnswerValidationError(ValueError):
    """Raised when an LLM answer does not match the JSON contract."""


class VisiblePayloadError(ValueError):
    """Raised when a visible payload leaks raw-study-only fields."""


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ensure_pack_dir_outside_repo(pack_dir: str | Path, repo_root: str | Path) -> None:
    pack = Path(pack_dir).resolve()
    root = Path(repo_root).resolve()
    if pack == root or root in pack.parents:
        raise VisiblePayloadError(f"study pack directory must be outside the project repo: {pack}")


def task_title(pair: dict[str, Any]) -> str:
    category, _ = CATEGORY_COPY.get(pair.get("task_category"), (pair.get("task_category") or "任務", "coding 任務"))
    return f"{category}：{pair.get('task_id')}"


def task_context(pair: dict[str, Any]) -> str:
    _, scenario = SCENARIO_COPY.get(pair.get("scenario"), (pair.get("scenario"), "請閱讀兩份執行摘要。"))
    _, category = CATEGORY_COPY.get(pair.get("task_category"), ("", "coding 任務"))
    return f"情境：{scenario} 任務類型：{category}。請依目前資訊完成下方選擇與信心評估。"


def build_sequence(pairs: list[dict[str, Any]], condition_order: str) -> list[dict[str, Any]]:
    if condition_order not in CONDITION_ORDERS:
        raise ValueError(f"condition_order must be one of {CONDITION_ORDERS}")

    set1 = [p for p in pairs if p.get("set") == "Set1"]
    set2 = [p for p in pairs if p.get("set") == "Set2"]
    if condition_order == "A_then_B":
        blocks = [(set1, "A"), (set2, "B")]
    else:
        blocks = [(set2, "B"), (set1, "A")]

    seq = []
    for block_pairs, condition in blocks:
        for pair in block_pairs:
            seq.append({"pair": pair, "condition": condition})
    return [{**item, "order": i + 1} for i, item in enumerate(seq)]


def _redacted_trace_refs(side_label: str, refs: list[str] | None) -> list[str]:
    return [f"{side_label}-trace-{i + 1}" for i, _ in enumerate(refs or [])]


def _visible_side(side: dict[str, Any], condition: str, side_label: str) -> dict[str, Any]:
    visible = {
        "tool_sequence": list(side.get("tool_sequence") or []),
        "outcome": side.get("outcome") or "無結果紀錄",
    }
    if condition == "B":
        evidence = side.get("evidence") or {}
        visible["evidence"] = {
            "method_agreement": evidence.get("method_agreement") or "未提供",
            "trace_refs": _redacted_trace_refs(side_label, evidence.get("trace_refs")),
            "decision_kind": DECISION_KIND_COPY.get(evidence.get("decision_kind"), evidence.get("decision_kind") or "未提供"),
        }
    return visible


def visible_trial(seq_item: dict[str, Any]) -> dict[str, Any]:
    pair = seq_item["pair"]
    condition = seq_item["condition"]
    scenario_label, _ = SCENARIO_COPY.get(pair.get("scenario"), (pair.get("scenario"), ""))
    return {
        "order": seq_item["order"],
        "pair_id": pair["pair_id"],
        "condition": condition,
        "scenario": pair.get("scenario"),
        "scenario_label": scenario_label,
        "task_title": task_title(pair),
        "task_context": task_context(pair),
        "outputs": {
            "A": _visible_side(pair.get("left") or {}, condition, "A"),
            "B": _visible_side(pair.get("right") or {}, condition, "B"),
        },
    }


def build_visible_study(
    pairs_doc: dict[str, Any],
    *,
    participant_id: str,
    condition_order: str,
) -> dict[str, Any]:
    trials = [visible_trial(item) for item in build_sequence(pairs_doc["pairs"], condition_order)]
    study = {
        "schema_version": 1,
        "study_name": STUDY_NAME,
        "participant_id": participant_id,
        "condition_order": condition_order,
        "answer_schema": ANSWER_SCHEMA,
        "choices": CHOICE_COPY,
        "safety": {
            "answer_fields_included": False,
            "raw_source_fields_included": False,
            "trace_refs_redacted": True,
        },
        "trials": trials,
    }
    assert_visible_payload(study)
    return study


def _walk_payload(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            items.extend(_walk_payload(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(_walk_payload(child, f"{path}[{index}]"))
    return items


def find_visible_payload_leaks(payload: Any) -> list[str]:
    leaks: list[str] = []
    for path, value in _walk_payload(payload):
        if isinstance(value, dict):
            for key in value:
                if key in FORBIDDEN_VISIBLE_KEYS:
                    leaks.append(f"{path}.{key}")
        if isinstance(value, str):
            for snippet in FORBIDDEN_VISIBLE_SNIPPETS:
                if snippet in value:
                    leaks.append(f"{path} contains {snippet!r}")
    return leaks


def assert_visible_payload(payload: Any) -> None:
    leaks = find_visible_payload_leaks(payload)
    if leaks:
        raise VisiblePayloadError("visible payload leaks raw fields: " + ", ".join(leaks[:10]))


def format_trial_prompt(trial: dict[str, Any]) -> str:
    assert_visible_payload(trial)
    return "\n".join(
        [
            "你正在參與一個 HCI 歸因判斷測試。只能根據本題提供的資訊作答，不要查找檔案、原始碼或外部資料。",
            "請在四種類型中選一個：",
            *[f"- {key}: {desc}" for key, desc in CHOICE_COPY.items()],
            '請只輸出一個 JSON 物件，格式為：{"choice":"harness|model|interaction|noise","confidence":1,"rationale":"一句理由"}',
            "本題資料：",
            json.dumps(trial, ensure_ascii=False, indent=2),
        ]
    )


def extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise AnswerValidationError("answer must contain a JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AnswerValidationError(f"answer JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise AnswerValidationError("answer JSON must be an object")
    return data


def parse_answer(text: str) -> dict[str, Any]:
    data = extract_json_object(text)
    choice = str(data.get("choice", "")).strip().lower()
    if choice not in TYPES:
        raise AnswerValidationError(f"choice must be one of {TYPES}")
    try:
        confidence = int(data.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise AnswerValidationError("confidence must be an integer from 1 to 5") from exc
    if confidence < 1 or confidence > 5:
        raise AnswerValidationError("confidence must be an integer from 1 to 5")
    rationale = str(data.get("rationale") or "").strip()
    if not rationale:
        raise AnswerValidationError("rationale must be a non-empty sentence")
    return {"choice": choice, "confidence": confidence, "rationale": rationale}


def raw_answer_record(trial: dict[str, Any], answer: dict[str, Any], *, time_ms: int) -> dict[str, Any]:
    return {
        "order": trial["order"],
        "pair_id": trial["pair_id"],
        "condition": trial["condition"],
        "scenario": trial["scenario"],
        "choice": answer["choice"],
        "confidence": answer["confidence"],
        "rationale": answer["rationale"],
        "time_ms": time_ms,
    }


def empty_group() -> dict[str, Any]:
    return {"total": 0, "correct": 0, "accuracy": 0, "meanConfidence": 0, "meanTimeSeconds": 0}


def group_summary(trials: list[dict[str, Any]]) -> dict[str, Any]:
    if not trials:
        return empty_group()
    correct = sum(1 for t in trials if t.get("correct"))
    confidence = sum(float(t.get("confidence") or 0) for t in trials)
    time_ms = sum(float(t.get("time_ms") or 0) for t in trials)
    return {
        "total": len(trials),
        "correct": correct,
        "accuracy": correct / len(trials),
        "meanConfidence": confidence / len(trials),
        "meanTimeSeconds": time_ms / len(trials) / 1000,
    }


def summarize_by(trials: list[dict[str, Any]], key: str, values: list[str]) -> dict[str, Any]:
    return {value: group_summary([t for t in trials if t.get(key) == value]) for value in values}


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    base = group_summary(trials)
    confusion = {truth: {choice: 0 for choice in TYPES} for truth in TYPES}
    for trial in trials:
        truth = trial.get("ground_truth")
        choice = trial.get("choice")
        if truth in confusion and choice in confusion[truth]:
            confusion[truth][choice] += 1

    calibration = {confidence: group_summary([t for t in trials if int(t.get("confidence") or 0) == confidence]) for confidence in range(1, 6)}
    high_risk = [t for t in trials if t.get("scenario") == "high_risk_review"]
    high_risk_blind = [t for t in high_risk if int(t.get("confidence") or 0) >= 4 and not t.get("correct")]

    return {
        **base,
        "byCondition": summarize_by(trials, "condition", CONDITIONS),
        "byScenario": summarize_by(trials, "scenario", SCENARIOS),
        "byGroundTruth": summarize_by(trials, "ground_truth", TYPES),
        "calibration": calibration,
        "confusion": confusion,
        "highRiskBlindAdoptionRate": len(high_risk_blind) / len(high_risk) if high_risk else 0,
    }


def score_answer_doc(pairs_doc: dict[str, Any], answer_doc: dict[str, Any]) -> dict[str, Any]:
    by_id = {pair["pair_id"]: pair for pair in pairs_doc["pairs"]}
    answers = answer_doc.get("answers") or answer_doc.get("trials") or []
    scored_trials = []
    for answer in answers:
        pair = by_id.get(answer.get("pair_id"))
        if not pair:
            raise ValueError(f"unknown pair_id: {answer.get('pair_id')}")
        choice = answer.get("choice")
        if choice not in TYPES:
            raise AnswerValidationError(f"choice must be one of {TYPES}")
        confidence = int(answer.get("confidence"))
        if confidence < 1 or confidence > 5:
            raise AnswerValidationError("confidence must be an integer from 1 to 5")
        ground_truth = pair["ground_truth"]
        scored_trials.append(
            {
                "pair_id": pair["pair_id"],
                "condition": answer["condition"],
                "scenario": pair["scenario"],
                "choice": choice,
                "ground_truth": ground_truth,
                "correct": choice == ground_truth,
                "confidence": confidence,
                "rationale": str(answer.get("rationale") or ""),
                "time_ms": int(answer.get("time_ms") or 0),
                "order": int(answer["order"]),
            }
        )

    return {
        "schema_version": 1,
        "participant_id": answer_doc.get("participant_id") or "llm-anon",
        "started_at": answer_doc.get("started_at"),
        "finished_at": answer_doc.get("finished_at"),
        "condition_order": answer_doc.get("condition_order"),
        "summary": summarize_trials(scored_trials),
        "trials": scored_trials,
    }


def write_study_pack(study: dict[str, Any], pack_dir: str | Path, *, repo_root: str | Path | None = None) -> list[Path]:
    assert_visible_payload(study)
    if repo_root is not None:
        ensure_pack_dir_outside_repo(pack_dir, repo_root)
    root = Path(pack_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    visible_path = root / "visible_trials.json"
    write_json(visible_path, study)
    written.append(visible_path)

    readme = root / "README_FOR_LLM.txt"
    readme.write_text(
        "\n".join(
            [
                "HCI attribution study pack",
                "",
                "Only use the files in this directory. Do not inspect source code, raw pairs, or external files.",
                "Answer each prompt with JSON only:",
                '{"choice":"harness|model|interaction|noise","confidence":1,"rationale":"one sentence"}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    written.append(readme)

    prompt_dir = root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    for trial in study["trials"]:
        prompt_path = prompt_dir / f"trial-{trial['order']:02d}.txt"
        prompt_path.write_text(format_trial_prompt(trial), encoding="utf-8")
        written.append(prompt_path)

    return written
