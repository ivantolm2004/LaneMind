import { _electron as electron } from "playwright-core";
import path from "node:path";

const app = await electron.launch({
  args: [path.resolve("."), ...(process.argv.includes("--dev") ? ["--dev"] : [])],
  env: { ...process.env, PYTHONUTF8: "1" },
});

try {
  const window = await app.firstWindow();
  await window.waitForLoadState("domcontentloaded");
  await window.getByRole("button", { name: "Запустить демо" }).click();
  await window.getByText("Match #8400000001").waitFor({ state: "visible", timeout: 15_000 });
  const score = await window.locator(".score-ring strong").innerText();
  const findings = await window.locator(".finding-list details").count();
  if (!/^\d+$/.test(score) || findings < 3) {
    throw new Error(`Unexpected demo report: score=${score}, findings=${findings}`);
  }
  await window.screenshot({ path: path.resolve("work", "lanemind-smoke.png"), fullPage: true });
  console.log(JSON.stringify({ ok: true, score, findings }));
} finally {
  await app.close();
}
