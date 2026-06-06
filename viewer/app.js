import {
  CONDITIONS,
  SCENARIOS,
  SCENARIO_COPY,
  TYPES,
  buildSequence,
  scoreTrial,
  summarizeTrials,
  taskContext,
  taskTitle,
} from "./study.js";

const TYPE_LABEL = {
  harness: "Harness（框架）",
  model: "Model（模型）",
  interaction: "交互",
  noise: "雜訊",
};

const CHOICES = [
  ["harness", "Harness", "提示、工具、skill 或流程框架造成差異"],
  ["model", "Model", "底層模型本身造成差異"],
  ["interaction", "交互", "特定 model × harness 組合才出現的差異"],
  ["noise", "雜訊", "同設定重跑時的隨機變異"],
];

const CONDITION = {
  A: ["摘要版 A", "只顯示工具序列與結果，避免一次塞入過多 trace。"],
  B: ["證據版 B", "在摘要之外揭露 M1–M4 一致度、trace 出處與判斷類型。"],
};

const DK_ZH = {
  initial_tool_strategy: "初始工具策略",
  semantic_output_convention: "輸出慣例（語意）差異",
  task_success_gap: "任務成敗落差",
  noise: "重跑變異",
};

const $ = (s) => document.querySelector(s);

const state = {
  seq: [],
  i: 0,
  pid: "",
  order: "",
  trials: [],
  events: [],
  startedAt: "",
  t0: 0,
  ans: {},
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function logEvent(type, data = {}) {
  state.events.push({
    type,
    order: state.seq[state.i]?.order ?? null,
    at: new Date().toISOString(),
    ...data,
  });
}

function showDialog(dialog) {
  if (dialog.showModal) dialog.showModal();
  else dialog.setAttribute("open", "");
}

async function load() {
  const res = await fetch("../data/pairs.json");
  if (!res.ok) throw new Error("無法載入 ../data/pairs.json");
  const pairs = (await res.json()).pairs;
  state.order = Math.random() < 0.5 ? "A_then_B" : "B_then_A";
  state.seq = buildSequence(pairs, state.order);
}

function seqHtml(seq) {
  if (!seq?.length) return '<span class="empty">無工具紀錄</span>';
  return seq.map((t, i) => {
    const arrow = i === seq.length - 1 ? "" : '<span class="arr">→</span>';
    return `<span class="tool">${esc(t)}</span>${arrow}`;
  }).join("");
}

function outcomeHtml(outcome) {
  const m = /(\d+)\s*\/\s*(\d+)/.exec(outcome || "");
  if (!m) return `<span class="oc">${esc(outcome || "—")}</span>`;
  const a = Number(m[1]);
  const b = Number(m[2]);
  let cls = "oc oc-part";
  let word = "部分通過";
  if (a === b && b > 0) {
    cls = "oc oc-ok";
    word = "全部通過";
  } else if (a === 0) {
    cls = "oc oc-fail";
    word = "未通過";
  }
  return `<span class="${cls}">${m[1]}/${m[2]}・${word}</span>`;
}

function dkZh(dk) {
  return DK_ZH[dk] || dk || "—";
}

function traceRefsHtml(refs) {
  if (!refs?.length) return '<span class="empty">無 trace 出處</span>';
  return `<ul class="trace-list">${refs.map((ref) => `<li>${esc(ref)}</li>`).join("")}</ul>`;
}

function evRow(label, left, right) {
  return `<tr class="ev"><th class="attr">${esc(label)}</th><td>${left}</td><td>${right}</td></tr>`;
}

function renderComparison(L, R, cond) {
  let evRows = "";
  const conditionNote = cond === "B"
    ? "證據版：本題多顯示來源與判斷線索；請依目前畫面資訊作答。"
    : "摘要版：本題刻意不顯示 M1–M4 與 trace；請依目前畫面資訊作答。";

  if (cond === "B") {
    const le = L.evidence || {};
    const re = R.evidence || {};
    evRows =
      evRow("M1–M4 一致度", esc(le.method_agreement || "—"), esc(re.method_agreement || "—")) +
      evRow("trace 出處", traceRefsHtml(le.trace_refs), traceRefsHtml(re.trace_refs)) +
      evRow("判斷類型", esc(dkZh(le.decision_kind)), esc(dkZh(re.decision_kind)));
  }

  return `<div class="output-block">
      <p class="condition-note">${conditionNote}</p>
      <table class="cmp">
        <colgroup>
          <col class="attr-col">
          <col class="out-col">
          <col class="out-col">
        </colgroup>
        <thead><tr><th class="attr"></th><th>輸出 A</th><th>輸出 B</th></tr></thead>
        <tbody>
          <tr><th class="attr">工具序列</th><td><div class="seq2">${seqHtml(L.tool_sequence)}</div></td><td><div class="seq2">${seqHtml(R.tool_sequence)}</div></td></tr>
          <tr><th class="attr">結果</th><td>${outcomeHtml(L.outcome)}</td><td>${outcomeHtml(R.outcome)}</td></tr>
          ${evRows}
        </tbody>
      </table>
    </div>`;
}

function bindSelect(scopeSel, itemSel, key) {
  document.querySelectorAll(`${scopeSel} ${itemSel}`).forEach((el) => {
    el.onclick = () => {
      document.querySelectorAll(`${scopeSel} ${itemSel}`).forEach((e) => e.setAttribute("aria-pressed", "false"));
      el.setAttribute("aria-pressed", "true");
      state.ans[key] = el.dataset.v;
    };
  });
}

function renderTrial() {
  const item = state.seq[state.i];
  const p = item.pair;
  const total = state.seq.length;
  const [scenario] = SCENARIO_COPY[p.scenario] || [p.scenario];
  const [conditionName, conditionDesc] = CONDITION[item.condition];

  $("#progress").textContent = `第 ${state.i + 1} / ${total} 題`;
  $("#scenario").textContent = scenario;
  $("#progressfill").style.width = `${((state.i + 1) / total) * 100}%`;
  $("#condition-name").textContent = conditionName;
  $("#condition-desc").textContent = conditionDesc;
  $("#task").textContent = taskTitle(p);
  $("#task-context").textContent = taskContext(p);
  $("#outputs").innerHTML = renderComparison(p.left, p.right, item.condition);

  $("#attribution .choices").innerHTML = CHOICES.map(
    ([v, t, d]) => `<button type="button" class="choice" data-v="${v}" aria-pressed="false"><span class="t">${t}</span><span class="d">${d}</span></button>`,
  ).join("");
  $("#confidence .confs").innerHTML = [1, 2, 3, 4, 5]
    .map((n) => `<button type="button" class="conf" data-v="${n}" aria-pressed="false">${n}</button>`)
    .join("");

  $("#rationale").value = "";
  const reveal = $("#reveal");
  reveal.hidden = true;
  reveal.className = "";
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
  logEvent("submit_trial", { pair_id: trial.pair_id, correct: trial.correct });

  const reveal = $("#reveal");
  reveal.innerHTML = `正解：<span class="verdict">${TYPE_LABEL[trial.ground_truth]}</span><br>你的判斷：${trial.correct ? "正確" : "不正確"}。可用右上角「填答狀況」回顧已完成題目。`;
  reveal.className = trial.correct ? "correct" : "incorrect";
  reveal.hidden = false;
  $("#submit").hidden = true;
  $("#next").hidden = false;
}

function next() {
  state.i += 1;
  if (state.i >= state.seq.length) {
    $("#trial").hidden = true;
    $("#done").hidden = false;
    renderSummary();
  } else {
    renderTrial();
  }
}

function fmtPct(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function metricCard(label, value, note = "") {
  return `<div class="metric-card"><span>${label}</span><strong>${value}</strong>${note ? `<small>${note}</small>` : ""}</div>`;
}

function pieCards(summary, labels) {
  return Object.entries(labels).map(([key, label], index) => {
    const item = summary[key] || { total: 0, accuracy: 0 };
    const percent = Math.round(item.accuracy * 100);
    return `<article class="pie-card" style="--angle:${Math.round(item.accuracy * 360)}deg; --pie-color: var(--chart-${(index % 5) + 1});">
      <div class="pie">
        <span>${item.total ? `${percent}%` : "無"}</span>
      </div>
      <div>
        <h4>${esc(label)}</h4>
        <p>${item.correct}/${item.total} 正確</p>
        <div class="pie-legend"><span class="hit"></span>正確 <span class="miss"></span>未答對</div>
      </div>
    </article>`;
  }).join("");
}

function renderConfusion(confusion) {
  const head = TYPES.map((t) => `<th>${TYPE_LABEL[t]}</th>`).join("");
  const rows = TYPES.map((truth) => {
    const cells = TYPES.map((choice) => `<td>${confusion[truth][choice]}</td>`).join("");
    return `<tr><th>${TYPE_LABEL[truth]}</th>${cells}</tr>`;
  }).join("");
  return `<table class="summary-table"><thead><tr><th>真值 \\ 選擇</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

function renderCalibration(calibration) {
  return [1, 2, 3, 4, 5].map((level) => {
    const item = calibration[level];
    const width = Math.round(item.accuracy * 100);
    return `<div class="bar-row">
      <span>信心 ${level}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
      <strong>${item.total ? fmtPct(item.accuracy) : "無資料"}</strong>
      <small>${item.correct}/${item.total}</small>
    </div>`;
  }).join("");
}

function renderSummary() {
  const s = summarizeTrials(state.trials);
  const conditionDiff = s.byCondition.B.accuracy - s.byCondition.A.accuracy;
  $("#summary").innerHTML = `
    <div class="metrics-grid">
      ${metricCard("完成題數", `${s.total} 題`, `平均 ${s.meanTimeSeconds.toFixed(1)} 秒/題`)}
      ${metricCard("整體歸因正確率", fmtPct(s.accuracy), `${s.correct}/${s.total}`)}
      ${metricCard("證據版 B − 摘要版 A", `${conditionDiff >= 0 ? "+" : ""}${fmtPct(conditionDiff)}`, "RQ4 progressive disclosure")}
      ${metricCard("高風險高信心答錯率", fmtPct(s.highRiskBlindAdoptionRate), "RQ3 trust calibration")}
    </div>
    <section class="summary-section">
      <h3>A/B 條件正確率</h3>
      <div class="pie-grid two">
        ${pieCards(s.byCondition, Object.fromEntries(CONDITIONS.map((c) => [c, CONDITION[c][0]])))}
      </div>
    </section>
    <section class="summary-section">
      <h3>三情境正確率</h3>
      <div class="pie-grid three">
        ${pieCards(s.byScenario, Object.fromEntries(SCENARIOS.map((k) => [k, SCENARIO_COPY[k][0]])))}
      </div>
    </section>
    <section class="summary-section">
      <h3>四類真值正確率</h3>
      <div class="pie-grid four">
        ${pieCards(s.byGroundTruth, TYPE_LABEL)}
      </div>
    </section>
    <section class="summary-section">
      <h3>信心校準曲線</h3>
      ${renderCalibration(s.calibration)}
    </section>
    <section class="summary-section">
      <h3>四類混淆矩陣</h3>
      ${renderConfusion(s.confusion)}
    </section>`;
}

function renderStatusDetail(order) {
  const item = state.seq.find((t) => t.order === order);
  const trial = state.trials.find((t) => t.order === order);
  if (!item) return "";
  if (!trial) {
    const current = state.seq[state.i]?.order === order ? "目前作答中" : "尚未作答";
    return `<h3>第 ${order} 題</h3><p class="muted">${current}，還沒有可回溯的作答紀錄。</p>`;
  }
  return `<h3>第 ${order} 題作答回顧</h3>
    <dl class="review-dl">
      <dt>任務</dt><dd>${esc(taskTitle(item.pair))}</dd>
      <dt>條件</dt><dd>${esc(CONDITION[trial.condition][0])}</dd>
      <dt>你的判斷</dt><dd>${TYPE_LABEL[trial.choice]}，信心 ${trial.confidence}</dd>
      <dt>正解</dt><dd>${TYPE_LABEL[trial.ground_truth]}，${trial.correct ? "正確" : "不正確"}</dd>
      <dt>一句理由</dt><dd>${esc(trial.rationale || "未填")}</dd>
    </dl>`;
}

function renderStatus(selectedOrder = null) {
  const answered = new Set(state.trials.map((t) => t.order));
  const currentOrder = state.seq[state.i]?.order;
  const fallbackOrder = selectedOrder || state.trials.at(-1)?.order || currentOrder || 1;
  $("#status-summary").innerHTML = `<div class="notice compact">已完成 ${state.trials.length} / ${state.seq.length} 題。點擊已完成題目可回溯自己的判斷、信心與理由。</div>`;
  $("#status-list").innerHTML = state.seq.map((item) => {
    const trial = state.trials.find((t) => t.order === item.order);
    const status = trial ? "已完成" : item.order === currentOrder ? "目前題目" : "未填";
    const pressed = item.order === fallbackOrder ? "true" : "false";
    const detail = trial ? `${TYPE_LABEL[trial.choice]}，信心 ${trial.confidence}` : status;
    return `<button type="button" class="status-item" data-order="${item.order}" aria-pressed="${pressed}">
      <span>第 ${item.order} 題 · ${CONDITION[item.condition][0]} · ${SCENARIO_COPY[item.pair.scenario][0]}</span>
      <small>${detail}</small>
    </button>`;
  }).join("");
  $("#status-detail").innerHTML = renderStatusDetail(fallbackOrder);
  document.querySelectorAll(".status-item").forEach((button) => {
    button.onclick = () => {
      const order = Number(button.dataset.order);
      renderStatus(order);
    };
  });
}

function setAssignment() {
  const changeAt = state.seq.findIndex((item, idx) => idx > 0 && item.condition !== state.seq[idx - 1].condition);
  const first = state.seq[0];
  const second = changeAt >= 0 ? state.seq[changeAt] : null;
  return {
    block1: first ? first.pair.set : null,
    block1_condition: first ? first.condition : null,
    block2: second ? second.pair.set : null,
    block2_condition: second ? second.condition : null,
  };
}

function exportJson() {
  const doc = {
    participant_id: state.pid,
    started_at: state.startedAt,
    finished_at: new Date().toISOString(),
    condition_order: state.order,
    set_assignment: setAssignment(),
    summary: summarizeTrials(state.trials),
    interaction_events: state.events,
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
    $("#intro").innerHTML = `<h2>載入失敗</h2><p>${esc(e.message)}</p><p class="muted">請先產生 data/pairs.json，並透過本機伺服器開啟（非 file://）。</p>`;
    return;
  }
  $("#open-help").onclick = () => {
    logEvent("open_help");
    showDialog($("#help-dialog"));
  };
  $("#open-status").onclick = () => {
    logEvent("open_status");
    renderStatus();
    showDialog($("#status-dialog"));
  };
  $("#start").onclick = () => {
    state.pid = $("#pid").value.trim() || "P-anon";
    state.startedAt = new Date().toISOString();
    logEvent("start_study", { participant_id: state.pid, condition_order: state.order });
    $("#intro").hidden = true;
    $("#trial").hidden = false;
    $("#open-status").hidden = false;
    renderTrial();
  };
  $("#submit").onclick = submit;
  $("#next").onclick = next;
  $("#export").onclick = exportJson;
});
