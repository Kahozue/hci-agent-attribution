# LLM CLI Runner

這個工具讓不同 LLM CLI 以「合成受試者」形式填答 HCI attribution study。它適合做 pilot、介面壓力測試、模型間比較或人類資料的對照，不應和真人受試者結果混在同一個樣本池解讀。

## 安全邊界

不要把整個 repo 交給 LLM agent。`llm_runner` 採用 trusted driver 模式：

- trusted driver 讀取 `data/pairs.json`，保留 ground truth 做收卷評分。
- LLM 子程序只收到單題 prompt，工作目錄是暫存 study pack。
- 可見 payload 會移除 `ground_truth`、`pair_type`、`set`、`config`、`source`。
- trace path 會改成 `A-trace-1`、`B-trace-1` 這種不含 repo path 的 opaque label。
- 子程序使用 `subprocess.run(..., shell=False)`，避免 shell injection。
- 子程序預設只保留 `PATH`、`HOME`、`TMPDIR`、`LANG`，且 `HOME`/`TMPDIR` 指向 study pack。
- study pack 目錄必須在 repo 外；CLI 會拒絕把 pack 放進專案目錄。

這能避免直接資料洩漏與 cwd 洩漏。但若某個 agent CLI 本身有任意檔案讀取工具，作業系統層級仍可能讀到主機其他路徑。若要做正式比較，請把 LLM CLI 放在獨立使用者帳號、container 或其他 OS sandbox 中，再使用本 runner。

## 互動式填答

```bash
cd /Users/kahokozue/Desktop/Master/HCI_HW/hci-agent-attribution
PYTHONPATH=. python3 -m llm_runner.cli run \
  --participant-id llm-manual-01 \
  --condition-order A_then_B
```

每題會印出 prompt，貼上一行 JSON：

```json
{"choice":"harness","confidence":4,"rationale":"工具序列差異主要集中在流程與工具使用。"}
```

完成後會產生 `responses-llm-manual-01.json`，格式和 viewer 匯出的 scored response 相容。

## 接 LLM CLI

LLM 命令必須從 stdin 讀 prompt，並只在 stdout 輸出答案 JSON。

```bash
cd /Users/kahokozue/Desktop/Master/HCI_HW/hci-agent-attribution
PYTHONPATH=. python3 -m llm_runner.cli run \
  --participant-id gpt5-cli-a \
  --condition-order A_then_B \
  --llm-cmd "your-llm-cli --json" \
  --out responses-gpt5-cli-a.json \
  --raw-out raw-gpt5-cli-a.json
```

如果 CLI 需要 API key，可以明確允許特定環境變數：

```bash
PYTHONPATH=. python3 -m llm_runner.cli run \
  --participant-id model-x \
  --llm-cmd "your-llm-cli --json" \
  --allow-env OPENAI_API_KEY
```

不要傳 `HOME`，除非你確定該 CLI 不能藉此讀到不該看的本機資料。

## 只產生 sanitized study pack

```bash
cd /Users/kahokozue/Desktop/Master/HCI_HW/hci-agent-attribution
PYTHONPATH=. python3 -m llm_runner.cli pack \
  --participant-id audit-pack \
  --condition-order B_then_A \
  --out /tmp/hci-llm-pack
```

`/tmp/hci-llm-pack` 只會包含：

- `visible_trials.json`
- `README_FOR_LLM.txt`
- `prompts/trial-01.txt` 到 `prompts/trial-20.txt`

它不會包含 viewer 原始碼、`data/pairs.json`、ground truth 或真實 trace path。

## 評分 raw answers

如果你手上已有不含 ground truth 的 raw answer 檔：

```bash
PYTHONPATH=. python3 -m llm_runner.cli score \
  --answers raw-gpt5-cli-a.json \
  --out responses-gpt5-cli-a.json
```

`score` 是 trusted step，會把 raw answers 和 `data/pairs.json` 的 ground truth 合併，輸出 summary、confusion matrix、信心校準與各類正確率。
