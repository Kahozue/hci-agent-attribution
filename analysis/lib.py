"""純函式：作答資料 → HCI 指標。可獨立測試。"""
import json
from collections import defaultdict

TYPES = ["harness", "model", "interaction", "noise"]

REQUIRED_TRIAL_FIELDS = {"ground_truth", "choice", "correct", "confidence", "scenario", "condition"}


def _extract_trials(data):
    """容納兩種匯出格式：{"trials": [...]} 或裸 list。"""
    if isinstance(data, dict):
        return data.get("trials", [])
    if isinstance(data, list):
        return data
    return []


def valid_trial(t):
    return isinstance(t, dict) and REQUIRED_TRIAL_FIELDS <= set(t.keys())


def load_trials(paths):
    """載入並只保留欄位齊全、可計分的 trial（殘缺格式自動略過）。"""
    trials = []
    for p in paths:
        for t in _extract_trials(json.load(open(p))):
            if valid_trial(t):
                trials.append(t)
    return trials


def accuracy(trials):
    return sum(t["correct"] for t in trials) / len(trials) if trials else 0.0


def accuracy_by(trials, key):
    g = defaultdict(list)
    for t in trials:
        g[t[key]].append(t)
    return {k: accuracy(v) for k, v in g.items()}


def confusion_matrix(trials):
    """真值類型 × 受試者所選。回答 RQ2（哪類最常被誤歸）。"""
    cm = {t: {c: 0 for c in TYPES} for t in TYPES}
    for tr in trials:
        cm[tr["ground_truth"]][tr["choice"]] += 1
    return cm


def calibration(trials):
    """各信心等級的實際正確率。回答 RQ3（信任校準）。"""
    g = defaultdict(list)
    for t in trials:
        g[t["confidence"]].append(t["correct"])
    return {c: sum(v) / len(v) for c, v in g.items()}


def blind_adoption_rate(trials, scenario=None):
    """高信心（>=4）卻答錯的比例＝盲目採納 / automation bias。"""
    sub = [t for t in trials if (scenario is None or t["scenario"] == scenario)]
    if not sub:
        return 0.0
    blind = [t for t in sub if t["confidence"] >= 4 and not t["correct"]]
    return len(blind) / len(sub)
