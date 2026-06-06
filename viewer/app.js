import { buildSequence, scoreTrial } from "./study.js";

const GT_LABEL = { harness: "Harness（框架）", model: "Model（模型）", interaction: "交互", noise: "雜訊" };
const CHOICES = [
  ["harness", "Harness（提示／工具／skill 設計）"],
  ["model", "Model（底層模型）"],
  ["interaction", "交互（特定組合的異常）"],
  ["noise", "雜訊（同設定重跑的隨機差異）"],
];
const SCEN = { switch_after: "切換後", high_risk_review: "高風險覆核", onboarding: "Onboarding" };
const $ = (s) => document.querySelector(s);

const state = { seq: [], i: 0, pid: "", order: "", trials: [], startedAt: "", t0: 0, ans: {} };

async function load() {
  const res = await fetch("../data/pairs.json");
  if (!res.ok) throw new Error("無法載入 ../data/pairs.json");
  const pairs = (await res.json()).pairs;
  state.order = Math.random() < 0.5 ? "A_then_B" : "B_then_A";
  state.seq = buildSequence(pairs, state.order);
}

function renderSide(side, label, cond) {
  const ev =
    cond === "B" && side.evidence
      ? `<div class="evidence">M1–M4：${side.evidence.method_agreement}<br>trace：${(side.evidence.trace_refs || []).join(", ")}<br>判斷類型：${side.evidence.decision_kind || ""}</div>`
      : "";
  return `<div class="output"><h3>${label}</h3>
    <div class="row">工具序列：${(side.tool_sequence || []).join(" → ")}</div>
    <div class="row">結果：${side.outcome || "—"}</div>${ev}</div>`;
}

function bindSelect(scopeSel, itemSel, key) {
  document.querySelectorAll(`${scopeSel} ${itemSel}`).forEach((el) => {
    el.onclick = () => {
      document.querySelectorAll(`${scopeSel} ${itemSel}`).forEach((e) => e.classList.remove("sel"));
      el.classList.add("sel");
      state.ans[key] = el.dataset.v;
    };
  });
}

function renderTrial() {
  const item = state.seq[state.i];
  const p = item.pair;
  $("#progress").textContent = `第 ${state.i + 1} / ${state.seq.length} 題`;
  $("#scenario").textContent = `情境：${SCEN[p.scenario] || p.scenario}`;
  $("#task").textContent = `任務：${p.task_id}`;
  $("#outputs").innerHTML = renderSide(p.left, "輸出 A", item.condition) + renderSide(p.right, "輸出 B", item.condition);
  $("#attribution").innerHTML =
    "<legend>這兩個輸出的差異主要來自？</legend>" +
    CHOICES.map(([v, t]) => `<span class="choice" data-v="${v}">${t}</span>`).join("");
  $("#confidence").innerHTML =
    "<legend>信心（1 低 – 5 高）</legend>" +
    [1, 2, 3, 4, 5].map((n) => `<span class="conf" data-v="${n}">${n}</span>`).join("");
  $("#rationale").value = "";
  $("#reveal").hidden = true;
  $("#next").hidden = true;
  $("#submit").hidden = false;
  state.ans = {};
  state.t0 = performance.now();
  bindSelect("#attribution", ".choice", "choice");
  bindSelect("#confidence", ".conf", "confidence");
}

function submit() {
  if (!state.ans.choice || !state.ans.confidence) {
    alert("請先選擇歸因與信心");
    return;
  }
  const item = state.seq[state.i];
  const trial = scoreTrial(item, {
    choice: state.ans.choice,
    confidence: Number(state.ans.confidence),
    rationale: $("#rationale").value,
    time_ms: Math.round(performance.now() - state.t0),
  });
  state.trials.push(trial);
  $("#reveal").innerHTML = `正解：<b>${GT_LABEL[trial.ground_truth]}</b>　你的判斷：${trial.correct ? "正確" : "不正確"}`;
  $("#reveal").hidden = false;
  $("#submit").hidden = true;
  $("#next").hidden = false;
}

function next() {
  state.i += 1;
  if (state.i >= state.seq.length) {
    $("#trial").hidden = true;
    $("#done").hidden = false;
  } else {
    renderTrial();
  }
}

function exportJson() {
  const doc = {
    participant_id: state.pid,
    started_at: state.startedAt,
    finished_at: new Date().toISOString(),
    condition_order: state.order,
    trials: state.trials,
  };
  const blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `responses-${state.pid || "anon"}.json`;
  a.click();
}

window.addEventListener("DOMContentLoaded", async () => {
  try {
    await load();
  } catch (e) {
    $("#intro").innerHTML = `<h1>載入失敗</h1><p>${e.message}</p><p class="muted">請先產生 data/pairs.json，並透過本機伺服器開啟（非 file://）。</p>`;
    return;
  }
  $("#start").onclick = () => {
    state.pid = $("#pid").value.trim() || "P-anon";
    state.startedAt = new Date().toISOString();
    $("#intro").hidden = true;
    $("#trial").hidden = false;
    renderTrial();
  };
  $("#submit").onclick = submit;
  $("#next").onclick = next;
  $("#export").onclick = exportJson;
});
