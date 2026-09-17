import { useEffect, useMemo, useState } from "react";

type Lang = "ru" | "en";
type Finding = {
  key: string;
  severity: number;
  title_ru: string;
  title_en: string;
  evidence_ru: string;
  evidence_en: string;
  advice_ru: string;
  advice_en: string;
  exercise_ru: string;
  exercise_en: string;
  target: string;
};
type Report = {
  match_id: string;
  hero_id: number;
  won: boolean;
  score: number;
  metrics: Record<string, number | boolean>;
  findings: Finding[];
  data_quality: "summary" | "replay";
  source?: string;
  ai_summary?: { model: string; language: string; content: string; created_at: string };
};
type Plan = { matches_analyzed: number; focus: Finding[]; next_review_after_matches: number; status: string };
type Status = { version: string; reports: Report[]; plan: Plan };
type RuntimeStatus = {
  hardware: { cpu: string; cpu_threads: number; ram_gb: number; gpus: Array<{ name: string; vram_gb: number }> };
  dota_active: boolean;
  fps_protection: boolean;
  policy: { mode: string; model: string | null; post_match_model: string | null; model_installed: boolean };
  ollama: { available: boolean; models: string[] };
  selected_model: string;
  automatic_model: string | null;
  ai_provider: "gemini" | "local" | "off";
  gemini: { configured: boolean; model: string };
  catalog: Array<{ id: string; label: string; size_gb: number; tier: string; installed: boolean; compatible: boolean; recommended: boolean }>;
};
type SummaryResult = { status: string; reason?: string; model?: string; content?: string | null; queued?: boolean };

const copy = {
  ru: {
    navOverview: "Обзор", navMatches: "Матчи", navPlan: "Мой план", navSettings: "Настройки",
    eyebrow: "ЛОКАЛЬНЫЙ DOTA 2 COACH", title: "Превращай матчи в навык.",
    subtitle: "LaneMind находит повторяющиеся ошибки и собирает короткий план тренировки — локально или с облачным AI.",
    sync: "Синхронизировать", import: "Импорт JSON / replay", demo: "Запустить демо",
    account: "Steam32 Account ID", recent: "Последние матчи", score: "Оценка матча",
    focus: "Главный фокус", evidence: "Что произошло", advice: "Что изменить", exercise: "Упражнение",
    plan: "План на следующие 3 матча", history: "История анализа", empty: "Добавьте матч, чтобы начать анализ.",
    local: "Реплеи локальны; в облако отправляется только отчёт", analyzed: "матчей проанализировано",
    dataSummary: "базовые данные", dataReplay: "данные replay", win: "Победа", loss: "Поражение",
    loading: "Анализируем…", ready: "Готово", error: "Не удалось выполнить операцию",
    goal: "Цель", allFindings: "Все наблюдения", select: "Выберите матч из истории",
    fpsTitle: "Защита FPS", dotaPaused: "Dota 2 активна — нейросеть приостановлена",
    systemReady: "Dota 2 не запущена — анализ разрешён", recommended: "После матча",
    ollamaMissing: "Ollama не обнаружена", cpuOnly: "Только CPU",
    modelManager: "Локальная нейросеть", automatic: "Автоматический выбор", noModel: "Без нейросети",
    install: "Скачать модель", installing: "Загрузка…", installed: "Установлена", incompatible: "Мало памяти",
    aiCoach: "Объяснение нейросети", generateAi: "Создать AI-отчёт", generatingAi: "Нейросеть анализирует…",
    queuedAi: "Отчёт поставлен в очередь до завершения Dota 2.", noOllama: "Запустите Ollama, чтобы использовать локальную нейросеть.",
    factsOnly: "Модель получает только рассчитанные факты и не должна выдумывать события.",
    aiMode: "Режим AI", geminiCloud: "Gemini Cloud", localOllama: "Локальная Ollama",
    geminiReady: "Ключ сохранён в защищённом хранилище", geminiMissing: "Добавьте Gemini API-ключ",
    keyPlaceholder: "Gemini API key", saveKey: "Сохранить ключ", removeKey: "Удалить ключ",
    keyStored: "Сохранён", cloudFacts: "В Gemini отправляется только рассчитанный отчёт выбранного матча.",
  },
  en: {
    navOverview: "Overview", navMatches: "Matches", navPlan: "My plan", navSettings: "Settings",
    eyebrow: "LOCAL DOTA 2 COACH", title: "Turn matches into skill.",
    subtitle: "LaneMind finds recurring mistakes and builds a short practice plan — locally or with cloud AI.",
    sync: "Sync matches", import: "Import JSON / replay", demo: "Run demo",
    account: "Steam32 Account ID", recent: "Recent matches", score: "Match score",
    focus: "Primary focus", evidence: "What happened", advice: "What to change", exercise: "Exercise",
    plan: "Plan for the next 3 matches", history: "Analysis history", empty: "Add a match to begin analysis.",
    local: "Replays stay local; only reports can go to the cloud", analyzed: "matches analyzed",
    dataSummary: "summary data", dataReplay: "replay data", win: "Victory", loss: "Defeat",
    loading: "Analyzing…", ready: "Ready", error: "Operation failed",
    goal: "Target", allFindings: "All findings", select: "Select a match from history",
    fpsTitle: "FPS protection", dotaPaused: "Dota 2 is active — AI is paused",
    systemReady: "Dota 2 is not running — analysis enabled", recommended: "After the match",
    ollamaMissing: "Ollama not detected", cpuOnly: "CPU only",
    modelManager: "Local AI model", automatic: "Automatic selection", noModel: "No AI model",
    install: "Download model", installing: "Downloading…", installed: "Installed", incompatible: "Not enough memory",
    aiCoach: "AI explanation", generateAi: "Generate AI report", generatingAi: "AI is analyzing…",
    queuedAi: "The report is queued until Dota 2 closes.", noOllama: "Start Ollama to use a local AI model.",
    factsOnly: "The model receives calculated facts only and must not invent events.",
    aiMode: "AI mode", geminiCloud: "Gemini Cloud", localOllama: "Local Ollama",
    geminiReady: "Key stored in secure credential storage", geminiMissing: "Add a Gemini API key",
    keyPlaceholder: "Gemini API key", saveKey: "Save key", removeKey: "Remove key",
    keyStored: "Stored", cloudFacts: "Only the calculated report for the selected match is sent to Gemini.",
  },
};

function coreCall<T>(request: Record<string, unknown>): Promise<T> {
  if (!window.laneMind) return Promise.reject(new Error("Open LaneMind in the Electron desktop app."));
  return window.laneMind.call(request) as Promise<T>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function App() {
  const [lang, setLang] = useState<Lang>("ru");
  const [accountId, setAccountId] = useState("");
  const [reports, setReports] = useState<Report[]>([]);
  const [plan, setPlan] = useState<Plan>({ matches_analyzed: 0, focus: [], next_review_after_matches: 3, status: "needs_matches" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [modelBusy, setModelBusy] = useState(false);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summary, setSummary] = useState<SummaryResult | null>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyConfigured, setKeyConfigured] = useState(false);
  const t = copy[lang];
  const selected = useMemo(() => reports.find((r) => r.match_id === selectedId) ?? reports[0], [reports, selectedId]);

  const applyResult = (value: unknown) => {
    const result = value as { reports?: Report[]; plan?: Plan; report?: Report; imported?: Report[] };
    if (result.reports) setReports(result.reports);
    if (result.plan) setPlan(result.plan);
    const first = result.report ?? result.imported?.[0] ?? result.reports?.[0];
    if (first) setSelectedId(first.match_id);
  };

  useEffect(() => {
    coreCall<Status>({ action: "status" }).then(applyResult).catch(() => undefined);
    window.laneMind?.geminiKeyStatus().then((result) => setKeyConfigured(result.configured)).catch(() => undefined);
  }, []);

  useEffect(() => {
    setSummary(selected?.ai_summary ? {
      status: "complete", model: selected.ai_summary.model, content: selected.ai_summary.content,
    } : null);
  }, [selected?.match_id]);

  useEffect(() => {
    if (summary?.status !== "deferred" || !runtime || runtime.dota_active || !selected) return;
    setSummaryBusy(true);
    coreCall<SummaryResult>({ action: "generate_summary", match_id: selected.match_id, language: lang })
      .then(setSummary).catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setSummaryBusy(false));
  }, [runtime?.dota_active, summary?.status, selected?.match_id, lang]);

  useEffect(() => {
    const refresh = () => coreCall<RuntimeStatus>({ action: "runtime_status" }).then(setRuntime).catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const run = async (operation: () => Promise<unknown>) => {
    setBusy(true); setError("");
    try { applyResult(await operation()); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setBusy(false); }
  };

  const sync = () => {
    if (!/^\d+$/.test(accountId)) { setError(lang === "ru" ? "Введите числовой Steam32 Account ID" : "Enter a numeric Steam32 Account ID"); return; }
    run(() => coreCall({ action: "sync_player", account_id: Number(accountId), count: 10 }));
  };

  const importFile = () => run(async () => {
    if (!window.laneMind) throw new Error("Desktop bridge is unavailable");
    const value = await window.laneMind.importFile(/^\d+$/.test(accountId) ? Number(accountId) : undefined);
    return value ?? { reports, plan };
  });

  const selectModel = async (model: string) => {
    setModelBusy(true); setError("");
    try { setRuntime(await coreCall<RuntimeStatus>({ action: "set_model", model })); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setModelBusy(false); }
  };

  const selectProvider = async (provider: RuntimeStatus["ai_provider"]) => {
    setModelBusy(true); setError(""); setSummary(null);
    try { setRuntime(await coreCall<RuntimeStatus>({ action: "set_ai_provider", provider })); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setModelBusy(false); }
  };

  const saveGeminiKey = async () => {
    if (!window.laneMind || !geminiKey.trim()) return;
    setKeyBusy(true); setError("");
    try {
      const result = await window.laneMind.setGeminiKey(geminiKey);
      setKeyConfigured(result.configured); setGeminiKey("");
      setRuntime(await coreCall<RuntimeStatus>({ action: "set_ai_provider", provider: "gemini" }));
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setKeyBusy(false); }
  };

  const removeGeminiKey = async () => {
    if (!window.laneMind) return;
    setKeyBusy(true); setError("");
    try {
      const result = await window.laneMind.clearGeminiKey();
      setKeyConfigured(result.configured);
      setRuntime(await coreCall<RuntimeStatus>({ action: "set_ai_provider", provider: "local" }));
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setKeyBusy(false); }
  };

  const installModel = async () => {
    if (!runtime) return;
    const model = runtime.selected_model === "auto" ? runtime.automatic_model : runtime.selected_model;
    if (!model || model === "off") return;
    setModelBusy(true); setError("");
    try {
      const result = await coreCall<{ runtime: RuntimeStatus }>({ action: "pull_model", model });
      if (result.runtime) setRuntime(result.runtime);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setModelBusy(false); }
  };

  const generateSummary = async () => {
    if (!selected) return;
    setSummaryBusy(true); setError("");
    try { setSummary(await coreCall<SummaryResult>({ action: "generate_summary", match_id: selected.match_id, language: lang })); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setSummaryBusy(false); }
  };

  const aiReady = runtime?.ai_provider === "gemini"
    ? runtime.gemini.configured
    : runtime?.ai_provider === "local"
      ? runtime.ollama.available && runtime.policy.model_installed && runtime.selected_model !== "off"
      : false;
  const activeAiModel = runtime?.ai_provider === "gemini"
    ? runtime.gemini.model
    : runtime?.ai_provider === "local"
      ? runtime.policy.post_match_model
      : null;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">L</div><div><b>LANEMIND</b><span>DOTA COACH</span></div></div>
        <nav>
          <button className="active"><i>⌂</i>{t.navOverview}</button>
          <button><i>◫</i>{t.navMatches}<em>{reports.length}</em></button>
          <button><i>◎</i>{t.navPlan}</button>
          <button><i>⚙</i>{t.navSettings}</button>
        </nav>
        <div className="privacy"><div className="pulse"/><b>LOCAL-FIRST</b><p>{t.local}</p></div>
        <div className="language">
          <button className={lang === "ru" ? "selected" : ""} onClick={() => setLang("ru")}>RU</button>
          <button className={lang === "en" ? "selected" : ""} onClick={() => setLang("en")}>EN</button>
        </div>
        <div className="version">v0.3 prototype</div>
      </aside>

      <main>
        <header className="hero">
          <div>
            <div className="eyebrow">{t.eyebrow}</div>
            <h1>{t.title}</h1>
            <p>{t.subtitle}</p>
          </div>
          <div className="hero-orbit"><span>{plan.matches_analyzed}</span><small>{t.analyzed}</small></div>
        </header>

        <section className="connect panel">
          <div className="field"><label>{t.account}</label><input value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="123456789" onKeyDown={(e) => e.key === "Enter" && sync()} /></div>
          <button className="primary" disabled={busy} onClick={sync}>{busy ? t.loading : t.sync}</button>
          <button className="secondary" disabled={busy} onClick={importFile}>↥ {t.import}</button>
          <button className="ghost" disabled={busy} onClick={() => run(() => coreCall({ action: "demo" }))}>{t.demo}</button>
        </section>
        {runtime && <section className={`runtime-bar panel ${runtime.dota_active ? "protecting" : "idle"}`}>
          <div className="shield">{runtime.dota_active ? "Ⅱ" : "✓"}</div>
          <div className="runtime-copy"><span>{t.fpsTitle}</span><b>{runtime.dota_active ? t.dotaPaused : t.systemReady}</b></div>
          <div className="hardware-chip"><small>RAM</small><b>{runtime.hardware.ram_gb} GB</b></div>
          <div className="hardware-chip gpu"><small>GPU</small><b>{runtime.hardware.gpus[0]?.name ?? t.cpuOnly}</b><em>{runtime.hardware.gpus[0] ? `${runtime.hardware.gpus[0].vram_gb} GB VRAM` : `${runtime.hardware.cpu_threads} threads`}</em></div>
          <div className="hardware-chip model"><small>{t.recommended}</small><b>{activeAiModel ?? "OFF"}</b><em>{runtime.ai_provider === "gemini" ? (runtime.gemini.configured ? t.keyStored : t.geminiMissing) : runtime.ollama.available ? (runtime.policy.model_installed ? "installed" : "download required") : t.ollamaMissing}</em></div>
        </section>}
        {error && <div className="error"><b>{t.error}</b><span>{error}</span><button onClick={() => setError("")}>×</button></div>}

        <div className="grid">
          <section className="report panel">
            {selected ? <>
              <div className="section-head"><div><span>{t.recent}</span><h2>Match #{selected.match_id}</h2></div><div className={`result ${selected.won ? "won" : "lost"}`}>{selected.won ? t.win : t.loss}</div></div>
              <div className="score-row">
                <div className="score-ring" style={{ "--score": `${selected.score * 3.6}deg` } as React.CSSProperties}><div><strong>{selected.score}</strong><span>/ 100</span></div></div>
                <div className="metrics">
                  <Metric label="KDA" value={selected.metrics.kda as number} />
                  <Metric label="GPM" value={selected.metrics.gpm as number} />
                  <Metric label="XPM" value={selected.metrics.xpm as number} />
                  <Metric label="LH/min" value={selected.metrics.lh_min as number} />
                </div>
              </div>
              {selected.findings[0] && <div className="featured-finding">
                <div className="severity">{selected.findings[0].severity}</div>
                <div><span>{t.focus}</span><h3>{selected.findings[0][`title_${lang}`]}</h3><p>{selected.findings[0][`advice_${lang}`]}</p></div>
              </div>}
              <div className={`ai-summary ${summary?.status ?? "idle"}`}>
                <div className="ai-summary-head"><div><span>{runtime?.ai_provider === "gemini" ? "GEMINI CLOUD" : "LOCAL AI"}</span><h3>{t.aiCoach}</h3></div>{summary?.model && <em>{summary.model}</em>}</div>
                {summary?.status === "complete" && <p>{summary.content}</p>}
                {summary?.status === "deferred" && <p>{t.queuedAi}</p>}
                {summary?.status === "unavailable" && <p>{summary.reason === "gemini_key_missing" ? t.geminiMissing : summary.reason === "ollama_unavailable" ? t.noOllama : t.install}</p>}
                {!summary && <><p>{runtime?.ai_provider === "gemini" ? t.cloudFacts : runtime?.ollama.available ? t.factsOnly : t.noOllama}</p><button disabled={summaryBusy || !aiReady || runtime?.dota_active} onClick={generateSummary}>{summaryBusy ? t.generatingAi : t.generateAi}</button></>}
                {summary?.status === "deferred" && <button disabled>{t.generatingAi}</button>}
              </div>
              <div className="quality">● {selected.data_quality === "replay" ? t.dataReplay : t.dataSummary}</div>
              <h3 className="subhead">{t.allFindings}</h3>
              <div className="finding-list">
                {selected.findings.map((finding, index) => <details key={finding.key} open={index === 0}>
                  <summary><span>{String(index + 1).padStart(2, "0")}</span><b>{finding[`title_${lang}`]}</b><i>＋</i></summary>
                  <div className="finding-body">
                    <div><label>{t.evidence}</label><p>{finding[`evidence_${lang}`]}</p></div>
                    <div><label>{t.advice}</label><p>{finding[`advice_${lang}`]}</p></div>
                    <div><label>{t.exercise}</label><p>{finding[`exercise_${lang}`]}</p></div>
                    <div className="target"><label>{t.goal}</label><b>{finding.target}</b></div>
                  </div>
                </details>)}
              </div>
            </> : <div className="empty"><div>◌</div><h2>{t.empty}</h2><p>{t.select}</p></div>}
          </section>

          <aside className="right-column">
            {runtime && <section className="models panel">
              <div className="section-head"><div><span>{t.aiMode}</span><h2>{t.modelManager}</h2></div><div className={`ollama-dot ${aiReady ? "online" : ""}`}/></div>
              <select value={runtime.ai_provider} disabled={modelBusy} onChange={(event) => selectProvider(event.target.value as RuntimeStatus["ai_provider"])}>
                <option value="gemini">{t.geminiCloud}</option>
                <option value="local">{t.localOllama}</option>
                <option value="off">{t.noModel}</option>
              </select>
              {runtime.ai_provider === "gemini" && <div className="gemini-settings">
                <p>{keyConfigured ? t.geminiReady : t.geminiMissing}</p>
                <input type="password" autoComplete="off" value={geminiKey} onChange={(event) => setGeminiKey(event.target.value)} placeholder={keyConfigured ? "••••••••••••••••" : t.keyPlaceholder} />
                <div className="key-actions">
                  <button className="model-install" disabled={keyBusy || !geminiKey.trim()} onClick={saveGeminiKey}>{keyBusy ? t.loading : t.saveKey}</button>
                  {keyConfigured && <button className="key-remove" disabled={keyBusy} onClick={removeGeminiKey}>{t.removeKey}</button>}
                </div>
                <div className="model-meta"><span>{runtime.gemini.configured ? t.keyStored : t.geminiMissing}</span><b>{runtime.gemini.model}</b></div>
              </div>}
              {runtime.ai_provider === "local" && <>
                <select value={runtime.selected_model} disabled={modelBusy} onChange={(event) => selectModel(event.target.value)}>
                  <option value="auto">{t.automatic} · {runtime.automatic_model ?? "OFF"}</option>
                  <option value="off">{t.noModel}</option>
                  {runtime.catalog.map((model) => <option key={model.id} value={model.id} disabled={!model.compatible}>
                    {model.label} · {model.size_gb} GB{model.installed ? ` · ${t.installed}` : ""}{!model.compatible ? ` · ${t.incompatible}` : ""}
                  </option>)}
                </select>
                <div className="model-meta">
                  <span>{runtime.ollama.available ? `${runtime.ollama.models.length} ${t.installed.toLowerCase()}` : t.ollamaMissing}</span>
                  <b>{runtime.policy.post_match_model ?? "OFF"}</b>
                </div>
                {!runtime.policy.model_installed && runtime.policy.post_match_model && <button className="model-install" disabled={modelBusy || !runtime.ollama.available || runtime.dota_active} onClick={installModel}>{modelBusy ? t.installing : t.install}</button>}
              </>}
            </section>}
            <section className="plan panel">
              <div className="section-head"><div><span>TRAINING LOOP</span><h2>{t.plan}</h2></div><div className="plan-count">{plan.focus.length}/3</div></div>
              {plan.focus.length ? plan.focus.map((finding, index) => <div className="plan-item" key={finding.key}>
                <span>{index + 1}</span><div><b>{finding[`title_${lang}`]}</b><p>{finding[`exercise_${lang}`]}</p><small>{t.goal}: {finding.target}</small></div>
              </div>) : <p className="muted">{t.empty}</p>}
            </section>
            <section className="history panel">
              <div className="section-head"><div><span>LOCAL DATABASE</span><h2>{t.history}</h2></div></div>
              <div className="history-list">
                {reports.slice(0, 7).map((report) => <button key={report.match_id} className={selected?.match_id === report.match_id ? "current" : ""} onClick={() => setSelectedId(report.match_id)}>
                  <span className={report.won ? "dot win" : "dot"}/><div><b>#{report.match_id}</b><small>{report.source ?? "local"} · {report.metrics.duration_min as number} min</small></div><strong>{report.score}</strong>
                </button>)}
                {!reports.length && <p className="muted">{t.empty}</p>}
              </div>
            </section>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default App;
