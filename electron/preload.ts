import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("laneMind", {
  call: (request: Record<string, unknown>) => ipcRenderer.invoke("core:call", request),
  importFile: (accountId?: number) => ipcRenderer.invoke("file:import", accountId),
});
