/**
 * A tiny in-memory stand-in for the NewsHelper API, used by the onboarding e2e tests.
 *
 * Both the Next.js server (session lookup) and the browser (via the /api rewrite) talk to it,
 * which is why it is a real HTTP server rather than Playwright route mocks. State is kept per
 * `dp_session` cookie value, so parallel tests never see each other's data.
 *
 *   API_URL=http://127.0.0.1:3199 pnpm build   (the rewrite target is baked in at build time)
 *   node e2e/mock-api.mjs
 */
import { createServer } from "node:http";

import { handleCatalogue, handleReader, runNightly, seed } from "./mock-reader.mjs";

const PORT = Number(process.env.MOCK_API_PORT ?? 3199);
const SESSION_COOKIE = "dp_session";
const STAGES = ["gathering", "choosing", "writing", "typesetting"];
const STAGE_MS = 450;

const TOPICS = [
  ["world", "World", "News"],
  ["pakistan", "Pakistan", "News"],
  ["business", "Business", "Money"],
  ["markets", "Markets", "Money"],
  ["ai", "Artificial Intelligence", "Tech"],
  ["software", "Software & Dev", "Tech"],
  ["science", "Science", "Science"],
  ["food", "Food", "Life"],
  ["cricket", "Cricket", "Sport"],
  ["f1", "Formula 1", "Sport"],
  ["film-tv", "Film & TV", "Culture"],
].map(([slug, label, group]) => ({ slug, label, group, description: `${label} news` }));

const SUGGESTIONS = {
  cricket: ["PSL", "Pakistan team", "Test cricket"],
  ai: ["AI agents", "Large language models"],
  f1: ["Race results", "Ferrari"],
};

const HEADLINES = Array.from({ length: 12 }, (_, i) => ({
  id: `00000000-0000-4000-8000-${String(i + 1).padStart(12, "0")}`,
  headline: `Headline number ${i + 1}: something worth knowing about this morning`,
  source: `The Daily ${i + 1}`,
  image_url: null,
  topic: ["ai", "cricket", "f1"][i % 3],
  outside: i % 4 === 3,
  answer: null,
}));

const PARSED = {
  topics: [
    { slug: "ai", weight: 0.9 },
    { slug: "cricket", weight: 0.8 },
  ],
  keywords: ["AI agents", "PSL"],
  entities: { people: [], companies: [], teams: [], places: [] },
  blocked: { topics: [], keywords: ["celebrity gossip"] },
  context: "Runs a digital agency.",
};

/** @type {Map<string, any>} */
const sessions = new Map();

function sessionFor(id) {
  if (!sessions.has(id)) {
    sessions.set(id, {
      step: 1,
      completed: false,
      steps: {},
      answers: {},
      saves: [],
      completeCalls: 0,
      completedAt: null,
      timezone: "Asia/Karachi",
      city: null,
    });
  }
  return sessions.get(id);
}

function cookieOf(req) {
  const match = new RegExp(`(?:^|;\\s*)${SESSION_COOKIE}=([^;]+)`).exec(req.headers.cookie ?? "");
  return match ? decodeURIComponent(match[1]) : null;
}

function send(res, status, body) {
  if (body === undefined) {
    res.writeHead(status).end();
    return;
  }
  res.writeHead(status, { "Content-Type": "application/json" }).end(JSON.stringify(body));
}

const error = (res, status, code, message) => send(res, status, { error: { code, message } });

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString();
  return text ? JSON.parse(text) : {};
}

function user(s) {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    email: "rafe@example.com",
    display_name: "Rafe Khan",
    timezone: s.timezone,
    city: s.city,
    onboarding_completed: s.completed,
  };
}

function profile(s) {
  return {
    onboarding_completed: s.completed,
    topics: {},
    keywords: [],
    entities: { people: [], companies: [], teams: [], places: [] },
    blocked: { topics: [], keywords: [], sources: [] },
    source_affinity: {},
    reading_minutes: 15,
    depth: "balanced",
    surprise_me: true,
    paper_name: s.steps[1]?.paper_name ?? null,
    context_notes: null,
  };
}

function state(s) {
  return {
    step: s.completed ? 6 : s.step,
    completed: s.completed,
    name: s.steps[1] ?? null,
    beats: s.steps[2] ?? null,
    words: s.steps[3] ?? null,
    reading: s.steps[5] ?? null,
    answers: s.answers,
  };
}

function editionStatus(s) {
  if (!s.completedAt) return { status: "none", stage: null, edition_id: null };
  const elapsed = Date.now() - s.completedAt;
  const index = Math.floor(elapsed / STAGE_MS);
  const edition_id = "22222222-2222-4222-8222-222222222222";
  if (index >= STAGES.length) return { status: "ready", stage: "done", edition_id };
  return { status: "pending", stage: STAGES[index], edition_id };
}

async function handle(req, res) {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`);
  const path = url.pathname;

  if (path === "/health") return send(res, 200, { status: "ok" });
  if (path === "/taxonomy") {
    return send(res, 200, { groups: ["News", "Money", "Tech", "Science", "Life", "Sport", "Culture"], topics: TOPICS });
  }

  if (handleCatalogue({ res, path, send })) return;

  const id = cookieOf(req);
  // test-only: read what the app saved
  if (path === "/__state") return id ? send(res, 200, sessionFor(id)) : error(res, 400, "bad_request", "no cookie");
  // test-only: the original article that /r/{id} redirects to
  if (path.startsWith("/__original/")) {
    res.writeHead(200, { "Content-Type": "text/html" }).end("<!doctype html><title>Original article</title><h1>Original article</h1>");
    return;
  }
  if (!id) return error(res, 401, "not_authenticated", "Sign in to continue");
  const s = sessionFor(id);
  if (path === "/__seed" && req.method === "POST") {
    seed(s, await readJson(req));
    return send(res, 204);
  }
  // test-only: run the nightly learn stage for this reader
  if (path === "/__learn" && req.method === "POST") {
    runNightly(s);
    return send(res, 204);
  }
  if (handleReader({ req, res, path, url, session: s, send, error, readJson })) return;

  if (path === "/auth/me") return send(res, 200, user(s));
  if (path === "/me/profile") return send(res, 200, profile(s));
  if (path === "/onboarding/state") return send(res, 200, state(s));

  const step = /^\/onboarding\/step\/(\d+)$/.exec(path);
  if (step && req.method === "PUT") {
    const n = Number(step[1]);
    const body = await readJson(req);
    if (n < 1 || n > 5) return error(res, 404, "unknown_step", `There is no step ${n}`);
    if (n === 2 && (body.topics?.length ?? 0) < 3) return error(res, 422, "validation_error", "Pick at least 3 topics");
    s.steps[n] = body;
    s.saves.push({ step: n, body });
    s.step = Math.max(s.step, n + 1);
    if (n === 1) {
      s.timezone = body.timezone;
      s.city = body.city;
    }
    return send(res, 200, state(s));
  }

  if (path === "/onboarding/suggestions") {
    const topic = url.searchParams.get("topic") ?? "";
    return send(res, 200, { topic, suggestions: SUGGESTIONS[topic] ?? ["Latest", "Analysis", "Explainers"] });
  }
  if (path === "/onboarding/parse" && req.method === "POST") return send(res, 200, PARSED);
  if (path === "/onboarding/headlines") {
    return send(res, 200, { headlines: HEADLINES.map((h) => ({ ...h, answer: s.answers[h.id] ?? null })) });
  }
  if (path === "/onboarding/taste" && req.method === "POST") {
    const body = await readJson(req);
    s.answers[body.article_id] = body.interested;
    return send(res, 204);
  }
  if (path === "/onboarding/complete" && req.method === "POST") {
    s.completeCalls += 1;
    s.completed = true;
    s.completedAt ??= Date.now();
    return send(res, 200, { edition_id: "22222222-2222-4222-8222-222222222222", status: "pending" });
  }
  if (path === "/onboarding/status") return send(res, 200, editionStatus(s));

  return error(res, 404, "not_found", `No mock for ${req.method} ${path}`);
}

createServer((req, res) => {
  handle(req, res).catch((e) => error(res, 500, "mock_failure", String(e)));
}).listen(PORT, "127.0.0.1", () => console.log(`mock API on http://127.0.0.1:${PORT}`));
