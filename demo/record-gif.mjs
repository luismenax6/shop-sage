// Short chat-only clip for the README GIF. Prereqs: stack running on :4200.
//   node record-gif.mjs   (then convert demo/videos/*.webm -> demo/shopsage-chat.gif)
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VIEW = { width: 1000, height: 740 };

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEW,
    recordVideo: { dir: path.join(__dirname, 'videos'), size: VIEW },
  });
  const page = await context.newPage();

  await page.goto('http://localhost:4200');
  await page.waitForTimeout(900);

  const input = page.locator('input[name="draft"]');
  await input.click();
  await input.type('a gift for my dad who camps, under $100', { delay: 40 });
  await page.keyboard.press('Enter');
  await page.waitForSelector('.card', { timeout: 40000 });
  await page.waitForTimeout(1600);

  await page.locator('.card__add').first().click();
  await page.waitForTimeout(2600);

  await context.close();
  await browser.close();
  console.log('clip saved in demo/videos/');
}

main().catch((e) => { console.error(e); process.exit(1); });
