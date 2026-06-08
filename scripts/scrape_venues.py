#!/usr/bin/env python3
"""WINTICKETの競輪場ページ埋め込みJSONから全競輪場の諸元を取得する。

任意の場ページ(例: /keirin/kishiwada/)に全競輪場の venues 配列が含まれる。
- name / regionId / address / websiteUrl / bankFeature(周長・みなし直線・脚質傾向の説明文)
bankFeatureから 周長(m) と みなし直線距離(m) を抽出する。

出力: data/raw/venues_detail.json
HTMLは data/raw/venue_html/ にキャッシュ。
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "data" / "raw" / "venue_html"
OUT = ROOT / "data" / "raw" / "venues_detail.json"
SRC = "https://www.winticket.jp/keirin/kishiwada/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_array(h: str, key: str):
    """h 内の "key":[ ... ] を括弧バランスで取り出して json.loads する。"""
    i = h.find(f'"{key}":[')
    if i < 0:
        return None
    start = h.index("[", i)
    depth = 0
    for j in range(start, len(h)):
        c = h[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(h[start:j + 1])
    return None


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    cache = HTML_DIR / "venues.html"
    if cache.exists() and cache.stat().st_size > 10000:
        h = cache.read_text(encoding="utf-8")
    else:
        h = fetch(SRC)
        cache.write_text(h, encoding="utf-8")

    regions = {r["id"]: r["name"] for r in (extract_array(h, "regions") or [])}
    venues = extract_array(h, "venues") or []
    out = []
    pref_re = re.compile(r"(北海道|東京都|京都府|大阪府|.{2,3}県)")
    for v in venues:
        feat = v.get("bankFeature", "") or ""
        # 周長: 全角ｍ/半角m 両対応
        circ = re.search(r"周長\s*(\d{3})\s*[mｍ]", feat)
        addr = v.get("address", "") or ""
        pref = pref_re.match(addr)
        out.append({
            "name": v.get("name"),
            "abbr": v.get("name1"),
            "region": regions.get(v.get("regionId")),
            "address": addr or None,
            "prefecture": pref.group(1) if pref else None,
            "website": v.get("websiteUrl"),
            "circumference_m": int(circ.group(1)) if circ else None,
            "feature": feat or None,
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    kinki = [x for x in out if x["region"] == "近畿"]
    print(f"全場: {len(out)} / 近畿: {len(kinki)}")
    for x in kinki:
        print(f"  {x['name']} {x['prefecture']} 周長{x['circumference_m']}m")


if __name__ == "__main__":
    main()
