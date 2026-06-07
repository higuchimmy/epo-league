# epo-league — 競輪学習データ基盤

Figmaボード「202606 高松宮記念杯競輪G1」を起点に、競輪学習Webアプリ
（4択クイズ＋単語帳）のためのマスターデータを収集・整理するリポジトリ。

## ディレクトリ

```
data/
├── raw/                     # 一次データ(中間生成物)
│   ├── figjam_board.xml      # FigJamボードのエクスポート
│   ├── figma_extract.json    # Figmaから抽出(選手ID/場/レース/出題形式)
│   ├── figma_regions.json    # 地区マップから導出した {登録番号: 地区}
│   ├── keirin_html/          # KEIRIN.JPの取得HTMLキャッシュ
│   └── players_keirin.json   # 選手パース結果
└── master/                  # ★アプリが読むマスターデータ
    ├── players.json
    ├── regions.json
    ├── velodromes.json
    ├── races.json
    ├── quiz_templates.json
    └── master.json           # 全部入り

scripts/
├── extract_figma.py   # figjam_board.xml -> figma_extract.json
├── extract_regions.py # 地区マップ -> figma_regions.json
├── parse_keirin.py    # KEIRIN.JP HTMLパーサ(モジュール)
├── fetch_players.py   # 選手HTML取得 -> players_keirin.json
└── build_master.py    # 統合 -> data/master/*

docs/schema.md         # マスターデータ仕様
```

## 再生成手順

```bash
python3 scripts/extract_figma.py     # Figma一次抽出
python3 scripts/extract_regions.py   # 地区導出
python3 scripts/fetch_players.py     # 選手収集(要ネット, HTMLはキャッシュ)
python3 scripts/build_master.py      # マスター生成
```

Figmaの内容を更新したら `data/raw/figjam_board.xml` を差し替えて再実行する。
選手HTMLは `data/raw/keirin_html/` にキャッシュされ、再取得をスキップする。

## データ概要

- 選手 107名 / 地区 8区分 / 競輪場 5 / レース映像 184 / 出題形式 9種

制約・注意点は `docs/schema.md` 末尾を参照。

## 学習アプリ (app/)

依存ゼロの静的SPA。UIは Google Fonts(`Zen Kaku Gothic New` / `Oxanium`)以外の
外部依存なし。`data/master/` をfetchで読むため、**静的サーバ経由**で開く。

```bash
# リポジトリ直下で
python3 -m http.server 8765
# → http://127.0.0.1:8765/app/ を開く
```

### 機能
- **クイズ**: 4択。出題形式10種・地区しぼり・問題数を選択。A〜Dキー / Enterで操作可。正答率で級班判定。
  Figmaボードのサンプル問題に対応:
  - 顔→名前 (4択形式)、名前→顔
  - **連想(ヒント)** — 複数ヒントから選手を当てる (連想・関係図形式)
  - 地区 / 級班 / 脚質 / 出身 / ホーム / 師匠 (1問1答形式)
  - 競輪場の地区 (1問1答形式)
  - **出走表形式** — 出走表の◯番車の選手を当てる（車番カラー付き）
  - **映像形式** — ダイジェスト映像を見て◯番車の選手を当てる（HLS/m3u8。iOS Safariは直接再生、その他はWINTICKETリンク）
- **単語帳**: 全選手の要点(写真+地区/級班/脚質/出身/期別/ホーム/師匠/得点)を1ページに一覧。地区フィルタ。
- **選手図鑑**: 107名グリッド。名前/カナ検索・地区/級班フィルタ・タップで詳細モーダル。
- **レース / 競輪場**: 学習用レース索引と場リンク集。
- **レスポンシブ**: スマートフォン最適化済み(ナビ横スクロール、写真4択は2列、モーダルはボトムシート等)。

### 構成
```
app/
├── index.html       # シェル + フォント読み込み
├── css/style.css    # 夜のバンク×スピードのテーマ
└── js/
    ├── quiz.js      # クイズ/単語帳の生成ロジック(純粋関数)
    └── app.js       # 画面制御(ハッシュルーティング)
```
データ更新後(`build_master.py`再実行)はアプリの再ビルド不要。リロードで反映。
