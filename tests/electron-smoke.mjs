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
  await window.locator(".models select").first().waitFor({ state: "visible", timeout: 15_000 });
  const providerSelect = window.locator(".models select").first();
  const originalProvider = await providerSelect.inputValue();
  const providerOptions = await providerSelect.locator("option").count();
  if (originalProvider !== "local") {
    await providerSelect.selectOption("local");
    await window.locator(".models select").nth(1).waitFor({ state: "visible", timeout: 15_000 });
  }
  const modelSelect = window.locator(".models select").nth(1);
  const modelOptions = await modelSelect.count() ? await modelSelect.locator("option").count() : 0;
  if (providerOptions !== 3 || modelOptions < 7) {
    throw new Error(`Expected provider and local model options, found providers=${providerOptions}, models=${modelOptions}`);
  }
  await window.getByRole("button", { name: "Запустить демо" }).click();
  await window.getByText("Match #8400000001").waitFor({ state: "visible", timeout: 15_000 });
  await window.getByRole("button", { name: "Синхронизировать" }).waitFor({ state: "visible", timeout: 15_000 });
  const score = await window.locator(".score-ring strong").innerText();
  const findings = await window.locator(".finding-list details").count();
  if (!/^\d+$/.test(score) || findings < 3) {
    throw new Error(`Unexpected demo report: score=${score}, findings=${findings}`);
  }
  await window.screenshot({ path: path.resolve("work", "lanemind-smoke.png"), fullPage: true });
  if (originalProvider !== "local") {
    await providerSelect.selectOption(originalProvider);
    if (originalProvider === "gemini") {
      await window.locator(".gemini-settings").waitFor({ state: "visible", timeout: 15_000 });
    }
  }
  console.log(JSON.stringify({ ok: true, score, findings, providerOptions, modelOptions }));
} finally {
  await app.close();
}
