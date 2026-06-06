# hci-agent-attribution 設計規格（Design Spec v1）

- 文件版本：v1（2026-06-06）。**取代** `docs/specs/2026-06-03-hci-agent-attribution-design.md`（v0 骨架）。
- 作者：（匿名，依規定個資不入庫）
- 課程：HCI 期末專題（報告日 2026-06-12）
- 報告類別：**Demo 影片類**（proposal §二「呈現方式：PPT 錄影」）。交付物＝完整版 Proposal PDF（≥12 頁）＋影片用 PPT（約 15 頁）＋Demo 報告影片（8–12 分）。
- 上游依賴：`xai-harness-faithfulness` 的 factorial trace 與 ground-truth 歸因標籤（已產出並 push）。
- 必須嚴格遵守：本 repo 的 `proposal.pdf` 與 `HCI_REPORT_NOON_REQUIREMENTS.md`。本 spec 未新增任何 proposal 以外的研究問題。

---

## 0. 不跑題鐵則（最高優先）

老師課程投影片每週都明劃 **xAI vs HCI 界線**（Week 9/10/11/12）：

- **xAI 問**：模型依賴哪些特徵／模態、依賴是否跨子群穩定、faithful explanation。
- **HCI 問**：人如何理解 agent 流程、會不會過度／不足信任、透明性揭露到什麼程度才不造成負擔、什麼互動能促成**正確覆核**與正確介入。

因此本專案的評估主軸是**人的歸因判斷、心理模型與信任校準**，不是模型／harness 的技術準確率。模型能力、整體成功率等純技術數字只能當素材背景，**不得當作 HCI 評估主軸**（依需求文件 §1）。介面語言繁體中文、全程禁 emoji、UI 乾淨無裝飾、可讀性優先。

---

## 1. 研究定位與 HCI 框架對齊

使用者在用 coding agent 而未自行檢查時常遇三情境：(1) agent 卡住，切到另一個重跑同 task；(2) 高風險改動前找另一個 agent 覆核；(3) 試用新 agent 時拿舊任務比較。三情境都須判斷「兩個 agent 的差異來自 **harness** 還是 **model**」。判錯＝形成錯誤心理模型（如誤以為「某模型較強」），導致信任校準失準、浪費錢與時間。

本專案以使用者研究比較三情境下的歸因判斷，並操弄介面「揭露程度」是否改善判斷。每個 proposal RQ 都對應老師反覆強調的 HCI 框架：

| Proposal RQ（原文） | 對應 HCI 框架 | HCI 詮釋 |
|---|---|---|
| RQ1 三情境合計歸因正確率多高？ | 心理模型正確性 / 正確覆核率 | 人能否形成正確的「差異來源」心理模型 |
| RQ2 哪類差異最常被誤歸？（假說：harness 誤歸到 model） | **Signal ≠ State** | 把工具序列差異（signal）誤讀成「模型較強」（state） |
| RQ3 信心與正確率是否校準？哪情境信心過剩最嚴重？ | **Trust Calibration / automation bias** | 信心與實際可靠度是否相符；高風險過剩＝盲目採納 |
| RQ4 介面該「揭露更多 trace」還是「直接給歸因 label」？ | **透明性 / progressive disclosure** | 條件 A（只給摘要）vs 條件 B（給證據＋限制）的揭露程度操弄 |

關鍵詞彙（報告與 PPT 一律使用老師的語言）：心理模型、透明性、progressive disclosure、Trust vs Reliance、信任校準、automation bias／盲目採納、Signal ≠ State、Gulf of Evaluation、Situation Awareness、Agentic UX（checkpoint／覆核／接手）、human-in-the-loop。

---

## 2. 研究問題（嚴格沿用 proposal，未新增）

- **RQ1**：三情境合計歸因正確率多高？（分情境亦報告）
- **RQ2**：哪類差異最常被誤歸？假說：harness 差異常被誤歸到 model（如「XX 模型較強」）。
- **RQ3**：信心與正確率是否校準？哪個情境信心過剩最嚴重？
- **RQ4**：若歸因不準，介面該「揭露更多 trace」還是「直接給歸因 label」？

---

## 3. 實驗設計

### 3.1 素材：24 對 contrastive pair

忠於 proposal 的四類 pair。xAI ground-truth 實際只標了 3 類（harness 主效應 6、model 主效應 6、交互 8，共 20），**無 noise**；為完整呈現 proposal 的四選一與 RQ2 混淆矩陣，補造 4 對 noise pair。

| Pair 類型 | 數量 | 配對方式 | 正解（ground truth） | 資料來源 |
|---|---|---|---|---|
| Harness-only | 6 | 同 model、不同 harness | harness 主效應 | `analysis/phase3/hci-ground-truth-labels.json` |
| Model-only | 6 | 同 harness、不同 model | model 主效應 | 同上 |
| Interaction | 8 | factorial 顯著異常組合 | 交互 | 同上 |
| Noise | 4 | **同一 config 的兩次正式重跑（run i vs run j）** | 雜訊（定義上真值） | 由 raw traces `traces/<config>/<task>/<run>.json` 配出 |

noise pair 挑選規則：在既有正式重跑中，選**同 config、同 task、兩次工具序列明顯不同但成敗相同**者，凸顯「無系統性成因、純執行期變異」。

### 3.2 三觸發情境（沿用 proposal 配比 8/8/4，noise 併入）

1. 切換後（8 對）：task 偏卡關／失敗案例。
2. 高風險覆核（8 對）：task 偏 destructive 或 prod-relevant 改動。
3. Onboarding（4 對）：task 偏受試者熟悉度測試。

情境為受試者所見的情境框（cover story），資料無此欄位，由我們依 task 性質分派，分派表寫入 `pairs.json` 並在報告交代規則。4 對 noise 平均併入三情境（不另立情境）。

### 3.3 兩條件 A／B（透明性 / progressive disclosure 操弄）

- **條件 A（只給摘要）**：每邊只顯示工具序列、成敗率。受試者僅憑結果摘要歸因。
- **條件 B（給證據＋限制）**：在 A 之上加「證據區」——M1–M4 歸因一致度、trace 出處、decision_kind／任務類別，及（case-pack 6 案例可得時）推理線索摘要。noise pair 的證據區明示「同 config 兩次重跑、M1–M4 不適用、差異屬執行期變異」。

**受試者內設計（within-subject）＋對半平衡**：24 對拆為 Set1／Set2 各 12 對（四類型與三情境在兩 set 盡量等比）。每位受試者前 12 題用一個條件、後 12 題用另一個條件（不同題，避免記憶污染）。跨受試者輪流哪個 set 配 A、哪個配 B，平衡題目難度混淆。

### 3.4 作答

四選一（harness／model／交互／雜訊）＋信心（1–5）＋一句理由。送出後揭露正解與對錯。

---

## 4. 系統架構（皆置於本 repo）

| 元件 | 位置／技術 | 職責 |
|---|---|---|
| 資料準備 `prep/build_pairs.py` | VPS、Python | 讀 xAI `hci-ground-truth-labels.json`＋`analysis/phase4/metrics-summary.json`，並從 raw traces 配 4 對 noise，輸出自足的 `data/pairs.json`（24 對：A 內容、B 內容、正解、情境、成敗率） |
| pair-viewer `viewer/` | 靜態單頁（index.html＋app.js＋styles.css） | 載入 `data/pairs.json`，跑 24 題協定，作答存成可下載 `responses-<participant>.json`。無後端、可在 Mac 本機開，便於截圖與錄影 |
| 分析 `analysis/analyze.py` | Python | 讀 responses，算指標、出圖（PNG/SVG），回答 RQ1–4 |

**執行與同步**：HCI 程式碼／spec／viewer 以 Mac clone 為主開發並 push；`build_pairs.py` 需 xAI 產物與 traces，故在 VPS `git pull` 後執行、產出 `data/pairs.json` 後 commit/push，Mac 再 pull。**絕不碰 xAI 的正式 360 baseline trace**；noise pair 只讀既有重跑、不重跑實驗。

---

## 5. 資料模型

### 5.1 `data/pairs.json`（prep 產出）

```
{
  "schema_version": 1,
  "source": { ... 來源檔路徑 ... },
  "pairs": [
    {
      "pair_id": "P01",
      "pair_type": "harness_main_effect | model_main_effect | interaction | noise",
      "ground_truth": "harness | model | interaction | noise",
      "scenario": "switch_after | high_risk_review | onboarding",
      "task_id": "addtests-t2-04",
      "task_excerpt": "為 ... 補測試覆蓋",
      "left":  { "label": "輸出 A", "tool_sequence": [...], "outcome": "3/3 通過",
                 "evidence": { "method_agreement": "4/4", "trace_refs": [...], "decision_kind": "...", "reasoning_cue": "（可得時）" } },
      "right": { "label": "輸出 B", "tool_sequence": [...], "outcome": "3/3 通過",
                 "evidence": { ... } }
    }
  ]
}
```

條件 A 渲染時隱藏 `evidence`；條件 B 顯示。

### 5.2 `responses-<participant>.json`（viewer 匯出）

```
{
  "participant_id": "P-anon-01",
  "started_at": "...", "finished_at": "...",
  "condition_order": "A_then_B | B_then_A",
  "set_assignment": { "block1": "Set1", "block2": "Set2" },
  "trials": [
    { "pair_id": "P01", "condition": "A", "scenario": "high_risk_review",
      "choice": "model", "ground_truth": "harness", "correct": false,
      "confidence": 4, "rationale": "...", "time_ms": 18234, "order": 1 }
  ]
}
```

---

## 6. 每題流程與記錄欄位

並列兩輸出 → 四選一 ＋ 信心 1–5 ＋ 一句理由 → 送出揭露正解。
每題記錄：`pair_id, condition, scenario, choice, ground_truth, correct, confidence, rationale, time_ms, order`；檔頭記 `participant_id, condition_order, set_assignment, timestamps`。

---

## 7. 指標與分析（行為／決策品質取向，照老師詞彙）

| 指標 | 計算 | 回答 | HCI 框架 |
|---|---|---|---|
| 整體與分情境歸因正確率 | 正確比例（總體／三情境／A vs B） | RQ1 | 正確覆核率 / 心理模型正確性 |
| 4×4 混淆矩陣 | 真值類型 × 受試者所選 | RQ2 | Signal ≠ State（看 harness→model 誤歸） |
| 信任校準曲線 | 各信心等級的實際正確率 | RQ3 | Trust Calibration；分情境找信心過剩 |
| 高風險「高信心卻答錯」率 | 高風險情境中 confidence≥4 且 correct=false 比例 | RQ3 | **盲目採納 / automation bias** |
| A vs B 正確率與校準差 | 條件 B − 條件 A | RQ4 | **progressive disclosure 是否有助** |
| 理由線索輕度編碼 | 質性歸類受試者依哪些 cue 判斷 | RQ2/RQ4 補充 | 心理模型探查 |

**recovery time 不套用**：老師 Week 10 的 recovery time 針對多步驟任務的錯誤恢復；本研究測的是「決策前的歸因判斷」，不涉及任務回退，報告會明說此區別，避免誤用指標。

**樣本誠實聲明**：N=1–3 為 pilot 等級，所有曲線／矩陣屬示意性質，報告明確標註樣本小、不宣稱統計顯著，定位為互動設計與方法的概念驗證。

---

## 8. 原型迭代（需求文件指定的「修改前後比較」素材）

pair-viewer **v1 → 一次 pilot（作者自跑一輪找可用性問題）→ v2 修正**。記錄 v1 痛點（如資訊層級、揭露時機、cue 可讀性）與 v2 改動，作為報告的「原型修改前後比較」與過程截圖。每個介面決策都對應到使用者需求與設計取捨（需求文件 §3）。

---

## 9. 受試者、知情同意、群體交代（倫理）

- N=1–3，作者本人＋少數同學。
- 報告交代：受試者背景（是否用過 coding agent、技術熟悉度）、知情同意（用途、可退出、匿名）、HCI 分析針對的群體。
- 匿名化：participant_id 不含可識別資訊。

---

## 10. 測試環境固定（需求文件 §2／§3）

沿用 xAI 的版本鎖（`ENVIRONMENT.lock.md` 與釘死的 harness／模型版本），報告附一小段環境介紹，說明 trace 來源條件一致、可比。pair-viewer 自身環境（瀏覽器、執行方式）亦於報告載明。

---

## 11. 來源標註計畫（需求文件 §2）

trace 與 ground-truth 標籤標明來自 xai-harness-faithfulness 對應檔；引用的 HCI 概念（心理模型、信任校準、progressive disclosure、automation bias、Signal≠State、Agentic UX 等）在 PPT 對應頁或附錄標示課程週次／文獻來源。

---

## 12. 交付物對應

### 12.1 Proposal PDF（≥12 頁）章節骨架
1. 研究背景與動機（使用情境、為何歸因重要）— 扣回 HCI
2. 研究問題（RQ1–4）與對應 HCI 框架
3. 採用方法與理由（為何用對照、為何四類、為何 within-subject）— 方法先行
4. 測試環境與固定版本介紹
5. 介面設計：pair-viewer 與 A/B 條件，逐功能對應使用者需求與設計取捨
6. 原型修改前後比較（v1→v2，含截圖）
7. 研究流程與資料記錄方法
8. 結果：圖表（正確率、混淆矩陣、信任校準曲線、A vs B）
9. 結果解釋：為何產生這些結果（不只列數值）；具體風險案例分析
10. 信任校準與 automation bias 討論；human-in-the-loop 對系統介入效果
11. 限制（N 小等）與未來展望、下一步驗證 — 扣回 HCI
12. 參考來源與附錄

### 12.2 PPT（約 15 頁）：上述濃縮，圖表為主、少文字牆。
### 12.3 Demo 影片（8–12 分）：PPT 講述＋pair-viewer 實際操作 demo。
### 12.4（加分，行有餘力）：簡單 HTML 儀表板整理截圖／關鍵指標／比較圖，不取代主簡報。

---

## 13. 嚴守邊界檢查清單

- [ ] 未新增 proposal 以外的 RQ；四類 pair、三情境配比、N、信心＋理由皆照 proposal。
- [ ] 評估主軸為 HCI（心理模型／信任校準／透明性），未把模型能力或準確率當主軸。
- [ ] 方法先行、環境固定、來源標註、圖表為主、原型前後比較、未來展望＋限制 — 對齊需求文件。
- [ ] 繁中、禁 emoji、UI 乾淨無裝飾。
- [ ] 不碰 xAI 360 baseline；noise 只用既有重跑。
