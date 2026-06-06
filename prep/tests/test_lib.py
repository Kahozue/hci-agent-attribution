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
