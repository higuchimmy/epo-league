#!/usr/bin/env python3
"""figma_extract.json の選手ID一覧をもとに KEIRIN.JP からプロフィールを取得・パースする。

- 生HTMLは data/raw/keirin_html/{id}.html にキャッシュ (再取得を避ける)
- パース結果は data/raw/players_keirin.json に保存
- 礼儀的に 1.2秒のディレイを入れ、失敗は最大3回リトライ
"""
import json
import time
import urllib.request
from pathlib import Path

from parse_keirin import parse_keirin_html

ROOT = Path(__file__).resolve().parent.parent
EXTRACT = ROOT / "data" / "raw" / "figma_extract.json"
HTML_DIR = ROOT / "data" / "raw" / "keirin_html"
OUT = ROOT / "data" / "raw" / "players_keirin.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
DELAY = 1.2


def fetch(url: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed: {url}: {last}")


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    ids = json.loads(EXTRACT.read_text(encoding="utf-8"))["player_ids"]
    players = []
    for n, pid in enumerate(ids, 1):
        cache = HTML_DIR / f"{pid}.html"
        if cache.exists():
            h = cache.read_text(encoding="utf-8")
        else:
            url = f"https://keirin.jp/pc/racerprofile?snum={pid}"
            h = fetch(url)
            cache.write_text(h, encoding="utf-8")
            time.sleep(DELAY)
        rec = parse_keirin_html(h)
        rec["id"] = pid
        rec["source_url"] = f"https://keirin.jp/pc/racerprofile?snum={pid}"
        rec["winticket_url"] = f"https://www.winticket.jp/keirin/cyclist/{pid}"
        players.append(rec)
        print(f"[{n:3}/{len(ids)}] {pid} {rec.get('name')} / {rec.get('class')} / {rec.get('prefecture')}")
    OUT.write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8")
    miss = [p["id"] for p in players if not p.get("name")]
    print(f"\n保存: {OUT}  ({len(players)}件)")
    if miss:
        print(f"⚠ name未取得: {miss}")


if __name__ == "__main__":
    main()
