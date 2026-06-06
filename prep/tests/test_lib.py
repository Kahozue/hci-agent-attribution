import json
import pathlib

from prep import lib

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_load_labeled_pairs_maps_ground_truth_and_fields():
    labels = json.load(open(FIX / "labels.json"))["labels"]
    pairs = lib.labeled_pairs(labels)
    assert len(pairs) == 2
    p = pairs[0]
    assert p["pair_type"] == "harness_main_effect"
    assert p["ground_truth"] == "harness"
    assert p["task_id"] == "bugfix-t2-03"
    assert p["left"]["tool_sequence"] == ["read", "edit"]
    assert p["right"]["tool_sequence"] == ["read", "search", "edit"]
    assert p["left"]["evidence"]["method_agreement"] == "4/4"
    assert p["left"]["evidence"]["trace_refs"] == ["traces/2/bugfix-t2-03/1.json"]
    assert pairs[1]["ground_truth"] == "model"


def test_tool_family_normalizes_harness_specific_names():
    # 避免 harness 原生工具名洩漏身份
    assert lib.tool_family("Bash") == "shell"
    assert lib.tool_family("read_file") == "read"
    assert lib.tool_family("Patch") == "edit"
    assert lib.tool_family("search_files") == "search"
    assert lib.tool_family("TodoWrite") == "plan"


def test_labeled_pairs_falls_back_to_trace_when_no_tool_sequence():
    # task_success_gap 的 contrast 沒有 *_dominant_family_sequence，工具序列要從 trace 抽
    labels = json.load(open(FIX / "labels_success_gap.json"))["labels"]
    pairs = lib.labeled_pairs(labels, repo_root=str(FIX))
    assert pairs[0]["pair_type"] == "interaction"
    assert pairs[0]["ground_truth"] == "interaction"
    assert pairs[0]["left"]["tool_sequence"] == ["read", "shell"]
    # 右邊 trace 不存在 → 安全 fallback 為空序列
    assert pairs[0]["right"]["tool_sequence"] == []


def test_attach_outcomes_from_cells():
    labels = json.load(open(FIX / "labels.json"))["labels"]
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.attach_outcomes(lib.labeled_pairs(labels), cells)
    assert pairs[0]["left"]["outcome"] == "3/3 通過"
    assert pairs[0]["right"]["outcome"] == "2/3 通過"


def test_build_noise_pairs_from_traces():
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.noise_pairs(cells, repo_root=str(FIX), want=1)
    assert len(pairs) == 1
    np_ = pairs[0]
    assert np_["ground_truth"] == "noise"
    assert np_["pair_type"] == "noise"
    assert np_["left"]["tool_sequence"] == ["read", "edit"]
    assert np_["right"]["tool_sequence"] == ["read", "shell", "edit"]
    assert "重跑" in np_["left"]["evidence"]["method_agreement"]


def test_assemble_pairs_json_structure():
    labels = json.load(open(FIX / "labels.json"))["labels"]
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.attach_outcomes(lib.labeled_pairs(labels), cells)
    pairs += lib.noise_pairs(cells, repo_root=str(FIX), want=1)
    doc = lib.assemble(pairs)
    ids = [p["pair_id"] for p in doc["pairs"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert all(p["scenario"] in {"switch_after", "high_risk_review", "onboarding"} for p in doc["pairs"])
    assert all(p["set"] in {"Set1", "Set2"} for p in doc["pairs"])
    assert doc["schema_version"] == 1


def test_select_study_pairs_matches_proposal_counts():
    def pair(pair_type, ground_truth, task_category):
        return {
            "pair_type": pair_type,
            "ground_truth": ground_truth,
            "task_id": f"{task_category}-{ground_truth}",
            "task_category": task_category,
            "left": {"tool_sequence": ["read"], "outcome": "1/1 通過", "config": 1, "evidence": {}},
            "right": {"tool_sequence": ["edit"], "outcome": "1/1 通過", "config": 2, "evidence": {}},
        }

    labeled = (
        [pair("harness_main_effect", "harness", "bug_fix") for _ in range(6)]
        + [pair("model_main_effect", "model", "benchmark") for _ in range(6)]
        + [pair("interaction", "interaction", "bug_fix") for _ in range(5)]
        + [pair("interaction", "interaction", "benchmark") for _ in range(3)]
        + [pair("model_main_effect", "model", "add_tests") for _ in range(2)]
        + [pair("interaction", "interaction", "add_tests") for _ in range(1)]
    )
    noise = [pair("noise", "noise", "add_tests") for _ in range(4)]

    doc = lib.assemble(lib.select_study_pairs(labeled, noise))
    assert len(doc["pairs"]) == 20

    scenarios = {}
    ground_truths = {}
    sets = {}
    for p in doc["pairs"]:
        scenarios[p["scenario"]] = scenarios.get(p["scenario"], 0) + 1
        ground_truths[p["ground_truth"]] = ground_truths.get(p["ground_truth"], 0) + 1
        sets[p["set"]] = sets.get(p["set"], 0) + 1

    assert scenarios == {"high_risk_review": 8, "switch_after": 8, "onboarding": 4}
    assert ground_truths == {"harness": 5, "model": 5, "interaction": 6, "noise": 4}
    assert sets == {"Set1": 10, "Set2": 10}


def test_generated_pairs_json_matches_proposal_contract():
    data_path = pathlib.Path(__file__).parents[2] / "data" / "pairs.json"
    pairs = json.load(open(data_path))["pairs"]

    def counts(key):
        out = {}
        for p in pairs:
            out[p[key]] = out.get(p[key], 0) + 1
        return out

    assert len(pairs) == 20
    assert counts("scenario") == {"high_risk_review": 8, "onboarding": 4, "switch_after": 8}
    assert counts("ground_truth") == {"harness": 5, "interaction": 6, "model": 5, "noise": 4}
    assert counts("set") == {"Set1": 10, "Set2": 10}
