#!/usr/bin/env python3
"""オリパ情報局（oripa-rank.jp）静的サイトビルダー。

外部依存ゼロ。content/ の Markdown（サブセット）を templates/ で HTML 化し
docs/ に出力する。GitHub Pages は docs/ を配信する。

使い方:
    python3 build.py        # 全ページ生成（docs/を作り直す）

Markdownサブセット仕様は README.md を参照。
"""
import os, re, shutil, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
TPL = os.path.join(ROOT, "templates")
OUT = os.path.join(ROOT, "docs")
SITE = "https://oripa-rank.jp"
SITE_NAME = "オリパ情報局"
AUTHOR = "オリパ研究家 ユウジ"

# 計測。空文字なら該当タグを出力しない。
# GA4_ID はSEOサイト専用の測定ID（LP用プロパティとは分離する）。
# GSC_VERIFY はSearch Consoleの「HTMLタグ」認証トークン（content="..." の中身だけ）。
# docs/ は毎回作り直すため、GSCのHTMLファイル認証ではなくmetaタグ認証を使う。
GA4_ID = "G-8N4RWW1SGW"
GSC_VERIFY = ""   # Search Consoleは別方式で認証済みのため空のまま


# ---------- frontmatter ----------

def parse_front(src):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", src, re.S)
    if not m:
        raise ValueError("frontmatterがありません")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


# ---------- markdown subset ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md2html(md):
    """必要最小限のMarkdown変換。対応: h2/h3/p/ul/ol/table/hr/画像/リンク/強調/注記ブロック"""
    out, toc = [], []
    lines = md.split("\n")
    i, in_ul, in_ol, in_tbl, in_note = 0, False, False, False, None

    def close_lists():
        nonlocal in_ul, in_ol, in_tbl
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False
        if in_tbl: out.append("</tbody></table></div>"); in_tbl = False

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith(":::"):  # :::note / :::author / :::warn / :::cta / :::
            close_lists()
            tag = s[3:].strip()
            if tag == "cta":
                # :::cta 内の2行（キャッチ / [ボタン文言](URL)）をLP誘導ボックスに変換
                body = []
                i += 1
                while i < len(lines) and lines[i].strip() != ":::":
                    if lines[i].strip():
                        body.append(lines[i].strip())
                    i += 1
                if len(body) >= 2:
                    m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", body[1])
                    if m:
                        out.append(f'<a class="cta-lp" href="{m.group(2)}">'
                                   f'<span class="c-catch">{inline(body[0])}</span>'
                                   f'<span class="c-btn">{html.escape(m.group(1))}</span></a>')
                i += 1; continue
            if tag == "gallery":
                # :::gallery 内の各行「画像パス|alt」をグリッド表示にする（当選報告の並べ置き用）
                i += 1
                cells = []
                while i < len(lines) and lines[i].strip() != ":::":
                    row = lines[i].strip()
                    if row:
                        parts = [p.strip() for p in row.split("|")]
                        src = html.escape(parts[0])
                        alt = html.escape(parts[1]) if len(parts) > 1 else ""
                        cells.append(f'<figure><img src="{src}" alt="{alt}" loading="lazy"></figure>')
                    i += 1
                if cells:
                    out.append('<div class="gallery">' + "".join(cells) + "</div>")
                i += 1; continue
            if tag == "code":
                # :::code 内の各行「アプリ名|コード|補足(任意)」をコピーボタン付きボックスに変換
                i += 1
                while i < len(lines) and lines[i].strip() != ":::":
                    row = lines[i].strip()
                    if row:
                        parts = [p.strip() for p in row.split("|")]
                        app = html.escape(parts[0])
                        code = html.escape(parts[1]) if len(parts) > 1 else ""
                        memo = inline(parts[2]) if len(parts) > 2 else ""
                        out.append(
                            f'<div class="ccopy" data-app="{app}">'
                            f'<p class="cc-app">{app}の招待コード</p>'
                            f'<div class="cc-row">'
                            f'<span class="cc-code">{code}</span>'
                            f'<button class="cc-btn" type="button" onclick="oripaCopy(this)">'
                            f'<span class="cc-label">コピー</span></button>'
                            f'</div>'
                            + (f'<p class="cc-memo">{memo}</p>' if memo else "")
                            + '</div>')
                    i += 1
                i += 1; continue
            if in_note:
                out.append("</div></div>" if in_note == "author" else "</div>")
                in_note = None
            elif tag in ("note", "warn", "author"):
                if tag == "author":
                    # LPと同じ見せ方: 丸アイコン＋吹き出し
                    out.append('<div class="box box-author">'
                               '<img class="ba-icon" src="/static/img/author.webp" alt="筆者ユウジ" width="96" height="96" loading="lazy">'
                               '<div class="ba-bubble"><p class="ba-name">筆者ユウジ</p>')
                else:
                    out.append(f'<div class="box box-{tag}">')
                in_note = tag
            i += 1; continue
        if s.startswith("## "):
            close_lists()
            t = s[3:]
            hid = f"h{sum(1 for lv, _, _ in toc if lv == 2) + 1}"
            toc.append((2, hid, t))
            out.append(f'<h2 id="{hid}">{inline(t)}</h2>')
        elif s.startswith("### "):
            close_lists()
            t = s[4:]
            # 直近のH2に紐づく連番でidを振る（h3-2-1 = 2番目のH2配下の1本目）
            parent = sum(1 for lv, _, _ in toc if lv == 2) or 1
            n = sum(1 for lv, i, _ in toc if lv == 3 and i.startswith(f"h3-{parent}-")) + 1
            hid = f"h3-{parent}-{n}"
            toc.append((3, hid, t))
            out.append(f'<h3 id="{hid}">{inline(t)}</h3>')
        elif s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if re.match(r"^[\s|:-]+$", s):
                i += 1; continue
            if not in_tbl:
                out.append('<div class="tbl-wrap"><table><thead><tr>'
                           + "".join(f"<th>{inline(c)}</th>" for c in cells)
                           + "</tr></thead><tbody>")
                in_tbl = True
            else:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        elif s.startswith("- "):
            if in_tbl: out.append("</tbody></table></div>"); in_tbl = False
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(s[2:])}</li>")
        elif re.match(r"^\d+\. ", s):
            if in_tbl: out.append("</tbody></table></div>"); in_tbl = False
            if not in_ol: out.append("<ol>"); in_ol = True
            item = re.sub(r"^\d+\. ", "", s)
            out.append(f"<li>{inline(item)}</li>")
        elif s == "---":
            close_lists(); out.append("<hr>")
        elif s.startswith("!["):
            close_lists()
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s)
            if m:
                out.append(f'<figure><img src="{m.group(2)}" alt="{html.escape(m.group(1))}" loading="lazy"></figure>')
        elif s == "":
            close_lists()
        else:
            close_lists()
            out.append(f"<p>{inline(s)}</p>")
        i += 1
    close_lists()
    if in_note:
        out.append("</div></div>" if in_note == "author" else "</div>")
    return "\n".join(out), toc


# ---------- templates ----------

def tpl(name):
    with open(os.path.join(TPL, name), encoding="utf-8") as f:
        return f.read()


def render(template, **kw):
    for k, v in kw.items():
        template = template.replace("{{" + k + "}}", v)
    return template


def css_version():
    import hashlib
    with open(os.path.join(ROOT, "static", "style.css"), "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


CSSV = None


def head_tags():
    """GA4とSearch Console認証タグ。IDが未設定なら何も出さない。"""
    out = []
    if GSC_VERIFY:
        out.append(f'<meta name="google-site-verification" content="{GSC_VERIFY}">')
    if GA4_ID:
        # ローカルプレビュー(localhost:8775)のヒットは送らない。gtag.js自体が
        # ga-disable-<測定ID> を見て送信を止めるので、IP除外設定より確実。
        out.append(f"<script>if(['localhost','127.0.0.1'].includes(location.hostname))"
                   f"window['ga-disable-{GA4_ID}']=true;</script>")
        out.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>')
        out.append("<script>window.dataLayer=window.dataLayer||[];"
                   "function gtag(){dataLayer.push(arguments);}"
                   "gtag('js',new Date());"
                   f"gtag('config','{GA4_ID}');</script>")
    return "\n".join(out)


def page(body, *, title, description, path, extra_head="", h1_in_body=True):
    global CSSV
    if CSSV is None:
        CSSV = css_version()
    if "og:image" not in extra_head:
        extra_head = f'<meta property="og:image" content="{SITE}/static/img/logo.png">\n' + extra_head
    return render(tpl("base.html"),
                  title=title, description=html.escape(description, quote=True),
                  canonical=SITE + path, body=body, extra_head=extra_head,
                  analytics=head_tags(),
                  year=str(datetime.date.today().year), site=SITE_NAME, cssv=CSSV)


# ---------- articles ----------

def jp_date(iso):
    y, m, d = iso.split("-")
    return f"{y}年{int(m)}月{int(d)}日"


def article_jsonld(meta, path):
    upd = meta.get("updated", meta["date"])
    return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": {jstr(meta["title"])},
  "description": {jstr(meta["description"])},
  "datePublished": "{meta["date"]}",
  "dateModified": "{upd}",
  "author": {{"@type": "Person", "name": "{AUTHOR}", "url": "{SITE}/about/"}},
  "publisher": {{"@type": "Organization", "name": "{SITE_NAME}"}},
  "mainEntityOfPage": "{SITE}{path}"
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{"@type": "ListItem", "position": 1, "name": "ホーム", "item": "{SITE}/"}},
    {{"@type": "ListItem", "position": 2, "name": {jstr(meta["title"])}, "item": "{SITE}{path}"}}
  ]
}}
</script>'''


def jstr(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def faq_jsonld(body_md):
    """「## よくある質問」配下の「### 質問」＋回答段落から FAQPage JSON-LD を生成。"""
    # 見出しは「〜のよくある質問」のように主題語が付くので部分一致で拾う
    # 見出しは「〜のよくある質問」のように主題語が付くので部分一致で拾う。
    # re.S下では . が改行にもマッチするため、見出し行の一致は [^\n] を使う
    m = re.search(r"^## [^\n]*よくある質問[^\n]*\n(.*?)(?=^## |\Z)", body_md, re.S | re.M)
    if not m:
        return ""
    pairs = re.findall(r"^### (.+?)\n(.*?)(?=^### |\Z)", m.group(1), re.S | re.M)
    if not pairs:
        return ""
    items = []
    for q, a in pairs:
        a_txt = re.sub(r":::.*?(:::|$)", "", a, flags=re.S)          # ボックスは除外
        a_txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", a_txt)        # リンクはテキスト化
        a_txt = re.sub(r"[*#|>-]", "", a_txt)
        a_txt = " ".join(a_txt.split())
        items.append(f'{{"@type": "Question", "name": {jstr(q.strip())}, '
                     f'"acceptedAnswer": {{"@type": "Answer", "text": {jstr(a_txt)}}}}}')
    return ('<script type="application/ld+json">\n{"@context": "https://schema.org", '
            '"@type": "FAQPage", "mainEntity": [' + ", ".join(items) + ']}\n</script>')


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"))

    # 1周目: 全記事のメタを集める（関連記事ブロックに他記事の情報が要るため2パス構成）
    adir = os.path.join(CONTENT, "articles")
    parsed = []
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith(".md"):
            continue
        meta, body_md = parse_front(open(os.path.join(adir, fn), encoding="utf-8").read())
        if meta.get("draft", "false") == "true":
            continue
        parsed.append((meta, body_md))
    by_slug = {m["slug"]: m for m, _ in parsed}

    def related_block(meta):
        """関連記事。frontmatterの related: で明示、なければ新しい順に他記事を最大3本。"""
        names = [s.strip() for s in meta.get("related", "").split(",") if s.strip()]
        picks = [by_slug[s] for s in names if s in by_slug and s != meta["slug"]]
        if not picks:
            others = [m for m, _ in parsed if m["slug"] != meta["slug"]]
            picks = sorted(others, key=lambda m: m["date"], reverse=True)[:3]
        if not picks:
            return ""
        li = "".join(
            f'<li><a href="/articles/{m["slug"]}/">{html.escape(m["title"])}</a></li>'
            for m in picks)
        return f'<nav class="related"><p class="rel-title">あわせて読みたい</p><ul>{li}</ul></nav>'

    articles = []
    for meta, body_md in parsed:
        body_html, toc = md2html(body_md)
        path = f"/articles/{meta['slug']}/"
        toc_html = ""
        if sum(1 for lv, _, _ in toc if lv == 2) >= 3:
            items, open_sub = [], False
            for lv, hid, t in toc:
                link = f'<a href="#{hid}">{html.escape(t)}</a>'
                if lv == 2:
                    if open_sub:
                        items.append("</ul></li>"); open_sub = False
                    items.append(f"<li>{link}")
                    items.append("__CLOSE__")
                else:
                    if not open_sub:
                        if items and items[-1] == "__CLOSE__":
                            items.pop()
                        items.append("<ul>"); open_sub = True
                    items.append(f"<li>{link}</li>")
            if open_sub:
                items.append("</ul></li>")
            body = "".join(x if x != "__CLOSE__" else "</li>" for x in items)
            toc_html = f'<nav class="toc"><p class="toc-title">目次</p><ol>{body}</ol></nav>'
        upd = meta.get("updated", meta["date"])
        fv = ""
        if "hero" in meta:
            fv = (f'<figure class="article-fv"><img src="{meta["hero"]}" '
                  f'alt="{html.escape(meta["title"])}"></figure>')
        crumb = ('<nav class="crumb"><a href="/">ホーム</a> › '
                 f'<span>{html.escape(meta["title"])}</span></nav>')
        art = render(tpl("article.html"),
                     title=html.escape(meta["title"]),
                     date=jp_date(meta["date"]), updated=jp_date(upd),
                     fv=fv, toc=toc_html, content=body_html,
                     crumb=crumb, related=related_block(meta), site=SITE_NAME)
        extra = article_jsonld(meta, path) + faq_jsonld(body_md)
        if "hero" in meta:
            extra = f'<meta property="og:image" content="{SITE}{meta["hero"]}">\n' + extra
        doc = page(art, title=f'{meta["title"]}｜{SITE_NAME}',
                   description=meta["description"], path=path,
                   extra_head=extra)
        d = os.path.join(OUT, "articles", meta["slug"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(doc)
        articles.append((meta, path))

    # 固定ページ
    for fn, path, title in (("about.md", "/about/", f"運営者情報｜{SITE_NAME}"),
                            ("privacy.md", "/privacy/", f"プライバシーポリシー・免責事項｜{SITE_NAME}")):
        meta, body_md = parse_front(open(os.path.join(CONTENT, "pages", fn), encoding="utf-8").read())
        body_html, _ = md2html(body_md)
        inner = f'<article class="article"><h1>{html.escape(meta["title"])}</h1>{body_html}</article>'
        doc = page(inner, title=title, description=meta["description"], path=path)
        d = os.path.join(OUT, path.strip("/"))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(doc)

    # トップ
    articles.sort(key=lambda a: a[0].get("updated", a[0]["date"]), reverse=True)
    cards = "".join(
        f'''<a class="card" href="{p}">
  <p class="card-date">{jp_date(m.get("updated", m["date"]))}</p>
  <p class="card-title">{html.escape(m["title"])}</p>
  <p class="card-desc">{html.escape(m["description"])}</p>
</a>''' for m, p in articles)
    top = render(tpl("index.html"), cards=cards, site=SITE_NAME)
    doc = page(top, title=f"{SITE_NAME}｜912万円課金した研究家のオリパ攻略メディア",
               description="24個のオリパアプリに自腹で約912万円課金した研究家が、オンラインオリパの選び方・還元率の見方・優良アプリを実体験ベースで解説します。",
               path="/")
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(doc)

    # 404 / robots / CNAME / sitemap / feed
    doc404 = page('<article class="article"><h1>ページが見つかりません</h1>'
                  '<p>URLが変更されたか、削除された可能性があります。'
                  '<a href="/">トップページへ戻る</a></p></article>',
                  title=f"404 Not Found｜{SITE_NAME}", description="ページが見つかりません", path="/404.html")
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(doc404)
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    open(os.path.join(OUT, "CNAME"), "w").write("oripa-rank.jp\n")

    urls = [("/", None)] + [(p, m.get("updated", m["date"])) for m, p in articles] + [("/about/", None), ("/privacy/", None)]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, lastmod in urls:
        sm.append("<url><loc>%s%s</loc>%s</url>" % (SITE, u, f"<lastmod>{lastmod}</lastmod>" if lastmod else ""))
    sm.append("</urlset>")
    open(os.path.join(OUT, "sitemap.xml"), "w").write("\n".join(sm))

    items = "".join(
        f"<item><title>{html.escape(m['title'])}</title><link>{SITE}{p}</link>"
        f"<pubDate>{m['date']}</pubDate><description>{html.escape(m['description'])}</description></item>"
        for m, p in articles)
    open(os.path.join(OUT, "feed.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f'<title>{SITE_NAME}</title><link>{SITE}/</link><description>オリパ攻略メディア</description>{items}</channel></rss>')

    print(f"build OK: 記事{len(articles)}本 → docs/")


if __name__ == "__main__":
    build()
