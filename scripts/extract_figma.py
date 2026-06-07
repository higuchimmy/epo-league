#!/usr/bin/env python3
"""FigJamボード(data/raw/figjam_board.xml)から一次データを抽出する。

抽出対象:
- players_ids: 参加選手の登録番号一覧 (winticket/keirin リンクから)
- velodromes: 「場の理解」表 (競輪場ごとの各種リンク)
- races: レース映像ピックアップ (WINTICKET埋め込みカード)
- quiz_templates: サンプル問題の出題形式ひな型

出力: data/raw/figma_extract.json
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "figjam_board.xml"
OUT = ROOT / "data" / "raw" / "figma_extract.json"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")

    # --- 選手ID (winticket cyclist と keirin snum) ---
    cyclist_ids = re.findall(r"winticket\.jp/keirin/cyclist/(\d+)", text)
    snum_ids = re.findall(r"keirin\.jp/pc/racerprofile\?snum=(\d+)", text)
    player_ids = sorted(set(cyclist_ids) | set(snum_ids))

    # --- 場の理解テーブル (競輪場 -> 各リンク) ---
    velodromes = extract_velodromes(text)

    # --- レース映像カード ---
    races = extract_races(text)

    # --- サンプル問題ひな型 ---
    quiz_templates = extract_quiz_templates(text)

    result = {
        "source": "FigJam 202606 高松宮記念杯競輪G1",
        "player_ids": player_ids,
        "player_id_count": len(player_ids),
        "velodromes": velodromes,
        "races": races,
        "race_count": len(races),
        "quiz_templates": quiz_templates,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"選手ID: {len(player_ids)}")
    print(f"競輪場(場の理解): {len(velodromes)}")
    print(f"レース映像: {len(races)}")
    print(f"クイズ雛形: {len(quiz_templates)}")
    print(f"-> {OUT}")


def extract_velodromes(text: str) -> list:
    """「場の理解」表 (id=1:105) を行単位で抽出する。"""
    m = re.search(r'<table id="1:105".*?</table>', text, re.S)
    if not m:
        return []
    cells = re.findall(
        r'<table-cell[^>]*tableCellRowIndex="(\d+)"[^>]*tableCellColumnIndex="(\d+)"[^>]*>(.*?)</table-cell>',
        m.group(0),
        re.S,
    )
    grid: dict = {}
    for r, c, v in cells:
        grid.setdefault(int(r), {})[int(c)] = clean(v)
    header = grid.get(0, {})
    cols = [header.get(i, f"col{i}") for i in range(5)]
    rows = []
    for r in sorted(grid):
        if r == 0:
            continue
        row = grid[r]
        rows.append(
            {
                "name": row.get(0, ""),
                "wt_page": strip_md_link(row.get(1, "")),
                "wt_column": strip_md_link(row.get(2, "")),
                "official_site": strip_md_link(row.get(3, "")),
                "racers_list": strip_md_link(row.get(4, "")),
            }
        )
    return {"columns": cols, "rows": rows}["rows"]


def extract_races(text: str) -> list:
    """WINTICKET埋め込み (widget) から レース情報を抽出。

    注意: FigJamのテキスト出力ではレース名は約20全角字で切り詰められ、
    埋め込み動画の実URLは含まれない。取得可能な範囲のみ抽出する。
    """
    races = []
    for w in re.finditer(r'<widget id="([^"]+)" name="WINTICKET\(ウィンチケット\)".*?</widget>', text, re.S):
        block = w.group(0)
        texts = re.findall(r'<text id="[^"]+" name="([^"]*)"', block)
        labels = [clean(t) for t in texts if t and t != "winticket.jp"]
        # サブ行(2行目)が情報量が多いので優先的にパース対象にする
        raw = labels[1] if len(labels) > 1 else (labels[0] if labels else "")
        parsed = parse_race_label(raw)
        races.append(
            {
                "widget_id": w.group(1),
                "raw_title": labels[0] if labels else "",
                "raw_subtitle": labels[1] if len(labels) > 1 else "",
                "video_url": None,  # FigJam出力に埋め込みURLが含まれないため取得不可
                **parsed,
            }
        )
    return races


def parse_race_label(s: str) -> dict:
    """'函館競輪 五稜郭杯争奪戦（2026年5月17日)7レ...' から構造化。"""
    out = {"venue": None, "event": None, "date": None, "race_no": None, "truncated": s.endswith("...")}
    vm = re.match(r"(.+?)競輪\s*(.*)", s)
    if vm:
        out["venue"] = vm.group(1).strip()
        rest = vm.group(2)
        em = re.match(r"(.*?)[（(]", rest)
        if em:
            out["event"] = em.group(1).strip() or None
    dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s)
    if dm:
        out["date"] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
    nm = re.search(r"[)）](\d{1,2})\s*レ", s)
    if nm:
        out["race_no"] = int(nm.group(1))
    return out


def extract_quiz_templates(text: str) -> list:
    """サンプル問題セクション(159:1909)配下の各形式と例題を抽出。"""
    m = re.search(r'<section id="159:1909" name="サンプル問題"[^>]*>(.*?)\n  </section>', text, re.S)
    region = m.group(1) if m else text
    templates = []
    for sec in re.finditer(r'<section id="([^"]+)" name="([^"]+)"[^>]*>(.*?)</section>', region, re.S):
        sid, name, body = sec.group(1), sec.group(2), sec.group(3)
        if sid == "159:1909":
            continue
        # 例題文: 最初の <text> name
        qm = re.search(r'<text id="[^"]+" name="([^"]+)"', body)
        question = clean(qm.group(1)) if qm else ""
        # 出題ルール付箋
        notes = [clean(s) for s in re.findall(r"<sticky[^>]*>(.*?)</sticky>", body, re.S)]
        rules = [clean(s) for s in re.findall(r'<shape-with-text[^>]*name="SQUARE">(.*?)</shape-with-text>', body, re.S)]
        rules = [r for r in rules if r and r != "？"]
        templates.append(
            {
                "section_id": sid,
                "format": name,
                "example_question": question,
                "rules": rules,
                "notes": notes,
            }
        )
    return templates


def strip_md_link(s: str) -> str:
    s = clean(s)
    m = re.match(r"\[(.*?)\]\((.*?)\)", s)
    if m:
        return m.group(2)
    return s


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("　", " ").strip()


if __name__ == "__main__":
    main()
