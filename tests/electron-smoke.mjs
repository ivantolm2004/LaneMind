import { _electron as electron } from "playwright-core";
import path from "node:path";

const app = await electron.launch({
  args: [path.resolve("."), ...(process.argv.includes("--dev") ? ["--dev"] : [])],
  env: { ...process.env, PYTHONUTF8: "1" },
});

try {
  const window = await app.firstWindow();
  await window.waitForLoadState("domcontentloaded");
  await window.locator(".runtime-bar").waitFor({ state: "visible", timeout: 15_000 });
  await window.locator(".models select").waitFor({ state: "visible", timeout: 15_000 });
  const modelOptions = await window.locator(".models select option").count();
  if (modelOptions < 7) throw new Error(`Expected model manager options, found ${modelOptions}`);
  await window.getByRole("button", { name: "Запустить демо" }).click();
  await window.getByText("Match #8400000001").waitFor({ state: "visible", timeout: 15_000 });
  await window.getByRole("button", { name: "Синхронизировать" }).waitFor({ state: "visible", timeout: 15_000 });
  const score = await window.locator(".score-ring strong").innerText();
  const findings = await window.locator(".finding-list details").count();
  if (!/^\d+$/.test(score) || findings < 3) {
    throw new Error(`Unexpected demo report: score=${score}, findings=${findings}`);
  }
  await window.screenshot({ path: path.resolve("work", "lanemind-smoke.png"), fullPage: true });
  console.log(JSON.stringify({ ok: true, score, findings, modelOptions }));
} finally {
  await app.close();
}
