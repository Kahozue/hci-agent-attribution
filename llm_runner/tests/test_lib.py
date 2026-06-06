import json
import pathlib

import pytest

from llm_runner import lib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_pairs():
    return json.loads((ROOT / "data" / "pairs.json").read_text(encoding="utf-8"))


def test_visible_study_removes_answer_and_source_fields():
    study = lib.build_visible_study(load_pairs(), participant_id="llm-test", condition_order="A_then_B")
    assert len(study["trials"]) == 20
    assert study["safety"]["answer_fields_included"] is False

    leaks = lib.find_visible_payload_leaks(study)
    assert leaks == []

    serialized = json.dumps(study, ensure_ascii=False)
    assert "ground_truth" not in serialized
    assert "pair_type" not in serialized
    assert "data/pairs" not in serialized
    assert "analysis/phase" not in serialized
    assert "traces/" not in serialized
    assert "/Users/" not in serialized


def test_condition_a_hides_evidence_and_condition_b_shows_redacted_evidence():
    study = lib.build_visible_study(load_pairs(), participant_id="llm-test", condition_order="A_then_B")
    a_trial = next(t for t in study["trials"] if t["condition"] == "A")
    b_trial = next(t for t in study["trials"] if t["condition"] == "B")

    assert "evidence" not in a_trial["outputs"]["A"]
    assert "evidence" not in a_trial["outputs"]["B"]

    assert b_trial["outputs"]["A"]["evidence"]["trace_refs"][0].startswith("A-trace-")
    assert b_trial["outputs"]["B"]["evidence"]["trace_refs"][0].startswith("B-trace-")
    assert "traces/" not in json.dumps(b_trial, ensure_ascii=False)


def test_prompt_contract_forbids_file_lookup_and_accepts_only_json():
    study = lib.build_visible_study(load_pairs(), participant_id="llm-test", condition_order="A_then_B")
    prompt = lib.format_trial_prompt(study["trials"][0])

    assert "不要查找檔案、原始碼或外部資料" in prompt
    assert "請只輸出一個 JSON 物件" in prompt
    assert "ground_truth" not in prompt
    assert "pair_type" not in prompt


def test_study_pack_rejects_directories_inside_repo():
    study = lib.build_visible_study(load_pairs(), participant_id="llm-test", condition_order="A_then_B")
    with pytest.raises(lib.VisiblePayloadError):
        lib.write_study_pack(study, ROOT / "llm-pack-inside-repo", repo_root=ROOT)


def test_parse_answer_validates_contract():
    parsed = lib.parse_answer('{"choice":"model","confidence":4,"rationale":"工具序列差異較像模型策略不同。"}')
    assert parsed == {"choice": "model", "confidence": 4, "rationale": "工具序列差異較像模型策略不同。"}

    with pytest.raises(lib.AnswerValidationError):
        lib.parse_answer('{"choice":"harness","confidence":9,"rationale":"x"}')


def test_score_answer_doc_adds_truth_only_after_collection():
    pairs = load_pairs()
    study = lib.build_visible_study(pairs, participant_id="llm-test", condition_order="A_then_B")
    raw_answers = {
        "participant_id": "llm-test",
        "condition_order": "A_then_B",
        "answers": [
            {
                "order": study["trials"][0]["order"],
                "pair_id": study["trials"][0]["pair_id"],
                "condition": study["trials"][0]["condition"],
                "scenario": study["trials"][0]["scenario"],
                "choice": "harness",
                "confidence": 5,
                "rationale": "工具序列差異明顯。",
                "time_ms": 1000,
            }
        ],
    }

    assert "ground_truth" not in json.dumps(raw_answers)
    scored = lib.score_answer_doc(pairs, raw_answers)
    assert scored["trials"][0]["ground_truth"] == "harness"
    assert scored["trials"][0]["correct"] is True
    assert scored["summary"]["accuracy"] == 1
