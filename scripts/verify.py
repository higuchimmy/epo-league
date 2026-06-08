#!/usr/bin/env python3
"""マスターデータの正確性・整合性を網羅的に検証する。

- 内部整合性: 必須項目欠損・型・重複・件数
- 相互参照: 地区⇔都道府県の1:1、regions集計、featured⊂entries⊂選手ID、写真の実在
- 形式: 日付/URL/級班/脚質/車番 の妥当性
失敗(ERROR)と注意(WARN)を集計して出力する。
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "data" / "master"
errors, warns = [], []


def err(m): errors.append(m)
def warn(m): warns.append(m)
def load(n): return json.loads((M / n).read_text(encoding="utf-8"))


players = load("players.json")
regions = load("regions.json")
velodromes = load("velodromes.json")
races = load("races.json")
pid_set = {p["id"] for p in players}

# 競輪9地区の「標準」対応(参考・逸脱の検出用)
STD_REGION = {
    "北海道": "北日本", "青森県": "北日本", "岩手県": "北日本", "宮城県": "北日本",
    "秋田県": "北日本", "山形県": "北日本", "福島県": "北日本",
    "茨城県": "関東", "栃木県": "関東", "群馬県": "関東", "埼玉県": "関東",
    "山梨県": "関東", "新潟県": "関東", "長野県": "関東",
    "千葉県": "南関東", "東京都": "南関東", "神奈川県": "南関東", "静岡県": "南関東",
    "富山県": "中部", "石川県": "中部", "岐阜県": "中部", "愛知県": "中部", "三重県": "中部",
    "福井県": "近畿", "滋賀県": "近畿", "京都府": "近畿", "大阪府": "近畿",
    "兵庫県": "近畿", "奈良県": "近畿", "和歌山県": "近畿",
    "鳥取県": "中国", "島根県": "中国", "岡山県": "中国", "広島県": "中国", "山口県": "中国",
    "徳島県": "四国", "香川県": "四国", "愛媛県": "四国", "高知県": "四国",
    "福岡県": "九州", "佐賀県": "九州", "長崎県": "九州", "熊本県": "九州",
    "大分県": "九州", "宮崎県": "九州", "鹿児島県": "九州", "沖縄県": "九州",
}

print("=" * 60)
print("PLAYERS")
print("=" * 60)
# 件数・重複
if len(players) != 107:
    warn(f"選手数が107でない: {len(players)}")
if len(pid_set) != len(players):
    err(f"選手IDに重複: {len(players)-len(pid_set)}件")

REQUIRED = ["id", "name", "name_kana", "birthdate", "prefecture", "region",
            "period", "class", "footwork", "footwork_label"]
FOOT_OK = {"逃げ", "追込", "両"}
for p in players:
    for k in REQUIRED:
        if p.get(k) in (None, ""):
            err(f"{p.get('id')} {p.get('name')}: 必須欠損 {k}")
    if not re.fullmatch(r"\d{6}", p["id"]):
        err(f"{p['id']}: ID形式異常")
    if p.get("birthdate") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["birthdate"]):
        err(f"{p['id']} {p['name']}: 生年月日形式異常 {p['birthdate']}")
    if p.get("class") and not re.fullmatch(r"[SA]級[S12]班", p["class"]):
        err(f"{p['id']} {p['name']}: 級班形式異常 {p['class']}")
    if p.get("footwork_label") not in FOOT_OK:
        err(f"{p['id']} {p['name']}: 脚質異常 {p.get('footwork_label')}")
    # 年齢と生年月日の整合(2026年基準でおおむね)
    if p.get("age") and p.get("birthdate"):
        by = int(p["birthdate"][:4])
        approx = 2026 - by
        if abs(approx - p["age"]) > 1:
            warn(f"{p['id']} {p['name']}: 年齢と生年月日が不整合(age={p['age']} 生年={by})")

# 地区 ⇔ 都道府県 の一貫性(1つの府県が複数地区に割れていないか)
pref2reg = defaultdict(set)
for p in players:
    if p.get("prefecture") and p.get("region"):
        pref2reg[p["prefecture"]].add(p["region"])
for pref, regs in sorted(pref2reg.items()):
    if len(regs) > 1:
        err(f"都道府県 {pref} が複数地区に分裂: {regs}")

# 標準地区との差異(ボード独自=想定内の逸脱を可視化)
print("\n-- 地区区分: 標準との差異(ボード準拠の意図的逸脱) --")
for pref, regs in sorted(pref2reg.items()):
    r = next(iter(regs))
    std = STD_REGION.get(pref)
    if std and std != r:
        print(f"  {pref}: 本データ={r} / 標準={std}")
    elif std is None:
        warn(f"{pref}: 標準地区表に未登録(要確認)")

print("\n" + "=" * 60)
print("REGIONS")
print("=" * 60)
total = sum(r["player_count"] for r in regions)
if total != len(players):
    err(f"regions.player_count合計({total}) ≠ 選手数({len(players)})")
# regions.prefectures と players の地区が一致するか
reg_by_name = {r["name"]: r for r in regions}
actual_count = Counter(p["region"] for p in players)
for r in regions:
    if r["player_count"] != actual_count.get(r["name"], 0):
        err(f"{r['name']}: player_count={r['player_count']} 実集計={actual_count.get(r['name'],0)}")
    # prefectures列挙が実データと一致
    actual_prefs = {p["prefecture"] for p in players if p["region"] == r["name"]}
    if set(r["prefectures"]) != actual_prefs:
        err(f"{r['name']}: prefecturesリスト不一致 json={set(r['prefectures'])} 実={actual_prefs}")

print("\n" + "=" * 60)
print("PHOTOS")
print("=" * 60)
missing_photo = []
for p in players:
    fp = M / p["photo"]
    if not fp.exists() or fp.stat().st_size < 1000:
        missing_photo.append(p["id"])
if missing_photo:
    err(f"写真欠損/極小: {missing_photo}")
else:
    print(f"  写真OK: {len(players)}枚すべて存在")

print("\n" + "=" * 60)
print("RACES")
print("=" * 60)
vid = sum(1 for r in races if r.get("video"))
print(f"  レース {len(races)}件 / 動画 {vid}件")
for r in races:
    cars = [e["car"] for e in r.get("entries", [])]
    if not cars:
        err(f"{r.get('title')}: 出走表なし")
        continue
    if len(cars) != len(set(cars)):
        err(f"{r.get('title')}: 車番重複 {cars}")
    if max(cars) > 9 or min(cars) < 1:
        err(f"{r.get('title')}: 車番範囲異常 {sorted(cars)}")
    if len(cars) not in (7, 9):  # 通常9車、ミッドナイト等7車
        warn(f"{r.get('title')}: 出走車数={len(cars)}(7/9以外)")
    for e in r["entries"]:
        if not e.get("name") and not e.get("absent"):
            warn(f"{r.get('title')} {e['car']}番車: 選手名なし(欠場でない)")
    # featured が entries に含まれるか / 選手IDとして妥当か
    ent_ids = {e["playerId"] for e in r["entries"]}
    for fid in r.get("featured", []):
        if fid not in ent_ids:
            warn(f"{r.get('title')}: featured {fid} が出走表に不在")
    if r.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"]):
        err(f"{r.get('title')}: 日付形式異常 {r['date']}")
    if r.get("video") and not r["video"].endswith(".m3u8"):
        warn(f"{r.get('title')}: 動画URLがm3u8でない {r['video']}")
    if r.get("url") and not r["url"].startswith("https://www.winticket.jp/"):
        err(f"{r.get('title')}: URL異常 {r['url']}")

# 出走表に登場するがマスター外の選手(名前のみ提供)— 情報として
ext = set()
for r in races:
    for e in r.get("entries", []):
        if e["playerId"] not in pid_set:
            ext.add(e["playerId"])
print(f"  出走表の非マスター選手(名前のみ): {len(ext)}名")

print("\n" + "=" * 60)
print("VELODROMES")
print("=" * 60)
for v in velodromes:
    for k in ["wt_page", "wt_column", "official_site", "racers_list"]:
        u = v.get(k)
        if u and not u.startswith("http"):
            err(f"{v['name']}.{k}: URL異常 {u}")
print(f"  競輪場 {len(velodromes)}件")

print("\n" + "=" * 60)
print(f"結果: ERROR {len(errors)} 件 / WARN {len(warns)} 件")
print("=" * 60)
for e in errors:
    print("  [ERROR]", e)
for w in warns:
    print("  [WARN ]", w)
