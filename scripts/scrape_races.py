#!/usr/bin/env python3
"""WINTICKETのレース結果ページから 出走表・ダイジェスト動画・メタ情報を収集する。

入力 : data/raw/race_index.json ([{url, players}])
出力 : data/raw/races_detail.json
HTMLは data/raw/wt_html/ にキャッシュ。
"""
import collections
import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "raw" / "race_index.json"
HTML_DIR = ROOT / "data" / "raw" / "wt_html"
OUT = ROOT / "data" / "raw" / "races_detail.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
DELAY = 1.2

ENTRY = re.compile(r'\{"number":(\d+),"raceId":"(\d+)","absent":(true|false),"playerId":"(\d+)"')


def fetch(url: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed: {url}: {last}")


def parse(h: str) -> dict:
    # タイトル(フル) と 日付・イベント・レース番号
    tm = re.search(r"<title[^>]*>([^<]*競輪[^<]*)</title>", h)
    title = tm.group(1).strip() if tm else None
    date = event = None
    race_no = None
    if title:
        dm = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title)
        if dm:
            date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        nm = re.search(r"[)）](\d{1,2})レース", title)
        if nm:
            race_no = int(nm.group(1))
        em = re.match(r"(.+?競輪)\s*(.*?)[（(]", title)
        if em:
            event = em.group(2).strip() or None
    # 出走表: raceIdごとに 車番->playerId を集計し、最も車数が多いものを採用
    groups = collections.defaultdict(dict)
    for num, rid, ab, pid in ENTRY.findall(h):
        groups[rid][int(num)] = (pid, ab == "true")
    cars = max(groups.values(), key=len) if groups else {}
    # 選手名 (playerId -> name)
    names = {}
    for a in re.finditer(r'href="/keirin/cyclist/(\d+)"[^>]*>([^<]+)</a>', h):
        names.setdefault(a.group(1), html.unescape(a.group(2)).strip())
    entries = []
    for car in sorted(cars):
        pid, absent = cars[car]
        entries.append({"car": car, "playerId": pid, "name": names.get(pid), "absent": absent})
    # ダイジェスト動画(HLS) と メタ
    dv = re.search(r'"digestVideo":"([^"]+\.m3u8)"', h)
    rt = re.search(r'"raceType3":"([^"]*)"', h)
    dist = re.search(r'"distance":(\d+)', h)
    return {
        "title": title, "date": date, "event": event, "race_no": race_no,
        "race_type": rt.group(1) if rt else None,
        "distance": int(dist.group(1)) if dist else None,
        "digest_video": dv.group(1) if dv else None,
        "entries": entries,
    }


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    races = json.loads(INDEX.read_text(encoding="utf-8"))
    out = []
    for n, r in enumerate(races, 1):
        url = r["url"]
        m = re.search(r"/keirin/([a-z]+)/raceresult/(\d+)/(\d+)/(\d+)", url)
        venue, rid, g, rn = m.group(1), m.group(2), m.group(3), m.group(4)
        cache = HTML_DIR / f"{venue}_{rid}_{g}_{rn}.html"
        if cache.exists() and cache.stat().st_size > 10000:
            h = cache.read_text(encoding="utf-8")
        else:
            h = fetch(url)
            cache.write_text(h, encoding="utf-8")
            time.sleep(DELAY)
        d = parse(h)
        d.update({"url": url, "venue": venue, "race_result_id": rid, "group": int(g),
                  "featured": r.get("players", [])})
        out.append(d)
        print(f"[{n:2}/{len(races)}] {venue} {d.get('date')} {d.get('race_no')}R "
              f"cars={len(d['entries'])} video={'Y' if d['digest_video'] else '-'} {d.get('event')}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    nocar = [x["url"] for x in out if not x["entries"]]
    novid = sum(1 for x in out if not x["digest_video"])
    print(f"\n保存: {OUT} ({len(out)}件) / 出走表なし={len(nocar)} 動画なし={novid}")
    if nocar:
        print("出走表取得失敗:", nocar)


if __name__ == "__main__":
    main()
