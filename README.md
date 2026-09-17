# LaneMind

LaneMind is a local-first, open-source Dota 2 coaching prototype. It imports OpenDota match data, calculates deterministic metrics, explains the most important mistakes, and creates a short practice plan. Match data and reports are stored in a local SQLite database.

## Current milestone

- Windows desktop shell built with Electron and React
- Russian and English UI
- OpenDota sync by Steam32 account ID
- OpenDota JSON import
- Explainable match analysis and recurring-problem training plan
- Local SQLite persistence
- Demo match for offline evaluation
- Automatic CPU, RAM, and NVIDIA VRAM detection
- FPS protection that pauses AI inference while `dota2.exe` is active
- Hardware-aware recommendations for Qwen3 1.7B, 4B, or 8B through Ollama
- A guarded Ollama provider that cannot start inference while Dota 2 is active

Native `.dem` replay parsing and local LLM rewriting are the next milestones. The current analysis is deterministic and does not need a model or API key.

## Development

Requirements: Node.js 22+, npm, and Python 3.11+.

```powershell
npm install
npm run dev
```

Run all checks:

```powershell
npm run check
```

Build frontend and Electron sources:

```powershell
npm run build
```

## Data format

JSON import accepts a full OpenDota match object, a list of match objects, or an object with a `matches` array. The selected player is matched by Steam32 account ID when available; otherwise the first player is used.

## Privacy

Imported data is stored only in Electron's local application data directory. OpenDota requests are made directly by the local Python process. No LaneMind server is involved.

## License

MIT. See `LICENSE`.
