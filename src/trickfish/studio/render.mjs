// Render HTML frames to PNG with Chromium. Usage: node render.mjs manifest.json
// manifest: [{"html": "/abs/frame.html", "out": "/abs/out.png", "width": 1080, "height": 1350, "scale": 2}]
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const browser = await chromium.launch();
try {
  for (const job of jobs) {
    const page = await browser.newPage({
      viewport: { width: job.width, height: job.height },
      deviceScaleFactor: job.scale ?? 2,
    });
    await page.goto("file://" + job.html);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: job.out, clip: { x: 0, y: 0, width: job.width, height: job.height } });
    await page.close();
  }
} finally {
  await browser.close();
}
