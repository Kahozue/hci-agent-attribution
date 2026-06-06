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
