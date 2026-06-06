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
