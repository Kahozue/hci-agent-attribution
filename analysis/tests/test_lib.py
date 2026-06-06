import pathlib

from analysis import lib

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_accuracy_overall_and_by_condition():
    trials = lib.load_trials([str(FIX / "responses.json")])
    assert len(trials) == 4
    assert lib.accuracy(trials) == 0.5
    by = lib.accuracy_by(trials, "condition")
    assert by["A"] == 0.5 and by["B"] == 0.5


def test_load_trials_handles_bare_list_and_skips_malformed():
    # 裸 list 格式 + 缺必要欄位的筆數應被略過（如殘缺的 008 匯出）
    trials = lib.load_trials([str(FIX / "responses_messy.json")])
    assert len(trials) == 1
    assert trials[0]["ground_truth"] == "harness"


def test_confusion_calibration_blind_adoption():
    trials = lib.load_trials([str(FIX / "responses.json")])
    cm = lib.confusion_matrix(trials)
    assert cm["harness"]["model"] == 1
    assert cm["harness"]["harness"] == 2
    cal = lib.calibration(trials)
    assert cal[5] == 0.0 and cal[3] == 1.0
    # 高風險、confidence>=4、答錯 → 盲目採納（P01 符合；P03 高風險但答對不算）
    assert lib.blind_adoption_rate(trials, scenario="high_risk_review") == 0.5
