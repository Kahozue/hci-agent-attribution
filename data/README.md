# data/ 資料說明

## pairs.json（研究素材，24 對 contrastive pair）

由 `prep/build_pairs.py` 讀取 xai-harness-faithfulness 的產物生成：

```bash
PYTHONPATH=. python3 prep/build_pairs.py \
  --xai-root /data/repos/xai-harness-faithfulness \
  --out data/pairs.json
```

來源：`analysis/phase3/hci-ground-truth-labels.json`（20 對已標籤）＋ `analysis/phase4/metrics-summary.json`（成敗率）＋ raw traces（noise 與部分工具序列）。

### 組成

| 類型 | 數量 | 正解 |
|---|---|---|
| harness_main_effect | 6 | harness |
| model_main_effect | 6 | model |
| interaction | 8 | interaction |
| noise（同 config 兩次重跑） | 4 | noise |

- A/B 條件對半：Set1 12 對、Set2 12 對。
- 工具序列一律正規化為跨 harness 的 family（read／edit／shell／search／plan…），與 xAI 的 `TOOL_FAMILIES` 一致，**避免受試者用 harness 原生工具名（如 read_file／patch／bash）直接認出 harness**，保護歸因任務效度。

### 情境分布（與 proposal 的差異，已知且有意）

實際分布：**high_risk_review 11 ／ switch_after 10 ／ onboarding 3**。

分派規則（確定性、可重現）：
- noise → switch_after（重跑情境）。
- task_category：`benchmark` → switch_after；`bug_fix`／`add_logging` → high_risk_review；`add_tests` → onboarding。

proposal 原訂 8／8／4（針對 20 對），但 onboarding 只對應 add_tests 任務，且加入 4 對 noise 後，依任務性質的有原則映射自然落在 11／10／3。硬湊 8／8／4 會讓情境框與任務性質語意不符。N=1–3 為 pilot 等級，分情境樣本極小、不做統計推論，故此差異對結論無實質影響；報告會明確交代此規則與限制。

## responses-*.json（受試者作答）

由 pair-viewer 匯出。**屬個資，已列入 .gitignore，不入庫。** 分析時放入本資料夾並執行 `analysis/analyze.py`。
