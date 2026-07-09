#!/usr/bin/env node
import { createRequire } from "node:module";
import { mkdir, readFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "assets", "wise-owl-cli-demo.gif");
const LOGO = path.join(ROOT, "assets", "wise-owl-logo-transparent.png");
const SIZE = { width: 960, height: 540 };

function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_NODE_MODULES,
    path.join(tmpdir(), "wiseowl-playwright", "node_modules"),
    path.join(ROOT, "node_modules"),
  ].filter(Boolean);

  for (const modulesPath of candidates) {
    if (existsSync(path.join(modulesPath, "playwright"))) {
      return createRequire(path.join(modulesPath, "package.json"))("playwright");
    }
  }

  throw new Error(
    [
      "Playwright was not found.",
      "Install it outside the repo, for example:",
      "  mkdir -p /tmp/wiseowl-playwright",
      "  cd /tmp/wiseowl-playwright",
      "  npm init -y",
      "  npm install playwright",
      "  npx playwright install chromium",
      "Then rerun with PLAYWRIGHT_NODE_MODULES=/tmp/wiseowl-playwright/node_modules.",
    ].join("\n"),
  );
}

const scenes = [
  {
    stage: "1. Prompt",
    title: "Ask Codex for a second opinion",
    prompt: "Use Wise Owl Standard to review this packaging docs diff.",
    terminal: [
      "$ codex --no-alt-screen",
      "> Use Wise Owl Standard to review this packaging docs diff.",
      "",
      "Wise Owl mode: Standard",
      "Review packet: ready",
    ],
    cards: [
      ["Mode", "Standard"],
      ["Sandbox", "read-only"],
      ["Scope", "docs diff"],
    ],
    hold: 6,
  },
  {
    stage: "2. Critics",
    title: "Read-only reviewers inspect the risky parts",
    prompt: "Logic Owl checks correctness. Proof Owl checks evidence.",
    terminal: [
      "Selected reviewers:",
      "  logic_owl: reviewing",
      "  proof_owl: reviewing",
      "  prime_owl: waiting",
      "",
      "[PARALLEL_CRITIC_PHASE]",
    ],
    cards: [
      ["Logic Owl", "reviewing"],
      ["Proof Owl", "reviewing"],
      ["Prime Owl", "waiting"],
    ],
    hold: 7,
  },
  {
    stage: "3. Prime",
    title: "Prime Owl reduces noise into one verdict",
    prompt: "Accepted finding: screenshot reference needs evidence.",
    terminal: [
      "Critic results received",
      "Prime Owl verdict: caution",
      "Accepted findings: 1 non_blocking",
      "",
      "Builder action: add/provide missing asset proof.",
    ],
    cards: [
      ["Verdict", "caution"],
      ["Accepted", "1"],
      ["Blocking", "0"],
    ],
    hold: 8,
  },
  {
    stage: "4. Final",
    title: "Codex gets a compact action list",
    prompt: "Proceed with checks run, execution notes, and final response.",
    terminal: [
      "Read-only Wise Owl Standard review complete.",
      "",
      "selected_reviewers: logic_owl, proof_owl, prime_owl",
      "prime_owl_verdict: caution",
      "checks: git status, git diff, rg --files",
      "execution_note: schema issues were reported, not hidden.",
    ],
    cards: [
      ["Status", "complete"],
      ["Checks", "listed"],
      ["Next", "finalize"],
    ],
    hold: 10,
  },
];

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderHtml(scene, index, total, logoDataUri) {
  const progress = Math.round(((index + 1) / total) * 100);
  const terminalLines = scene.terminal
    .map((line) => {
      const text = escapeHtml(line);
      const kind = line.startsWith("$")
        ? "cmd"
        : line.startsWith(">")
          ? "ask"
          : line.includes("verdict") || line.includes("Accepted")
            ? "signal"
            : line.includes("[")
              ? "phase"
              : "";
      return `<div class="line ${kind}">${text || "&nbsp;"}</div>`;
    })
    .join("");
  const cards = scene.cards
    .map(([label, value]) => `<div class="card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");

  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    width: ${SIZE.width}px;
    height: ${SIZE.height}px;
    overflow: hidden;
    color: #eef6ff;
    font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background:
      radial-gradient(circle at 18% 8%, rgba(104, 211, 145, 0.28), transparent 30%),
      linear-gradient(135deg, #07111f 0%, #10223a 44%, #203a49 100%);
  }
  .wrap {
    height: 100%;
    padding: 36px;
    display: grid;
    grid-template-columns: 1.1fr 0.85fr;
    gap: 28px;
    align-items: stretch;
  }
  .terminal {
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 18px;
    background: rgba(7, 13, 24, 0.9);
    box-shadow: 0 22px 58px rgba(0, 0, 0, 0.34);
    overflow: hidden;
  }
  .bar {
    height: 44px;
    display: flex;
    align-items: center;
    padding: 0 18px;
    gap: 9px;
    color: #9fb3c8;
    font-size: 13px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    background: rgba(255, 255, 255, 0.04);
  }
  .dot { width: 11px; height: 11px; border-radius: 99px; }
  .red { background: #ff6b6b; }
  .yellow { background: #ffd166; }
  .green { background: #67d982; }
  .titlebar { margin-left: 9px; letter-spacing: 0; }
  .screen {
    height: 408px;
    padding: 24px;
    font: 20px/1.48 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }
  .line { min-height: 29px; color: #d6e4f2; white-space: pre-wrap; }
  .cmd { color: #90cdf4; }
  .ask { color: #b9f6ca; }
  .signal { color: #ffd166; }
  .phase { color: #9be7ff; }
  .side {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-width: 0;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .brand img {
    width: 82px;
    height: 82px;
    object-fit: contain;
    filter: drop-shadow(0 14px 24px rgba(0, 0, 0, 0.28));
  }
  .name {
    font-size: 42px;
    font-weight: 780;
    letter-spacing: 0;
  }
  .sub {
    color: #b7c8d9;
    font-size: 15px;
    margin-top: 4px;
  }
  .stage {
    color: #94f1c5;
    font-size: 15px;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: 0;
  }
  h1 {
    margin: 12px 0 10px;
    font-size: 32px;
    line-height: 1.08;
    letter-spacing: 0;
  }
  .prompt {
    color: #dce9f8;
    font-size: 18px;
    line-height: 1.35;
    margin-bottom: 22px;
  }
  .cards {
    display: grid;
    gap: 10px;
  }
  .card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 15px;
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.08);
  }
  .card span { color: #b8c7d6; font-size: 14px; }
  .card strong { color: #ffffff; font-size: 17px; letter-spacing: 0; }
  .foot {
    color: #aebdca;
    font-size: 12px;
    line-height: 1.35;
  }
  .progress {
    margin-top: 12px;
    width: 100%;
    height: 7px;
    border-radius: 99px;
    background: rgba(255, 255, 255, 0.13);
    overflow: hidden;
  }
  .fill {
    width: ${progress}%;
    height: 100%;
    background: linear-gradient(90deg, #67d982, #ffd166);
  }
</style>
</head>
<body>
  <main class="wrap">
    <section class="terminal">
      <div class="bar"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span><span class="titlebar">Codex CLI</span></div>
      <div class="screen">${terminalLines}</div>
    </section>
    <section class="side">
      <div>
        <div class="brand">
          <img src="${logoDataUri}" alt="">
          <div>
            <div class="name">Wise Owl</div>
            <div class="sub">second-opinion review for Codex</div>
          </div>
        </div>
        <div style="height: 24px"></div>
        <div class="stage">${escapeHtml(scene.stage)}</div>
        <h1>${escapeHtml(scene.title)}</h1>
        <div class="prompt">${escapeHtml(scene.prompt)}</div>
        <div class="cards">${cards}</div>
      </div>
      <div class="foot">
        Replay from a real Codex CLI transcript. Timing compressed. Local warning noise removed.
        <div class="progress"><div class="fill"></div></div>
      </div>
    </section>
  </main>
</body>
</html>`;
}

async function main() {
  const { chromium } = loadPlaywright();
  const logoDataUri = `data:image/png;base64,${(await readFile(LOGO)).toString("base64")}`;
  const frameDir = path.join(tmpdir(), `wise-owl-cli-demo-${process.pid}`);
  await rm(frameDir, { recursive: true, force: true });
  await mkdir(frameDir, { recursive: true });

  const expanded = [];
  for (const scene of scenes) {
    for (let i = 0; i < scene.hold; i += 1) {
      expanded.push(scene);
    }
  }

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: SIZE, deviceScaleFactor: 1 });
    for (let i = 0; i < expanded.length; i += 1) {
      await page.setContent(renderHtml(expanded[i], i, expanded.length, logoDataUri), { waitUntil: "load" });
      await page.screenshot({ path: path.join(frameDir, `frame-${String(i).padStart(3, "0")}.png`) });
    }
  } finally {
    await browser.close();
  }

  const palette = path.join(frameDir, "palette.png");
  const input = path.join(frameDir, "frame-%03d.png");
  const paletteResult = spawnSync(
    "ffmpeg",
    ["-y", "-framerate", "7", "-i", input, "-vf", "palettegen=stats_mode=diff", "-frames:v", "1", "-update", "1", palette],
    { stdio: "inherit" },
  );
  if (paletteResult.status !== 0) {
    throw new Error("ffmpeg palette generation failed");
  }

  const gifResult = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-framerate",
      "7",
      "-i",
      input,
      "-i",
      palette,
      "-lavfi",
      "paletteuse=dither=bayer:bayer_scale=5",
      "-loop",
      "0",
      OUT,
    ],
    { stdio: "inherit" },
  );
  if (gifResult.status !== 0) {
    throw new Error("ffmpeg GIF generation failed");
  }

  await rm(frameDir, { recursive: true, force: true });
  console.log(`Wrote ${path.relative(ROOT, OUT)}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
