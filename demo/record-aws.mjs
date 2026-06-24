// Records a demo against the LIVE AWS deployment (CloudFront), including the
// freshly-ingested loyalty.md doc. Higher latency than local, so waits are
// generous.  node record-aws.mjs
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = 'https://d2at00pcyip50e.cloudfront.net';
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
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 50000 });
  await sleep(page, 2000);
  await scrollToBottom(page);
  await sleep(page, 3400);
}

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEW,
    recordVideo: { dir: path.join(__dirname, 'videos'), size: VIEW },
  });
  const page = await context.newPage();

  // Intro: architecture
  await page.goto(scene('arch-aws.html'));
  await sleep(page, 6500);

  // Live app on AWS
  await page.goto(FRONTEND, { waitUntil: 'networkidle' });
  await sleep(page, 2500);

  await ask(page, 'a gift for my dad who camps, under $100', '.card');

  await page.locator('.card__add').first().click();
  await sleep(page, 3400);

  await ask(page, "can I return a Father's Day gift after 45 days?", '.cite');

  // Live ingestion story, then ask about the just-uploaded doc
  await page.goto(scene('ingest-aws.html'));
  await sleep(page, 8500);
  await page.goto(FRONTEND, { waitUntil: 'networkidle' });
  await sleep(page, 1500);
  await ask(page, 'How does the rewards program work? How many points per dollar?', '.cite');

  // Outro
  await page.goto(scene('arch-aws.html'));
  await sleep(page, 3000);

  await context.close();
  await browser.close();
  console.log('AWS demo saved in demo/videos/');
}

main().catch((e) => { console.error(e); process.exit(1); });
