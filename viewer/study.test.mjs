import { test } from "node:test";
import assert from "node:assert";
import { buildSequence, scoreTrial } from "./study.js";

test("split-half: 12-block per condition, counterbalanced", () => {
  const pairs = Array.from({ length: 24 }, (_, i) => ({ pair_id: `P${i + 1}`, set: i % 2 ? "Set2" : "Set1" }));
  const seq = buildSequence(pairs, "A_then_B");
  assert.equal(seq.length, 24);
  assert.equal(seq.filter((t) => t.condition === "A").length, 12);
  assert.equal(seq.filter((t) => t.condition === "B").length, 12);
  // A_then_B: 前 12 為 Set1=A
  assert.ok(seq.slice(0, 12).every((t) => t.condition === "A"));
  const seqB = buildSequence(pairs, "B_then_A");
  assert.ok(seqB.slice(0, 12).every((t) => t.condition === "B"));
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
