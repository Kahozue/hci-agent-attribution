"""讀 responses-*.json → metrics.json ＋ 圖（PNG）。

用法（於 hci-agent-attribution 根目錄、venv 內）：
    python -m analysis.analyze --responses "data/responses-*.json" --outdir analysis/figures
"""
import argparse
import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from analysis import lib  # noqa: E402


def _use_cjk_font():
    candidates = [
        "PingFang TC", "Heiti TC", "Arial Unicode MS",
        "Noto Sans CJK TC", "Noto Sans CJK SC",
        "Microsoft JhengHei", "WenQuanYi Zen Hei",
    ]
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in candidates:
        if any(cand.lower() in n.lower() for n in names):
            plt.rcParams["font.sans-serif"] = [cand]
            break
    plt.rcParams["axes.unicode_minus"] = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", nargs="+", required=True, help="responses-*.json（可用萬用字元）")
    ap.add_argument("--outdir", default="analysis/figures")
    a = ap.parse_args()

    paths = sorted({p for pat in a.responses for p in glob.glob(pat)})
    if not paths:
        raise SystemExit("找不到任何 responses 檔")
    trials = lib.load_trials(paths)
    os.makedirs(a.outdir, exist_ok=True)
    _use_cjk_font()

    metrics = {
        "n_trials": len(trials),
        "n_participants": len(paths),
        "accuracy_overall": lib.accuracy(trials),
        "accuracy_by_condition": lib.accuracy_by(trials, "condition"),
        "accuracy_by_scenario": lib.accuracy_by(trials, "scenario"),
        "confusion_matrix": lib.confusion_matrix(trials),
        "calibration": lib.calibration(trials),
        "blind_adoption_high_risk": lib.blind_adoption_rate(trials, "high_risk_review"),
        "blind_adoption_overall": lib.blind_adoption_rate(trials),
    }
    with open(os.path.join(a.outdir, "metrics.json"), "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=1)

    # 圖1：A vs B 正確率
    cond = metrics["accuracy_by_condition"]
    if cond:
        plt.figure()
        plt.bar(list(cond), [cond[k] for k in cond])
        plt.ylim(0, 1)
        plt.ylabel("歸因正確率")
        plt.title("條件 A（摘要）vs 條件 B（證據）")
        plt.savefig(os.path.join(a.outdir, "accuracy_by_condition.png"), dpi=150, bbox_inches="tight")
        plt.close()

    # 圖2：信任校準
    cal = metrics["calibration"]
    if cal:
        xs = sorted(cal)
        plt.figure()
        plt.plot(xs, [cal[x] for x in xs], marker="o", label="實際正確率")
        plt.plot([1, 5], [0, 1], "--", color="gray", label="完美校準")
        plt.xlabel("信心 (1-5)")
        plt.ylabel("實際正確率")
        plt.ylim(0, 1)
        plt.title("信任校準")
        plt.legend()
        plt.savefig(os.path.join(a.outdir, "calibration.png"), dpi=150, bbox_inches="tight")
        plt.close()

    print(f"wrote metrics.json + figures to {a.outdir} ({len(trials)} trials, {len(paths)} participants)")


if __name__ == "__main__":
    main()
