/* 서울 소비 잠재력 대시보드 — 데이터: data.js (window.DASH) */
(() => {
  "use strict";
  const D = window.DASH;
  const TYPES = ["초과달성", "기대수준", "저평가", "데이터점검"];
  const TYPE_VAR = { "초과달성": "--over", "기대수준": "--normal", "저평가": "--under", "데이터점검": "--flag" };
  const RISING = "떠오르는 잠재상권";
  const CLIP = 1.5;                       // 지도 색 범위: log 배율 ±1.5 (×0.22 ~ ×4.5)
  const byCode = new Map(D.dongs.map(d => [d.code, d]));

  const state = { gu: "", types: new Set(TYPES), q: "", sel: null, sortKey: "ratio", sortDir: -1, open: new Set() };

  /* ---------------------------------------------------------------- utils */
  const $ = s => document.querySelector(s);
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmtWon = v => v == null ? "–" : v >= 10000 ? `${(v / 10000).toFixed(2)}조` : v >= 100 ? `${Math.round(v).toLocaleString()}억` : `${v.toFixed(1)}억`;
  const fmtRatio = v => v == null ? "–" : `×${v >= 10 ? v.toFixed(1) : v.toFixed(2)}`;
  const fmtTrend = v => v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(2)}`;
  const fmtInt = v => v == null ? "–" : Math.round(v).toLocaleString();
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const clip = (v, a) => Math.max(-a, Math.min(a, v));

  const matches = d =>
    (!state.gu || d.gu === state.gu) &&
    state.types.has(d.type) &&
    (!state.q || d.name.includes(state.q) || d.gu.includes(state.q));

  function theme() {
    return {
      ink: css("--ink"), ink2: css("--ink-2"), muted: css("--muted"), grid: css("--grid"),
      axis: css("--axis"), surface: css("--surface"), over: css("--over"), under: css("--under"),
      normal: css("--normal"), neutral: css("--neutral"), flag: css("--flag"),
      overStrong: css("--over-strong"), underStrong: css("--under-strong"),
      overSoft: css("--over-soft"), underSoft: css("--under-soft"),
      dark: document.documentElement.getAttribute("data-theme") === "dark" ||
        (!document.documentElement.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches),
    };
  }

  function baseLayout(t, extra = {}) {
    return Object.assign({
      paper_bgcolor: t.surface, plot_bgcolor: t.surface,
      font: { family: css("--sans") || "sans-serif", color: t.ink2, size: 12 },
      margin: { l: 10, r: 16, t: 8, b: 40 },
      hoverlabel: { bgcolor: t.surface, bordercolor: t.axis, font: { color: t.ink, size: 12.5 } },
      showlegend: false,
    }, extra);
  }
  const axis = (t, o = {}) => Object.assign({
    gridcolor: t.grid, zerolinecolor: t.axis, linecolor: t.axis, tickcolor: t.axis,
    tickfont: { color: t.muted }, automargin: true,
  }, o);
  const CFG = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"] };

  const HANDLERS = {};
  function draw(id, traces, layout) {
    const el = document.getElementById(id);
    if (el.dataset.empty) { el.innerHTML = ""; delete el.dataset.empty; }
    Plotly.react(el, traces, layout, CFG);
    if (HANDLERS[id]) {
      if (el.removeAllListeners) el.removeAllListeners("plotly_click");
      el.on("plotly_click", HANDLERS[id]);
    }
  }
  function empty(id, html) {
    const el = document.getElementById(id);
    Plotly.purge(el);
    el.innerHTML = html;
    el.dataset.empty = "1";
  }

  const ratioTicks = [0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50];
  const logTicks = arr => ({ tickvals: arr.map(Math.log), ticktext: arr.map(v => `×${v}`) });

  /* ---------------------------------------------------------------- KPI */
  function renderKpis() {
    const list = D.dongs.filter(d => !state.gu || d.gu === state.gu);
    const cnt = k => list.filter(d => d.type === k).length;
    const rising = list.filter(d => d.quad === RISING).length;
    const best = D.perf[0];
    const scope = state.gu || "서울";
    const tiles = [
      { label: `${scope} 분석 대상`, value: `${list.length}`, sub: state.gu ? "개 행정동" : "개 행정동 · 25개 자치구" },
      { label: "모델 설명력 (R²)", value: `${Math.round(best.R2 * 100)}%`, sub: `${best["모델"]} · 평균 오차 ×${best["평균오차배율"].toFixed(2)}` },
      { label: "초과달성", dot: "--over", value: cnt("초과달성"), sub: "기대의 1.5배 이상" },
      { label: "저평가", dot: "--under", value: cnt("저평가"), sub: "기대의 2/3 이하" },
      { label: "떠오르는 잠재상권", dot: "--under", ring: true, value: rising, sub: "기대 미만(×1↓) + 격차가 줄어드는 중" },
      { label: "데이터점검", dot: "--flag", value: cnt("데이터점검"), sub: "지출 급변·재건축 → 순위 제외" },
    ];
    $("#kpis").innerHTML = tiles.map(k => `
      <div class="kpi">
        <div class="label">${k.dot ? `<span class="dot" style="background:var(${k.dot});${k.ring ? "box-shadow:0 0 0 2px var(--under-soft)" : ""}"></span>` : ""}${esc(k.label)}</div>
        <div class="value">${k.value}</div>
        <div class="sub">${esc(k.sub)}</div>
      </div>`).join("");
  }

  /* ---------------------------------------------------------------- filters */
  function initFilters() {
    const sel = $("#guSel");
    [...D.gus].sort((a, b) => a.name.localeCompare(b.name, "ko")).forEach(g => {
      sel.insertAdjacentHTML("beforeend", `<option value="${esc(g.name)}">${esc(g.name)} (${g.n}개 동)</option>`);
    });
    sel.addEventListener("change", () => setGu(sel.value));

    $("#typeChips").innerHTML = TYPES.map(t =>
      `<button class="chip" type="button" data-t="${t}" aria-pressed="true"><span class="dot" style="background:var(${TYPE_VAR[t]})"></span>${t}</button>`
    ).join("");
    $("#typeChips").addEventListener("click", e => {
      const b = e.target.closest(".chip");
      if (!b) return;
      const t = b.dataset.t;
      if (state.types.has(t)) state.types.delete(t); else state.types.add(t);
      if (state.types.size === 0) TYPES.forEach(x => state.types.add(x));
      syncChips();
      refresh();
    });

    let timer;
    $("#search").addEventListener("input", e => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        state.q = e.target.value.trim();
        const hits = D.dongs.filter(matches);
        if (state.q && hits.length) {
          hits.forEach(d => state.open.add(d.gu));
          if (hits.length === 1) state.sel = hits[0].code;
        }
        refresh();
      }, 180);
    });

    $("#resetBtn").addEventListener("click", () => {
      state.gu = ""; state.q = ""; state.sel = null;
      TYPES.forEach(x => state.types.add(x));
      $("#guSel").value = ""; $("#search").value = "";
      state.open.clear();
      syncChips();
      refresh();
    });
  }
  function syncChips() {
    document.querySelectorAll(".chip").forEach(b => b.setAttribute("aria-pressed", state.types.has(b.dataset.t)));
  }
  function setGu(g) {
    state.gu = g;
    $("#guSel").value = g;
    if (g) state.open.add(g);
    if (state.sel && g && byCode.get(state.sel).gu !== g) state.sel = null;
    refresh();
  }
  function select(code) {
    state.sel = code;
    const d = byCode.get(code);
    if (d) state.open.add(d.gu);
    renderDetail(); renderMap(); renderTable(); renderQuad(); renderTops();
  }

  /* ---------------------------------------------------------------- map */
  function renderMap() {
    const t = theme();
    const all = D.dongs;
    const on = all.map(matches);
    const scale = [[0, t.underStrong], [0.2, t.under], [0.4, t.underSoft], [0.5, t.neutral],
      [0.6, t.overSoft], [0.8, t.over], [1, t.overStrong]];
    const size = all.map(d => 5 + 16 * Math.max(0, Math.log10(Math.max(d.actual, 0.1)) + 1) / 5.5);
    const hover = all.map(d =>
      `<b>${esc(d.name)}</b> · ${esc(d.gu)}<br>실제 ${fmtWon(d.actual)} / 기대 ${fmtWon(d.expected)}<br>` +
      `배율 <b>${fmtRatio(d.ratio)}</b> · ${esc(d.type)}<br>${esc(d.quad)}`);

    const normal = all.map((d, i) => d.type !== "데이터점검" ? i : -1).filter(i => i >= 0);
    const flagged = all.map((d, i) => d.type === "데이터점검" ? i : -1).filter(i => i >= 0);
    const pick = (arr, idx) => idx.map(i => arr[i]);

    const traces = [{
      type: "scatter", mode: "markers",
      x: pick(all.map(d => d.lon), normal), y: pick(all.map(d => d.lat), normal),
      customdata: pick(all.map(d => d.code), normal),
      text: pick(hover, normal), hovertemplate: "%{text}<extra></extra>",
      marker: {
        size: pick(size, normal),
        color: pick(all.map(d => clip(d.resid, CLIP)), normal),
        cmin: -CLIP, cmax: CLIP, colorscale: scale,
        opacity: pick(on.map(v => v ? 0.95 : 0.12), normal),
        line: { color: t.surface, width: 1 },
        colorbar: {
          thickness: 10, len: 0.6, x: 1.0, outlinewidth: 0,
          tickvals: [-1.386, -0.693, 0, 0.693, 1.386], ticktext: ["×0.25", "×0.5", "기대", "×2", "×4"],
          tickfont: { color: t.muted, size: 11 },
        },
      },
    }, {
      type: "scatter", mode: "markers",
      x: pick(all.map(d => d.lon), flagged), y: pick(all.map(d => d.lat), flagged),
      customdata: pick(all.map(d => d.code), flagged),
      text: pick(hover, flagged).map((h, k) => `${h}<br>⚠ ${esc(all[flagged[k]].flag)}`),
      hovertemplate: "%{text}<extra></extra>",
      marker: { symbol: "x-thin", size: 11, line: { color: t.flag, width: 2 }, opacity: pick(on.map(v => v ? 1 : 0.15), flagged) },
    }];

    // 자치구 라벨
    const gc = {};
    all.forEach(d => { (gc[d.gu] = gc[d.gu] || []).push(d); });
    const gnames = Object.keys(gc);
    traces.push({
      type: "scatter", mode: "text", hoverinfo: "skip",
      x: gnames.map(g => gc[g].reduce((s, d) => s + d.lon, 0) / gc[g].length),
      y: gnames.map(g => gc[g].reduce((s, d) => s + d.lat, 0) / gc[g].length),
      text: gnames,
      textfont: { size: gnames.map(g => g === state.gu ? 14 : 11), color: gnames.map(g => g === state.gu ? t.ink : t.muted) },
    });

    if (state.sel) {
      const d = byCode.get(state.sel);
      traces.push({
        type: "scatter", mode: "markers+text", x: [d.lon], y: [d.lat], text: [d.name],
        textposition: "top center", textfont: { color: t.ink, size: 13 }, hoverinfo: "skip",
        marker: { size: 24, color: "rgba(0,0,0,0)", line: { color: t.ink, width: 2 } },
      });
    }

    let xr, yr;
    if (state.gu) {
      const ds = gc[state.gu];
      const lons = ds.map(d => d.lon), lats = ds.map(d => d.lat);
      const pad = 0.012;
      xr = [Math.min(...lons) - pad, Math.max(...lons) + pad];
      yr = [Math.min(...lats) - pad, Math.max(...lats) + pad];
    }
    const layout = baseLayout(t, {
      margin: { l: 0, r: 0, t: 0, b: 0 },
      xaxis: { visible: false, range: xr, autorange: !xr },
      yaxis: { visible: false, range: yr, autorange: !yr, scaleanchor: "x", scaleratio: 1 / Math.cos(37.55 * Math.PI / 180) },
      dragmode: "pan",
    });
    draw("map", traces, layout);
  }

  /* ---------------------------------------------------------------- detail */
  function renderDetail() {
    const t = theme();
    if (!state.sel) {
      $("#dName").textContent = "행정동을 선택하세요";
      $("#dSub").textContent = "지도·표·순위 막대에서 동을 누르면 12분기 추이가 나타납니다.";
      $("#dStats").innerHTML = "";
      $("#dNote").textContent = "";
      $("#dNote").className = "note";
      empty("dLine", `<p class="note" style="padding-top:120px;text-align:center">예: 지도에서 파란 점(저평가) 또는 빨간 점(초과달성)을 눌러 보세요.</p>`);
      return;
    }
    const d = byCode.get(state.sel);
    const s = D.series[d.code];
    $("#dName").textContent = `${d.name} · ${d.gu}`;
    $("#dSub").innerHTML = `<span class="tag ${{ "초과달성": "over", "기대수준": "normal", "저평가": "under", "데이터점검": "flag" }[d.type]}">${esc(d.type)}</span> ${esc(d.quad)}`;
    const stats = [
      ["실제 소비 (분기 평균)", fmtWon(d.actual)], ["기대 소비 (분기 평균)", fmtWon(d.expected)],
      ["배율 (실제÷기대)", fmtRatio(d.ratio)], ["연간 추세", fmtTrend(d.trend)],
      ["상주인구", fmtInt(d.pop)], ["직장인구", fmtInt(d.work)],
      ["유동인구 (분기)", fmtInt(d.flow)], ["집객시설", fmtInt(d.fac)],
      ["지하철역", fmtInt(d.subway)],
    ];
    $("#dStats").innerHTML = stats.map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");

    const fill = d.resid >= 0 ? t.over : t.under;
    draw("dLine", [
      { x: D.quarters, y: s.e, name: "기대 (모델)", mode: "lines", line: { color: t.muted, width: 2 },
        hovertemplate: "기대 %{y:,.1f}억<extra></extra>" },
      { x: D.quarters, y: s.a, name: "실제", mode: "lines+markers", line: { color: fill, width: 2 },
        marker: { size: 8, color: fill, line: { color: t.surface, width: 2 } },
        fill: "tonexty", fillcolor: hexA(fill, 0.12), hovertemplate: "실제 %{y:,.1f}억<extra></extra>" },
    ], baseLayout(t, {
      margin: { l: 10, r: 10, t: 10, b: 40 }, showlegend: true, hovermode: "x unified",
      legend: { orientation: "h", x: 0, y: 1.12, font: { color: t.ink2 } },
      xaxis: axis(t, { showgrid: false, tickangle: -40 }),
      yaxis: axis(t, { rangemode: "tozero", ticksuffix: "억", tickformat: ",.0f" }),
    }));

    let note = "", warn = false;
    if (d.flag) { note = `⚠ 데이터점검: ${d.flag}. 순위·해석에서 제외하세요.`; warn = true; }
    else if (d.ratio >= 5) note = "기대의 5배 이상입니다. 지역 활력 외에 대형 점포·본사 매출이 이 주소로 집계되었을 가능성을 함께 확인하세요.";
    else if (d.quad === RISING) note = "아직 기대보다 덜 쓰이지만 격차가 해마다 줄고 있습니다. 인구·인프라가 받쳐 주는 만큼 소비가 따라오는 중인 후보입니다.";
    else if (d.type === "저평가") note = "인구·인프라 조건에 비해 소비가 적습니다. 인접 동으로 소비가 빠져나가는지, 업종 구성이 부족한지 확인해 보세요.";
    else if (d.type === "초과달성") note = "조건보다 소비가 많이 일어나는 강한 상권입니다. 외부 방문객을 끌어들이는 요인이 있는지 살펴보세요.";
    else note = "인구·인프라로 설명되는 만큼 소비가 일어나는 평범한 동네입니다.";
    $("#dNote").textContent = note;
    $("#dNote").className = warn ? "note warn" : "note";
  }
  function hexA(hex, a) {
    const h = hex.replace("#", "");
    const n = parseInt(h.length === 3 ? h.split("").map(c => c + c).join("") : h, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  /* ---------------------------------------------------------------- top / bottom */
  function renderTops() {
    const t = theme();
    const pool = D.dongs.filter(d => d.type !== "데이터점검" && (!state.gu || d.gu === state.gu) &&
      (!state.q || d.name.includes(state.q) || d.gu.includes(state.q)));
    const over = pool.filter(d => d.resid > 0).sort((a, b) => b.resid - a.resid).slice(0, 10).reverse();
    const under = pool.filter(d => d.resid < 0).sort((a, b) => a.resid - b.resid).slice(0, 10).reverse();
    // 저평가도 막대가 오른쪽으로 자라도록 |잔차|를 길이로 쓰고, 눈금은 실제 배율로 표기
    const bar = (list, color, id, ticks, flip) => {
      if (!list.length) { empty(id, `<p class="note">해당 조건의 동이 없습니다.</p>`); return; }
      draw(id, [{
        type: "bar", orientation: "h",
        y: list.map(d => `${d.name} (${d.gu})`), x: list.map(d => Math.abs(d.resid)),
        customdata: list.map(d => d.code),
        marker: {
          color,
          line: { color: list.map(d => d.code === state.sel ? t.ink : color), width: list.map(d => d.code === state.sel ? 2.5 : 0) },
        },
        text: list.map(d => `${fmtRatio(d.ratio)}  ${fmtWon(d.actual)} / ${fmtWon(d.expected)}`),
        textposition: "outside", cliponaxis: false, textfont: { color: t.ink2, size: 11 },
        hovertemplate: "<b>%{y}</b><br>실제 ÷ 기대 %{text}<extra></extra>",
        width: 0.62,
      }], baseLayout(t, {
        margin: { l: 10, r: 150, t: 4, b: 36 },
        xaxis: axis(t, {
          tickvals: ticks.map(v => Math.abs(Math.log(v))), ticktext: ticks.map(v => `×${v}`),
          zeroline: true, rangemode: "tozero",
          title: { text: flip ? "기대보다 얼마나 적게 쓰나 (실제 ÷ 기대, 로그 축)" : "기대보다 얼마나 많이 쓰나 (실제 ÷ 기대, 로그 축)", font: { size: 11 } },
        }),
        yaxis: axis(t, { showgrid: false, tickfont: { color: t.ink2, size: 12 } }),
        bargap: 0.3,
      }));
    };
    bar(over, t.over, "topOver", [1, 2, 5, 10, 25, 50], false);
    bar(under, t.under, "topUnder", [1, 0.5, 0.25, 0.1], true);
  }

  /* ---------------------------------------------------------------- gu charts */
  function renderGu() {
    const t = theme();
    const g = [...D.gus].sort((a, b) => a.resid - b.resid);
    const colorOf = x => {
      const base = x.resid >= 0 ? t.over : t.under;
      return !state.gu || state.gu === x.name ? base : hexA(base, 0.25);
    };
    draw("guBar", [{
      type: "bar", orientation: "h", y: g.map(x => x.name), x: g.map(x => x.resid),
      customdata: g.map(x => x.name),
      marker: { color: g.map(colorOf) },
      text: g.map(x => fmtRatio(x.ratio)), textposition: "outside", cliponaxis: false,
      textfont: { color: t.ink2, size: 11 },
      hovertemplate: g.map(x => `<b>${x.name}</b> (${x.n}개 동)<br>평균 배율 ${fmtRatio(x.ratio)}<br>초과 ${x.over} · 기대수준 ${x.normal} · 저평가 ${x.under}<br>떠오르는 잠재 ${x.rising}<extra></extra>`),
      width: 0.66,
    }], baseLayout(t, {
      margin: { l: 10, r: 50, t: 4, b: 36 },
      xaxis: axis(t, Object.assign(logTicks([0.75, 0.85, 1, 1.15, 1.3]), { zeroline: true, range: [Math.log(0.68), Math.log(1.45)] })),
      yaxis: axis(t, { showgrid: false, tickfont: { color: t.ink2, size: 12 } }),
    }));

    const g2 = [...D.gus].sort((a, b) => ((a.over - a.under) / a.n) - ((b.over - b.under) / b.n));
    const keys = [["under", "저평가", t.under], ["normal", "기대수준", t.normal], ["over", "초과달성", t.over], ["flag", "데이터점검", t.flag]];
    draw("guStack", keys.map(([k, label, color]) => ({
      type: "bar", orientation: "h", name: label, y: g2.map(x => x.name), x: g2.map(x => x[k]),
      customdata: g2.map(x => x.name),
      marker: { color: g2.map(x => !state.gu || state.gu === x.name ? color : hexA(color, 0.3)), line: { color: t.surface, width: 1.5 } },
      text: g2.map(x => x[k] >= 2 ? x[k] : ""), textposition: "inside", insidetextanchor: "middle", textangle: 0,
      textfont: { color: k === "normal" ? t.ink : "#ffffff", size: 11 },
      hovertemplate: `<b>%{y}</b><br>${label} %{x}곳<extra></extra>`,
      width: 0.7,
    })), baseLayout(t, {
      barmode: "stack", showlegend: true, uniformtext: { mode: "hide", minsize: 10 }, margin: { l: 10, r: 10, t: 30, b: 36 },
      legend: { orientation: "h", x: 0, y: 1.06, font: { color: t.ink2 }, traceorder: "normal" },
      xaxis: axis(t, { title: { text: "행정동 수", font: { size: 11 } } }),
      yaxis: axis(t, { showgrid: false, tickfont: { color: t.ink2, size: 12 } }),
    }));
  }

  /* ---------------------------------------------------------------- quadrant */
  function renderQuad() {
    const t = theme();
    const pool = D.dongs.filter(d => d.type !== "데이터점검");
    const on = pool.filter(matches);
    const rise = on.filter(d => d.quad === RISING);
    const rest = on.filter(d => d.quad !== RISING);
    const off = pool.filter(d => !matches(d));
    const pt = (list, color, size, name, op) => ({
      type: "scatter", mode: "markers", name,
      x: list.map(d => Math.max(-2.5, Math.min(4.5, d.resid))),
      y: list.map(d => Math.max(-0.6, Math.min(0.6, d.trend))),
      customdata: list.map(d => d.code),
      text: list.map(d => `<b>${esc(d.name)}</b> · ${esc(d.gu)}<br>배율 ${fmtRatio(d.ratio)} · 추세 ${fmtTrend(d.trend)}/년<br>${esc(d.quad)}`),
      hovertemplate: "%{text}<extra></extra>",
      marker: { color, size, opacity: op, line: { color: t.surface, width: 1 } },
    });
    const traces = [
      Object.assign(pt(off, t.normal, 6, "필터 밖", 0.25), { showlegend: false }),
      pt(rest, t.normal, 8, "그 외", 0.9),
      pt(rise, t.under, 10, "떠오르는 잠재상권", 1),
    ];
    if (state.sel && byCode.get(state.sel).type !== "데이터점검") {
      const d = byCode.get(state.sel);
      traces.push({
        type: "scatter", mode: "markers+text", hoverinfo: "skip", text: [d.name], textposition: "top center",
        textfont: { color: t.ink, size: 12 }, showlegend: false,
        x: [Math.max(-2.5, Math.min(4.5, d.resid))], y: [Math.max(-0.6, Math.min(0.6, d.trend))],
        marker: { size: 20, color: "rgba(0,0,0,0)", line: { color: t.ink, width: 2 } },
      });
    }
    const counts = D.summary.quad_counts;
    const lab = (x, y, text, xa, color) => ({ x, y, text, xanchor: xa, showarrow: false, font: { size: 12.5, color }, xref: "x", yref: "y" });
    draw("quad", traces, baseLayout(t, {
      showlegend: true, legend: { orientation: "h", x: 0, y: -0.14, font: { color: t.ink2 } },
      margin: { l: 10, r: 10, t: 10, b: 60 },
      xaxis: axis(t, Object.assign(logTicks(ratioTicks), { range: [-2.55, 4.55], zeroline: true, zerolinecolor: t.axis,
        title: { text: "현재 수준: 실제 ÷ 기대", font: { size: 11 } } })),
      yaxis: axis(t, { range: [-0.65, 0.65], zeroline: true, title: { text: "연간 추세 (+ 격차가 줄며 소비가 따라붙음)", font: { size: 11 } } }),
      shapes: [{ type: "rect", xref: "paper", x0: 0, x1: 1, y0: -0.05, y1: 0.05, fillcolor: t.neutral, line: { width: 0 }, layer: "below" }],
      annotations: [
        lab(-2.45, 0.58, `<b>떠오르는 잠재상권 ${counts[RISING] || 0}</b>`, "left", t.underStrong),
        lab(4.45, 0.58, `<b>성장하는 강세상권 ${counts["성장하는 강세상권"] || 0}</b>`, "right", t.ink2),
        lab(-2.45, -0.58, `<b>위축되는 약세상권 ${counts["위축되는 약세상권"] || 0}</b>`, "left", t.ink2),
        lab(4.45, -0.58, `<b>식어가는 강세상권 ${counts["식어가는 강세상권"] || 0}</b>`, "right", t.ink2),
      ],
    }));
  }

  /* ---------------------------------------------------------------- importance + perf */
  function renderImp() {
    const t = theme();
    const pal = t.dark ? { "인구": "#3987e5", "인프라": "#d95926", "주거": "#199e70", "공간·시간": t.normal }
                       : { "인구": "#2a78d6", "인프라": "#eb6834", "주거": "#1baf7a", "공간·시간": t.normal };
    const list = [...D.importance].reverse();
    const groups = Object.keys(pal);
    draw("imp", groups.map(gname => {
      const sub = list.map(x => x["그룹"] === gname ? x["중요도"] : null);
      return {
        type: "bar", orientation: "h", name: gname, y: list.map(x => x["변수명"]), x: sub,
        marker: { color: pal[gname] },
        hovertemplate: `%{y}<br>R² 감소 %{x:.3f}<extra>${gname}</extra>`,
        width: 0.66,
      };
    }), baseLayout(t, {
      barmode: "overlay", showlegend: true,
      legend: { orientation: "h", x: 0, y: 1.06, font: { color: t.ink2 } },
      margin: { l: 10, r: 20, t: 30, b: 36 },
      xaxis: axis(t, { title: { text: "R² 감소폭", font: { size: 11 } } }),
      yaxis: axis(t, { showgrid: false, tickfont: { color: t.ink2, size: 12 } }),
    }));

    $("#perf").innerHTML = D.perf.map((p, i) =>
      `<span class="pm ${i === 0 ? "best" : ""}">${i === 0 ? "✓ " : ""}${esc(p["모델"])} · R² <b>${p.R2.toFixed(3)}</b> · 오차 ×<b>${p["평균오차배율"].toFixed(2)}</b></span>`
    ).join("");
  }

  /* ---------------------------------------------------------------- table */
  function renderTable() {
    const k = state.sortKey, dir = state.sortDir;
    const cmp = (a, b) => {
      const x = a[k], y = b[k];
      if (typeof x === "string" || typeof y === "string") return dir * String(x ?? "").localeCompare(String(y ?? ""), "ko");
      return dir * ((x ?? -Infinity) - (y ?? -Infinity));
    };
    const byGu = {};
    D.dongs.filter(matches).forEach(d => { (byGu[d.gu] = byGu[d.gu] || []).push(d); });
    const guRows = D.gus.filter(g => byGu[g.name]).map(g => {
      const ds = byGu[g.name];
      const trend = ds.reduce((s, d) => s + (d.trend || 0), 0) / ds.length;
      return Object.assign({}, g, { trend, type: `초과 ${g.over} · 저평가 ${g.under}`, quad: `떠오르는 잠재 ${g.rising}`, dongs: ds });
    }).sort(cmp);

    const rows = [];
    guRows.forEach(g => {
      const open = state.open.has(g.name);
      const bar = `<span class="mini" aria-hidden="true">${[["--under", g.under], ["--normal", g.normal], ["--over", g.over], ["--flag", g.flag]]
        .map(([v, n]) => n ? `<i style="width:${n * 4}px;background:var(${v})"></i>` : "").join("")}</span>`;
      rows.push(`<tr class="gu-row ${open ? "open" : ""}" data-gu="${esc(g.name)}" aria-expanded="${open}">
        <td>${esc(g.name)} <span style="color:var(--muted);font-weight:400">(${g.dongs.length}/${g.n})</span>${bar}</td>
        <td class="num">${fmtWon(g.actual)}</td><td class="num">${fmtWon(g.expected)}</td>
        <td class="num ${g.resid >= 0 ? "pos" : "neg"}">${fmtRatio(g.ratio)}</td>
        <td class="num">${fmtTrend(g.trend)}</td><td>${esc(g.type)}</td><td>${esc(g.quad)}</td></tr>`);
      if (!open) return;
      g.dongs.sort(cmp).forEach(d => {
        const cls = { "초과달성": "over", "기대수준": "normal", "저평가": "under", "데이터점검": "flag" }[d.type];
        rows.push(`<tr class="dong-row ${d.code === state.sel ? "sel" : ""}" data-code="${d.code}">
          <td>${esc(d.name)}${d.flag ? ` <span title="${esc(d.flag)}">⚠</span>` : ""}</td>
          <td class="num">${fmtWon(d.actual)}</td><td class="num">${fmtWon(d.expected)}</td>
          <td class="num ${d.resid >= 0 ? "pos" : "neg"}">${fmtRatio(d.ratio)}</td>
          <td class="num">${fmtTrend(d.trend)}</td>
          <td><span class="tag ${cls}">${esc(d.type)}</span></td><td>${esc(d.quad)}</td></tr>`);
      });
    });
    $("#tbl tbody").innerHTML = rows.join("") || `<tr><td colspan="7" class="note">조건에 맞는 행정동이 없습니다.</td></tr>`;
    document.querySelectorAll("#tbl th").forEach(th =>
      th.setAttribute("aria-sort", th.dataset.k === k ? (dir > 0 ? "ascending" : "descending") : "none"));
  }
  function initTable() {
    $("#tbl thead").addEventListener("click", e => {
      const th = e.target.closest("th");
      if (!th) return;
      const k = th.dataset.k;
      if (state.sortKey === k) state.sortDir *= -1;
      else { state.sortKey = k; state.sortDir = ["name", "type", "quad"].includes(k) ? 1 : -1; }
      renderTable();
    });
    $("#tbl tbody").addEventListener("click", e => {
      const gr = e.target.closest("tr.gu-row");
      if (gr) {
        const g = gr.dataset.gu;
        if (state.open.has(g)) state.open.delete(g); else state.open.add(g);
        renderTable();
        return;
      }
      const dr = e.target.closest("tr.dong-row");
      if (dr) {
        select(dr.dataset.code);
        $("#detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
    $("#expandAll").addEventListener("click", () => { D.gus.forEach(g => state.open.add(g.name)); renderTable(); });
    $("#collapseAll").addEventListener("click", () => { state.open.clear(); renderTable(); });
  }

  /* ---------------------------------------------------------------- wiring */
  const onDong = ev => {
    const c = ev.points && ev.points[0] && ev.points[0].customdata;
    if (c && byCode.has(c)) select(c);
  };
  const onGu = ev => {
    const g = ev.points && ev.points[0] && ev.points[0].customdata;
    if (g) setGu(state.gu === g ? "" : g);
  };
  ["map", "topOver", "topUnder", "quad"].forEach(id => { HANDLERS[id] = onDong; });
  ["guBar", "guStack"].forEach(id => { HANDLERS[id] = onGu; });

  function refresh() {
    renderKpis(); renderMap(); renderDetail(); renderTops(); renderGu(); renderQuad(); renderTable();
  }
  function renderAll() { refresh(); renderImp(); }

  $("#themeBtn").addEventListener("click", () => {
    const cur = theme().dark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
    renderAll();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!document.documentElement.getAttribute("data-theme")) renderAll();
  });

  initFilters();
  initTable();
  // 첫 화면: 떠오르는 잠재상권 중 가장 저평가된 동을 예시로 선택
  const firstRise = D.dongs.filter(d => d.quad === RISING).sort((a, b) => a.resid - b.resid)[0];
  if (firstRise) { state.sel = firstRise.code; state.open.add(firstRise.gu); }
  renderAll();
})();
