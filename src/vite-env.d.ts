/// <reference types="vite/client" />

interface Window {
  laneMind?: {
    call(request: Record<string, unknown>): Promise<unknown>;
    importFile(accountId?: number): Promise<unknown>;
  };
}
