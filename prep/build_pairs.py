"""在 xai-harness-faithfulness repo 旁執行；輸出 data/pairs.json。

用法（於 hci-agent-attribution 根目錄）：
    PYTHONPATH=. python3 prep/build_pairs.py \\
        --xai-root /data/repos/xai-harness-faithfulness \\
        --out data/pairs.json
"""
import argparse
import json
import os

from prep import lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xai-root", required=True, help="xai-harness-faithfulness 根目錄")
    ap.add_argument("--out", required=True, help="輸出 pairs.json 路徑")
    a = ap.parse_args()

    labels_path = os.path.join(a.xai_root, "analysis/phase3/hci-ground-truth-labels.json")
    cells_path = os.path.join(a.xai_root, "analysis/phase4/metrics-summary.json")
    labels = json.load(open(labels_path))["labels"]
    cells = json.load(open(cells_path))["cell_summaries"]

    labeled = lib.attach_outcomes(lib.labeled_pairs(labels, repo_root=a.xai_root), cells)
    noise = lib.noise_pairs(cells, repo_root=a.xai_root, want=4)
    doc = lib.assemble(lib.select_study_pairs(labeled, noise))

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(doc['pairs'])} pairs -> {a.out}")


if __name__ == "__main__":
    main()
