/* Clause Lens - front end. Vanilla JS, no build step, no dependencies. */

const $ = (id) => document.getElementById(id);
const state = { result: null, meta: null };

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

/* ---------------------------------------------------------------- meta -- */

async function loadMeta() {
  const res = await fetch("/api/meta");
  const meta = await res.json();
  state.meta = meta;

  const typeSel = $("contract-type");
  meta.contract_types.forEach((t) => {
    const opt = el("option", null, t.label);
    opt.value = t.key;
    typeSel.appendChild(opt);
  });

  const perSel = $("perspective");
  meta.perspectives.forEach((p) => {
    const opt = el("option", null, p.label);
    opt.value = p.key;
    perSel.appendChild(opt);
  });

  const sampleSel = $("sample-select");
  const blank = el("option", null, "Choose a sample contract");
  blank.value = "";
  sampleSel.appendChild(blank);
  meta.samples.forEach((s) => {
    const opt = el("option", null, s.name);
    opt.value = s.id;
    sampleSel.appendChild(opt);
  });
  sampleSel.addEventListener("change", showSampleBlurb);
  showSampleBlurb();
}

function showSampleBlurb() {
  const id = $("sample-select").value;
  const s = state.meta && state.meta.samples.find((x) => x.id === id);
  $("sample-blurb").textContent = s ? s.blurb : "";
}

/* -------------------------------------------------------------- review -- */

async function runReview() {
  const text = $("contract-text").value;
  if (!text.trim()) {
    showError("Paste a contract first.");
    return;
  }
  showError("");
  const btn = $("run");
  btn.disabled = true;
  btn.textContent = "Reading the contract...";

  try {
    const res = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        title: $("title").value,
        contract_type: $("contract-type").value,
        perspective: $("perspective").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }
    state.result = data;
    render(data);
  } catch (err) {
    showError("Could not reach the local server: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Review this contract";
  }
}

function showError(msg) {
  const box = $("error");
  box.textContent = msg;
  box.classList.toggle("hidden", !msg);
}

/* -------------------------------------------------------------- render -- */

function render(result) {
  $("empty-state").classList.add("hidden");
  $("report").classList.remove("hidden");

  const score = result.score;
  const scoreValue = $("score-value");
  clear(scoreValue);
  scoreValue.appendChild(document.createTextNode(String(score.overall)));
  const small = el("small", null, " / 100");
  scoreValue.appendChild(small);

  $("verdict").textContent = score.verdict_label;
  $("verdict-advice").textContent = score.verdict_advice;

  const chips = $("severity-chips");
  clear(chips);
  const counts = score.counts;
  ["critical", "high", "medium", "low", "positive"].forEach((k) => {
    if (!counts[k]) return;
    const chip = el("span", "chip " + k);
    chip.appendChild(el("b", null, counts[k]));
    chip.appendChild(document.createTextNode(" " + k));
    chips.appendChild(chip);
  });

  renderAxes(score.axes);

  const caps = $("caps");
  clear(caps);
  if (score.caps && score.caps.length) {
    caps.classList.remove("hidden");
    caps.appendChild(el("h3", null, "Why the score is held down"));
    const ul = el("ul");
    score.caps.forEach((c) => ul.appendChild(el("li", null, c.reason)));
    caps.appendChild(ul);
  } else {
    caps.classList.add("hidden");
  }

  $("count-findings").textContent = "(" + result.findings.length + ")";
  $("count-missing").textContent = "(" + result.missing.length + ")";
  $("count-dates").textContent = "(" + result.deadlines.length + ")";

  renderFindings(result.findings);
  renderMissing(result.missing);
  renderDates(result.deadlines);
  renderPlan(result.negotiation_plan);
  renderDraft(result.counter_proposal);
  renderStars();
}

function renderAxes(axes) {
  const box = $("axes");
  clear(box);
  axes.forEach((a) => {
    const row = el("div", "axis-row");
    const name = el("div", "axis-name");
    name.appendChild(document.createTextNode(a.label));
    name.appendChild(el("span", "axis-about", a.about));
    row.appendChild(name);

    const bar = el("div", "bar");
    const fill = el("span");
    const colour = a.score >= 80 ? "#4ec9a5" : a.score >= 60 ? "#ffd166" : a.score >= 40 ? "#ff9f43" : "#ff5c7a";
    fill.style.width = Math.max(2, a.score) + "%";
    fill.style.background = colour;
    bar.appendChild(fill);
    row.appendChild(bar);

    row.appendChild(el("div", "axis-score", a.score));
    box.appendChild(row);
  });
}

function renderFindings(findings) {
  const box = $("tab-findings");
  clear(box);
  if (!findings.length) {
    box.appendChild(el("p", "hint", "No findings. That is unusual - check the contract was pasted in full."));
    return;
  }
  findings.forEach((f) => {
    const card = el("div", "finding " + f.severity);
    const head = el("div", "finding-head");
    head.appendChild(el("span", "sev " + f.severity, f.severity));
    head.appendChild(el("h3", null, f.title));
    head.appendChild(el("span", "finding-id", f.id));
    card.appendChild(head);

    if (f.evidence) card.appendChild(el("div", "evidence", f.evidence));

    const why = el("div", "why");
    why.appendChild(el("b", null, "why it matters"));
    why.appendChild(document.createTextNode(f.why));
    card.appendChild(why);

    const fix = el("div", "fix");
    fix.appendChild(el("b", null, "fix"));
    fix.appendChild(document.createTextNode(f.fix));
    card.appendChild(fix);

    if (f.fallback) {
      const fb = el("div", "fallback");
      fb.appendChild(el("b", null, "fallback"));
      fb.appendChild(document.createTextNode(f.fallback));
      card.appendChild(fb);
    }
    card.appendChild(el("div", "leverage",
      "Leverage " + f.leverage + "/5 - " + leverageNote(f.leverage)));
    box.appendChild(card);
  });
}

function leverageNote(n) {
  if (n >= 5) return "standard ask, likely to be accepted";
  if (n === 4) return "common ask, usually conceded";
  if (n === 3) return "reasonable but contested";
  return "hard sell, raise it once";
}

function renderMissing(missing) {
  const box = $("tab-missing");
  clear(box);
  if (!missing.length) {
    box.appendChild(el("p", "hint", "Nothing standard is missing for this type of contract."));
    return;
  }
  missing.forEach((m) => {
    const card = el("div", "gap");
    card.appendChild(el("h3", null, m.label));
    card.appendChild(el("div", "why", m.why));
    const sug = el("div", "suggest");
    sug.appendChild(el("b", null, "suggested wording"));
    sug.appendChild(document.createTextNode(m.suggested));
    card.appendChild(sug);
    box.appendChild(card);
  });
}

function renderDates(dates) {
  const box = $("tab-dates");
  clear(box);
  if (!dates.length) {
    box.appendChild(el("p", "hint", "No dates found. Check the contract states an effective date."));
    return;
  }
  const table = el("table", "dates");
  const head = el("tr");
  ["Date", "What happens", "Why it matters"].forEach((h) => head.appendChild(el("th", null, h)));
  table.appendChild(head);
  dates.forEach((d) => {
    const tr = el("tr");
    tr.appendChild(el("td", "date", d.date));
    const label = el("td");
    label.appendChild(el("b", null, d.label));
    label.appendChild(el("div", "hint", d.source));
    tr.appendChild(label);
    tr.appendChild(el("td", "note", d.note));
    table.appendChild(tr);
  });
  box.appendChild(table);
}

function renderPlan(plan) {
  const box = $("tab-plan");
  clear(box);
  if (!plan.length) {
    box.appendChild(el("p", "hint", "Nothing to negotiate."));
    return;
  }
  plan.forEach((item) => {
    const row = el("div", "plan-item");
    row.appendChild(el("div", "plan-rank", item.rank));
    const body = el("div");
    body.appendChild(el("h3", null, item.title));
    body.appendChild(el("div", "hint", item.severity + " - " + item.why));
    if (item.ask) {
      const ask = el("div", "plan-ask");
      ask.appendChild(el("b", null, "ask"));
      ask.appendChild(document.createTextNode(item.ask));
      body.appendChild(ask);
    }
    if (item.fallback) {
      body.appendChild(el("div", "plan-fallback", "Fallback: " + item.fallback));
    }
    body.appendChild(el("div", "plan-meta", item.leverage_note));
    row.appendChild(body);
    box.appendChild(row);
  });
}

function renderDraft(text) {
  const box = $("tab-draft");
  clear(box);
  const row = el("div", "copy-row");
  const copy = el("button", "ghost", "Copy draft");
  copy.addEventListener("click", () => {
    navigator.clipboard.writeText(text).then(() => {
      copy.textContent = "Copied";
      setTimeout(() => { copy.textContent = "Copy draft"; }, 1500);
    });
  });
  row.appendChild(copy);
  box.appendChild(row);
  box.appendChild(el("div", "draft-box", text));
}

/* --------------------------------------------------------------- tabs --- */

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      ["findings", "missing", "dates", "plan", "draft"].forEach((name) => {
        $("tab-" + name).classList.toggle("hidden", name !== tab.dataset.tab);
      });
    });
  });
}

/* ------------------------------------------------------------- exports -- */

function download(filename, content, type) {
  const blob = new Blob([content], { type: type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slugify(value) {
  return (value || "contract").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
}

async function exportFile(format) {
  if (!state.result) return;
  const title = state.result.meta.title || "contract";
  const id = state.result.review_id;
  if (id) {
    const res = await fetch("/api/export/" + id + "?format=" + format);
    if (res.ok) {
      const text = await res.text();
      const types = { md: "text/markdown", json: "application/json", ics: "text/calendar" };
      const exts = { md: "md", json: "json", ics: "ics" };
      download(slugify(title) + "." + exts[format], text, types[format]);
      return;
    }
  }
  // no stored id (saving disabled): build the export locally
  if (format === "json") {
    download(slugify(title) + ".json", JSON.stringify(state.result, null, 2), "application/json");
  } else if (format === "ics") {
    download(slugify(title) + ".ics", buildIcs(state.result.deadlines, title), "text/calendar");
  } else {
    download(slugify(title) + ".md", buildMarkdown(state.result), "text/markdown");
  }
}

function buildIcs(dates, title) {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Clause Lens//Deadlines//EN"];
  (dates || []).forEach((d) => {
    const start = d.date.replace(/-/g, "");
    const end = new Date(d.date + "T00:00:00");
    end.setDate(end.getDate() + 1);
    const endStr = end.toISOString().slice(0, 10).replace(/-/g, "");
    lines.push("BEGIN:VEVENT");
    lines.push("DTSTART;VALUE=DATE:" + start);
    lines.push("DTEND;VALUE=DATE:" + endStr);
    lines.push("SUMMARY:" + title + ": " + d.label);
    lines.push("DESCRIPTION:" + (d.note || ""));
    lines.push("END:VEVENT");
  });
  lines.push("END:VCALENDAR");
  return lines.join("\r\n") + "\r\n";
}

function buildMarkdown(result) {
  const out = [];
  out.push("# Contract review: " + (result.meta.title || "Untitled agreement"));
  out.push("");
  out.push("**Score: " + result.score.overall + " / 100 - " + result.score.verdict_label + "**");
  out.push("");
  result.findings.forEach((f) => {
    out.push("## [" + f.id + "] " + f.title + " (" + f.severity + ")");
    out.push("");
    if (f.evidence) { out.push("> " + f.evidence); out.push(""); }
    out.push("**Why it matters:** " + f.why);
    out.push("");
    out.push("**Fix:** " + f.fix);
    out.push("");
  });
  return out.join("\n");
}

/* ------------------------------------------------------------- ratings -- */

function renderStars() {
  const box = $("stars");
  clear(box);
  const saved = state.result && state.result.rating;
  for (let i = 1; i <= 5; i++) {
    const b = el("button", saved === i ? "on" : null, String(i));
    b.addEventListener("click", () => saveRating(i));
    box.appendChild(b);
  }
}

async function saveRating(value) {
  if (!state.result || !state.result.review_id) return;
  const notes = $("notes").value;
  await fetch("/api/history/" + state.result.review_id, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating: value, notes: notes }),
  });
  state.result.rating = value;
  renderStars();
}

/* ------------------------------------------------------------- history -- */

async function loadHistory() {
  const res = await fetch("/api/history");
  const data = await res.json();
  const box = $("history-list");
  clear(box);
  if (!data.reviews.length) {
    box.appendChild(el("p", "hint", "No past reviews yet."));
    return;
  }
  data.reviews.forEach((r) => {
    const item = el("div", "history-item");
    item.appendChild(el("div", "h-title", r.title || "Untitled agreement"));
    const meta = el("div", "h-meta",
      (r.created_at || "").slice(0, 10) + " - " + r.score + "/100 - " + r.contract_type);
    item.appendChild(meta);
    item.addEventListener("click", () => openReview(r.id));
    box.appendChild(item);
  });
}

async function openReview(id) {
  const res = await fetch("/api/export/" + id + "?format=json");
  if (!res.ok) return;
  const result = await res.json();
  result.review_id = id;
  state.result = result;
  $("title").value = result.meta.title || "";
  $("contract-type").value = result.meta.contract_type || "generic";
  $("perspective").value = result.meta.perspective || "party";
  $("contract-text").value = "";
  render(result);
  $("history-panel").classList.add("hidden");
  updateWordCount();
}

/* ---------------------------------------------------------------- init -- */

function updateWordCount() {
  const text = $("contract-text").value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  $("word-count").textContent = words + (words === 1 ? " word" : " words");
}

function init() {
  setupTabs();
  loadMeta();

  $("run").addEventListener("click", runReview);
  $("clear").addEventListener("click", () => {
    $("contract-text").value = "";
    $("title").value = "";
    updateWordCount();
  });
  $("contract-text").addEventListener("input", updateWordCount);
  $("load-sample").addEventListener("click", async () => {
    const id = $("sample-select").value;
    if (!id) return;
    const res = await fetch("/api/samples/" + id);
    const s = await res.json();
    $("contract-text").value = s.text;
    $("title").value = s.name;
    $("contract-type").value = s.contract_type;
    $("perspective").value = s.perspective;
    updateWordCount();
  });
  document.querySelectorAll("[data-export]").forEach((btn) => {
    btn.addEventListener("click", () => exportFile(btn.dataset.export));
  });
  $("history-toggle").addEventListener("click", async () => {
    await loadHistory();
    $("history-panel").classList.toggle("hidden");
  });
  $("history-close").addEventListener("click", () => $("history-panel").classList.add("hidden"));
  $("notes").addEventListener("change", () => {
    if (state.result && state.result.review_id && state.result.rating) saveRating(state.result.rating);
  });
  updateWordCount();
}

document.addEventListener("DOMContentLoaded", init);
