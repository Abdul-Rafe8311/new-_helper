/**
 * The reader half of the mock API: a seeded edition, per-reader event folding, the archive, saved
 * stories, the /r redirect and a stand-in PDF. It mirrors what apps/api does, so the e2e tests
 * exercise the real request shapes.
 */

const DAY_MS = 86_400_000;
const PAGE_MAX = 60;

const id = (n) => `00000000-0000-4000-a000-${String(n).padStart(12, "0")}`;
const isoDay = (offsetDays = 0) => new Date(Date.now() - offsetDays * DAY_MS).toISOString().slice(0, 10);

const BREAKDOWN = {
  components: { semantic: 0.21, topic: 0.12, match: 0.07, recency: 0.08, importance: 0.04, novelty: 0.01 },
  penalties: {},
  total: 0.53,
  cluster_size: 5,
  terms: ["agents"],
};

// [section, slot, headline]
const STORIES = [
  ["The Agent Economy", "lead", "Agents are now negotiating their own contracts"],
  ["The Agent Economy", "feature", "Inside the startup selling AI interns by the hour"],
  ["The Agent Economy", "standard", "Why every SaaS pricing page just changed"],
  ["The Agent Economy", "standard", "Benchmarks no longer tell you which model is better"],
  ["Pavilion End", "feature", "Babar finds his rhythm in Multan"],
  ["Pavilion End", "standard", "PSL draft: the five picks that surprised everyone"],
  ["Pavilion End", "brief", "Rain delays the second Test"],
  ["Markets", "feature", "Central banks signal a synchronised pause"],
  ["Markets", "standard", "Rupee steadies as imports slow"],
  ["Markets", "brief", "Oil edges up on supply worries"],
  ["Science", "standard", "A new battery chemistry survives 10,000 cycles"],
  ["Science", "brief", "Webb spots a galaxy that should not exist"],
  ["Outside your bubble", "explore", "How Georgian wine got its second wind"],
  ["Outside your bubble", "explore", "The quiet comeback of the paper map"],
];

const svg = (color, label) =>
  `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="800" height="600" fill="${color}"/><text x="40" y="300" font-size="48" fill="white">${label}</text></svg>`,
  )}`;
const COLORS = ["#556b2f", "#2f4f6b", "#6b2f4f", "#6b5a2f"];
/** Stories 1, 2 and 5 have pictures; story 3's picture is broken (the card must fall back). */
const IMAGES = { 1: svg(COLORS[0], "one"), 2: svg(COLORS[1], "two"), 3: "http://127.0.0.1:1/broken.jpg", 5: svg(COLORS[2], "five") };

const SECTIONS = [...new Set(STORIES.map(([section]) => section))];

function items(sessionState) {
  const states = foldStates(sessionState);
  return STORIES.map(([section, slot, headline], index) => ({
    id: id(index + 1),
    article_id: id(1000 + index + 1),
    section,
    position: index,
    slot,
    headline,
    summary: `${headline}. This is the longer summary of story ${index + 1}, written to run past a single line so truncation and expansion can both be seen.`,
    key_facts: [`Fact one of story ${index + 1}`, "Second fact"],
    why_text: `Because you follow ${section.toLowerCase()}`,
    url: `https://news${(index % 4) + 1}.example.com/story-${index + 1}`,
    source: ["The Wire", "Dawn", "Ars Technica", "Reuters"][index % 4],
    image_url: IMAGES[index + 1] ?? null,
    published_at: new Date(Date.now() - (index + 1) * 40 * 60_000).toISOString(),
    score: 0.5,
    score_breakdown: BREAKDOWN,
    state: states[id(index + 1)] ?? { read: false, saved: false, skipped: false, reaction: null },
  }));
}

/** Same rules as apps/api/app/services/editions.py: the latest event of each kind wins. */
function foldStates(sessionState) {
  const states = {};
  for (const e of sessionState.events ?? []) {
    const state = (states[e.edition_item_id] ??= { read: false, saved: false, skipped: false, reaction: null });
    const on = e.value !== 0;
    if (e.type === "open" || e.type === "mark_read") state.read = true;
    else if (e.type === "skip") state.skipped = on;
    else if (e.type === "save") state.saved = on;
    else if (e.type === "more_like" || e.type === "less_like") {
      const mine = e.type === "more_like" ? "more" : "less";
      if (on) state.reaction = mine;
      else if (state.reaction === mine) state.reaction = null;
    }
  }
  return states;
}

function edition(sessionState, date) {
  return {
    id: `11111111-0000-4000-b000-${date.replaceAll("-", "").padStart(12, "0")}`,
    date,
    number: 12,
    status: "ready",
    title: "The Rafe Courier",
    editor_note: "Good morning, Rafe. Agents are signing contracts and central banks are pausing.",
    layout: {
      sections: SECTIONS.map((name) => ({
        name,
        item_ids: STORIES.flatMap(([section], i) => (section === name ? [id(i + 1)] : [])),
      })),
      lead_item_id: id(1),
      three_things: ["Agents are signing contracts.", "Central banks are pausing.", "Babar is in form."],
    },
    items: items(sessionState),
    stats: { sources: 4, items: STORIES.length },
    generated_at: new Date().toISOString(),
  };
}

const PENDING_STAGES = ["gathering", "choosing", "writing", "typesetting"];

function todaysEdition(s) {
  const plan = s.editionPlan ?? { mode: "ready" };
  if (plan.mode === "none") return null;
  if (plan.mode === "pending" && Date.now() < plan.readyAt) {
    const stage = PENDING_STAGES[Math.min(3, Math.floor((Date.now() - plan.startedAt) / 800))];
    return { ...edition(s, isoDay()), status: "pending", items: [], layout: {}, stats: { stage } };
  }
  return edition(s, isoDay());
}

function archive(before, limit) {
  const days = Array.from({ length: 45 }, (_, i) => isoDay(i + 1)).filter((d) => !before || d < before);
  return days.slice(0, limit).map((date, i) => ({
    id: `11111111-0000-4000-b000-${date.replaceAll("-", "").padStart(12, "0")}`,
    date,
    number: 11 - i,
    title: "The Rafe Courier",
    item_count: 14,
    top_topics: ["AI", "Cricket", "Markets"],
  }));
}

const PDF = Buffer.from("%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n");

/**
 * @returns {boolean} whether the request was handled
 */
export function handleReader({ req, res, path, url, session, send, error, readJson }) {
  const s = session;
  if (!s.completed) return false;
  s.events ??= [];
  s.opens ??= [];
  s.pdfDownloads ??= 0;

  if (path === "/editions/today" && req.method === "GET") {
    const today = todaysEdition(s);
    if (!today) return error(res, 404, "edition_not_found", "No edition for today"), true;
    return send(res, 200, today), true;
  }
  if (path === "/editions/today/regenerate" && req.method === "POST") {
    s.editionPlan = { mode: "pending", startedAt: Date.now(), readyAt: Date.now() + 1500 };
    return send(res, 202, todaysEdition(s)), true;
  }
  if (path === "/editions" && req.method === "GET") {
    const limit = Math.min(PAGE_MAX, Number(url.searchParams.get("limit") ?? 20));
    return send(res, 200, archive(url.searchParams.get("before"), limit)), true;
  }
  const pdf = /^\/editions\/(\d{4}-\d{2}-\d{2})\/pdf$/.exec(path);
  if (pdf) {
    s.pdfDownloads += 1;
    res.writeHead(200, {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="the-rafe-courier-${pdf[1]}.pdf"`,
    });
    return res.end(PDF), true;
  }
  const byDate = /^\/editions\/(\d{4}-\d{2}-\d{2})$/.exec(path);
  if (byDate) return send(res, 200, edition(s, byDate[1])), true;

  const story = /^\/stories\/([0-9a-f-]{36})$/.exec(path);
  if (story) {
    const item = items(s).find((i) => i.id === story[1]);
    if (!item) return error(res, 404, "not_found", "That story is not in your paper"), true;
    const number = Number(item.id.slice(-12));
    const images = [item.image_url, ...COLORS.map((c, i) => svg(c, `extra${i}`))]
      .filter((u) => u && !u.includes("broken"))
      .slice(0, 4)
      .map((url, i) => ({ url, credit: ["The Wire", "Dawn", "Reuters", "Ars Technica"][i % 4] }));
    return send(res, 200, {
      item,
      edition_id: "11111111-0000-4000-b000-000000000001",
      edition_date: isoDay(),
      edition_number: 12,
      author: "Sara Khan",
      images,
      sources: [
        { name: item.source, title: item.headline, url: `/r/${item.id}`, published_at: item.published_at, primary: true },
        { name: "Reuters", title: `Reuters on story ${number}`, url: "https://reuters.example.com/a", published_at: item.published_at, primary: false },
      ],
    }), true;
  }

  if (path === "/saved") {
    const saved = items(s).filter((item) => item.state.saved);
    return send(res, 200, saved.map((item) => ({ ...item, edition_date: isoDay() }))), true;
  }

  if (path === "/events" && req.method === "POST") {
    return readJson(req).then((body) => {
      const known = new Set(STORIES.map((_, i) => id(i + 1)));
      let accepted = 0;
      for (const e of body.events ?? []) {
        if (known.has(e.edition_item_id)) {
          s.events.push({ ...e, at: Date.now() });
          accepted += 1;
        }
      }
      s.eventBatches = (s.eventBatches ?? 0) + 1;
      send(res, 200, { accepted, rejected: (body.events?.length ?? 0) - accepted });
    }), true;
  }

  const open = /^\/r\/([0-9a-f-]{36})$/.exec(path);
  if (open) {
    const n = Number(open[1].slice(-12));
    if (!n || n > STORIES.length) return error(res, 404, "not_found", "That story is not in your paper"), true;
    s.events.push({ type: "open", edition_item_id: open[1], at: Date.now() });
    s.opens.push(open[1]);
    res.writeHead(302, { Location: `http://127.0.0.1:${process.env.MOCK_API_PORT ?? 3199}/__original/${n}` });
    return res.end(), true;
  }
  return false;
}

/** Test-only: put a reader into a known situation. */
export function seed(s, body) {
  s.completed = true;
  s.editionPlan =
    body.edition === "pending"
      ? { mode: "pending", startedAt: Date.now(), readyAt: Date.now() + (body.readyAfterMs ?? 3000) }
      : { mode: body.edition ?? "ready" };
}
