// quiz.js — マスターデータから4択クイズ/単語帳を動的生成するロジック (依存なし)
// すべて純粋関数。app.js から利用する。

export const QUIZ_TYPES = [
  { id: "photo2name", label: "顔→名前", group: "選手", media: "photo",
    desc: "顔写真から選手名を当てる (4択形式)" },
  { id: "name2photo", label: "名前→顔", group: "選手", media: "photoChoices",
    desc: "選手名から顔写真を当てる" },
  { id: "hints", label: "連想(ヒント)", group: "選手",
    desc: "複数ヒントからこの選手は誰かを当てる (連想・関係図形式)" },
  { id: "region",   label: "地区",   group: "選手", desc: "選手の所属地区を当てる" },
  { id: "class",    label: "級班",   group: "選手", desc: "選手の級班を当てる" },
  { id: "footwork", label: "脚質",   group: "選手", desc: "選手の脚質を当てる" },
  { id: "pref",     label: "出身",   group: "選手", desc: "選手の登録地(府県)を当てる" },
  { id: "home",     label: "ホーム", group: "選手", desc: "選手のホームバンクを当てる" },
  { id: "mentor",   label: "師匠",   group: "選手", desc: "選手の師匠を当てる" },
  { id: "venueRegion", label: "競輪場の地区", group: "場", desc: "競輪場のある地区を当てる" },
  { id: "venuePref", label: "競輪場の所在地", group: "場", desc: "競輪場のある都道府県を当てる" },
  { id: "venueCircum", label: "競輪場の周長", group: "場", desc: "競輪場のバンク周長(m)を当てる" },
  { id: "raceCar", label: "出走表", group: "レース", desc: "出走表の◯番車の選手を当てる (出走表形式)" },
  { id: "video", label: "映像", group: "レース", desc: "ダイジェスト映像を見て◯番車の選手を当てる (映像形式)" },
  { id: "glossaryTerm", label: "意味→用語", group: "用語", desc: "競輪用語の意味から用語名を当てる" },
  { id: "glossaryDesc", label: "用語→意味", group: "用語", desc: "競輪用語の意味を当てる" },
];

// --- ユーティリティ ---
function shuffle(a) {
  const r = a.slice();
  for (let i = r.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [r[i], r[j]] = [r[j], r[i]];
  }
  return r;
}
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const uniq = (a) => [...new Set(a)];

// 正解1 + ダミー3 を作る。distractorPool から正解と異なる値を優先的に3つ。
function buildChoices(correct, distractorPool, n = 4) {
  const pool = shuffle(uniq(distractorPool.filter((v) => v != null && v !== correct)));
  const choices = shuffle([correct, ...pool.slice(0, n - 1)]);
  return choices;
}

// プレイヤー母集団からダミーを近いカテゴリで選ぶ(難易度UP)
function similarPlayers(p, players) {
  const same = players.filter((q) => q.id !== p.id && q.region === p.region);
  return same.length >= 3 ? same : players.filter((q) => q.id !== p.id);
}

// --- 1問生成 ---
export function generateQuestion(typeId, data) {
  const { players, regions, velodromes, races } = data;
  const terms = data.terms || [];
  // クイズ向き用語: 説明が十分長く、説明文に用語名が露出していないもの
  const quizTerms = terms.filter((t) => t.desc.length >= 12 && !t.desc.includes(t.term));
  const firstSentence = (s) => { const i = s.indexOf("。"); return i > 0 ? s.slice(0, i + 1) : s; };
  const FOOT = ["逃げ", "追込", "両"];
  const CLASSES = uniq(players.map((p) => p.class));
  // 属性クイズの出題対象。スコープ指定があればその地区の選手のみ(顔↔名前は全選手のまま)
  const attr = (data.attrPlayers && data.attrPlayers.length) ? data.attrPlayers : players;

  // レース系: 出走表(車番→選手名)から1台を伏せて当てる
  function raceQuestion(needVideo) {
    const pool = (races || []).filter((r) =>
      (!needVideo || r.video) && r.entries && r.entries.filter((e) => e.name && !e.absent).length >= 4);
    if (!pool.length) return generateQuestion("photo2name", data); // フォールバック
    const r = pick(pool);
    const named = r.entries.filter((e) => e.name && !e.absent);
    const target = pick(named);
    const choices = buildChoices(target.name, named.map((e) => e.name));
    const label = `${r.venue}競輪 ${r.event || ""}（${r.date || ""}）${r.race_no || ""}R`;
    return {
      type: typeId,
      prompt: `${target.car}番車の選手は？`,
      media: needVideo
        ? { kind: "video", video: r.video, url: r.url, label }
        : { kind: "entries", race: r, hideCar: target.car, label },
      choices, answer: target.name,
      explain: `${label} の${target.car}番車は ${target.name}`,
    };
  }

  switch (typeId) {
    case "raceCar": return raceQuestion(false);
    case "video": return raceQuestion(true);
    case "photo2name": {
      const p = pick(players);
      const opts = buildChoices(p.name, similarPlayers(p, players).map((q) => q.name));
      return {
        type: typeId, prompt: "この選手は誰？", media: { kind: "photo", player: p },
        choices: opts, answer: p.name, player: p,
        explain: `${p.name}（${p.region}・${p.class}・${p.footwork_label}）`,
      };
    }
    case "name2photo": {
      const p = pick(players);
      const others = shuffle(similarPlayers(p, players)).slice(0, 3);
      const choices = shuffle([p, ...others]);
      return {
        type: typeId, prompt: `「${p.name}」はどの顔？`,
        media: { kind: "photoChoices" }, choices, answer: p.id,
        choiceRender: "photo", player: p,
        explain: `${p.name}（${p.region}・${p.class}）`,
      };
    }
    case "hints": {
      const p = pick(attr);
      const cand = [
        ["生年月日", p.birthdate], ["期別", p.period ? p.period + "期" : null],
        ["級班", p.class], ["脚質", p.footwork_label], ["出身", p.prefecture],
        ["地区", p.region], ["ホーム", p.home], ["師匠", p.mentor],
        ["身長", p.height_cm ? p.height_cm + "cm" : null], ["今期得点", p.points],
      ].filter(([, v]) => v != null && v !== "");
      // ヒントは5つ前後をランダムに(難易度のため名前を直接示すものは無し)
      const hints = shuffle(cand).slice(0, Math.min(6, cand.length))
        .map(([k, v]) => ({ k, v: String(v) }));
      return {
        type: typeId, prompt: "この選手は誰？",
        media: { kind: "hints", hints },
        choices: buildChoices(p.name, similarPlayers(p, players).map((q) => q.name)),
        answer: p.name, player: p,
        explain: `${p.name}（${p.region}・${p.class}・${p.footwork_label}）`,
      };
    }
    case "region": {
      const p = pick(attr);
      return {
        type: typeId, prompt: `${p.name} の地区は？`,
        media: { kind: "photo", player: p, small: true },
        choices: buildChoices(p.region, regions.map((r) => r.name)),
        answer: p.region, player: p,
        explain: `${p.name} は ${p.prefecture}（${p.region}）`,
      };
    }
    case "class": {
      const p = pick(attr);
      return {
        type: typeId, prompt: `${p.name} の級班は？`,
        media: { kind: "photo", player: p, small: true },
        choices: buildChoices(p.class, CLASSES),
        answer: p.class, player: p,
        explain: `${p.name} は ${p.class}（今期得点 ${p.points ?? "-"}）`,
      };
    }
    case "footwork": {
      const p = pick(attr);
      return {
        type: typeId, prompt: `${p.name} の脚質は？`,
        media: { kind: "photo", player: p, small: true },
        choices: shuffle(FOOT.slice()), answer: p.footwork_label, player: p,
        explain: `${p.name} の脚質は ${p.footwork_label}`,
      };
    }
    case "pref": {
      const p = pick(attr);
      return {
        type: typeId, prompt: `${p.name} の登録地（府県）は？`,
        media: { kind: "photo", player: p, small: true },
        choices: buildChoices(p.prefecture, players.map((q) => q.prefecture)),
        answer: p.prefecture, player: p,
        explain: `${p.name} は ${p.prefecture}（${p.region}）`,
      };
    }
    case "home": {
      const p = pick(attr.filter((q) => q.home));
      return {
        type: typeId, prompt: `${p.name} のホーム（バンク／練習地）は？`,
        media: { kind: "photo", player: p, small: true },
        choices: buildChoices(p.home, players.filter((q) => q.home).map((q) => q.home)),
        answer: p.home, player: p,
        explain: `${p.name} のホームは ${p.home}`,
      };
    }
    case "mentor": {
      const p = pick(attr.filter((q) => q.mentor));
      return {
        type: typeId, prompt: `${p.name} の師匠は？`,
        media: { kind: "photo", player: p, small: true },
        choices: buildChoices(p.mentor, players.filter((q) => q.mentor).map((q) => q.mentor)),
        answer: p.mentor, player: p,
        explain: `${p.name} の師匠は ${p.mentor}`,
      };
    }
    case "venueRegion": {
      // 競輪場 -> 地区 (ボードの地区区分準拠: 東京=関東, 静岡=南関東 等)
      const VENUE_REGION = {
        "函館": "北日本", "青森": "北日本",
        "西武園": "関東", "取手": "関東", "宇都宮": "関東",
        "平塚": "南関東", "伊東": "南関東", "小田原": "南関東", "静岡": "南関東",
        "豊橋": "中部", "大垣": "中部",
        "福井": "近畿", "奈良": "近畿", "京都向日町": "近畿", "和歌山": "近畿", "岸和田": "近畿",
        "防府": "中国", "松山": "四国",
        "熊本": "九州", "武雄": "九州",
      };
      const names = Object.keys(VENUE_REGION);
      const v = pick(names);
      const ans = VENUE_REGION[v];
      return {
        type: typeId, prompt: `「${v}競輪場」がある地区は？`,
        media: null,
        choices: buildChoices(ans, regions.map((r) => r.name)),
        answer: ans,
        explain: `${v}競輪場は ${ans} 地区`,
      };
    }
    case "venuePref": {
      const pool = (velodromes || []).filter((v) => v.prefecture);
      if (!pool.length) return generateQuestion("photo2name", data);
      const v = pick(pool);
      return {
        type: typeId, prompt: `${v.name}競輪場の所在地（都道府県）は？`,
        media: null,
        choices: buildChoices(v.prefecture, pool.map((x) => x.prefecture)),
        answer: v.prefecture,
        explain: `${v.name}競輪場は ${v.prefecture}（${v.region}）`,
      };
    }
    case "venueCircum": {
      const pool = (velodromes || []).filter((v) => v.circumference_m);
      if (!pool.length) return generateQuestion("photo2name", data);
      const v = pick(pool);
      const ans = v.circumference_m + "m";
      return {
        type: typeId, prompt: `${v.name}競輪場のバンク周長は？`,
        media: null,
        choices: shuffle(["333m", "400m", "500m"]),
        answer: ans,
        explain: `${v.name}競輪場のバンク周長は ${ans}`,
      };
    }
    case "glossaryTerm": {
      if (!terms.length) return generateQuestion("photo2name", data);
      const t = pick(quizTerms.length >= 4 ? quizTerms : terms);
      return {
        type: typeId, prompt: "次の意味の競輪用語は？",
        media: { kind: "term", text: t.desc },
        choices: buildChoices(t.term, terms.map((x) => x.term)),
        answer: t.term,
        explain: `${t.term}（${t.reading}）— ${t.desc}`,
      };
    }
    case "glossaryDesc": {
      if (!terms.length) return generateQuestion("photo2name", data);
      const t = pick(quizTerms.length >= 4 ? quizTerms : terms);
      const correct = firstSentence(t.desc);
      return {
        type: typeId, prompt: `「${t.term}（${t.reading}）」の意味は？`,
        media: null,
        choices: buildChoices(correct, terms.filter((x) => x.term !== t.term).map((x) => firstSentence(x.desc))),
        answer: correct,
        explain: `${t.term} — ${t.desc}`,
      };
    }
    default:
      return generateQuestion("photo2name", data);
  }
}

// --- セッション(複数問) ---
export function buildSession(data, { types, count = 10, pool = null, attrPlayers = null }) {
  const usable = types && types.length ? types : QUIZ_TYPES.map((t) => t.id);
  let scoped = pool ? { ...data, players: data.players.filter(pool) } : data;
  if (attrPlayers) scoped = { ...scoped, attrPlayers };  // 属性クイズのみ対象を絞る
  const qs = [];
  for (let i = 0; i < count; i++) {
    qs.push(generateQuestion(pick(usable), scoped));
  }
  return qs;
}

// --- 単語帳(フラッシュカード) ---
export function buildFlashcards(data, filterFn = null) {
  let ps = data.players.slice();
  if (filterFn) ps = ps.filter(filterFn);
  return ps;
}
