import { app, BrowserWindow, dialog, ipcMain, safeStorage } from "electron";
import path from "node:path";
import { spawn } from "node:child_process";
import fs from "node:fs";

type CoreRequest = { action: string; [key: string]: unknown };
type SecretStore = { geminiApiKey?: string };

function projectRoot(): string {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
}

function secretsPath(): string {
  return path.join(app.getPath("userData"), "secrets.json");
}

function readGeminiKey(): string | undefined {
  try {
    const payload = JSON.parse(fs.readFileSync(secretsPath(), "utf8")) as SecretStore;
    if (!payload.geminiApiKey || !safeStorage.isEncryptionAvailable()) return undefined;
    return safeStorage.decryptString(Buffer.from(payload.geminiApiKey, "base64"));
  } catch {
    return undefined;
  }
}

function writeGeminiKey(key: string): void {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error("Secure credential storage is unavailable on this computer");
  }
  const target = secretsPath();
  const temporary = `${target}.tmp`;
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const payload: SecretStore = {
    geminiApiKey: safeStorage.encryptString(key).toString("base64"),
  };
  fs.writeFileSync(temporary, JSON.stringify(payload), { encoding: "utf8", mode: 0o600 });
  fs.renameSync(temporary, target);
}

function clearGeminiKey(): void {
  try {
    fs.rmSync(secretsPath());
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
}

function runCore(request: CoreRequest): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const root = projectRoot();
    const dbPath = path.join(app.getPath("userData"), "lanemind.sqlite3");
    const python = process.platform === "win32" ? "python" : "python3";
    const childEnv: NodeJS.ProcessEnv = { ...process.env, PYTHONUTF8: "1" };
    const geminiApiKey = readGeminiKey();
    if (geminiApiKey) childEnv.GEMINI_API_KEY = geminiApiKey;
    else delete childEnv.GEMINI_API_KEY;
    const child = spawn(python, ["-m", "coach_core.cli", "--db", dbPath], {
      cwd: root,
      windowsHide: true,
      env: childEnv,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) return reject(new Error(stderr || `Core exited with ${code}`));
      try {
        const result = JSON.parse(stdout);
        if (result.ok === false) reject(new Error(result.error));
        else resolve(result.data);
      } catch {
        reject(new Error(stderr || "Invalid response from coaching core"));
      }
    });
    child.stdin.end(JSON.stringify(request));
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1040,
    minHeight: 680,
    backgroundColor: "#090d19",
    titleBarStyle: "hiddenInset",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (!app.isPackaged && process.argv.includes("--dev")) win.loadURL("http://localhost:5173");
  else win.loadFile(path.join(projectRoot(), "dist", "index.html"));
}

app.whenReady().then(() => {
  ipcMain.handle("core:call", (_event, request: CoreRequest) => runCore(request));
  ipcMain.handle("gemini-key:status", () => ({ configured: Boolean(readGeminiKey()) }));
  ipcMain.handle("gemini-key:set", (_event, rawKey: string) => {
    const key = String(rawKey ?? "").trim();
    if (key.length < 20) throw new Error("Gemini API key is too short");
    writeGeminiKey(key);
    return { configured: true };
  });
  ipcMain.handle("gemini-key:clear", () => {
    clearGeminiKey();
    return { configured: false };
  });
  ipcMain.handle("file:import", async (_event, accountId?: number) => {
    const result = await dialog.showOpenDialog({
      properties: ["openFile"],
      filters: [
        { name: "Dota match data", extensions: ["json", "dem"] },
        { name: "All files", extensions: ["*"] },
      ],
    });
    if (result.canceled || !result.filePaths[0]) return null;
    const filePath = result.filePaths[0];
    if (path.extname(filePath).toLowerCase() === ".dem") {
      return runCore({ action: "import_replay", path: filePath });
    }
    return runCore({
      action: "import_json",
      content: fs.readFileSync(filePath, "utf8"),
      source_path: filePath,
      account_id: accountId,
    });
  });
  createWindow();
  app.on("activate", () => BrowserWindow.getAllWindows().length === 0 && createWindow());
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
