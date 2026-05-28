# hci-agent-attribution

**Attribution under Disagreement: Distinguishing Harness vs. Model Sources in Agent Divergence**

Course proposal and experiment repository for an HCI study measuring how accurately users can attribute behavioral differences between AI coding agents to harness design versus the underlying model — across three real-world triggering scenarios.

## Research Question

When a user observes two AI agents producing different outputs on the same task, can they correctly identify whether the difference came from the harness (prompts, tools, skills) or the model? And does their accuracy vary by scenario?

## Design

Uses the factorial trace from [xai-harness-faithfulness](https://github.com/KahoKozue/xai-harness-faithfulness) as ground truth (6 configs × 20 tasks).

**20 contrastive pairs across 4 types:**

| Pair Type | How Paired | Ground Truth |
|-----------|-----------|--------------|
| Harness-only | Same model, different harness | Harness main effect |
| Model-only | Same harness, different model | Model main effect |
| Interaction | Anomalous combination in factorial | Interaction term |
| Noise | Same config, re-run | Random error |

**3 triggering scenarios:**
1. **Switch-after** (8 pairs) — agent stalled, user switched to another
2. **High-risk review** (8 pairs) — destructive or prod-relevant changes need a second opinion
3. **Onboarding** (4 pairs) — familiar task used to compare a new agent

**Per trial:** side-by-side pair viewer → 4-choice attribution + confidence (1–5) + one-sentence rationale → ground truth reveal.

**Metrics:** Overall attribution accuracy, confusion matrix across 4 pair types, confidence calibration curve, rationale cues.

## Research Questions

| RQ | Question |
|----|---------|
| RQ1 | What is users' overall attribution accuracy across the three scenarios? |
| RQ2 | Which pair type is most frequently misattributed? (Hypothesis: harness differences blamed on the model) |
| RQ3 | Is confidence calibrated with accuracy? Which scenario shows the worst overconfidence? |
| RQ4 | If attribution is inaccurate, should the UI expose more trace or directly provide attribution labels? |

## Repository Structure

```
proposal.pdf    Experiment proposal
```

Experiment tool, pair viewer, and result analysis will be added as the study progresses.
