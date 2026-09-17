import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("laneMind", {
  call: (request: Record<string, unknown>) => ipcRenderer.invoke("core:call", request),
  importFile: (accountId?: number) => ipcRenderer.invoke("file:import", accountId),
  geminiKeyStatus: () => ipcRenderer.invoke("gemini-key:status"),
  setGeminiKey: (key: string) => ipcRenderer.invoke("gemini-key:set", key),
  clearGeminiKey: () => ipcRenderer.invoke("gemini-key:clear"),
});
