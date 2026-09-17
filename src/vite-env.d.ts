/// <reference types="vite/client" />

interface Window {
  laneMind?: {
    call(request: Record<string, unknown>): Promise<unknown>;
    importFile(accountId?: number): Promise<unknown>;
    geminiKeyStatus(): Promise<{ configured: boolean }>;
    setGeminiKey(key: string): Promise<{ configured: boolean }>;
    clearGeminiKey(): Promise<{ configured: boolean }>;
  };
}
