#!/usr/bin/env python3
"""Собирает research/portal.html из portal.template.html:
   - встраивает иллюстрации как data URI (CSP артефактов режет внешние картинки)
   - генерирует строки тепловой карты и пересчитывает итоги
Запуск: python3 research/build_portal.py
"""
import base64
import csv
import pathlib
import sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = pathlib.Path(__file__).parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"

IMAGES = {
    "IMG_UNCERTAINTY": "web_ltplos2uri7elexjzjo6k3krzw8kgs41.png",
    "IMG_EV":          "web_mf02rpmkafrhyx12kzsgcca1fu456x6k.png",
    "IMG_PESTEL":      "web_ajhpkfnlar8x41usr2syt6uu1a2jb2dv.png",
    "IMG_HEATMAP":     "web_g6x614w7z8jtvzppvsjb96nsvxsh5h8g.png",
    "IMG_MATRIX":      "web_yo2g6fg4635ih6w3hycm2flamexz5gti.png",
    # Trendradar (4strat) — снимки интерфейса, версия 3.9.1
    "IMG_4S_RATE":             "web_4strat_rate.png",
    "IMG_4S_CRITERIA_FILLED":  "web_4strat_criteria_filled.png",
    "IMG_4S_CALC_ALGO":        "web_4strat_calc_algo.png",
    "IMG_4S_CALC_WEIGHTS":     "web_4strat_calc_weights.png",
    "IMG_4S_PROOF":            "web_4strat_proof.png",
    "IMG_4S_ORGANIZE":         "web_4strat_organize.png",
    "IMG_4S_LINK":             "web_4strat_link.png",
    "IMG_4S_RADAR":            "web_4strat_radar.png",
    "IMG_4S_MONITOR":          "web_4strat_monitor.png",
    "IMG_4S_TRENDING":         "web_4strat_trending.png",
    # Trendtracker — сайт продукта, PDF ROESI, снимки интерфейса
    "IMG_TT_ROESI":     "web_tt_roesi_actions.jpg",
    "IMG_TT_STEPS":     "web_tt_six_steps.jpg",
    "IMG_TT_LAYERS":    "web_tt_three_layers.jpg",
    "IMG_TT_DISCOVER":  "web_tt_discover_agentic_ai.jpg",
    "IMG_TT_FORECAST":  "web_tt_forecast_card.jpg",
    "IMG_TT_TABLE":     "web_tt_trend_board_table.jpg",
    "IMG_TT_RADAR":     "web_tt_radar.jpg",
    "IMG_TT_TRENDING":  "web_tt_trending_now_soon.jpg",
    "IMG_TT_FNB":       "web_tt_discover_ai_fnb.jpg",
    "IMG_TT_LEVELS":    "web_tt_trend_levels.jpg",
    "IMG_TT_CONTEXT":   "web_tt_context_setup.jpg",
    # Trend Hunter — карточка идеи и страница методологии TIE
    "IMG_TH_SCORE":     "web_th_score_block.png",
    "IMG_TH_HERO":      "web_th_tie_hero.png",
    "IMG_TH_FACTORS":   "web_th_tie_five_factors.png",
    "IMG_TH_STAGES":    "web_th_tie_three_stages.png",
    "IMG_TH_ARCHIVE":   "web_th_archive_2016_stats.png",
    # Emergence Score — Porter, Garner, Carley, Newman (2019), рисунки из статьи
    "IMG_ES_PANEL":     "web_escore_ei_panel.jpg",
    "IMG_ES_PLAYERS":   "web_escore_players_scatter.jpg",
    # Карты KEM и KIM — метод Yoon, разбор по реализации Ebadi и соавторов (2022)
    "IMG_YOON_PIPELINE": "web_yoon_pipeline.jpg",
    "IMG_YOON_CUBE":     "web_yoon_hiltunen_cube.jpg",
    # BERTrend — RTE France (2024)
    "IMG_BT_ARCH":      "web_bertrend_architecture.jpg",
    "IMG_BT_UI":        "web_bertrend_ui.jpg",
}

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

# Данные тепловой карты, перенесённые с иллюстрации 4 статьи SBS.
# сила влияния: масса, частота, эконом. эффект, импульс, связность
# неопределённость: данные, технологии, регуляторика, поведение, сценарии
TRENDS = [
    ("T01", "Care / старение",              [9, 9, 9, 9, 9], [0, 1, 3, 1, 1]),
    ("T02", "Жильё",                        [9, 9, 9, 9, 9], [1, 1, 3, 1, 1]),
    ("T03", "Мобильность / 15 минут",       [9, 9, 9, 9, 9], [1, 1, 3, 3, 1]),
    ("T04", "Wellness / рекреация",         [3, 9, 9, 3, 9], [3, 1, 3, 3, 3]),
    ("T05", "Климат / ЖКХ / энергия",       [9, 9, 9, 9, 9], [1, 3, 3, 1, 3]),
    ("T06", "Цифровой город / ИИ / доверие",[9, 9, 9, 9, 9], [3, 3, 9, 3, 3]),
    ("T07", "Сообщества / одиночество",     [9, 3, 3, 3, 9], [3, 1, 1, 3, 3]),
    ("T08", "Циркулярность / ремонт",       [3, 3, 3, 3, 3], [3, 1, 3, 3, 3]),
    ("T09", "Безопасность / навигация",     [9, 3, 3, 3, 9], [1, 3, 3, 1, 1]),
    ("T10", "Локальная занятость / навыки", [9, 3, 9, 3, 9], [3, 3, 3, 3, 3]),
    ("T11", "Гибридное одиночество",        [9, 9, 9, 3, 9], [9, 9, 9, 9, 9]),
]

# итоги, напечатанные в статье — для сверки с пересчётом
PUBLISHED = {
    "T01": (9, 1.2), "T02": (9, 1.4), "T03": (9, 1.8), "T04": (6.6, 2.6),
    "T05": (9, 2.2), "T06": (9, 4.2), "T07": (5.4, 2.2), "T08": (3, 2.6),
    "T09": (5.4, 1.8), "T10": (6.6, 3.0), "T11": (7.8, 9.0),
}

SILA_NAMES = ["Масса", "Частота", "Экономический эффект", "Импульс", "Связность"]
NEOPR_NAMES = ["Данные", "Технологии", "Регуляторика", "Поведение", "Сценарии"]


def fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def build_rows() -> tuple[str, int, int]:
    rows, ok, total = [], 0, 0
    for tid, name, sila, neopr in TRENDS:
        s_avg = sum(sila) / 5
        n_avg = sum(neopr) / 5
        p_s, p_n = PUBLISHED[tid]
        for calc, pub in ((s_avg, p_s), (n_avg, p_n)):
            total += 1
            if abs(calc - pub) < 1e-9:
                ok += 1
            else:
                print(f"  РАСХОЖДЕНИЕ {tid}: посчитано {calc}, в статье {pub}", file=sys.stderr)

        cells = [f'<td class="id">{tid}</td>', f'<td class="lbl">{name}</td>']
        for v, pname in zip(sila, SILA_NAMES):
            cells.append(f'<td class="a{v}" title="{name} — {pname}: {v}">{v}</td>')
        cells.append(f'<td class="a{9 if s_avg >= 7 else 3 if s_avg >= 4 else 1} tot" '
                     f'title="Гравитационность = сумма пяти параметров / 5">{fmt(s_avg)}</td>')
        cells.append('<td class="gap"></td>')
        for v, pname in zip(neopr, NEOPR_NAMES):
            cells.append(f'<td class="b{v}" title="{name} — неопределённость, {pname}: {v}">{v}</td>')
        cells.append(f'<td class="b{9 if n_avg >= 7 else 3 if n_avg >= 3 else 1} tot" '
                     f'title="Неопределённость = сумма пяти параметров / 5">{fmt(n_avg)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(rows), ok, total


# Восстановленная формула публичного балла Trend Hunter:
# Score = (Popularity + Activity + Freshness) / 3 / 10, округление до 0,1.
# Проверяется при каждой сборке по выгрузке data/trendhunter_scores.csv (95 карточек).
TH_SHOWCASE = [
    "centauri-60-asuka-edition", "projector-5-pro", "chatgpt-group-chats",
    "the-grinch-meal", "hello-kitty-x-yugioh", "clerri-bridge",
    "spooky-stuff-you-love", "austin-post",
]


def th_score(pop: int, act: int, fresh: int) -> float:
    mean = (pop + act + fresh) / 3 / 10
    return float(Decimal(str(mean)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def build_th_rows() -> tuple[str, int, int]:
    """Сверяет восстановленную формулу со всеми выгруженными баллами,
    возвращает строки показательной таблицы для вкладки Trend Hunter."""
    path = DATA / "trendhunter_scores.csv"
    records, ok, total = {}, 0, 0
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            pop, act, fresh = int(r["popularity"]), int(r["activity"]), int(r["freshness"])
            published, pred = float(r["score"]), th_score(pop, act, fresh)
            total += 1
            if abs(published - pred) < 1e-9:
                ok += 1
            else:
                print(f"  РАСХОЖДЕНИЕ {r['slug']}: на сайте {published}, "
                      f"по формуле {pred}", file=sys.stderr)
            records[r["slug"]] = (pop, act, fresh, published, pred, r["published"])

    rows = []
    for slug in TH_SHOWCASE:
        if slug not in records:
            print(f"нет наблюдения {slug} в выгрузке", file=sys.stderr)
            return "", 0, 1
        pop, act, fresh, published, pred, date = records[slug]
        exact = (pop + act + fresh) / 3 / 10
        rows.append(
            "<tr>"
            f'<td class="lbl">{slug}</td>'
            f"<td>{date}</td>"
            f'<td class="num">{pop}</td><td class="num">{act}</td>'
            f'<td class="num">{fresh}</td>'
            f'<td class="num">{exact:.2f}</td>'
            f'<td class="num tot">{pred:.1f}</td>'
            f'<td class="num tot">{published:.1f}</td>'
            "</tr>"
        )
    return "\n".join(rows), ok, total


def main() -> int:
    template = (ROOT / "portal.template.html").read_text(encoding="utf-8")

    rows, ok, total = build_rows()
    print(f"тепловая карта: пересчёт сошёлся с публикацией {ok} из {total}")
    if ok != total:
        print("СБОРКА ОСТАНОВЛЕНА: числа не сходятся", file=sys.stderr)
        return 1
    html = template.replace("{{HEATMAP_ROWS}}", rows)

    th_rows, th_ok, th_total = build_th_rows()
    print(f"Trend Hunter: формула среднего трёх сошлась с сайтом {th_ok} из {th_total}")
    if th_ok != th_total or not th_rows:
        print("СБОРКА ОСТАНОВЛЕНА: балл Trend Hunter не воспроизводится", file=sys.stderr)
        return 1
    html = html.replace("{{TH_ROWS}}", th_rows)
    html = html.replace("{{TH_CHECK}}", f"{th_ok} из {th_total}")

    for key, fname in IMAGES.items():
        path = ASSETS / fname
        if not path.exists():
            print(f"нет файла {path}", file=sys.stderr)
            return 1
        mime = MIME.get(path.suffix.lower())
        if mime is None:
            print(f"неизвестный тип картинки: {path.name}", file=sys.stderr)
            return 1
        uri = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace("{{" + key + "}}", uri)
        print(f"встроено {fname}: {len(uri)/1024:.0f} КБ в base64")

    if "{{" in html:
        leftover = html[html.index("{{"):html.index("{{") + 40]
        print(f"остался незаполненный плейсхолдер: {leftover}", file=sys.stderr)
        return 1

    out = ROOT / "portal.html"
    out.write_text(html, encoding="utf-8")
    print(f"собрано: {out} — {len(html.encode())/1024/1024:.2f} МБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
