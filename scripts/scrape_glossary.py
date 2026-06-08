#!/usr/bin/env python3
"""KEIRIN.JP の競輪用語集(9ページ)を取得し、用語データを抽出する。

出力: data/raw/glossary_terms.json  -> [{term, reading, desc, section}]
HTMLは data/raw/glossary_html/ にキャッシュし、再取得をスキップする。

各ページの構造:
  <h2>あ</h2>
  <table> ... <tr><th><dfn>青板<span class="ruby">あおばん</span></dfn></th>
                  <td>残り3周のこと。...</td></tr> ... </table>
"""
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CACHE = RAW / "glossary_html"

BASE = "https://keirin.jp/pc/static/beginner/keirin-glossary/"
PAGES = [
    "a-o", "ka-ko", "sa-so", "ta-to", "na-no",
    "ha-ho", "ma-mo", "ya-ra-wa", "numbers-alphabets",
]
UA = "Mozilla/5.0 (epo-league glossary fetcher)"


class GlossaryParser(HTMLParser):
    """用語テーブルを 1行=1用語 にパースする。"""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self.section = ""
        self._in_th = False
        self._in_td = False
        self._in_ruby = False
        self._in_h2 = False
        self._term: list[str] = []
        self._reading: list[str] = []
        self._desc: list[str] = []
        self._h2: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "th":
            self._in_th, self._term, self._reading = True, [], []
        elif tag == "td":
            self._in_td, self._desc = True, []
        elif tag == "h2":
            self._in_h2, self._h2 = True, []
        elif tag == "span" and self._in_th and "ruby" in a.get("class", ""):
            self._in_ruby = True
        elif tag == "br" and self._in_td:
            self._desc.append(" ")

    def handle_endtag(self, tag):
        if tag == "span" and self._in_ruby:
            self._in_ruby = False
        elif tag == "th":
            self._in_th = False
        elif tag == "td":
            self._in_td = False
        elif tag == "h2":
            self._in_h2 = False
            self.section = "".join(self._h2).strip()
        elif tag == "tr":
            term = "".join(self._term).strip()
            desc = re.sub(r"\s+", " ", "".join(self._desc)).strip()
            if term and desc:
                self.rows.append({
                    "term": term,
                    "reading": "".join(self._reading).strip(),
                    "desc": desc,
                    "section": self.section,
                })
            self._term, self._reading, self._desc = [], [], []

    def handle_data(self, data):
        if self._in_ruby:
            self._reading.append(data)
        elif self._in_th:
            self._term.append(data)
        elif self._in_td:
            self._desc.append(data)
        elif self._in_h2:
            self._h2.append(data)


def fetch(page: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{page}.html"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    url = BASE + f"{page}.html"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    cached.write_text(html, encoding="utf-8")
    time.sleep(1)  # 取得間隔を空ける
    return html


def main() -> None:
    terms: list[dict] = []
    seen: set[str] = set()
    for page in PAGES:
        p = GlossaryParser()
        p.feed(fetch(page))
        new = 0
        for row in p.rows:
            key = row["term"]
            if key in seen:
                continue
            seen.add(key)
            terms.append(row)
            new += 1
        print(f"{page}: {len(p.rows)} rows ({new} new)")

    out = RAW / "glossary_terms.json"
    out.write_text(json.dumps(terms, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total terms = {len(terms)} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
