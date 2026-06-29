/* FX Journal Stats dashboard — renders panels from data.json.
   Panel chosen via ?panel=calendar|time|risk|discipline (default: calendar). */

const GREEN = "#2ecc71";
const RED = "#ff6b6b";
const MUTED = "#8b8b8b";

const params = new URLSearchParams(location.search);
const PANEL = (params.get("panel") || "calendar").toLowerCase();

const app = document.getElementById("app");
const footer = document.getElementById("footer");

function money(v, dec = 2) {
  const sign = v < 0 ? "-" : "";
  return sign + "$" + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function moneyK(v) {
  const a = Math.abs(v);
  if (a >= 1000) return (v < 0 ? "-" : "") + (a / 1000).toFixed(1) + "K";
  return v.toFixed(1);
}
function cls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }

function card(label, value, isMoney = true, pct = false) {
  const c = typeof value === "number" ? cls(value) : "";
  let disp;
  if (pct) disp = value.toFixed(1) + "%";
  else if (isMoney) disp = money(value);
  else disp = value;
  return `<div class="card"><div class="label"><span>${label}</span></div>
    <div class="value ${c}">${disp}</div></div>`;
}

function chartBox(id, title) {
  return `<div class="chart-box"><h3>${title}</h3>
    <div class="chart-canvas-wrap"><canvas id="${id}"></canvas></div></div>`;
}

function barChart(id, items, opts = {}) {
  const labels = items.map(i => i.label);
  const values = items.map(i => i.value);
  const colors = values.map(v => (v < 0 ? RED : GREEN));
  new Chart(document.getElementById(id), {
    type: opts.horizontal ? "bar" : "bar",
    data: { labels, datasets: [{ label: "P&L", data: values, backgroundColor: colors, borderRadius: 4, maxBarThickness: 70 }] },
    options: {
      indexAxis: opts.horizontal ? "y" : "x",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: MUTED } },
        tooltip: { callbacks: { label: c => money(c.parsed[opts.horizontal ? "x" : "y"]) } } },
      scales: {
        x: { ticks: { color: MUTED }, grid: { color: "#2a2a2a" } },
        y: { ticks: { color: MUTED }, grid: { color: "#2a2a2a" } },
      },
    },
  });
}

function areaChart(id, items, valueKey, color) {
  new Chart(document.getElementById(id), {
    type: "line",
    data: {
      labels: items.map(i => i.date),
      datasets: [{
        label: valueKey === "drawdown" ? "Drawdown" : "Equity",
        data: items.map(i => i[valueKey]),
        borderColor: color, backgroundColor: color + "33",
        fill: true, tension: 0.1, pointRadius: items.length > 40 ? 0 : 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: MUTED } },
        tooltip: { callbacks: { label: c => money(c.parsed.y) } } },
      scales: {
        x: { ticks: { color: MUTED, maxTicksLimit: 12 }, grid: { color: "#2a2a2a" } },
        y: { ticks: { color: MUTED }, grid: { color: "#2a2a2a" } },
      },
    },
  });
}

/* ---------- panels ---------- */

function renderTime(d) {
  const s = d.stats;
  app.innerHTML = `<h2 class="panel-title">Time Analysis</h2>
    <div class="cards">
      ${card("Avg P&L / Day", s.avg_pl_day)}
      ${card("Avg P&L / Month", s.avg_pl_month)}
      ${card("Best Trading Day", s.best_day)}
      ${card("Worst Trading Day", s.worst_day)}
    </div>
    <div class="charts-row">
      ${chartBox("c_dow", "Daily Performance")}
      ${chartBox("c_ew", "Entry Window Stats")}
    </div>`;
  barChart("c_dow", d.charts.dow);
  barChart("c_ew", d.charts.entry_window);
}

function renderRisk(d) {
  const s = d.stats;
  app.innerHTML = `<h2 class="panel-title">Risk Analysis</h2>
    <div class="cards">
      ${card("Max Drawdown", s.max_drawdown)}
      ${card("Biggest Loser", s.biggest_loser)}
      ${card("Biggest Winner", s.biggest_winner)}
      ${card("Recovery Factor", s.recovery_factor, false)}
    </div>
    <div class="cards">
      ${card("Avg Win", s.avg_win)}
      ${card("Avg Loss", s.avg_loss)}
      ${card("Risk / Reward", s.risk_reward, false)}
      ${card("Consistency Score", s.consistency, false, true)}
    </div>
    <div class="charts-row">
      ${chartBox("c_dd", "Drawdown Chart")}
    </div>`;
  areaChart("c_dd", d.charts.drawdown, "drawdown", RED);
}

function renderDiscipline(d) {
  const s = d.stats;
  app.innerHTML = `<h2 class="panel-title">Discipline Analysis</h2>
    <div class="cards">
      ${card("Plan Adherence", s.plan_adherence, false, true)}
      ${card("Followed Plan P&L", s.followed_pl)}
      ${card("Followed Plan Win Rate", s.followed_win_rate, false, true)}
    </div>
    <div class="charts-row">
      ${chartBox("c_pos", "Positive Tags Performance")}
      ${chartBox("c_neg", "Negative Tags Performance")}
    </div>`;
  barChart("c_pos", d.charts.pos_tags);
  barChart("c_neg", d.charts.neg_tags);
}

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

function renderCalendar(d) {
  const daily = {};
  let tradesByDay = {};
  (d.charts ? d.charts.daily : []).forEach(x => { daily[x.date] = x.value; });
  (d.trades || []).forEach(t => { tradesByDay[t.date] = (tradesByDay[t.date] || 0) + 1; });

  const dates = Object.keys(daily).sort();
  const months = [...new Set(dates.map(x => x.slice(0, 7)))];
  let cur = months.length ? months[months.length - 1] : new Date().toISOString().slice(0, 7);

  function draw() {
    const [yy, mm] = cur.split("-").map(Number);
    const first = new Date(yy, mm - 1, 1);
    const monthName = first.toLocaleString("en-US", { month: "long", year: "numeric" });
    let monthPL = 0;
    for (const dkey in daily) if (dkey.slice(0, 7) === cur) monthPL += daily[dkey];

    // build weeks (Mon-Fri), with weekly summary column
    let startDow = (first.getDay() + 6) % 7; // 0=Mon
    const daysInMonth = new Date(yy, mm, 0).getDate();
    let cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) cells.push(day);

    let rows = "";
    for (let w = 0; w < cells.length; w += 7) {
      const week = cells.slice(w, w + 7);
      let weekPL = 0, weekTrades = 0, tds = "";
      for (let i = 0; i < 5; i++) { // Mon-Fri only
        const day = week[i];
        if (!day) { tds += `<td></td>`; continue; }
        const dkey = `${yy}-${String(mm).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const pl = daily[dkey];
        const nt = tradesByDay[dkey] || 0;
        if (pl === undefined) { tds += `<td class="daynum">${day}</td>`; continue; }
        weekPL += pl; weekTrades += nt;
        const klass = pl > 0 ? "win" : pl < 0 ? "loss" : "";
        tds += `<td class="daynum ${klass}">${day}
          <span class="day-trades">${nt} trade${nt > 1 ? "s" : ""}</span>
          <span class="day-pl ${cls(pl)}">${moneyK(pl)}</span></td>`;
      }
      const sumKlass = weekPL > 0 ? "pos" : weekPL < 0 ? "neg" : "";
      const summary = weekTrades
        ? `<span class="s-trades">${weekTrades} trades</span><span class="s-pl ${sumKlass}">${moneyK(weekPL)}</span>`
        : "";
      tds += `<td class="summary">${summary}</td>`;
      rows += `<tr>${tds}</tr>`;
    }

    app.innerHTML = `
      <div class="cal-header">
        <div class="cal-nav">
          <button id="prev">‹</button>
          <span class="cal-month">${monthName}</span>
          <button id="next">›</button>
        </div>
        <div class="cal-pl">P/L: <b class="${cls(monthPL)}">${moneyK(monthPL)}</b></div>
      </div>
      <table class="calendar">
        <thead><tr>${DOW_LABELS.map(d => `<th>${d}</th>`).join("")}<th>Summary</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
    document.getElementById("prev").onclick = () => { shift(-1); };
    document.getElementById("next").onclick = () => { shift(1); };
  }
  function shift(n) {
    let [yy, mm] = cur.split("-").map(Number);
    mm += n; if (mm < 1) { mm = 12; yy--; } if (mm > 12) { mm = 1; yy++; }
    cur = `${yy}-${String(mm).padStart(2, "0")}`;
    draw();
  }
  draw();
}

/* ---------- boot ---------- */

fetch("data.json?_=" + Date.now())
  .then(r => r.json())
  .then(d => {
    if (d.empty || d.trade_count === 0) {
      app.innerHTML = `<div class="empty-note">No trades logged yet.<br>This dashboard fills automatically as you add trades to your Notion TRADES DB.</div>`;
    } else if (PANEL === "time") renderTime(d);
    else if (PANEL === "risk") renderRisk(d);
    else if (PANEL === "discipline") renderDiscipline(d);
    else renderCalendar(d);
    const dt = d.generated_at ? new Date(d.generated_at).toLocaleString() : "";
    footer.textContent = `${d.trade_count} trades · updated ${dt}`;
  })
  .catch(e => { app.innerHTML = `<div class="empty-note">Failed to load data.json<br>${e}</div>`; });
