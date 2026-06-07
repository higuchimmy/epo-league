# マスターデータ スキーマ仕様

競輪学習Webアプリ（4択クイズ＋単語帳）のためのマスターデータ定義。
すべて UTF-8 / JSON。`data/master/` に出力される。

出典:
- 選手データ … KEIRIN.JP `https://keirin.jp/pc/racerprofile?snum={id}`
- 地区区分 … Figmaボード「202606 高松宮記念杯競輪G1」の地区マップ
- 競輪場リンク・レース映像・出題形式 … 同Figmaボード

---

## players.json — 選手 (107件)

| フィールド | 型 | 説明 | 例 |
|---|---|---|---|
| `id` | string | 登録番号(ゼロ埋め6桁)。winticket/keirin共通の主キー | `"013162"` |
| `name` | string | 氏名(姓 名) | `"佐藤 慎太郎"` |
| `name_kana` | string | フリガナ | `"サトウ シンタロウ"` |
| `birthdate` | string\|null | 生年月日 `YYYY-MM-DD` | `"1976-11-07"` |
| `age` | number\|null | 年齢 | `49` |
| `gender` | string | 性別 | `"男"` |
| `prefecture` | string | 登録地(府県) | `"福島県"` |
| `region` | string | 地区(8区分)。下記regionsと対応 | `"北日本"` |
| `period` | number\|null | 期別 | `78` |
| `class` | string | 級班(半角正規化) | `"S級1班"` |
| `class_next` | string\|null | 次期級班 | `"S級1班"` |
| `footwork` | string | 脚質(原文1字: 逃/追/両) | `"追"` |
| `footwork_label` | string | 脚質の表示名 | `"追込"` |
| `home_bank` | string\|null | ホームバンク | `"いわき平"` |
| `mentor` | string\|null | 師匠 | `"添田 広福"` |
| `nickname` | string\|null | ニックネーム | `null` |
| `height_cm` | number\|null | 身長(cm) | `165.0` |
| `weight_kg` | number\|null | 体重(kg) | `80.0` |
| `points` | number\|null | 今期得点 | `112.62` |
| `stats` | object | 成績。`win_rate`/`place2_rate`/`place3_rate`(文字列%)、`race_score`(number) | |
| `links.keirin_jp` | string | KEIRIN.JP選手ページ | |
| `links.winticket` | string | WINTICKET選手ページ | |

## regions.json — 地区 (8件)

8区分: 北日本 / 関東 / 南関東 / 中部 / 近畿 / 中国 / 四国 / 九州

| フィールド | 型 | 説明 |
|---|---|---|
| `name` | string | 地区名 |
| `prefectures` | string[] | 属する都道府県(本データに登場する範囲) |
| `player_count` | number | 所属選手数 |

> 注: 地区区分はFigmaボード準拠。標準的な競輪区分と一部異なる
> （**東京→関東**、福井→近畿、静岡→南関東、長野/新潟→関東）。

## velodromes.json — 競輪場リンク集 (5件)

「場の理解」表。各競輪場の学習用リンク。

| フィールド | 型 | 説明 |
|---|---|---|
| `name` | string | 競輪場名 |
| `wt_page` | string | WINTICKET 場ページ |
| `wt_column` | string | WINTICKETコラム「深掘り！競輪場！」 |
| `official_site` | string | 公式HP |
| `racers_list` | string | 場所属選手一覧 |

## races.json — レース (79件: ユニーク)

Figma埋め込み(LINK_UNFURL)の実URLから、WINTICKETレース結果ページを収集。
出走表とダイジェスト映像つき。

| フィールド | 型 | 説明 |
|---|---|---|
| `venue` | string | 競輪場(日本語) |
| `venue_slug` | string | WINTICKETスラッグ |
| `date` | string | 開催日 `YYYY-MM-DD` |
| `race_no` | number | レース番号 |
| `event` | string | 開催名(例: 日本選手権競輪) |
| `race_type` | string\|null | 決勝/予選など |
| `distance` | number\|null | 距離(m) |
| `title` | string | フルタイトル |
| `url` | string | WINTICKETレース結果ページ |
| `video` | string\|null | ダイジェスト動画(HLS m3u8)。27/79件 |
| `featured` | string[] | Figmaカードが取り上げた選手の登録番号 |
| `entries` | object[] | 出走表。`{car(車番), playerId, name, absent}` × 9 |

## quiz_templates.json — 出題形式ひな型 (9件)

| フィールド | 型 | 説明 |
|---|---|---|
| `section_id` | string | Figmaセクションid |
| `format` | string | 形式名(例: 4択形式, 映像形式) |
| `example_question` | string | 例題文 |
| `rules` | string[] | 出題ルール(付随ラベル) |
| `notes` | string[] | 付箋メモ |

---

## 既知の制約

1. レース映像の実URLは Figma埋め込み(LINK_UNFURL)の `linkUnfurlData.url` から取得済み。出走表・ダイジェスト動画もWINTICKETから収集済み。ダイジェスト動画(HLS)は27/79レースのみ提供あり。HLSはiOS Safariは直接再生可、デスクトップChrome等は不可のためWINTICKETリンクで代替。
2. 地区区分は競輪の標準区分とは一部異なる（ボード準拠）。標準区分に合わせたい場合は `build_master.py` の対応を差し替える。
3. 選手の顔写真はKEIRIN.JPから取得済み(`data/master/photos/`)。出走表に登場する非参加選手の顔写真は未取得(名前のみ)。
