"""結果行(着順表)から 車番→選手名 を独立抽出し、races.json(entries=JSON由来)と照合する。"""
import json
import re
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
races = json.loads((ROOT / "data/master/races.json").read_text(encoding="utf-8"))
HTML = ROOT / "data/raw/wt_html"


def result_rows(h):
    """結果テーブルの各行から (車番, 選手名) を取る。
    行は着順順。車番セルと選手リンクが同一行(<tr>)内にある。"""
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        a = re.search(r'href="/keirin/cyclist/(\d+)"[^>]*>([^<]+)</a>', tr)
        if not a:
            continue
        # 車番は Bib___Wrapper クラスの要素(着順ではない)
        b = re.search(r'class="Bib___Wrapper[^"]*"[^>]*>([1-9])<', tr)
        if not b:
            continue
        car = int(b.group(1))
        out[car] = html.unescape(a.group(2)).strip()
    return out


mismatch = 0
checked = 0
for r in races:
    venue = r["venue_slug"]
    m = re.search(r"/raceresult/(\d+)/(\d+)/(\d+)", r["url"])
    rid, g, rn = m.groups()
    f = HTML / f"{venue}_{rid}_{g}_{rn}.html"
    if not f.exists():
        continue
    rows = result_rows(f.read_text(encoding="utf-8"))
    if len(rows) < 5:
        continue
    checked += 1
    ent = {e["car"]: (e["name"] or "").replace(" ", "").replace("　", "") for e in r["entries"]}
    for car, nm in rows.items():
        nm2 = nm.replace(" ", "").replace("　", "")
        if car in ent and ent[car] and ent[car] != nm2:
            mismatch += 1
            print(f"MISMATCH {r['title']} {car}番: entries={ent[car]!r} 結果行={nm2!r}")

print(f"\n照合レース数={checked} / 車番-選手 不一致={mismatch}")
