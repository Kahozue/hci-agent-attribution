"""純函式：把 xAI 產物轉成 pair-viewer 用的 pairs。可獨立測試。"""
import json
import os

GT = {
    "harness_main_effect": "harness",
    "model_main_effect": "model",
    "interaction": "interaction",
}


def _side(side_label, contrast_seq, agreement, decision_kind):
    ac, mc = agreement["agreement_count"], agreement["method_count"]
    return {
        "tool_sequence": contrast_seq,
        "outcome": None,  # 由 attach_outcomes 補
        "config": side_label["config"],
        "evidence": {
            "method_agreement": f"{ac}/{mc}",
            "trace_refs": side_label["baseline_traces"],
            "decision_kind": decision_kind,
        },
    }


def labeled_pairs(labels):
    """20 對已標籤 pair：對應 ground_truth、工具序列、證據。"""
    out = []
    for lb in labels:
        c = lb["contrast"]
        ag = lb["method_agreement"]
        dk = lb["decision_kind"]
        out.append({
            "pair_type": lb["factorial_label"],
            "ground_truth": GT[lb["factorial_label"]],
            "task_id": lb["task_id"],
            "task_category": lb["task_category"],
            "left": _side(lb["left"], c["left_dominant_family_sequence"], ag, dk),
            "right": _side(lb["right"], c["right_dominant_family_sequence"], ag, dk),
        })
    return out


def _cell_index(cells):
    return {(c["config_id"], c["task_id"]): c for c in cells}


def attach_outcomes(pairs, cells):
    """從 cell_summaries 補每邊成敗率。"""
    idx = _cell_index(cells)
    for p in pairs:
        for side in ("left", "right"):
            c = idx.get((p[side]["config"], p["task_id"]))
            if c:
                p[side]["outcome"] = f'{c["success_count"]}/{c["n"]} 通過'
    return pairs


NOISE_NOTE = "同 config 兩次重跑；M1–M4 不適用，差異屬執行期變異"


def _tool_seq(trace_path):
    t = json.load(open(trace_path))
    return [tc["tool_name"].lower() for tc in t.get("tool_calls", [])]


def noise_pairs(cells, repo_root, want=4):
    """從 repeat_stability<1 的格，配同 config 兩次重跑、工具序列不同者為 noise pair。"""
    out = []
    for c in cells:
        if c.get("repeat_stability", 1.0) >= 1.0:
            continue
        paths = c.get("trace_paths", [])
        if len(paths) < 2:
            continue
        p1 = os.path.join(repo_root, paths[0])
        p2 = os.path.join(repo_root, paths[1])
        if not (os.path.exists(p1) and os.path.exists(p2)):
            continue
        s1, s2 = _tool_seq(p1), _tool_seq(p2)
        if s1 == s2:
            continue

        def mk(seq):
            return {
                "tool_sequence": seq,
                "outcome": f'{c["success_count"]}/{c["n"]} 通過',
                "config": c["config_id"],
                "evidence": {
                    "method_agreement": NOISE_NOTE,
                    "trace_refs": [paths[0]],
                    "decision_kind": "noise",
                },
            }

        out.append({
            "pair_type": "noise",
            "ground_truth": "noise",
            "task_id": c["task_id"],
            "task_category": c.get("task_category", ""),
            "left": mk(s1),
            "right": mk(s2),
        })
        if len(out) >= want:
            break
    return out


CAT_SCENARIO = {
    "benchmark": "switch_after",
    "bug_fix": "high_risk_review",
    "add_logging": "high_risk_review",
    "add_tests": "onboarding",
}


def _scenario(p):
    if p["pair_type"] == "noise":
        return "switch_after"
    return CAT_SCENARIO.get(p["task_category"], "switch_after")


def assemble(pairs):
    """指派 pair_id、情境、A/B set，組成 pairs.json 文件。"""
    for i, p in enumerate(pairs):
        p["pair_id"] = f"P{i + 1:02d}"
        p["scenario"] = _scenario(p)
        p["set"] = "Set1" if i % 2 == 0 else "Set2"
    pairs.sort(key=lambda p: p["pair_id"])
    return {
        "schema_version": 1,
        "source": {
            "labels": "analysis/phase3/hci-ground-truth-labels.json",
            "cells": "analysis/phase4/metrics-summary.json",
        },
        "pairs": pairs,
    }
