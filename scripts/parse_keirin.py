#!/usr/bin/env python3
"""KEIRIN.JP 選手プロフィールHTMLをパースして辞書化する。"""
import html
import re

# 行ペアリングで拾う標準ラベル
_LABELS = set(
    "選手名 フリガナ 府県 生年月日 年齢 性別 登録番号 期別 級班 級班所属日 次期級班 "
    "脚質 今期得点 星座 九星 血液型 身長 体重 胸囲 太股 背筋力 肺活量 "
    "勝率 2連対率 3連対率 競走得点 ホーム回数 バック回数 総出走回数".split()
)


def _txt(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace("　", " ").strip()


def parse_keirin_html(h: str) -> dict:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [_txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        rows.append(cells)

    pair: dict = {}
    for i, r in enumerate(rows):
        if not r:
            continue
        labelish = sum(1 for c in r if c in _LABELS)
        if labelish >= 2 and i + 1 < len(rows) and len(rows[i + 1]) == len(r):
            for k, v in zip(r, rows[i + 1]):
                if k in _LABELS and k not in pair and v not in ("", "-"):
                    pair[k] = v

    # --- 行ペアで取れない項目を個別抽出 ---
    name = _first(r"登録番号</td>\s*</tr>\s*<tr>\s*<td[^>]*>([^<]+)</td>", h)
    mentor = _mentor(h)
    nickname = _block_first_value("ニックネーム", h)
    home_bank, home_track = _home_fields(h)

    return {
        "reg_no": pair.get("登録番号"),
        "name": _norm(name),
        "name_kana": pair.get("フリガナ"),
        "prefecture": pair.get("府県"),
        "birthdate": _date(pair.get("生年月日")),
        "age": _int(pair.get("年齢")),
        "gender": pair.get("性別"),
        "period": _int(pair.get("期別")),
        "class": _norm(pair.get("級班")),
        "class_next": _norm(pair.get("次期級班")),
        "footwork": pair.get("脚質"),
        "points": _float(pair.get("今期得点")),
        "height_cm": _num(pair.get("身長")),
        "weight_kg": _num(pair.get("体重")),
        "mentor": _norm(mentor),
        "nickname": _norm(nickname),
        "home_bank": home_bank,
        "home_track": home_track,
        "stats": {
            "win_rate": pair.get("勝率"),
            "place2_rate": pair.get("2連対率"),
            "place3_rate": pair.get("3連対率"),
            "race_score": _float(pair.get("競走得点")),
        },
    }


def _mentor(h: str) -> str | None:
    """師匠を正しく抽出する。

    師匠/弟子/練習グループ の3列ヘッダの直後の値行で、
    最初の値セル(=師匠)のみを対象にする。師匠が "-" の場合は None。
    弟子・練習グループの氏名を誤って拾わないよう、値セルを class で分割する。
    """
    i = h.find(">師匠</td>")
    if i < 0:
        return None
    region = h[i: i + 1800]
    # 値セルは <td class="al-c" colspan="2"> （ヘッダは tbl_header なので一致しない）
    parts = region.split('<td class="al-c" colspan="2">')
    if len(parts) < 2:
        return None
    cell = parts[1]  # 師匠の値セル(次の値セル直前まで)
    a = re.search(r'<a href="\?snum=\d+"[^>]*>([^<]+)</a>', cell)
    if a:
        return _norm(a.group(1))
    return None  # "-" 等 -> 師匠なし


def _home_fields(h: str):
    """ホームバンク と ホーム競技場（練習地）を返す。

    ヘッダ行(ホームバンク|ホーム競技場（練習地）|得意な周長|…)の直後の値行で、
    1セル目=ホームバンク, 2セル目=ホーム競技場。'-'/空は None。
    """
    i = h.find(">ホームバンク</td>")
    if i < 0:
        return None, None
    j = h.find("</tr>", i)          # ヘッダ行の終端
    k = h.find("</tr>", j + 1)      # 値行の終端
    row = h[j:k]
    cells = [_txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
    norm = lambda v: None if (not v or v == "-") else v  # noqa: E731
    bank = norm(cells[0]) if len(cells) > 0 else None
    track = norm(cells[1]) if len(cells) > 1 else None
    return bank, track


def _block_first_value(label: str, h: str) -> str | None:
    """`<td...>label</td> ... <tr> <td...>VALUE</td>` の最初の値を取る。"""
    m = re.search(re.escape(label) + r"</td>.*?<tr>\s*<td[^>]*>(.*?)</td>", h, re.S)
    if not m:
        return None
    v = _txt(m.group(1))
    return v or None


def _first(pat: str, h: str):
    m = re.search(pat, h, re.S)
    return _txt(m.group(1)) if m else None


def _norm(s):
    if not s or s == "-":
        return None
    return re.sub(r"\s+", " ", s).strip()


def _int(s):
    if not s:
        return None
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None


def _float(s):
    if not s:
        return None
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _num(s):
    if not s:
        return None
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else s


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(parse_keirin_html(open(sys.argv[1], encoding="utf-8").read()), ensure_ascii=False, indent=2))
