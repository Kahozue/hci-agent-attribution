// pair-viewer 純邏輯：對半平衡抽題序列、計分。無 DOM 依賴，可用 node --test 測試。

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
