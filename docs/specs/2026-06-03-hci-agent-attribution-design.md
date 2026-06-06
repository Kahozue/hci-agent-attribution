# hci-agent-attribution 設計規格（Design Spec，骨架版）

- 文件版本：v0（2026-06-03，骨架；待 xAI 產出 trace 後細化為 v1）
- 作者：（匿名，依規定個資不入庫）
- 課程：HCI 期末專題（報告日 2026-06-12）
- 狀態：方向已核准；pair-viewer 介面屬視覺設計，將於細化階段另以視覺協作進行
- 對應 repo：`hci-agent-attribution`（GitHub: `Kahozue/hci-agent-attribution`）
- 上游依賴：`xai-harness-faithfulness` 的 factorial trace 與 ground-truth 歸因標籤

> 本專案為使用者研究，建立在 xAI 專案產出的 trace 之上。評分偏好與檢查條件以 repo 內 `HCI_REPORT_NOON_REQUIREMENTS.md` 為準（設計／互動取向、方法先行、環境固定、來源標註、圖表、未來展望）。

---

## 0. 研究問題與摘要

**題目**：Attribution under Disagreement — 分辨 Agent 差異中的 Harness 與 Model 來源。

使用者在用 coding agent 且未自行檢查時，常遇三情境：(1) agent 卡住、切到另一個重跑同 task；(2) 高風險改動前找另一個 agent 覆核；(3) 試用新 agent 時拿舊任務比較。三情境下都須判斷差異來自 **harness** 還是 **model**，判錯等於浪費錢與時間。本研究比較使用者在這三情境的歸因準確度。

**研究問題**

| RQ | 問題 |
|----|------|
| RQ1 | 三情境合計歸因正確率多高？ |
| RQ2 | 哪類差異最常被誤歸？（假說：harness 差異常被誤歸到 model，如「XX 模型較強」） |
| RQ3 | 信心與正確率是否校準？哪個情境信心過剩最嚴重？ |
| RQ4 | 若歸因不準，介面該「揭露更多 trace」還是「直接給歸因 label」？ |

---

## 1. 設計取捨（依 proposal）

- 以 xAI 已產出的 6 configs × 20 tasks factorial trace 當 ground truth；N=1–3，但每 trial 都有明確正解。
- 不只記正確率，也記**信心（1–5）與一句理由**，以分辨「答對」與「猜對」。

---

## 2. 實驗素材：20 對 contrastive pair

| Pair 類型 | 配對方式 | xAI Ground Truth |
|-----------|---------|------------------|
| Harness-only | 同 model、不同 harness | harness 主效應 |
| Model-only | 同 harness、不同 model | model 主效應 |
| Interaction | factorial 中顯著異常組合 | 交互項 |
| Noise | 同配置重跑 | 隨機誤差 |

三情境 case 配比：
1. 切換後場景：8 對，task 偏卡關／失敗案例。
2. 高風險覆核場景：8 對，task 偏 destructive 或 prod-relevant 改動。
3. Onboarding 場景：4 對，task 偏受試者熟悉度測試。

（pair 的具體挑選腳本與 ground-truth 標籤來源，待 xAI trace 完成後依實際分歧分佈決定。）

---

## 3. Pair Viewer（互動工具，待視覺設計）

每個 trial 流程：並列顯示一對輸出 → 受試者四選一歸因 + 信心 1–5 + 一句理由 → 揭露 ground truth → 比對。系統記錄每筆作答、信心、理由、看了哪些 cue、作答時間。

介面設計（版面、cue 呈現方式、揭露時機）將於細化階段以視覺協作進行，並保留原型修改前後比較作為報告素材。

---

## 4. 指標與分析

- 整體歸因正確率（三情境合計與分情境）。
- 四類 pair 的混淆矩陣（誰最常被誤歸 → RQ2）。
- 信心校準曲線（信心 vs 正確率，找過剩情境 → RQ3）。
- 理由線索分析（受試者依哪些 cue 判斷）。
- 介面意涵（→ RQ4：揭露更多 trace vs 直接給 label）。

---

## 5. 報告對齊（HCI_REPORT_NOON_REQUIREMENTS.md）

- 先講研究背景、研究/調查流程與採用方法，再講結果。
- 測試環境固定版本＋環境介紹（沿用 xAI 的 `ENVIRONMENT.lock.md`）。
- 過程截圖、原型修改前後比較、圖表/流程圖/比較表，避免文字牆。
- 引用資料、規格、來源在對應頁面/附錄標註。
- 結尾未來展望、限制、下一步，且扣回 HCI（介面信任、安全感、清楚性）。
- 不可把 XAI 取向（模型能力、準確率等純技術指標）混入 HCI 評估主軸。
- 行有餘力補一個簡單 HTML 儀表板/展示頁（截圖、關鍵指標、流程畫面、比較圖）作加分附加素材，不取代主簡報。
- PPT 約 15 頁內、口頭 8–9 分鐘。

---

## 6. 細化待辦（v1 將補）

- 依 xAI 實際分歧分佈，定 20 對 pair 的挑選準則與腳本。
- pair-viewer 的視覺設計與原型（含修改前後比較）。
- 受試者招募與 N（1–3）安排、知情同意、HCI 分析針對的群體交代。
- 信任校準討論（避免認知偏差導致誤判）。
- human-in-the-loop 框架下對系統介入效果與結果成因的進一步分析（吸收 HCI 同儕回饋）。
