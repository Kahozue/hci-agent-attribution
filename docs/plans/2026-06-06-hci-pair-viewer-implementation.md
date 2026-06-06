# HCI pair-viewer 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建一套 pair-viewer 使用者研究工具：把 xAI 的 24 對 contrastive pair 變成可操作的歸因實驗（A/B 兩條件），收資料、做分析、產出回答 RQ1–4 的圖表。

**Architecture:** 三段管線——`prep/build_pairs.py`（VPS：讀 xAI 產物→`data/pairs.json`）→ `viewer/`（靜態單頁，跑 24 題、匯出作答）→ `analysis/analyze.py`（讀作答→指標與圖）。純邏輯（資料組裝、抽題序列、計分、指標）以 TDD 寫；DOM/CSS 以視覺驗證。設計與框架以 `docs/specs/2026-06-06-hci-agent-attribution-design-v1.md` 為準。

**Tech Stack:** Python 3.10（pytest、matplotlib）、原生 JavaScript（ES module，node 內建 test runner）、HTML/CSS。

**資料來源（已實測確認，欄位固定）：**
- `analysis/phase3/hci-ground-truth-labels.json` → `labels[]`，每項：`factorial_label`、`contrast.{left,right}_dominant_family_sequence`、`left/right.{config,harness,model,baseline_traces}`、`method_agreement.{agreement_count,method_count,primary_label,unanimous}`、`decision_kind`、`detail_label`、`task_id`、`task_category`、`config_pair`。
- `analysis/phase4/metrics-summary.json` → `cell_summaries[]`（120 格），每格：`config_id`、`task_id`、`success_count`、`n`、`success_rate`、`repeat_stability`、`trace_paths`、`tool_family_counts`。
- raw trace `traces/<config>/<task>/<run>.json` → `tool_calls[].tool_name`（逐次工具）、`outcome`、`repeat_index`。
- `factorial_label` → `ground_truth` 對應：`harness_main_effect→harness`、`model_main_effect→model`、`interaction→interaction`。

---

## File Structure

| 檔案 | 職責 |
|---|---|
| `prep/build_pairs.py` | xAI 產物 → `data/pairs.json`（24 對） |
| `prep/lib.py` | 純函式：載入標籤、對應成敗、配 noise、分情境、組 schema（可測） |
| `prep/tests/test_lib.py` | pytest |
| `prep/tests/fixtures/*.json` | 迷你假資料（labels、cell_summaries、traces） |
| `data/pairs.json` | 產出（小、入庫） |
| `viewer/study.js` | 純邏輯：對半平衡、抽題序列、計分、組作答紀錄（ES module） |
| `viewer/study.test.mjs` | node 內建 test |
| `viewer/index.html` | 單頁結構 |
| `viewer/app.js` | DOM 綁定（載 pairs.json、渲染、收事件、匯出） |
| `viewer/styles.css` | 乾淨極簡樣式 |
| `analysis/lib.py` | 純函式：正確率、混淆矩陣、信任校準、盲目採納、A/B 差（可測） |
| `analysis/analyze.py` | CLI：讀 responses → 指標 JSON ＋ 圖 |
| `analysis/tests/test_lib.py` | pytest |
| `.gitignore` | 排除受試者資料、venv、`.superpowers/` |
| `README.md` | 結構與執行說明 |

**鐵則（每個 commit 前自檢）：** 介面繁中、禁 emoji、UI 無裝飾可讀性優先；**任何檔案不得含個資**（姓名/學號/email/IP/secrets）；`responses-*.json` 受試者資料**不入庫**；不碰 xAI 360 baseline，noise 只讀既有重跑。

---

## Task 0：Scaffolding 與 .gitignore

**Files:** Create `prep/`, `viewer/`, `analysis/`, `data/`；Create `.gitignore`；Modify `README.md`

- [ ] **Step 1: 建目錄與 .gitignore**

`.gitignore`：
```
# 受試者資料（個資，不入庫）
responses-*.json
viewer/responses-*.json
# 工具與環境
.superpowers/
__pycache__/
*.pyc
.venv/
venv/
analysis/figures/*.png
node_modules/
```

- [ ] **Step 2: 建 Python venv 與相依**

Run:
```bash
cd /path/to/hci-agent-attribution
python3 -m venv .venv && . .venv/bin/activate
pip install pytest matplotlib
```
Expected: 安裝成功。

- [ ] **Step 3: Commit**
```bash
git add .gitignore
git commit -m "chore: add gitignore (exclude participant data, venv, tooling)"
```

---

## Task 1：prep — 載入並轉換 20 對標籤

**Files:** Create `prep/lib.py`、`prep/tests/test_lib.py`、`prep/tests/fixtures/labels.json`

- [ ] **Step 1: 寫 fixture `prep/tests/fixtures/labels.json`**（2 筆即可，涵蓋 harness/model）
```json
{"label_count":2,"labels":[
 {"factorial_label":"harness_main_effect","decision_kind":"initial_tool_strategy","detail_label":"tool_path_style",
  "task_id":"bugfix-t2-03","task_category":"bug_fix","config_pair":[2,3],
  "contrast":{"left_dominant_family_sequence":["read","edit"],"right_dominant_family_sequence":["read","search","edit"]},
  "left":{"config":2,"harness":"opencode","model":"claude-haiku-4-5-20251001","baseline_traces":["traces/2/bugfix-t2-03/1.json"]},
  "right":{"config":3,"harness":"hermes","model":"claude-haiku-4-5-20251001","baseline_traces":["traces/3/bugfix-t2-03/1.json"]},
  "method_agreement":{"agreement_count":4,"method_count":4,"primary_label":"harness_main_effect","unanimous":true}},
 {"factorial_label":"model_main_effect","decision_kind":"initial_tool_strategy","detail_label":"x",
  "task_id":"addtests-t2-04","task_category":"add_tests","config_pair":[2,5],
  "contrast":{"left_dominant_family_sequence":["read","shell"],"right_dominant_family_sequence":["read","edit"]},
  "left":{"config":2,"harness":"opencode","model":"claude-haiku-4-5-20251001","baseline_traces":["traces/2/addtests-t2-04/1.json"]},
  "right":{"config":5,"harness":"opencode","model":"gpt-5.4-mini-2026-03-17","baseline_traces":["traces/5/addtests-t2-04/1.json"]},
  "method_agreement":{"agreement_count":3,"method_count":4,"primary_label":"model_main_effect","unanimous":false}}
]}
```

- [ ] **Step 2: 寫失敗測試 `prep/tests/test_lib.py`**
```python
import json, pathlib
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
```

- [ ] **Step 3: 跑測試確認失敗**
Run: `. .venv/bin/activate && python -m pytest prep/tests/test_lib.py -q`
Expected: FAIL（`lib` 無 `labeled_pairs`）。需要 `prep/__init__.py`（空檔）。

- [ ] **Step 4: 實作 `prep/lib.py`**
```python
GT = {"harness_main_effect": "harness", "model_main_effect": "model", "interaction": "interaction"}

def _side(side_label, contrast_seq, agreement):
    ac, mc = agreement["agreement_count"], agreement["method_count"]
    return {
        "tool_sequence": contrast_seq,
        "outcome": None,  # Task 2 補
        "evidence": {
            "method_agreement": f"{ac}/{mc}",
            "trace_refs": side_label["baseline_traces"],
        },
    }

def labeled_pairs(labels):
    out = []
    for lb in labels:
        c = lb["contrast"]; ag = lb["method_agreement"]
        left = _side(lb["left"], c["left_dominant_family_sequence"], ag)
        right = _side(lb["right"], c["right_dominant_family_sequence"], ag)
        for s, key in ((left, "left"), (right, "right")):
            s["evidence"]["decision_kind"] = lb["decision_kind"]
            s["config"] = lb[key]["config"]
        out.append({
            "pair_type": lb["factorial_label"],
            "ground_truth": GT[lb["factorial_label"]],
            "task_id": lb["task_id"],
            "task_category": lb["task_category"],
            "left": left, "right": right,
        })
    return out
```

- [ ] **Step 5: 跑測試確認通過**
Run: `python -m pytest prep/tests/test_lib.py -q` Expected: PASS（建 `prep/__init__.py`、`prep/tests/__init__.py`）。

- [ ] **Step 6: Commit**
```bash
git add prep/ && git commit -m "feat(prep): load and map labeled contrastive pairs"
```

---

## Task 2：prep — 從 cell_summaries 補成敗率

**Files:** Modify `prep/lib.py`、`prep/tests/test_lib.py`；Create `prep/tests/fixtures/cells.json`

- [ ] **Step 1: fixture `cells.json`**
```json
[{"config_id":2,"task_id":"bugfix-t2-03","success_count":3,"n":3,"success_rate":1.0,"repeat_stability":1.0,"trace_paths":["traces/2/bugfix-t2-03/1.json","traces/2/bugfix-t2-03/2.json","traces/2/bugfix-t2-03/3.json"]},
 {"config_id":3,"task_id":"bugfix-t2-03","success_count":2,"n":3,"success_rate":0.667,"repeat_stability":0.5,"trace_paths":["traces/3/bugfix-t2-03/1.json","traces/3/bugfix-t2-03/2.json","traces/3/bugfix-t2-03/3.json"]}]
```

- [ ] **Step 2: 失敗測試**
```python
def test_attach_outcomes_from_cells():
    labels = json.load(open(FIX / "labels.json"))["labels"]
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.attach_outcomes(lib.labeled_pairs(labels), cells)
    assert pairs[0]["left"]["outcome"] == "3/3 通過"
    assert pairs[0]["right"]["outcome"] == "2/3 通過"
```

- [ ] **Step 3: 跑測試確認失敗** Run: `python -m pytest prep/tests/test_lib.py -q` Expected: FAIL。

- [ ] **Step 4: 實作（加到 `prep/lib.py`）**
```python
def _cell_index(cells):
    return {(c["config_id"], c["task_id"]): c for c in cells}

def attach_outcomes(pairs, cells):
    idx = _cell_index(cells)
    for p in pairs:
        for side in ("left", "right"):
            c = idx.get((p[side]["config"], p["task_id"]))
            if c:
                p[side]["outcome"] = f'{c["success_count"]}/{c["n"]} 通過'
    return pairs
```

- [ ] **Step 5: 跑測試確認通過** Expected: PASS。
- [ ] **Step 6: Commit** `git commit -am "feat(prep): attach success outcomes from cell summaries"`

---

## Task 3：prep — 從 raw trace 配 4 對 noise pair

**Files:** Modify `prep/lib.py`、`prep/tests/test_lib.py`；Create `prep/tests/fixtures/traces/3/bugfix-t2-03/{1,2}.json`

挑選規則：在 `cells` 中取 `repeat_stability < 1.0` 的格（重跑有差異），讀其 `trace_paths` 前兩個 run，抽 `tool_calls[].tool_name`（小寫化當 family）；若兩 run 工具序列不同則成立一對 noise（`ground_truth="noise"`），取前 4 對。

- [ ] **Step 1: fixture 兩個 trace**
`prep/tests/fixtures/traces/3/bugfix-t2-03/1.json`：
```json
{"config_id":3,"task_id":"bugfix-t2-03","repeat_index":1,"outcome":{"success":true},"tool_calls":[{"tool_name":"Read","step":1},{"tool_name":"Edit","step":2}]}
```
`.../2.json`：
```json
{"config_id":3,"task_id":"bugfix-t2-03","repeat_index":2,"outcome":{"success":true},"tool_calls":[{"tool_name":"Read","step":1},{"tool_name":"Shell","step":2},{"tool_name":"Edit","step":3}]}
```

- [ ] **Step 2: 失敗測試**
```python
def test_build_noise_pairs_from_traces():
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.noise_pairs(cells, repo_root=str(FIX), want=1)
    assert len(pairs) == 1
    np_ = pairs[0]
    assert np_["ground_truth"] == "noise"
    assert np_["pair_type"] == "noise"
    assert np_["left"]["tool_sequence"] == ["read", "edit"]
    assert np_["right"]["tool_sequence"] == ["read", "shell", "edit"]
    assert "重跑" in np_["left"]["evidence"]["method_agreement"]  # noise 註記
```

- [ ] **Step 3: 跑測試確認失敗** Expected: FAIL。

- [ ] **Step 4: 實作（加到 `prep/lib.py`）**
```python
import json, os

def _tool_seq(trace_path):
    t = json.load(open(trace_path))
    return [tc["tool_name"].lower() for tc in t.get("tool_calls", [])]

def noise_pairs(cells, repo_root, want=4):
    out = []
    for c in cells:
        if c.get("repeat_stability", 1.0) >= 1.0:
            continue
        paths = c.get("trace_paths", [])
        if len(paths) < 2:
            continue
        p1, p2 = (os.path.join(repo_root, paths[0]), os.path.join(repo_root, paths[1]))
        if not (os.path.exists(p1) and os.path.exists(p2)):
            continue
        s1, s2 = _tool_seq(p1), _tool_seq(p2)
        if s1 == s2:
            continue
        note = "同 config 兩次重跑；M1–M4 不適用，差異屬執行期變異"
        mk = lambda seq: {"tool_sequence": seq, "outcome": f'{c["success_count"]}/{c["n"]} 通過',
                          "config": c["config_id"],
                          "evidence": {"method_agreement": note, "trace_refs": [paths[0]], "decision_kind": "noise"}}
        out.append({"pair_type": "noise", "ground_truth": "noise",
                    "task_id": c["task_id"], "task_category": c.get("task_category", ""),
                    "left": mk(s1), "right": mk(s2)})
        if len(out) >= want:
            break
    return out
```

- [ ] **Step 5: 跑測試確認通過** Expected: PASS。
- [ ] **Step 6: Commit** `git commit -am "feat(prep): construct noise pairs from same-config re-runs"`

---

## Task 4：prep — 分情境、A/B 對半、組裝並寫 pairs.json

**Files:** Modify `prep/lib.py`、`prep/tests/test_lib.py`；Create `prep/build_pairs.py`

情境規則（確定性，目標貼近 proposal 8/8/4，noise 歸 switch_after）：
- noise → `switch_after`（重跑＝「我重跑了一次」情境）。
- 其餘依 `task_category`：`benchmark`→`switch_after`；`bug_fix`,`add_logging`→`high_risk_review`；`add_tests`→`onboarding`。
- 指派後若某情境數量超出，依 `pair_id` 順序溢出到數量最少的情境，使分布穩定可重現。
set 分組：依 `pair_id` 交錯（index 偶數→Set1、奇數→Set2），力求兩 set 類型均衡。

- [ ] **Step 1: 失敗測試**
```python
def test_assemble_pairs_json_structure():
    labels = json.load(open(FIX / "labels.json"))["labels"]
    cells = json.load(open(FIX / "cells.json"))
    pairs = lib.attach_outcomes(lib.labeled_pairs(labels), cells)
    pairs += lib.noise_pairs(cells, repo_root=str(FIX), want=1)
    doc = lib.assemble(pairs)
    ids = [p["pair_id"] for p in doc["pairs"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids))     # 唯一且排序
    assert all(p["scenario"] in {"switch_after","high_risk_review","onboarding"} for p in doc["pairs"])
    assert all(p["set"] in {"Set1","Set2"} for p in doc["pairs"])
    assert doc["schema_version"] == 1
```

- [ ] **Step 2: 跑測試確認失敗** Expected: FAIL。

- [ ] **Step 3: 實作 `assemble`（加到 `prep/lib.py`）**
```python
CAT_SCENARIO = {"benchmark": "switch_after", "bug_fix": "high_risk_review",
                "add_logging": "high_risk_review", "add_tests": "onboarding"}

def _scenario(p):
    if p["pair_type"] == "noise":
        return "switch_after"
    return CAT_SCENARIO.get(p["task_category"], "switch_after")

def assemble(pairs):
    for i, p in enumerate(pairs):
        p["pair_id"] = f"P{i+1:02d}"
        p["scenario"] = _scenario(p)
        p["set"] = "Set1" if i % 2 == 0 else "Set2"
    pairs.sort(key=lambda p: p["pair_id"])
    return {"schema_version": 1,
            "source": {"labels": "analysis/phase3/hci-ground-truth-labels.json",
                       "cells": "analysis/phase4/metrics-summary.json"},
            "pairs": pairs}
```

- [ ] **Step 4: 跑測試確認通過** Expected: PASS。

- [ ] **Step 5: 寫 `prep/build_pairs.py`（CLI，串起來）**
```python
"""在 xai-harness-faithfulness repo 根目錄執行；輸出 pairs.json。"""
import argparse, json, os
from prep import lib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xai-root", required=True, help="xai-harness-faithfulness 根目錄")
    ap.add_argument("--out", required=True, help="輸出 pairs.json 路徑")
    a = ap.parse_args()
    labels = json.load(open(os.path.join(a.xai_root, "analysis/phase3/hci-ground-truth-labels.json")))["labels"]
    cells = json.load(open(os.path.join(a.xai_root, "analysis/phase4/metrics-summary.json")))["cell_summaries"]
    pairs = lib.attach_outcomes(lib.labeled_pairs(labels), cells)
    pairs += lib.noise_pairs(cells, repo_root=a.xai_root, want=4)
    doc = lib.assemble(pairs)
    json.dump(doc, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {len(doc['pairs'])} pairs -> {a.out}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit** `git commit -am "feat(prep): scenario/set assignment + build_pairs CLI"`

---

## Task 5：viewer — study.js 純邏輯（對半平衡＋抽題序列）

**Files:** Create `viewer/study.js`、`viewer/study.test.mjs`

- [ ] **Step 1: 失敗測試 `viewer/study.test.mjs`**
```js
import { test } from "node:test";
import assert from "node:assert";
import { buildSequence } from "./study.js";

test("split-half: 12-block per condition, counterbalanced", () => {
  const pairs = Array.from({length: 24}, (_, i) => ({ pair_id: `P${i+1}`, set: i % 2 ? "Set2" : "Set1" }));
  const seq = buildSequence(pairs, "A_then_B");
  assert.equal(seq.length, 24);
  assert.equal(seq.filter(t => t.condition === "A").length, 12);
  assert.equal(seq.filter(t => t.condition === "B").length, 12);
  // A_then_B: 前 12 為 Set1=A, 後 12 為 Set2=B
  assert.ok(seq.slice(0,12).every(t => t.condition === "A"));
  const seqB = buildSequence(pairs, "B_then_A");
  assert.ok(seqB.slice(0,12).every(t => t.condition === "B"));
});
```

- [ ] **Step 2: 跑測試確認失敗** Run: `node --test viewer/` Expected: FAIL（無 study.js）。

- [ ] **Step 3: 實作 `viewer/study.js`**
```js
// 對半平衡：Set1 一組、Set2 一組；condition_order 決定哪組先、配哪個條件
export function buildSequence(pairs, order) {
  const set1 = pairs.filter(p => p.set === "Set1");
  const set2 = pairs.filter(p => p.set === "Set2");
  const [firstSet, firstCond, secondSet, secondCond] =
    order === "A_then_B" ? [set1, "A", set2, "B"] : [set2, "B", set1, "A"];
  const block = (arr, cond) => arr.map((p, i) => ({ pair: p, condition: cond, order: i }));
  const seq = [...block(firstSet, firstCond), ...block(secondSet, secondCond)];
  return seq.map((t, i) => ({ ...t, order: i + 1 }));
}
```

- [ ] **Step 4: 跑測試確認通過** Run: `node --test viewer/` Expected: PASS。
- [ ] **Step 5: Commit** `git commit -am "feat(viewer): split-half counterbalanced sequence logic"`

---

## Task 6：viewer — study.js 計分與作答紀錄

**Files:** Modify `viewer/study.js`、`viewer/study.test.mjs`

- [ ] **Step 1: 失敗測試（加到 study.test.mjs）**
```js
import { scoreTrial } from "./study.js";
test("scoreTrial records correctness", () => {
  const t = scoreTrial(
    { pair: { pair_id: "P1", ground_truth: "harness", scenario: "high_risk_review" }, condition: "A", order: 1 },
    { choice: "model", confidence: 4, rationale: "x", time_ms: 1200 });
  assert.equal(t.correct, false);
  assert.equal(t.ground_truth, "harness");
  assert.equal(t.choice, "model");
  assert.equal(t.confidence, 4);
  assert.equal(t.condition, "A");
});
```

- [ ] **Step 2: 跑測試確認失敗** Expected: FAIL。

- [ ] **Step 3: 實作（加到 study.js）**
```js
export function scoreTrial(seqItem, answer) {
  const gt = seqItem.pair.ground_truth;
  return {
    pair_id: seqItem.pair.pair_id,
    condition: seqItem.condition,
    scenario: seqItem.pair.scenario,
    choice: answer.choice,
    ground_truth: gt,
    correct: answer.choice === gt,
    confidence: answer.confidence,
    rationale: answer.rationale,
    time_ms: answer.time_ms,
    order: seqItem.order,
  };
}
```

- [ ] **Step 4: 跑測試確認通過** Expected: PASS。
- [ ] **Step 5: Commit** `git commit -am "feat(viewer): trial scoring and response record"`

---

## Task 7：viewer — UI（index.html / app.js / styles.css）

**Files:** Create `viewer/index.html`、`viewer/app.js`、`viewer/styles.css`
**驗證：** 視覺檢查（瀏覽器開 `viewer/index.html`，需與 `data/pairs.json` 同層或可載入）。設計依 spec：上方任務 → 左右並列輸出（條件 B 多顯示證據區）→ 四選一＋信心 1–5＋一句理由 → 揭露正解 → 下一題；24 題完成後匯出 `responses-<id>.json`。乾淨無裝飾、可讀字級。

- [ ] **Step 1: `viewer/index.html`**
```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent 歸因研究</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<main id="app">
  <section id="intro">
    <h1>Agent 差異歸因研究</h1>
    <p>每題會並列兩個 agent 對同一任務的輸出。請判斷兩者差異主要來自哪裡，給出信心與一句理由。</p>
    <label>受試者代號（匿名）：<input id="pid" placeholder="P-anon-01"></label>
    <button id="start">開始</button>
  </section>
  <section id="trial" hidden>
    <header><span id="progress"></span><span id="scenario"></span></header>
    <p id="task"></p>
    <div id="outputs"></div>
    <fieldset id="attribution"><legend>這兩個輸出的差異主要來自？</legend></fieldset>
    <fieldset id="confidence"><legend>信心（1 低 – 5 高）</legend></fieldset>
    <label id="rationale-wrap">一句理由：<input id="rationale"></label>
    <button id="submit">送出並揭露正解</button>
    <div id="reveal" hidden></div>
    <button id="next" hidden>下一題</button>
  </section>
  <section id="done" hidden>
    <h2>完成，謝謝</h2>
    <button id="export">下載作答檔</button>
  </section>
</main>
<script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: `viewer/styles.css`（極簡、可讀、少量層級處理）**
```css
:root { --fg:#1a1a1a; --muted:#555; --line:#d8d8d8; --bg:#fff; --accent:#1f4e79; }
* { box-sizing: border-box; }
body { font-family: system-ui, "Noto Sans CJK TC", sans-serif; color: var(--fg); background: var(--bg);
       line-height: 1.7; max-width: 980px; margin: 0 auto; padding: 24px; font-size: 16px; }
h1 { font-size: 24px; } h2 { font-size: 20px; }
#trial header { display: flex; justify-content: space-between; color: var(--muted); margin-bottom: 8px; }
#task { font-weight: 600; }
#outputs { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 12px 0; }
.output { border: 1px solid var(--line); border-radius: 6px; padding: 14px; }
.output h3 { margin: 0 0 8px; font-size: 17px; }
.evidence { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); color: var(--muted); }
fieldset { border: 1px solid var(--line); border-radius: 6px; margin: 12px 0; padding: 12px; }
.choice, .conf { display: inline-block; margin: 4px 8px 4px 0; padding: 8px 12px; border: 1px solid var(--line);
                 border-radius: 6px; cursor: pointer; }
.choice.sel, .conf.sel { border-color: var(--accent); background: #eef3f9; font-weight: 600; }
input { font-size: 16px; padding: 6px 8px; } button { font-size: 16px; padding: 8px 16px; cursor: pointer; }
#rationale { width: 100%; }
#reveal { margin: 12px 0; padding: 12px; border-left: 4px solid var(--accent); background: #f6f8fb; }
[hidden] { display: none !important; }
```

- [ ] **Step 3: `viewer/app.js`（DOM 綁定）**
```js
import { buildSequence, scoreTrial } from "./study.js";

const GT_LABEL = { harness: "Harness（框架）", model: "Model（模型）", interaction: "交互", noise: "雜訊" };
const CHOICES = [["harness","Harness（提示/工具/skill 設計）"],["model","Model（底層模型）"],
                 ["interaction","交互（特定組合的異常）"],["noise","雜訊（同設定重跑的隨機差異）"]];
const SCEN = { switch_after:"切換後", high_risk_review:"高風險覆核", onboarding:"Onboarding" };
const $ = s => document.querySelector(s);
let state = { seq: [], i: 0, pid: "", order: "", trials: [], startedAt: "", t0: 0, ans: {} };

async function load() {
  const pairs = (await (await fetch("../data/pairs.json")).json()).pairs;
  state.order = Math.random() < 0.5 ? "A_then_B" : "B_then_A";
  state.seq = buildSequence(pairs, state.order);
}
function renderSide(side, cond) {
  const ev = (cond === "B" && side.evidence)
    ? `<div class="evidence">M1–M4：${side.evidence.method_agreement}<br>trace：${(side.evidence.trace_refs||[]).join(", ")}<br>判斷類型：${side.evidence.decision_kind||""}</div>` : "";
  return `<div class="output"><h3>${side.label||"輸出"}</h3>
    <div>工具序列：${(side.tool_sequence||[]).join(" → ")}</div>
    <div>結果：${side.outcome||"—"}</div>${ev}</div>`;
}
function renderTrial() {
  const item = state.seq[state.i], p = item.pair;
  $("#progress").textContent = `第 ${state.i+1} / ${state.seq.length} 題`;
  $("#scenario").textContent = `情境：${SCEN[p.scenario]||p.scenario}`;
  $("#task").textContent = `任務：${p.task_id}`;
  p.left.label = "輸出 A"; p.right.label = "輸出 B";
  $("#outputs").innerHTML = renderSide(p.left, item.condition) + renderSide(p.right, item.condition);
  $("#attribution").innerHTML = "<legend>這兩個輸出的差異主要來自？</legend>" +
    CHOICES.map(([v,t]) => `<span class="choice" data-v="${v}">${t}</span>`).join("");
  $("#confidence").innerHTML = "<legend>信心（1 低 – 5 高）</legend>" +
    [1,2,3,4,5].map(n => `<span class="conf" data-v="${n}">${n}</span>`).join("");
  $("#rationale").value = ""; $("#reveal").hidden = true; $("#next").hidden = true;
  $("#submit").hidden = false; state.ans = {}; state.t0 = performance.now();
  bindSelect("#attribution", ".choice", "choice");
  bindSelect("#confidence", ".conf", "confidence");
}
function bindSelect(scope, sel, key) {
  document.querySelectorAll(`${scope} ${sel}`).forEach(el => el.onclick = () => {
    document.querySelectorAll(`${scope} ${sel}`).forEach(e => e.classList.remove("sel"));
    el.classList.add("sel"); state.ans[key] = el.dataset.v;
  });
}
function submit() {
  if (!state.ans.choice || !state.ans.confidence) { alert("請選擇歸因與信心"); return; }
  const item = state.seq[state.i];
  const trial = scoreTrial(item, { choice: state.ans.choice, confidence: Number(state.ans.confidence),
    rationale: $("#rationale").value, time_ms: Math.round(performance.now() - state.t0) });
  state.trials.push(trial);
  $("#reveal").innerHTML = `正解：<b>${GT_LABEL[trial.ground_truth]}</b>　你的判斷：${trial.correct ? "正確" : "不正確"}`;
  $("#reveal").hidden = false; $("#submit").hidden = true; $("#next").hidden = false;
}
function next() {
  state.i++;
  if (state.i >= state.seq.length) { $("#trial").hidden = true; $("#done").hidden = false; }
  else renderTrial();
}
function exportJson() {
  const doc = { participant_id: state.pid, started_at: state.startedAt, finished_at: new Date().toISOString(),
    condition_order: state.order, trials: state.trials };
  const blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = `responses-${state.pid || "anon"}.json`; a.click();
}
window.addEventListener("DOMContentLoaded", async () => {
  await load();
  $("#start").onclick = () => { state.pid = $("#pid").value.trim() || "P-anon"; state.startedAt = new Date().toISOString();
    $("#intro").hidden = true; $("#trial").hidden = false; renderTrial(); };
  $("#submit").onclick = submit; $("#next").onclick = next; $("#export").onclick = exportJson;
});
```

- [ ] **Step 4: 視覺驗證**
Run: `cd viewer && python3 -m http.server 8000`，瀏覽器開 `http://localhost:8000/`（需先有 `data/pairs.json`，可用 fixture 暫代）。檢查：左右並列、條件 B 顯示證據、四選一/信心可選、揭露正解、可走完並下載。**用子代理或截圖做視覺挑錯**（重疊、字級、可讀性）。
- [ ] **Step 5: Commit** `git commit -am "feat(viewer): pair-viewer UI (index/app/styles)"`

---

## Task 8：analysis — 載入與正確率

**Files:** Create `analysis/lib.py`、`analysis/tests/test_lib.py`、`analysis/tests/fixtures/responses.json`

- [ ] **Step 1: fixture `responses.json`**（4 筆，含對/錯、A/B、高風險高信心錯）
```json
{"participant_id":"P-anon-01","condition_order":"A_then_B","trials":[
 {"pair_id":"P01","condition":"A","scenario":"high_risk_review","choice":"model","ground_truth":"harness","correct":false,"confidence":5,"rationale":"","time_ms":1000,"order":1},
 {"pair_id":"P02","condition":"A","scenario":"switch_after","choice":"harness","ground_truth":"harness","correct":true,"confidence":3,"rationale":"","time_ms":1000,"order":2},
 {"pair_id":"P03","condition":"B","scenario":"high_risk_review","choice":"harness","ground_truth":"harness","correct":true,"confidence":4,"rationale":"","time_ms":1000,"order":3},
 {"pair_id":"P04","condition":"B","scenario":"onboarding","choice":"noise","ground_truth":"interaction","correct":false,"confidence":2,"rationale":"","time_ms":1000,"order":4}]}
```

- [ ] **Step 2: 失敗測試**
```python
import json, pathlib
from analysis import lib
FIX = pathlib.Path(__file__).parent / "fixtures"

def test_accuracy_overall_and_by_condition():
    trials = lib.load_trials([str(FIX / "responses.json")])
    assert len(trials) == 4
    assert lib.accuracy(trials) == 0.5
    by = lib.accuracy_by(trials, "condition")
    assert by["A"] == 0.5 and by["B"] == 0.5
```

- [ ] **Step 3: 跑測試確認失敗** Run: `python -m pytest analysis/tests -q` Expected: FAIL。

- [ ] **Step 4: 實作 `analysis/lib.py`**
```python
import json
from collections import defaultdict

def load_trials(paths):
    trials = []
    for p in paths:
        trials += json.load(open(p))["trials"]
    return trials

def accuracy(trials):
    return sum(t["correct"] for t in trials) / len(trials) if trials else 0.0

def accuracy_by(trials, key):
    g = defaultdict(list)
    for t in trials:
        g[t[key]].append(t)
    return {k: accuracy(v) for k, v in g.items()}
```

- [ ] **Step 5: 跑測試確認通過** Expected: PASS（建 `analysis/__init__.py`、`analysis/tests/__init__.py`）。
- [ ] **Step 6: Commit** `git commit -am "feat(analysis): load trials and accuracy metrics"`

---

## Task 9：analysis — 混淆矩陣、信任校準、盲目採納

**Files:** Modify `analysis/lib.py`、`analysis/tests/test_lib.py`

- [ ] **Step 1: 失敗測試**
```python
def test_confusion_calibration_blind_adoption():
    trials = lib.load_trials([str(FIX / "responses.json")])
    cm = lib.confusion_matrix(trials)            # {true: {chosen: count}}
    assert cm["harness"]["model"] == 1
    assert cm["harness"]["harness"] == 2
    cal = lib.calibration(trials)                # {confidence: accuracy}
    assert cal[5] == 0.0 and cal[3] == 1.0
    # 高風險、confidence>=4、答錯 → 盲目採納
    assert lib.blind_adoption_rate(trials, scenario="high_risk_review") == 0.5
```

- [ ] **Step 2: 跑測試確認失敗** Expected: FAIL。

- [ ] **Step 3: 實作（加到 analysis/lib.py）**
```python
TYPES = ["harness", "model", "interaction", "noise"]

def confusion_matrix(trials):
    cm = {t: {c: 0 for c in TYPES} for t in TYPES}
    for tr in trials:
        cm[tr["ground_truth"]][tr["choice"]] += 1
    return cm

def calibration(trials):
    g = defaultdict(list)
    for t in trials:
        g[t["confidence"]].append(t["correct"])
    return {c: sum(v) / len(v) for c, v in g.items()}

def blind_adoption_rate(trials, scenario=None):
    sub = [t for t in trials if (scenario is None or t["scenario"] == scenario)]
    if not sub:
        return 0.0
    blind = [t for t in sub if t["confidence"] >= 4 and not t["correct"]]
    return len(blind) / len(sub)
```

- [ ] **Step 4: 跑測試確認通過** Expected: PASS。
- [ ] **Step 5: Commit** `git commit -am "feat(analysis): confusion matrix, calibration, blind-adoption"`

---

## Task 10：analysis — analyze.py CLI（指標 JSON ＋ 圖）

**Files:** Create `analysis/analyze.py`

- [ ] **Step 1: 寫 `analysis/analyze.py`**
```python
"""讀 responses-*.json → metrics.json ＋ 圖（PNG）。"""
import argparse, glob, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analysis import lib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", nargs="+", required=True, help="responses-*.json（可用萬用字元）")
    ap.add_argument("--outdir", default="analysis/figures")
    a = ap.parse_args()
    paths = [p for pat in a.responses for p in glob.glob(pat)]
    trials = lib.load_trials(paths)
    os.makedirs(a.outdir, exist_ok=True)
    metrics = {"n_trials": len(trials), "n_participants": len(paths),
               "accuracy_overall": lib.accuracy(trials),
               "accuracy_by_condition": lib.accuracy_by(trials, "condition"),
               "accuracy_by_scenario": lib.accuracy_by(trials, "scenario"),
               "confusion_matrix": lib.confusion_matrix(trials),
               "calibration": lib.calibration(trials),
               "blind_adoption_high_risk": lib.blind_adoption_rate(trials, "high_risk_review")}
    json.dump(metrics, open(os.path.join(a.outdir, "metrics.json"), "w"), ensure_ascii=False, indent=1)

    # 圖1：A vs B 正確率
    cond = metrics["accuracy_by_condition"]
    plt.figure(); plt.bar(list(cond), list(cond.values())); plt.ylim(0,1)
    plt.ylabel("歸因正確率"); plt.title("條件 A vs B")
    plt.savefig(os.path.join(a.outdir, "accuracy_by_condition.png"), dpi=150, bbox_inches="tight"); plt.close()

    # 圖2：信任校準
    cal = metrics["calibration"]; xs = sorted(cal)
    plt.figure(); plt.plot(xs, [cal[x] for x in xs], marker="o"); plt.plot([1,5],[0,1],"--",color="gray")
    plt.xlabel("信心"); plt.ylabel("實際正確率"); plt.ylim(0,1); plt.title("信任校準")
    plt.savefig(os.path.join(a.outdir, "calibration.png"), dpi=150, bbox_inches="tight"); plt.close()
    print("wrote metrics.json + figures to", a.outdir)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 以 fixture 跑一次驗證**
Run: `python -m analysis.analyze --responses "analysis/tests/fixtures/responses.json" --outdir /tmp/figs`
Expected: 印出 wrote；`/tmp/figs/metrics.json`、兩張 PNG 存在。
- [ ] **Step 3: Commit** `git commit -am "feat(analysis): analyze CLI with metrics json and charts"`

---

## Task 11（操作）：在 VPS 產生真實 pairs.json

- [ ] **Step 1:** 在 VPS `git pull`（HCI repo），把 `prep/` 放到能 import 的位置。
- [ ] **Step 2:** Run（在 VPS）：
```bash
cd /data/repos/hci-agent-attribution
PYTHONPATH=. python3 prep/build_pairs.py --xai-root /data/repos/xai-harness-faithfulness --out data/pairs.json
```
Expected: `wrote 24 pairs -> data/pairs.json`。
- [ ] **Step 3:** 檢查 `data/pairs.json`：24 對、四類齊、無個資、scenario/set 已填。
- [ ] **Step 4: Commit + push（VPS）** `git add data/pairs.json && git commit -m "data: generate 24-pair study set" && git push`，Mac 端 `git pull`。

---

## Task 12（操作）：pilot → 原型 v2（修改前後比較素材）

- [ ] **Step 1:** 本機 `cd viewer && python3 -m http.server 8000`，自己跑完 24 題，截圖每個關鍵畫面。
- [ ] **Step 2:** 記錄 v1 可用性問題（資訊層級、揭露時機、cue 可讀性、按鈕流程），寫入 `docs/prototype-iteration.md`。
- [ ] **Step 3:** 針對問題改 `viewer/`（v2），保留 v1 截圖與 v2 截圖做「修改前後比較」。
- [ ] **Step 4: Commit** `git commit -am "feat(viewer): v2 refinements from pilot; add prototype iteration notes"`

---

## Self-Review（撰寫後自檢）

- **Spec 覆蓋**：24 對/四類/三情境/A-B 對半（Task 1–7）、信心＋理由（Task 6–7）、正確率/混淆/校準/盲目採納/A-B 差（Task 8–10）、原型 v1→v2（Task 12）、來源標註（pairs.json `source`）、不碰 baseline（Task 3 只讀既有重跑、Task 11 唯讀 xai-root）。RQ1–4 皆有對應指標。✓
- **Placeholder**：每步皆有實際程式與指令，無 TBD/TODO。✓
- **型別一致**：`pair`/`set`/`condition`/`ground_truth`/`scenario`/`choice`/`confidence` 在 prep、study.js、analysis 三處名稱一致。✓
- **缺口**：理由線索質性編碼（spec §7）屬人工分析，列為報告撰寫階段工作，非程式 task；recovery time 依 spec 不實作。
