# オリパ比較ナビ（oripa-rank.jp）SEO記事サイト

静的サイト。`content/` のMarkdownを `build.py` が `docs/` にHTML出力し、GitHub Pagesが `docs/` を配信する。**外部依存ゼロ**（システムのpython3だけで動く）。

## 運用サイクル

```
記事を書く(content/articles/*.md) → python3 build.py → git add -A && git commit && git push
```

pushから数十秒〜数分でGitHub Pagesに反映される。

## 記事ファイルの書式

`content/articles/{slug}.md`:

```
---
title: 記事タイトル
description: メタディスクリプション（検索結果に出る120字前後）
slug: url-slug
date: 2026-08-07
updated: 2026-08-20   ← 任意。リライト時に付ける
draft: false          ← trueで非公開（ビルド対象外）
---

本文…
```

### Markdownサブセット仕様（build.pyのmd2htmlが対応する記法のみ使う）

- `## 見出し2`（目次に自動収録・3個以上で目次表示）、`### 見出し3`
- `**強調**`（黄色マーカー表示）、`[リンク](url)`、`![alt](src)`
- `- 箇条書き`、`1. 番号リスト`、`| 表 | 記法 |`、`---`（罫線）
- `:::note` 〜 `:::` = グレー注記ボックス（免責・補足用）
- `:::author` 〜 `:::` = 「筆者」コメントボックス
- `:::warn` 〜 `:::` = 赤系警告ボックス

**この仕様外の記法（ネストリスト・コードブロック等）は使わない。**

## 記事執筆ルール（景表法・ステマ規制）

- PR表記はテンプレートがサイト共通で表示（ヘッダー直下）。記事側での追加は不要
- 当選・成果を保証する断定表現は禁止（「必ず当たる」「絶対儲かる」等）
- 体験談には「個人差があります」系の注記を `:::note` で添える
- 還元率・特典等の数値はLP（lp2）で使用済みの検証済み文言に揃える
- 案件名の記載はOK（広告の指名NGは配信の話。記事への掲載は可）

## 構成

- `build.py` … ビルダー本体（sitemap.xml / feed.xml / robots.txt / CNAME / 404も生成）
- `templates/` … base.html（共通枠・PR表記・フッター免責）/ article.html（記事+筆者ボックス）/ index.html（トップ）
- `static/style.css` … 全スタイル（LPと同系のnavy×goldトーン）
- `content/articles/` … 記事Markdown
- `content/pages/` … about.md / privacy.md
- `docs/` … 生成物（GitHub Pages配信対象。手で編集しない）

## 構造化データ

記事ページに Article + BreadcrumbList のJSON-LDを自動出力。著者=オリパ研究家 ユウジ（Person）、発行者=オリパ比較ナビ（Organization）。

## ロードマップ

- [ ] Search Console接続（DNS設定後に認証・sitemap送信）
- [ ] GA4プロパティ追加（既存GA4 MCPに組み込み）
- [ ] FAQセクションのFAQPage構造化データ自動生成
- [ ] 案件カード（lp2のsvc-cardの記事用ミニ版）コンポーネント
- [ ] 記事→lp1〜lp4への内部リンク動線の型化（KWの意図別に出し分け）
