from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    key: str
    severity: int
    title_ru: str
    title_en: str
    evidence_ru: str
    evidence_en: str
    advice_ru: str
    advice_en: str
    exercise_ru: str
    exercise_en: str
    target: str


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def find_player(match: dict[str, Any], account_id: int | None) -> dict[str, Any]:
    players = match.get("players") or []
    if not players:
        raise ValueError("Match has no player data")
    if account_id is not None:
        for player in players:
            if int(player.get("account_id") or -1) == int(account_id):
                return player
    return players[0]


def analyze_match(match: dict[str, Any], account_id: int | None = None) -> dict[str, Any]:
    player = find_player(match, account_id)
    duration_seconds = max(_num(match.get("duration"), 1), 1)
    minutes = duration_seconds / 60
    kills = _num(player.get("kills"))
    assists = _num(player.get("assists"))
    deaths = _num(player.get("deaths"))
    last_hits = _num(player.get("last_hits"))
    denies = _num(player.get("denies"))
    gpm = _num(player.get("gold_per_min"))
    xpm = _num(player.get("xp_per_min"))
    hero_damage = _num(player.get("hero_damage"))
    tower_damage = _num(player.get("tower_damage"))
    wards = _num(player.get("obs_placed")) + _num(player.get("sen_placed"))
    is_core = int(player.get("lane_role") or 0) in (1, 2, 3) and gpm >= 350
    lh_min = last_hits / minutes
    kda = (kills + assists) / max(deaths, 1)
    findings: list[Finding] = []

    def add(**kwargs: Any) -> None:
        findings.append(Finding(**kwargs))

    if deaths >= 9:
        add(
            key="survivability",
            severity=min(100, int(55 + (deaths - 9) * 7)),
            title_ru="Слишком много дорогих смертей",
            title_en="Too many costly deaths",
            evidence_ru=f"{int(deaths)} смертей за {minutes:.0f} мин. — одна каждые {minutes / deaths:.1f} мин.",
            evidence_en=f"{int(deaths)} deaths in {minutes:.0f} min — one every {minutes / deaths:.1f} min.",
            advice_ru="Перед опасным перемещением проверьте видимость ключевых соперников и ближайшую безопасную точку отхода.",
            advice_en="Before a risky move, check missing enemy cores and identify your nearest safe retreat.",
            exercise_ru="В следующих 3 матчах проговаривайте причину каждого выхода на тёмную часть карты.",
            exercise_en="For the next 3 matches, state a reason before entering an unwarded area.",
            target="Не более 7 смертей",
        )

    if is_core and lh_min < 5.5:
        add(
            key="farm",
            severity=min(95, int(60 + (5.5 - lh_min) * 9)),
            title_ru="Темп фарма ниже устойчивого",
            title_en="Farm pace is below a stable baseline",
            evidence_ru=f"{lh_min:.1f} добивания/мин и {int(gpm)} GPM на core-позиции.",
            evidence_en=f"{lh_min:.1f} last hits/min and {int(gpm)} GPM in a core role.",
            advice_ru="Планируйте следующий лагерь до завершения текущего и сокращайте пустые переходы между линиями.",
            advice_en="Choose the next camp before finishing the current one and reduce empty rotations between lanes.",
            exercise_ru="10 минут Last Hit Trainer перед каждой игровой сессией; цель — 80 добиваний к 10:00 без предметов.",
            exercise_en="Play 10 minutes of Last Hit Trainer before each session; target 80 last hits by 10:00 without items.",
            target="Не менее 6 добиваний/мин",
        )

    if deaths >= 5 and kda < 2.2:
        add(
            key="fight_selection",
            severity=min(90, int(58 + (2.2 - kda) * 12)),
            title_ru="Низкая отдача от участия в драках",
            title_en="Low impact from fight participation",
            evidence_ru=f"KDA {kda:.2f}: {int(kills)} убийств, {int(deaths)} смертей, {int(assists)} помощи.",
            evidence_en=f"{kda:.2f} KDA: {int(kills)} kills, {int(deaths)} deaths, {int(assists)} assists.",
            advice_ru="До входа в драку определяйте свою цель, опасный контроль соперника и условие выхода.",
            advice_en="Before entering a fight, identify your target, the enemy's key disable, and your exit condition.",
            exercise_ru="После каждого матча пересмотрите три смерти и отметьте: цель, информация, путь отхода.",
            exercise_en="After each match, review three deaths and note: target, information, retreat path.",
            target="KDA не ниже 2.5",
        )

    if minutes >= 25 and tower_damage < 1200:
        add(
            key="objectives",
            severity=62 if tower_damage < 400 else 48,
            title_ru="Преимущество редко превращается в объекты",
            title_en="Advantages rarely convert into objectives",
            evidence_ru=f"Всего {int(tower_damage)} урона строениям за {minutes:.0f} мин.",
            evidence_en=f"Only {int(tower_damage)} building damage in {minutes:.0f} min.",
            advice_ru="После выигранной драки сначала проверяйте башню, Рошана и вражескую территорию, а уже затем возвращайтесь к фарму.",
            advice_en="After a won fight, check towers, Roshan, and enemy territory before returning to farm.",
            exercise_ru="В трёх матчах после каждой победной драки называйте ближайший доступный объект.",
            exercise_en="For three matches, name the nearest available objective after every won fight.",
            target="Не менее 2 000 урона строениям",
        )

    if not is_core and minutes >= 25 and wards < 5:
        add(
            key="vision",
            severity=min(85, int(62 + (5 - wards) * 5)),
            title_ru="Недостаточный вклад в обзор",
            title_en="Insufficient vision contribution",
            evidence_ru=f"Установлено {int(wards)} observer/sentry ward за {minutes:.0f} мин.",
            evidence_en=f"Placed {int(wards)} observer/sentry wards in {minutes:.0f} min.",
            advice_ru="Ставьте обзор под ближайшую задачу команды: защиту зоны фарма, Рошана или давление на башню.",
            advice_en="Place vision for the team's next objective: safe farm, Roshan, or tower pressure.",
            exercise_ru="Покупайте обзор перед каждым выходом с базы и оценивайте, какую задачу он решает.",
            exercise_en="Buy vision before leaving base and name the purpose of each ward.",
            target="Не менее 7 установленных wards",
        )

    if not findings:
        add(
            key="consistency",
            severity=35,
            title_ru="Закрепите стабильность",
            title_en="Build consistency",
            evidence_ru=f"Базовые показатели ровные: KDA {kda:.2f}, {lh_min:.1f} добивания/мин, {int(gpm)} GPM.",
            evidence_en=f"Core metrics are stable: {kda:.2f} KDA, {lh_min:.1f} last hits/min, {int(gpm)} GPM.",
            advice_ru="Выберите один повторяемый ориентир и удерживайте его три матча подряд.",
            advice_en="Choose one repeatable benchmark and maintain it for three consecutive matches.",
            exercise_ru="Перед матчем запишите одну измеримую цель и проверьте её после игры.",
            exercise_en="Write down one measurable goal before the match and check it afterward.",
            target="3 стабильных матча подряд",
        )

    findings.sort(key=lambda item: item.severity, reverse=True)
    findings = findings[:5]
    score = max(20, min(95, round(82 - sum(item.severity for item in findings[:3]) / 7)))
    metrics = {
        "kills": int(kills), "deaths": int(deaths), "assists": int(assists),
        "kda": round(kda, 2), "gpm": int(gpm), "xpm": int(xpm),
        "last_hits": int(last_hits), "denies": int(denies), "lh_min": round(lh_min, 1),
        "hero_damage": int(hero_damage), "tower_damage": int(tower_damage),
        "duration_min": round(minutes, 1), "is_core": is_core,
    }
    return {
        "match_id": str(match.get("match_id") or "local"),
        "hero_id": int(player.get("hero_id") or 0),
        "player_slot": int(player.get("player_slot") or 0),
        "radiant_win": bool(match.get("radiant_win")),
        "won": bool(match.get("radiant_win")) == (int(player.get("player_slot") or 0) < 128),
        "score": score,
        "metrics": metrics,
        "findings": [asdict(item) for item in findings],
        "data_quality": "replay" if player.get("times") or player.get("purchase_log") else "summary",
    }


def build_training_plan(reports: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, dict[str, Any]] = {}
    for report in reports:
        for finding in report.get("findings", []):
            entry = counts.setdefault(finding["key"], {"count": 0, "severity": 0, "finding": finding})
            entry["count"] += 1
            entry["severity"] += finding["severity"]
    ranked = sorted(counts.values(), key=lambda x: (x["count"], x["severity"]), reverse=True)
    focus = [entry["finding"] for entry in ranked[:3]]
    return {
        "matches_analyzed": len(reports),
        "focus": focus,
        "next_review_after_matches": 3,
        "status": "ready" if reports else "needs_matches",
    }
