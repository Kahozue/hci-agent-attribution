"""純函式：把 xAI 產物轉成 pair-viewer 用的 pairs。可獨立測試。"""
import copy
import json
import os

GT = {
    "harness_main_effect": "harness",
    "model_main_effect": "model",
    "interaction": "interaction",
}

# 與 xAI runner/phase3_selection.py 的 TOOL_FAMILIES 一致：把各 harness 原生工具名
# 正規化成跨 harness 的 family，避免受試者用工具名稱直接認出 harness（效度保護）。
TOOL_FAMILIES = {
    "bash": "shell", "command_execution": "shell", "execute_code": "shell", "terminal": "shell",
    "edit": "edit", "apply_patch": "edit", "file_change": "edit", "multiedit": "edit",
    "patch": "edit", "write": "edit", "write_file": "edit",
    "glob": "search", "grep": "search", "search_files": "search",
    "read": "read", "read_file": "read",
    "todo_write": "plan", "todowrite": "plan",
}


def tool_family(tool_name):
    normalized = tool_name.replace("-", "_").lower()
    return TOOL_FAMILIES.get(normalized, normalized)


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


def _seq_for_side(contrast, which, side_label, repo_root):
    """工具序列：initial_tool_strategy 直接用 contrast；其餘類型從代表 trace 抽。"""
    key = f"{which}_dominant_family_sequence"
    if key in contrast:
        return contrast[key]
    traces = side_label.get("baseline_traces", [])
    if repo_root and traces:
        path = os.path.join(repo_root, traces[0])
        if os.path.exists(path):
            return _tool_seq(path)
    return []


def labeled_pairs(labels, repo_root=None):
    """20 對已標籤 pair：對應 ground_truth、工具序列、證據。

    三種 decision_kind 的 contrast 結構不同：initial_tool_strategy 有
    *_dominant_family_sequence；task_success_gap／semantic_output_convention 沒有，
    其工具序列由代表 trace（baseline_traces[0]）抽出（需 repo_root）。
    """
    out = []
    for lb in labels:
        c = lb["contrast"]
        ag = lb["method_agreement"]
        dk = lb["decision_kind"]
        left_seq = _seq_for_side(c, "left", lb["left"], repo_root)
        right_seq = _seq_for_side(c, "right", lb["right"], repo_root)
        out.append({
            "pair_type": lb["factorial_label"],
            "ground_truth": GT[lb["factorial_label"]],
            "task_id": lb["task_id"],
            "task_category": lb["task_category"],
            "left": _side(lb["left"], left_seq, ag, dk),
            "right": _side(lb["right"], right_seq, ag, dk),
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
    return [tool_family(tc["tool_name"]) for tc in t.get("tool_calls", [])]


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

SCENARIO_QUOTA = {
    "high_risk_review": 8,
    "switch_after": 8,
    "onboarding": 4,
}

# Proposal 要 20 trial，但上游標籤為 harness/model/interaction 20 對，
# 因此保留 4 對 noise 後，採接近均衡且不增造資料的 5/5/6/4。
GROUND_TRUTH_TARGET = {
    "harness": 5,
    "model": 5,
    "interaction": 6,
    "noise": 4,
}

NOISE_SCENARIOS = ("switch_after", "switch_after", "switch_after", "onboarding")


def _scenario(p):
    if "_scenario_override" in p:
        return p["_scenario_override"]
    if p["pair_type"] == "noise":
        return "switch_after"
    return CAT_SCENARIO.get(p["task_category"], "switch_after")


def _count(items, key):
    counts = {}
    for item in items:
        value = item[key] if key in item else _scenario(item)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _drop_candidate(items, scenario):
    type_counts = _count(items, "ground_truth")
    candidates = [p for p in items if _scenario(p) == scenario and p["ground_truth"] != "noise"]
    removable = [p for p in candidates if type_counts[p["ground_truth"]] > GROUND_TRUTH_TARGET[p["ground_truth"]]]
    if not removable:
        removable = candidates

    def score(p):
        gt = p["ground_truth"]
        overage = type_counts[gt] - GROUND_TRUTH_TARGET.get(gt, 0)
        ratio = type_counts[gt] / GROUND_TRUTH_TARGET.get(gt, max(type_counts[gt], 1))
        return (overage, ratio, p.get("_source_index", 0))

    return max(removable, key=score)


def select_study_pairs(labeled, noise):
    """選出符合 proposal 的 20 題：三情境 8/8/4、四類 ground truth 皆保留。

    上游 xAI labels 已有 20 對但缺 noise；proposal 又要求 20 trial 且含 noise。
    這裡用既有正式重跑補 4 對 noise，再從非 noise 中修剪 4 對，避免把研究擴成
    proposal 以外的 24 題。
    """
    items = []
    for i, p in enumerate(labeled):
        item = copy.deepcopy(p)
        item["_source_index"] = i
        item["_scenario_override"] = _scenario(item)
        items.append(item)

    if len(noise) < GROUND_TRUTH_TARGET["noise"]:
        raise ValueError("noise pairs fewer than proposal target")
    for i, p in enumerate(noise[:GROUND_TRUTH_TARGET["noise"]]):
        item = copy.deepcopy(p)
        item["_source_index"] = len(items) + i
        item["_scenario_override"] = NOISE_SCENARIOS[i] if i < len(NOISE_SCENARIOS) else _scenario(item)
        items.append(item)

    for scenario, target in SCENARIO_QUOTA.items():
        while _count(items, "scenario").get(scenario, 0) > target:
            items.remove(_drop_candidate(items, scenario))

    if len(items) != sum(SCENARIO_QUOTA.values()):
        raise ValueError(f"selected {len(items)} pairs, expected {sum(SCENARIO_QUOTA.values())}")
    if _count(items, "scenario") != SCENARIO_QUOTA:
        raise ValueError(f"scenario quota mismatch: {_count(items, 'scenario')}")
    if _count(items, "ground_truth") != GROUND_TRUTH_TARGET:
        raise ValueError(f"ground-truth target mismatch: {_count(items, 'ground_truth')}")

    return items


def assemble(pairs):
    """指派 pair_id、情境、A/B set，組成 pairs.json 文件。"""
    for i, p in enumerate(pairs):
        p["pair_id"] = f"P{i + 1:02d}"
        p["scenario"] = _scenario(p)
        p["set"] = "Set1" if i % 2 == 0 else "Set2"
        p.pop("_source_index", None)
        p.pop("_scenario_override", None)
    pairs.sort(key=lambda p: p["pair_id"])
    return {
        "schema_version": 1,
        "source": {
            "labels": "analysis/phase3/hci-ground-truth-labels.json",
            "cells": "analysis/phase4/metrics-summary.json",
        },
        "pairs": pairs,
    }
