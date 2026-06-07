#!/usr/bin/env python3
"""Figmaの地区マップ(section 447:2315)から 選手登録番号 -> 地区 を導出する。

ロジック:
- 地区ラベル(テキスト付きSQUARE)とコンテナ(空SQUARE)を抽出
- connectorで コンテナ->地区ラベル を対応付け
- 未接続コンテナは重心が最も近い接続済みコンテナの地区を継承(オーバーフロー列対応)
- 各選手カード(cyclist URLを持つtext)の(x,y)を内包するコンテナの地区を割り当て

出力: data/raw/figma_regions.json  ({snum: region})
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "figjam_board.xml"
OUT = ROOT / "data" / "raw" / "figma_regions.json"

REGION_CANON = {
    "北日本（北海道）": "北日本",
    "北日本": "北日本",
    "関東": "関東",
    "南関東": "南関東",
    "中部": "中部",
    "近畿": "近畿",
    "中国": "中国",
    "四国": "四国",
    "九州": "九州",
    "九州（沖縄）": "九州",
}


def main() -> None:
    t = SRC.read_text(encoding="utf-8")
    sec = re.search(r'<section id="447:2315".*?\n  </section>', t, re.S).group(0)

    shapes = {}
    for m in re.finditer(
        r'<shape-with-text id="([^"]+)" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" name="SQUARE">([^<]*)</shape-with-text>',
        sec,
    ):
        sid, x, y, w, h, txt = m.groups()
        shapes[sid] = {
            "txt": txt.replace("\n", "").strip(),
            "x": float(x), "y": float(y), "w": float(w), "h": float(h),
        }

    labels = {sid: s for sid, s in shapes.items() if s["txt"] in REGION_CANON}
    containers = {sid: s for sid, s in shapes.items() if not s["txt"]}

    conns = re.findall(r'connectorStart="([^"]+)"[^>]*connectorEnd="([^"]+)"', sec)
    container_region = {}
    for a, b in conns:
        if a in containers and b in labels:
            container_region[a] = REGION_CANON[labels[b]["txt"]]
        elif b in containers and a in labels:
            container_region[b] = REGION_CANON[labels[a]["txt"]]

    # 未接続コンテナ -> 最寄り接続済みコンテナの地区
    def centroid(s):
        return (s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)

    for sid, s in containers.items():
        if sid in container_region:
            continue
        cx, cy = centroid(s)
        best, bestd = None, 1e18
        for tid in container_region:
            tx, ty = centroid(containers[tid])
            d = (cx - tx) ** 2 + (cy - ty) ** 2
            if d < bestd:
                best, bestd = container_region[tid], d
        container_region[sid] = best

    # 選手カード(cyclist URL付き text) を内包コンテナへ
    region_of = {}
    for m in re.finditer(
        r'<text id="[^"]+" name="https://www\.winticket\.jp/keirin/cyclist/(\d+)[^"]*" x="([\d.]+)" y="([\d.]+)"',
        sec,
    ):
        snum, x, y = m.group(1), float(m.group(2)), float(m.group(3))
        hit = None
        for sid, s in containers.items():
            if s["x"] <= x <= s["x"] + s["w"] and s["y"] <= y <= s["y"] + s["h"]:
                hit = container_region.get(sid)
                break
        if hit and snum not in region_of:
            region_of[snum] = hit

    OUT.write_text(json.dumps(region_of, ensure_ascii=False, indent=2), encoding="utf-8")
    import collections
    print("地区割当済み選手:", len(region_of))
    print(collections.Counter(region_of.values()))
    print("->", OUT)


if __name__ == "__main__":
    main()
