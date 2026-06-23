// Drives the running app and records a demo video (.webm) into ./videos.
// Prereqs: docker DB up, backend on :5001, frontend on :4200.
//   node record.mjs
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = 'http://localhost:4200';
const VIEW = { width: 1280, height: 800 };
const scene = (name) => 'file://' + path.join(__dirname, name);

const sleep = (page, ms) => page.waitForTimeout(ms);

async function scrollToBottom(page) {
  await page.evaluate(() => {
    const el = document.querySelector('.chat__messages');
    if (el) el.scrollTop = el.scrollHeight;
  });
}

async function ask(page, text, waitFor) {
  const input = page.locator('input[name="draft"]');
  await input.click();
  await input.type(text, { delay: 45 });
  await sleep(page, 500);
  await page.keyboard.press('Enter');
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 40000 });
  await sleep(page, 1600);
  await scrollToBottom(page);
  await sleep(page, 3200);
}

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEW,
    recordVideo: { dir: path.join(__dirname, 'videos'), size: VIEW },
  });
  const page = await context.newPage();

  // --- Intro: architecture card ---
  await page.goto(scene('arch-aws.html'));
  await sleep(page, 7500);

  // --- Behind the scenes: ingestion + C retriever (shown up front) ---
  await page.goto(scene('pipeline.html'));
  await sleep(page, 9000);

  // --- Live demo ---
  await page.goto(FRONTEND);
  await sleep(page, 2000);

  // 1. product search -> cards
  await ask(page, 'a gift for my dad who camps, under $100', '.card');

  // 2. add to cart -> mini-cart updates
  await page.locator('.card__add').first().click();
  await sleep(page, 3400);

  // 3. support question -> answer with citations
  await ask(page, "can I return a Father's Day gift after 45 days?", '.cite');

  // 4. off-topic -> guardrail (no hallucination)
  await ask(page, 'do you have a store in Madrid?', null);
  await sleep(page, 3000);

  // --- Outro: architecture card again ---
  await page.goto(scene('arch-aws.html'));
  await sleep(page, 3000);

  await context.close(); // finalizes and writes the video file
  await browser.close();
  console.log('Done. Video saved in demo/videos/');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
