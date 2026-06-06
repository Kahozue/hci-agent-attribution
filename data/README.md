# data/ 資料說明

## pairs.json（研究素材，20 對 contrastive pair）

由 `prep/build_pairs.py` 讀取 xai-harness-faithfulness 的產物生成：

```bash
PYTHONPATH=. python3 prep/build_pairs.py \
  --xai-root /data/repos/xai-harness-faithfulness \
  --out data/pairs.json
```

來源：`analysis/phase3/hci-ground-truth-labels.json`（已標籤 contrastive pairs）＋ `analysis/phase4/metrics-summary.json`（成敗率）＋ raw traces（noise 與部分工具序列）。

### 組成

| 類型 | 數量 | 正解 |
|---|---|---|
| harness_main_effect | 5 | harness |
| model_main_effect | 5 | model |
| interaction | 6 | interaction |
| noise（同 config 兩次重跑） | 4 | noise |

- A/B 條件對半：Set1 10 對、Set2 10 對。
- 工具序列一律正規化為跨 harness 的 family（read／edit／shell／search／plan…），與 xAI 的 `TOOL_FAMILIES` 一致，**避免受試者用 harness 原生工具名（如 read_file／patch／bash）直接認出 harness**，保護歸因任務效度。

### 情境分布

現行分布與 proposal 對齊：**high_risk_review 8 ／ switch_after 8 ／ onboarding 4**。

分派規則（確定性、可重現）：
- noise → switch_after（重跑情境）。
- task_category：`benchmark` → switch_after；`bug_fix`／`add_logging` → high_risk_review；`add_tests` → onboarding。

## responses-*.json（受試者作答）

由 pair-viewer 匯出。**屬個資，已列入 .gitignore，不入庫。** 分析時放入本資料夾並執行 `analysis/analyze.py`。
