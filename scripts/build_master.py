#!/usr/bin/env python3
"""一次データ(data/raw)を統合し、アプリ用マスターデータ(data/master)を生成する。

生成物:
- regions.json     : 地区とそれに属する都道府県 (Figma地区マップから導出)
- players.json     : 選手107名 (keirin.jp由来 + 地区)
- velodromes.json  : 競輪場リンク集 (場の理解)
- races.json       : レース映像メタ (184)
- quiz_templates.json : 出題形式ひな型 (9)
- master.json      : 上記を束ねた1ファイル
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MASTER = ROOT / "data" / "master"

REGION_ORDER = ["北日本", "関東", "南関東", "中部", "近畿", "中国", "四国", "九州"]
FOOTWORK = {"逃": "逃げ", "追": "追込", "両": "両"}

# レース会場 -> WINTICKET場ページのスラッグ
VENUE_SLUG = {
    "平塚": "hiratsuka", "函館": "hakodate", "熊本": "kumamoto", "豊橋": "toyohashi",
    "西武園": "seibuen", "防府": "hofu", "武雄": "takeo", "奈良": "nara",
    "松山": "matsuyama", "伊東": "ito", "取手": "toride", "青森": "aomori",
    "宇都宮": "utsunomiya", "小田原": "odawara", "静岡": "shizuoka", "大垣": "ogaki",
}


def zen2han(s: str) -> str:
    if not s:
        return s
    table = str.maketrans("ＳＡＢ０１２３４５６７８９", "SAB0123456789")
    return s.translate(table)


def main() -> None:
    MASTER.mkdir(parents=True, exist_ok=True)
    players_raw = load("players_keirin.json")
    figma = load("figma_extract.json")
    regions_map = load("figma_regions.json")  # {snum: region}
    photos = load("player_photos.json")  # {snum: keirin写真URL}

    # --- 都道府県 -> 地区 (Figma地区マップから1:1で導出) ---
    pref2region = {}
    for p in players_raw:
        r = regions_map.get(p["id"])
        if r and p.get("prefecture"):
            pref2region[p["prefecture"]] = r

    # --- players ---
    players = []
    for p in players_raw:
        pref = p.get("prefecture")
        region = regions_map.get(p["id"]) or pref2region.get(pref)
        cls = zen2han(p.get("class"))
        players.append(
            {
                "id": p["id"],
                "name": p["name"],
                "name_kana": p.get("name_kana"),
                "birthdate": p.get("birthdate"),
                "age": p.get("age"),
                "gender": p.get("gender"),
                "prefecture": pref,
                "region": region,
                "period": p.get("period"),
                "class": cls,
                "class_next": zen2han(p.get("class_next")),
                "footwork": p.get("footwork"),
                "footwork_label": FOOTWORK.get(p.get("footwork"), p.get("footwork")),
                "home_bank": p.get("home_bank"),
                "mentor": p.get("mentor"),
                "nickname": p.get("nickname"),
                "height_cm": p.get("height_cm"),
                "weight_kg": p.get("weight_kg"),
                "points": p.get("points"),
                "stats": p.get("stats"),
                "photo": f"photos/{p['id']}.jpg",
                "photo_source": photos.get(p["id"]),
                "links": {
                    "keirin_jp": p.get("source_url"),
                    "winticket": p.get("winticket_url"),
                },
            }
        )
    players.sort(key=lambda x: (REGION_ORDER.index(x["region"]) if x["region"] in REGION_ORDER else 99, x["id"]))

    # --- regions ---
    region_prefs = {r: [] for r in REGION_ORDER}
    for pref, r in sorted(pref2region.items()):
        region_prefs[r].append(pref)
    regions = [
        {"name": r, "prefectures": region_prefs[r], "player_count": sum(1 for p in players if p["region"] == r)}
        for r in REGION_ORDER
    ]

    # --- velodromes (場の理解リンク + WINTICKET由来の諸元を統合) ---
    velodromes = figma["velodromes"]
    vdetail = {v["name"]: v for v in load("venues_detail.json")}
    # ボード名 -> WINTICKET名 の対応(差異のみ)
    VNAME = {"京都向日町": "向日町"}
    for v in velodromes:
        d = vdetail.get(VNAME.get(v["name"], v["name"]))
        if d:
            v["prefecture"] = d.get("prefecture")
            v["region"] = d.get("region")
            v["circumference_m"] = d.get("circumference_m")
            v["website"] = d.get("website")
            v["feature"] = d.get("feature")

    # --- races (WINTICKETから収集した実データ: 出走表・ダイジェスト動画つき) ---
    slug2jp = {v: k for k, v in VENUE_SLUG.items()}
    detail = load("races_detail.json")
    races = []
    for r in detail:
        races.append({
            "venue": slug2jp.get(r["venue"], r["venue"]),
            "venue_slug": r["venue"],
            "date": r.get("date"),
            "race_no": r.get("race_no"),
            "event": r.get("event"),
            "race_type": r.get("race_type"),
            "distance": r.get("distance"),
            "title": r.get("title"),
            "url": r.get("url"),
            "video": r.get("digest_video"),
            "featured": r.get("featured", []),
            "entries": r.get("entries", []),
        })

    # --- quiz templates ---
    quiz = figma["quiz_templates"]

    # --- glossary terms (KEIRIN.JP 競輪用語集) ---
    glossary = load("glossary_terms.json")
    terms = [
        {"term": t["term"], "reading": t.get("reading", ""), "desc": t["desc"]}
        for t in glossary
    ]

    dump("regions.json", regions)
    dump("players.json", players)
    dump("velodromes.json", velodromes)
    dump("races.json", races)
    dump("quiz_templates.json", quiz)
    dump("terms.json", terms)
    dump(
        "master.json",
        {
            "meta": {
                "title": "202606 高松宮記念杯競輪G1 学習マスターデータ",
                "player_count": len(players),
                "region_count": len(regions),
                "velodrome_count": len(velodromes),
                "race_count": len(races),
                "quiz_template_count": len(quiz),
                "term_count": len(terms),
                "notes": [
                    "選手データの出典: KEIRIN.JP (keirin.jp/pc/racerprofile)",
                    "地区区分はFigmaボードの地区マップ準拠(東京は関東、福井は近畿、静岡は南関東、長野/新潟は関東)",
                    "レースはFigma埋め込み(LINK_UNFURL)の実URLから収集。WINTICKETレース結果ページより出走表(車番→選手)とダイジェスト動画(HLS)を取得",
                ],
            },
            "regions": regions,
            "players": players,
            "velodromes": velodromes,
            "races": races,
            "quiz_templates": quiz,
            "terms": terms,
        },
    )

    print(f"players={len(players)} regions={len(regions)} velodromes={len(velodromes)} races={len(races)} quiz={len(quiz)}")
    print("region別人数:", {r["name"]: r["player_count"] for r in regions})


def load(name: str):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def dump(name: str, obj) -> None:
    (MASTER / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
