// pair-viewer 純邏輯：對半平衡抽題序列、計分。無 DOM 依賴，可用 node --test 測試。

export const TYPES = ["harness", "model", "interaction", "noise"];
export const SCENARIOS = ["switch_after", "high_risk_review", "onboarding"];
export const CONDITIONS = ["A", "B"];

export const SCENARIO_COPY = {
  switch_after: ["切換後", "同一任務已有前次執行紀錄，現在呈現另一份同任務執行摘要供檢視。"],
  high_risk_review: ["高風險覆核", "此題來自錯誤成本較高的程式變更情境，請先閱讀兩份執行摘要。"],
  onboarding: ["Onboarding", "此題來自熟悉任務的試用情境，請先閱讀兩份執行摘要。"],
};

export const CATEGORY_COPY = {
  bug_fix: ["Bug 修復", "修正既有錯誤並讓測試通過"],
  add_tests: ["補測試", "增加測試覆蓋以驗證既有功能"],
  add_logging: ["加入 logging", "補上觀測與紀錄，降低後續除錯成本"],
  benchmark: ["Benchmark", "在固定任務中檢查流程執行結果"],
};

export function taskTitle(pair) {
  const [category] = CATEGORY_COPY[pair.task_category] || [pair.task_category || "任務"];
  return `${category}：${pair.task_id}`;
}

export function taskContext(pair) {
  const [, scenario] = SCENARIO_COPY[pair.scenario] || [pair.scenario, "請閱讀兩份執行摘要。"];
  const [, category] = CATEGORY_COPY[pair.task_category] || ["", "coding 任務"];
  return `情境：${scenario} 任務類型：${category}。請依目前畫面資訊完成下方選擇與信心評估。`;
}

// 對半平衡：Set1 一組、Set2 一組；condition_order 決定哪組先、配哪個條件。
export function buildSequence(pairs, order) {
  const set1 = pairs.filter((p) => p.set === "Set1");
  const set2 = pairs.filter((p) => p.set === "Set2");
  const [firstSet, firstCond, secondSet, secondCond] =
    order === "A_then_B" ? [set1, "A", set2, "B"] : [set2, "B", set1, "A"];
  const block = (arr, cond) => arr.map((p) => ({ pair: p, condition: cond }));
  const seq = [...block(firstSet, firstCond), ...block(secondSet, secondCond)];
  return seq.map((t, i) => ({ ...t, order: i + 1 }));
}

// 計分並組一筆作答紀錄。
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

function emptyGroup() {
  return { total: 0, correct: 0, accuracy: 0, meanConfidence: 0, meanTimeSeconds: 0 };
}

function groupSummary(trials) {
  if (!trials.length) return emptyGroup();
  const correct = trials.filter((t) => t.correct).length;
  const confidence = trials.reduce((sum, t) => sum + Number(t.confidence || 0), 0);
  const time = trials.reduce((sum, t) => sum + Number(t.time_ms || 0), 0);
  return {
    total: trials.length,
    correct,
    accuracy: correct / trials.length,
    meanConfidence: confidence / trials.length,
    meanTimeSeconds: time / trials.length / 1000,
  };
}

function summarizeBy(trials, key, values) {
  const out = {};
  for (const value of values) {
    out[value] = groupSummary(trials.filter((t) => t[key] === value));
  }
  return out;
}

export function summarizeTrials(trials) {
  const base = groupSummary(trials);
  const confusion = Object.fromEntries(TYPES.map((t) => [t, Object.fromEntries(TYPES.map((c) => [c, 0]))]));
  for (const t of trials) {
    if (confusion[t.ground_truth] && t.choice in confusion[t.ground_truth]) {
      confusion[t.ground_truth][t.choice] += 1;
    }
  }

  const calibration = {};
  for (const confidence of [1, 2, 3, 4, 5]) {
    calibration[confidence] = groupSummary(trials.filter((t) => Number(t.confidence) === confidence));
  }

  const highRisk = trials.filter((t) => t.scenario === "high_risk_review");
  const highRiskBlind = highRisk.filter((t) => Number(t.confidence) >= 4 && !t.correct);

  return {
    ...base,
    byCondition: summarizeBy(trials, "condition", CONDITIONS),
    byScenario: summarizeBy(trials, "scenario", SCENARIOS),
    byGroundTruth: summarizeBy(trials, "ground_truth", TYPES),
    calibration,
    confusion,
    highRiskBlindAdoptionRate: highRisk.length ? highRiskBlind.length / highRisk.length : 0,
  };
}
