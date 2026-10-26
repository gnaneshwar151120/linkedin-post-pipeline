// Record an animated HTML page to GIF or MP4: node record.mjs <in.html> <out.gif|out.mp4> [fps] [selector]
// The page must define window.FRAMES (frame count) and window.setFrame(i) that draws frame i deterministically.
// Frames are screenshotted with installed Google Chrome, then joined by ffmpeg (palette pass for GIFs).
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const [, , input, output, fps = "12", selector = "#stage"] = process.argv;
if (!input || !output) {
  console.error("usage: node record.mjs <in.html> <out.gif|out.mp4> [fps] [selector]");
  process.exit(1);
}

const require = createRequire(path.join(process.env.PLAYWRIGHT_DIR ?? process.cwd(), "noop.js"));
const { chromium } = require("playwright");

const dir = mkdtempSync(path.join(os.tmpdir(), "frames-"));
const browser = await chromium.launch({ channel: process.env.PW_CHANNEL ?? "chrome" });
const page = await browser.newPage({ viewport: { width: 1200, height: 1500 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.resolve(input)).href);
await page.evaluate(() => document.fonts.ready);
const frames = await page.evaluate(() => window.FRAMES);
const stage = page.locator(selector);
for (let i = 0; i < frames; i++) {
  await page.evaluate((n) => window.setFrame(n), i);
  await stage.screenshot({ path: path.join(dir, `f${String(i).padStart(4, "0")}.png`) });
}
await browser.close();

const src = ["-y", "-framerate", fps, "-i", path.join(dir, "f%04d.png")];
if (output.endsWith(".gif")) {
  execFileSync("ffmpeg", [...src, "-vf", "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle", "-loop", "0", output], { stdio: "ignore" });
} else {
  execFileSync("ffmpeg", [...src, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", output], { stdio: "ignore" });
}
rmSync(dir, { recursive: true });
console.log(`wrote ${output} (${frames} frames @ ${fps} fps)`);
