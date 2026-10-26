// Render an HTML infographic to PNG: node render.mjs <in.html> <out.png> [selector] [scale]
// Uses installed Google Chrome (PW_CHANNEL to override). PLAYWRIGHT_DIR points at a node_modules folder that has `playwright`.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , input, output, selector = "#sheet", scale = "2"] = process.argv;
if (!input || !output) {
  console.error("usage: node render.mjs <in.html> <out.png> [selector] [scale]");
  process.exit(1);
}

const require = createRequire(path.join(process.env.PLAYWRIGHT_DIR ?? process.cwd(), "noop.js"));
const { chromium } = require("playwright");

const browser = await chromium.launch({ channel: process.env.PW_CHANNEL ?? "chrome" });
const page = await browser.newPage({ viewport: { width: 1700, height: 1000 }, deviceScaleFactor: Number(scale) });
await page.goto(pathToFileURL(path.resolve(input)).href);
await page.evaluate(() => document.fonts.ready);
await page.locator(selector).screenshot({ path: output });
await browser.close();
console.log(`wrote ${output}`);
