import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";
import { spawn } from "node:child_process";
import fs from "node:fs";

type CoreRequest = { action: string; [key: string]: unknown };

function projectRoot(): string {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
}

function runCore(request: CoreRequest): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const root = projectRoot();
    const dbPath = path.join(app.getPath("userData"), "lanemind.sqlite3");
    const python = process.platform === "win32" ? "python" : "python3";
    const child = spawn(python, ["-m", "coach_core.cli", "--db", dbPath], {
      cwd: root,
      windowsHide: true,
      env: { ...process.env, PYTHONUTF8: "1" },
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
