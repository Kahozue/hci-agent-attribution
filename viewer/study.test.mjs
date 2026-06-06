import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { buildSequence, scoreTrial, summarizeTrials, taskContext, taskTitle } from "./study.js";

test("split-half: 10-block per condition, counterbalanced for 20-trial proposal", () => {
  const pairs = Array.from({ length: 20 }, (_, i) => ({ pair_id: `P${i + 1}`, set: i % 2 ? "Set2" : "Set1" }));
  const seq = buildSequence(pairs, "A_then_B");
  assert.equal(seq.length, 20);
  assert.equal(seq.filter((t) => t.condition === "A").length, 10);
  assert.equal(seq.filter((t) => t.condition === "B").length, 10);
  // A_then_B: 前 10 為 Set1=A
  assert.ok(seq.slice(0, 10).every((t) => t.condition === "A"));
  const seqB = buildSequence(pairs, "B_then_A");
  assert.ok(seqB.slice(0, 10).every((t) => t.condition === "B"));
});

test("scoreTrial records correctness", () => {
  const t = scoreTrial(
    { pair: { pair_id: "P1", ground_truth: "harness", scenario: "high_risk_review" }, condition: "A", order: 1 },
    { choice: "model", confidence: 4, rationale: "x", time_ms: 1200 },
  );
  assert.equal(t.correct, false);
  assert.equal(t.ground_truth, "harness");
  assert.equal(t.choice, "model");
  assert.equal(t.confidence, 4);
  assert.equal(t.condition, "A");
});

test("summarizeTrials returns HCI behavior metrics for completion page", () => {
  const trials = [
    { condition: "A", scenario: "high_risk_review", ground_truth: "harness", choice: "model", correct: false, confidence: 5, time_ms: 1000 },
    { condition: "A", scenario: "high_risk_review", ground_truth: "harness", choice: "harness", correct: true, confidence: 3, time_ms: 2000 },
    { condition: "B", scenario: "switch_after", ground_truth: "model", choice: "model", correct: true, confidence: 4, time_ms: 3000 },
    { condition: "B", scenario: "onboarding", ground_truth: "noise", choice: "interaction", correct: false, confidence: 2, time_ms: 4000 },
  ];

  const s = summarizeTrials(trials);
  assert.equal(s.total, 4);
  assert.equal(s.correct, 2);
  assert.equal(s.accuracy, 0.5);
  assert.equal(s.byCondition.A.accuracy, 0.5);
  assert.equal(s.byCondition.B.accuracy, 0.5);
  assert.equal(s.byScenario.high_risk_review.total, 2);
  assert.equal(s.confusion.harness.model, 1);
  assert.equal(s.calibration[5].accuracy, 0);
  assert.equal(s.highRiskBlindAdoptionRate, 0.5);
  assert.equal(s.meanTimeSeconds, 2.5);
});

test("task background stays neutral and does not leak study purpose", () => {
  const pairs = JSON.parse(readFileSync(new URL("../data/pairs.json", import.meta.url), "utf8")).pairs;
  const forbidden = [
    "心理模型",
    "判斷兩邊差異",
    "差異主要來自",
    "選哪個 agent",
    "比較好",
    "測試新 agent",
    "信任或覆核 agent",
  ];

  for (const pair of pairs) {
    const text = `${taskTitle(pair)} ${taskContext(pair)}`;
    for (const phrase of forbidden) {
      assert.equal(text.includes(phrase), false, `${pair.pair_id} leaks phrase: ${phrase}`);
    }
  }
});
