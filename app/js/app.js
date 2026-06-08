// app.js — 画面制御 (依存なし / ESモジュール)
import { QUIZ_TYPES, buildSession, generateQuestion } from "./quiz.js?v=11";

const DATA_BASE = "../data/master/";
const photoUrl = (p) => DATA_BASE + p.photo;

// 画像が読めない場合のフォールバック(頭文字プレースホルダ)
function placeholderSVG(name) {
  const ch = esc((String(name || "?").trim()[0]) || "?");
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='180' height='240'>
    <rect width='100%' height='100%' fill='#21252f'/>
    <text x='50%' y='54%' font-family='sans-serif' font-size='90' font-weight='900'
      fill='#3a4150' text-anchor='middle' dominant-baseline='middle'>${ch}</text></svg>`;
  return "data:image/svg+xml," + encodeURIComponent(svg);
}
// 写真img: lazyは使わず(一部ブラウザで壊れ表示になるため)、data-nmで氏名を保持
const imgTag = (p, cls = "") =>
  `<img ${cls ? `class="${cls}" ` : ""}src="${photoUrl(p)}" alt="${esc(p.name)}" data-nm="${esc(p.name)}">`;

const view = document.getElementById("view");
const nav = document.getElementById("nav");
const modalRoot = document.getElementById("modal-root");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let DB = null;
const state = { regionFilter: "all", classFilter: "all", search: "" };

// ===== 出題スコープ設定（一旦の範囲限定） =====================================
// 出題範囲: 岸和田G1出場選手(=全107名) / 近畿の場 / 近畿が地元の選手
//  - 顔↔名前・図鑑・単語帳 … 全107名
//  - 属性クイズ(地区/級班/脚質/出身/ホーム/師匠/連想) … 近畿登録の選手のみ
//  - レース(映像/出走表クイズ・レース画面) と 競輪場の地区クイズ … 範囲外で無効化
// 全データに戻すには enabled を false にするだけ。
const SCOPE = { enabled: true, region: "近畿" };
// 範囲外として無効化する出題形式
const SCOPE_DISABLED_TYPES = ["raceCar", "video", "venueRegion"];
// 範囲外として無効化する画面
const SCOPE_DISABLED_NAV = ["races"];
const kinkiPlayers = () => DB.players.filter((p) => p.region === SCOPE.region);
// スコープ有効時に使える出題形式(範囲外を除外)
const scopedQuizTypes = () => SCOPE.enabled
  ? QUIZ_TYPES.filter((t) => !SCOPE_DISABLED_TYPES.includes(t.id))
  : QUIZ_TYPES;
// ===========================================================================

// ---------------- 起動 ----------------
init();
async function init() {
  try {
    const res = await fetch(DATA_BASE + "master.json");
    if (!res.ok) throw new Error(res.status);
    DB = await res.json();
  } catch (e) {
    view.innerHTML = `<div class="loader"><p style="color:#ff5d7e;max-width:46ch;text-align:center">
      データを読み込めませんでした。<br>静的サーバ経由で開いてください（例: リポジトリ直下で <code>python3 -m http.server</code> → <code>/app/</code>）。</p></div>`;
    return;
  }
  // 画像読み込み失敗を頭文字プレースホルダに差し替え(error はバブルしないので capture)
  document.addEventListener("error", (e) => {
    const t = e.target;
    if (t && t.tagName === "IMG" && !t.dataset.fb) { t.dataset.fb = "1"; t.src = placeholderSVG(t.dataset.nm); }
  }, true);
  // スコープ: 範囲外の画面はナビから隠す
  if (SCOPE.enabled) {
    SCOPE_DISABLED_NAV.forEach((n) => {
      const b = nav.querySelector(`[data-nav="${n}"]`);
      if (b) b.style.display = "none";
    });
  }
  nav.addEventListener("click", (e) => { const b = e.target.closest("[data-nav]"); if (b) go(b.dataset.nav); });
  document.querySelector(".brand").addEventListener("click", () => go("home"));
  window.addEventListener("hashchange", () => route(location.hash.slice(1) || "home"));
  route(location.hash.slice(1) || "home");
}

// nav操作: ハッシュを変えるだけ。実描画は hashchange -> route が担う
function go(name) {
  if ((location.hash.slice(1) || "home") === name) route(name); // 同一でも再描画
  else location.hash = name;
}

function route(name) {
  if (!DB) return;
  if (SCOPE.enabled && SCOPE_DISABLED_NAV.includes(name)) name = "home";  // 範囲外画面はホームへ
  document.onkeydown = null;
  modalRoot.innerHTML = "";
  [...nav.children].forEach((b) => b.classList.toggle("active", b.dataset.nav === name));
  window.scrollTo(0, 0);
  ({ home: Home, quiz: QuizSetup, cards: Dex, dex: Dex, races: Races, velo: Velo }[name] || Home)();
}

// ================= HOME =================
function Home() {
  const m = DB.meta;
  let modes = [
    ["01", "クイズ", "4択で実戦インプット。出題形式を選んでスタート。", "quiz"],
    ["02", "選手図鑑", `${m.player_count}選手をカードで一覧。検索・地区・級班で絞り込み。`, "dex"],
    ["03", "レース映像", `学習用ピックアップ ${m.race_count} レースの索引。`, "races"],
    ["04", "競輪場", "近畿の場の理解。所在地・周長・特徴・リンク。", "velo"],
  ];
  if (SCOPE.enabled) modes = modes.filter((x) => !SCOPE_DISABLED_NAV.includes(x[3]));
  view.innerHTML = `
    <section class="hero">
      <div class="speed"></div>
      <span class="kicker">202606 / 高松宮記念杯競輪 G1</span>
      <h1 class="title">バンクの上の<br>全員を、覚える。</h1>
      <p class="lead">エポリーグの学習ボードをそのままアプリに。選手・ライン・地区・場を、4択クイズと単語帳で叩き込む競輪インプット道場。</p>
      <div class="stats-row">
        ${SCOPE.enabled
          ? stat(m.player_count, "G1出場") + stat(kinkiPlayers().length, "近畿選手") + stat(m.velodrome_count, "近畿の場") + stat(scopedQuizTypes().length, "出題形式")
          : stat(m.player_count, "選手") + stat(m.region_count, "地区") + stat(m.velodrome_count, "競輪場") + stat(m.race_count, "レース") + stat(QUIZ_TYPES.length, "出題形式")}
      </div>
    </section>
    <div class="modes">
      ${modes.map(([no, nm, ds, to]) => `
        <div class="card mode" data-nav="${to}">
          <div class="glow"></div>
          <div class="no">MODE ${no}</div>
          <div class="nm">${nm}</div>
          <div class="ds">${esc(ds)}</div>
          <div class="arrow">→</div>
        </div>`).join("")}
    </div>`;
  view.querySelectorAll(".mode").forEach((el) => el.addEventListener("click", () => go(el.dataset.nav)));
}
const stat = (n, l) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`;

// ================= QUIZ =================
const _defaultTypes = () => scopedQuizTypes().filter((t) => t.group === "選手" || t.group === "場").map((t) => t.id);
const quizState = { types: new Set(_defaultTypes()), count: 10, region: "all" };
function QuizSetup() {
  const regions = ["all", ...DB.regions.map((r) => r.name)];
  const typeList = scopedQuizTypes();
  // スコープ無効化された形式が選択に残らないよう掃除
  for (const id of [...quizState.types]) {
    if (!typeList.some((t) => t.id === id)) quizState.types.delete(id);
  }
  if (quizState.types.size === 0) _defaultTypes().forEach((id) => quizState.types.add(id));
  view.innerHTML = `
    <section class="quiz-setup">
      <span class="kicker">QUIZ</span>
      <h1 class="title" style="font-size:clamp(26px,5vw,42px)">出題設定</h1>
      ${SCOPE.enabled ? `<p class="lead">出題範囲: 岸和田G1出場選手(全${DB.players.length}名) ／ 近畿の場 ／ 近畿が地元の選手。<br>顔↔名前は全選手、属性問題は近畿登録選手から出題。</p>` : ""}
      <div class="card" style="padding:24px;margin-top:14px">
        <div class="group">
          <div class="glabel">出題形式 <span class="tag region" id="tcount"></span></div>
          <div class="chips" id="typeChips">
            ${typeList.map((t) => `<button class="chip ${quizState.types.has(t.id) ? "on red" : ""}" data-t="${t.id}" title="${esc(t.desc)}">${esc(t.label)}</button>`).join("")}
          </div>
        </div>
        ${SCOPE.enabled ? "" : `
        <div class="group">
          <div class="glabel">地区しぼり</div>
          <div class="chips" id="regChips">
            ${regions.map((r) => `<button class="chip ${quizState.region === r ? "on" : ""}" data-r="${r}">${r === "all" ? "すべて" : r}</button>`).join("")}
          </div>
        </div>`}
        <div class="group">
          <div class="glabel">問題数</div>
          <div class="chips" id="cntChips">
            ${[5, 10, 20, 30].map((c) => `<button class="chip ${quizState.count === c ? "on" : ""}" data-c="${c}">${c}問</button>`).join("")}
          </div>
        </div>
        <button class="btn" id="startBtn" style="width:100%;margin-top:8px">スタート ▸</button>
      </div>
    </section>`;
  const upd = () => { document.getElementById("tcount").textContent = `${quizState.types.size} 形式`; };
  upd();
  view.querySelector("#typeChips").addEventListener("click", (e) => {
    const b = e.target.closest("[data-t]"); if (!b) return;
    const id = b.dataset.t;
    if (quizState.types.has(id)) { if (quizState.types.size > 1) quizState.types.delete(id); }
    else quizState.types.add(id);
    b.classList.toggle("on"); b.classList.toggle("red", quizState.types.has(id)); upd();
  });
  if (view.querySelector("#regChips")) toggleGroup("#regChips", "r", (v) => { quizState.region = v; });
  toggleGroup("#cntChips", "c", (v) => { quizState.count = +v; });
  document.getElementById("startBtn").addEventListener("click", startQuiz);
}
function toggleGroup(sel, attr, set) {
  view.querySelector(sel).addEventListener("click", (e) => {
    const b = e.target.closest(`[data-${attr}]`); if (!b) return;
    set(b.dataset[attr]);
    [...b.parentElement.children].forEach((c) => c.classList.toggle("on", c === b));
  });
}

let session = null;
function startQuiz() {
  let types = [...quizState.types];
  let pool = null;
  let attrPlayers = null;
  if (SCOPE.enabled) {
    // 範囲外形式を除外し、属性クイズの対象を近畿選手に限定(顔↔名前は全選手)
    types = types.filter((t) => !SCOPE_DISABLED_TYPES.includes(t));
    attrPlayers = kinkiPlayers();
  } else {
    pool = quizState.region === "all" ? null : (p) => p.region === quizState.region;
    if (pool) types = types.filter((t) => t !== "venueRegion");
  }
  if (!types.length) types = ["photo2name"];
  const qs = buildSession(DB, { types, count: quizState.count, pool, attrPlayers });
  session = { qs, i: 0, correct: 0, answered: false };
  renderQuestion();
}

function renderQuestion() {
  window.scrollTo(0, 0);
  const { qs, i } = session;
  const q = qs[i];
  session.answered = false;
  const pct = (i / qs.length) * 100;
  const isPhotoChoices = q.choiceRender === "photo";
  view.innerHTML = `
    <div class="q-meta"><span>Q${i + 1} / ${qs.length}</span><span>SCORE ${session.correct}</span></div>
    <div class="progress"><i style="width:${pct}%"></i></div>
    <div class="card q-card">
      <div class="q-prompt">${esc(q.prompt)}</div>
      ${q.media && q.media.kind === "photo" ? imgTag(q.media.player, `q-photo ${q.media.small ? "small" : ""}`) : ""}
      ${q.media && q.media.kind === "hints" ? `<div class="hints">${q.media.hints.map((h) => `<div class="hint"><span class="hk">${esc(h.k)}</span><span class="hv">${esc(h.v)}</span></div>`).join("")}</div>` : ""}
      ${q.media && q.media.kind === "entries" ? renderEntries(q.media) : ""}
      ${q.media && q.media.kind === "video" ? renderVideo(q.media) : ""}
      <div class="choices ${isPhotoChoices ? "photo-grid" : (q.choices.some((c) => String(c).length > 10) ? "one-col" : "")}" id="choices">
        ${q.choices.map((c, idx) => choiceHTML(c, idx, q, isPhotoChoices)).join("")}
      </div>
      <div id="fb"></div>
      <div class="q-actions hidden" id="acts">
        <button class="btn" id="nextBtn">${i + 1 < qs.length ? "次の問題 ▸" : "結果を見る ▸"}</button>
      </div>
    </div>`;
  const keys = ["A", "B", "C", "D"];
  view.querySelectorAll(".choice").forEach((el, idx) => {
    el.addEventListener("click", () => answer(el, q, isPhotoChoices));
  });
  document.onkeydown = (e) => {
    if (session.answered) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); document.getElementById("nextBtn")?.click(); } return; }
    const k = keys.indexOf(e.key.toUpperCase());
    if (k >= 0) view.querySelectorAll(".choice")[k]?.click();
  };
}
function renderEntries(m) {
  const r = m.race;
  const rows = r.entries.map((e) => {
    const hidden = e.car === m.hideCar;
    return `<div class="ent ${hidden ? "q" : ""}"><span class="car car-${e.car}">${e.car}</span><span class="enm">${hidden ? "？" : esc(e.name || "—")}</span></div>`;
  }).join("");
  return `<div class="racebar">${esc(m.label)}</div><div class="entries">${rows}</div>`;
}
function renderVideo(m) {
  return `<div class="racebar">${esc(m.label)}</div>
    <video class="dvideo" controls playsinline preload="metadata" src="${esc(m.video)}"></video>
    <div class="vlink"><a href="${esc(m.url)}" target="_blank" rel="noopener">▶ WINTICKETで見る ↗</a>（映像が再生できない場合）</div>`;
}
function choiceHTML(c, idx, q, isPhoto) {
  const key = ["A", "B", "C", "D"][idx];
  if (isPhoto) {
    // 名前→顔クイズ: 写真の下に名前を出すと答えがバレるので表示しない
    return `<button class="choice photo" data-v="${esc(c.id)}">${imgTag(c)}</button>`;
  }
  return `<button class="choice" data-v="${esc(c)}"><span class="key">${key}</span><span>${esc(c)}</span><span class="mark"></span></button>`;
}
function answer(el, q, isPhoto) {
  if (session.answered) return;
  session.answered = true;
  const chosen = isPhoto ? el.dataset.v : el.dataset.v;
  const correctVal = String(q.answer);
  const ok = chosen === correctVal;
  if (ok) session.correct++;
  view.querySelectorAll(".choice").forEach((b) => {
    b.disabled = true;
    const v = b.dataset.v;
    if (v === correctVal) { b.classList.add("correct"); setMark(b, "✓"); }
    else if (b === el) { b.classList.add("wrong"); setMark(b, "✕"); }
  });
  const fb = document.getElementById("fb");
  fb.innerHTML = `<div class="feedback ${ok ? "ok" : "ng"}">
      <div class="ttl">${ok ? "正解！" : "不正解"}</div>
      <div class="ex">${esc(q.explain)}</div>
    </div>`;
  document.getElementById("acts").classList.remove("hidden");
  document.getElementById("nextBtn").addEventListener("click", () => {
    session.i++;
    if (session.i < session.qs.length) renderQuestion(); else renderResult();
  });
}
function setMark(b, s) { const m = b.querySelector(".mark"); if (m) m.textContent = s; }

function renderResult() {
  window.scrollTo(0, 0);
  document.onkeydown = null;
  const { correct, qs } = session;
  const total = qs.length;
  const pct = Math.round((correct / total) * 100);
  const grade = pct >= 90 ? "S級S班" : pct >= 75 ? "S級1班" : pct >= 60 ? "S級2班" : pct >= 40 ? "A級1班" : "練習生";
  const msg = pct >= 90 ? "完璧。バンクの主だ。" : pct >= 60 ? "いい走り。あと一歩。" : "周回不足。もう一本！";
  view.innerHTML = `
    <div class="card result">
      <span class="kicker">RESULT</span>
      <div class="score"><b>${correct}</b> / ${total}</div>
      <div class="grade">判定：${grade}</div>
      <p class="lead" style="margin:0 auto">${msg}（正答率 ${pct}%）</p>
      <div class="actions">
        <button class="btn" id="again">もう一度</button>
        <button class="btn ghost" id="toSetup">設定を変える</button>
      </div>
    </div>`;
  document.getElementById("again").addEventListener("click", startQuiz);
  document.getElementById("toSetup").addEventListener("click", QuizSetup);
}

// ================= 選手図鑑 (単語帳カードUI + 検索/地区/級班フィルタを統合) =================
function Dex() {
  const regions = ["all", ...DB.regions.map((r) => r.name)];
  const classes = ["all", ...[...new Set(DB.players.map((p) => p.class))]];
  view.innerHTML = `
    <span class="kicker">PLAYER DEX</span>
    <h1 class="title" style="font-size:clamp(26px,5vw,42px)">選手図鑑</h1>
    <div class="toolbar">
      <input type="search" id="search" placeholder="名前・カナで検索" value="${esc(state.search)}">
      <div class="chips" id="rf">${regions.map((r) => `<button class="chip ${state.regionFilter === r ? "on" : ""}" data-r="${r}">${r === "all" ? "全地区" : r}</button>`).join("")}</div>
    </div>
    <div class="toolbar"><div class="chips" id="cf">${classes.map((c) => `<button class="chip ${state.classFilter === c ? "on" : ""}" data-c="${c}">${c === "all" ? "全級班" : c}</button>`).join("")}</div></div>
    <div id="dexGrid"></div>`;
  const draw = () => {
    const q = state.search.trim();
    const list = DB.players.filter((p) =>
      (state.regionFilter === "all" || p.region === state.regionFilter) &&
      (state.classFilter === "all" || p.class === state.classFilter) &&
      (!q || (p.name + p.name_kana).replace(/\s/g, "").includes(q.replace(/\s/g, ""))));
    const grid = document.getElementById("dexGrid");
    grid.innerHTML = `<p style="color:var(--ink-faint);font-size:13px;margin:6px 0 12px">${list.length} 名</p>
      <div class="study-grid">${list.map(studyCard).join("")}</div>`;
    grid.querySelectorAll(".study").forEach((el) => el.addEventListener("click", (e) => {
      if (e.target.closest("a")) return;  // 外部リンクのクリックはモーダルを開かない
      openModal(el.dataset.id);
    }));
  };
  view.querySelector("#search").addEventListener("input", (e) => { state.search = e.target.value; draw(); });
  view.querySelector("#rf").addEventListener("click", (e) => { const b = e.target.closest("[data-r]"); if (!b) return; state.regionFilter = b.dataset.r; [...b.parentElement.children].forEach((c) => c.classList.toggle("on", c === b)); draw(); });
  view.querySelector("#cf").addEventListener("click", (e) => { const b = e.target.closest("[data-c]"); if (!b) return; state.classFilter = b.dataset.c; [...b.parentElement.children].forEach((c) => c.classList.toggle("on", c === b)); draw(); });
  draw();
}
function studyCard(p) {
  const fact = (k, v) => v != null && v !== "" ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : "";
  return `<div class="card study" data-id="${p.id}" style="cursor:pointer">
    <div class="ph">${imgTag(p)}</div>
    <div class="body">
      <div class="nm">${esc(p.name)}</div>
      <div class="kana">${esc(p.name_kana || "")}</div>
      <div class="meta">${tag("region", p.region)} ${tag("cls", p.class)} ${tag("gait", p.footwork_label)}</div>
      <dl class="facts">
        ${fact("出身", p.prefecture)}${fact("期別", p.period ? p.period + "期" : null)}
        ${fact("ホーム", p.home_bank)}${fact("師匠", p.mentor)}
        ${fact("得点", p.points)}${fact("登録", p.id)}
      </dl>
      <div class="lk">
        <a href="${p.links.keirin_jp}" target="_blank" rel="noopener">KEIRIN.JP ↗</a>
        <a href="${p.links.winticket}" target="_blank" rel="noopener">WINTICKET ↗</a>
      </div>
    </div></div>`;
}

// ================= レース =================
function Races() {
  const byVenue = {};
  DB.races.forEach((r) => { (byVenue[r.venue] = byVenue[r.venue] || []).push(r); });
  const venues = Object.keys(byVenue).sort((a, b) => byVenue[b].length - byVenue[a].length);
  view.innerHTML = `
    <span class="kicker">RACE INDEX</span>
    <h1 class="title" style="font-size:clamp(26px,5vw,42px)">レース映像</h1>
    <p class="lead">学習用ピックアップ ${DB.races.length} レース。出走表とダイジェスト映像（${DB.races.filter((r) => r.video).length}本）付き。</p>
    ${venues.map((v) => `
      <div class="venue-block">
        <h3>${esc(v)}競輪 <span class="tag region">${byVenue[v].length}本</span></h3>
        <div class="race-list">
          ${byVenue[v].map((r) => `<div class="card race-item">
            <div class="ev">${esc(r.event || r.venue)}${r.video ? ' <span class="tag gait">▶映像</span>' : ""}</div>
            <div class="sub">${r.date || "日付不明"}${r.race_no ? " ・ " + r.race_no + "R" : ""}${r.race_type ? " ・ " + esc(r.race_type) : ""}</div>
            <a href="${r.url}" target="_blank" rel="noopener">WINTICKETで見る ↗</a>
          </div>`).join("")}
        </div>
      </div>`).join("")}`;
}

// ================= 競輪場 =================
function Velo() {
  view.innerHTML = `
    <span class="kicker">VELODROMES</span>
    <h1 class="title" style="font-size:clamp(26px,5vw,42px)">競輪場</h1>
    <p class="lead">近畿の場の理解。所在地・バンク周長・特徴とリンク集。</p>
    <div class="velo-grid" style="margin-top:18px">
      ${DB.velodromes.map((v) => `
        <div class="card velo">
          <h3>${esc(v.name)}</h3>
          <div class="velo-spec">
            ${v.prefecture ? `<span class="tag region">${esc(v.prefecture)}</span>` : ""}
            ${v.circumference_m ? `<span class="tag cls">周長 ${v.circumference_m}m</span>` : ""}
          </div>
          ${v.feature ? `<p class="velo-feat">${esc(v.feature)}</p>` : ""}
          ${link("WINTICKET 場ページ", v.wt_page)}
          ${link("コラム 深掘り！競輪場！", v.wt_column)}
          ${link("公式サイト", v.official_site)}
          ${link("所属選手一覧", v.racers_list)}
        </div>`).join("")}
    </div>`;
}
const link = (label, url) => url ? `<a href="${url}" target="_blank" rel="noopener"><span>${esc(label)}</span> ↗</a>` : "";

// ================= モーダル =================
function openModal(id) {
  const p = DB.players.find((x) => x.id === id);
  modalRoot.innerHTML = `
    <div class="modal" id="modal">
      <div class="card box">
        <button class="x" id="mx">×</button>
        <div class="hd">
          ${imgTag(p)}
          <div>
            <div class="nm">${esc(p.name)}</div>
            <div class="kana">${esc(p.name_kana || "")}</div>
            <div class="meta">${tag("region", p.region)} ${tag("cls", p.class)} ${tag("gait", p.footwork_label)}</div>
          </div>
        </div>
        <div class="bd">
          ${playerKV(p)}
          <div class="links">
            <a class="btn ghost" href="${p.links.keirin_jp}" target="_blank" rel="noopener">KEIRIN.JP ↗</a>
            <a class="btn ghost" href="${p.links.winticket}" target="_blank" rel="noopener">WINTICKET ↗</a>
          </div>
        </div>
      </div>
    </div>`;
  const close = () => (modalRoot.innerHTML = "");
  document.getElementById("mx").addEventListener("click", close);
  document.getElementById("modal").addEventListener("click", (e) => { if (e.target.id === "modal") close(); });
}

// ---------- 共通レンダ ----------
function playerKV(p) {
  const s = p.stats || {};
  const rows = [
    ["登録番号", p.id], ["生年月日", p.birthdate], ["年齢", p.age != null ? p.age + "歳" : null],
    ["登録地", p.prefecture], ["地区", p.region], ["期別", p.period ? p.period + "期" : null],
    ["級班", p.class], ["脚質", p.footwork_label], ["ホーム", p.home_bank], ["師匠", p.mentor],
    ["身長", p.height_cm ? p.height_cm + "cm" : null], ["体重", p.weight_kg ? p.weight_kg + "kg" : null],
    ["今期得点", p.points], ["勝率", s.win_rate], ["2連対率", s.place2_rate], ["3連対率", s.place3_rate],
  ].filter(([, v]) => v != null && v !== "");
  return `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
}
const tag = (cls, v) => v ? `<span class="tag ${cls}">${esc(v)}</span>` : "";
