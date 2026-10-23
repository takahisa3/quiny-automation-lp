#!/usr/bin/env python3
"""src/ のテンプレートから公開用の docs/ を生成する。

使い方: python3 build.py
- src/pages/**/*.html の先頭 <!--META {...} META--> からタイトル等を読み、共通ヘッダー等を差し込む
- src/static/ はそのままコピー
- sitemap.xml は各ページの updated から生成
"""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
SRC = ROOT / "src"
OUT = ROOT / "docs"
SITE = "https://automation.quiny.co.jp"

MAIL_TO = "info@quiny.co.jp"
MAIL_SUBJECT = "【自動化相談LP】ご相談"
MAIL_BODY = """会社名：
所在地（都道府県・市町村）：
ご担当者名：
お電話番号（任意）：

■自動化したい作業・工程：
■対象物（材質・大きさ・重さなど）：
■1日の処理量・作業人数（分かる範囲で）：
■困っていること：

※動画・写真・図面は、お持ちであれば添付してください（必須ではありません）。
"""
MAILTO = f"mailto:{MAIL_TO}?subject={quote(MAIL_SUBJECT)}&body={quote(MAIL_BODY)}"

META_RE = re.compile(r"\A\s*<!--META\s*(\{.*?\})\s*META-->\s*", re.S)


def render(partial: str, **vars) -> str:
    text = (SRC / "partials" / partial).read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", v)
    return text


FAQ_RE = re.compile(r"<details[^>]*><summary>(.*?)</summary><div class=\"ans\">(.*?)</div></details>", re.S)


def faq_jsonld(body: str) -> str:
    """表示中の <details> から FAQPage 構造化データを作る（表示と食い違わないように）"""
    items = []
    for q, a in FAQ_RE.findall(body):
        text = re.sub(r"<[^>]+>", "", a)
        text = re.sub(r"\s+", " ", text).strip()
        items.append({"@type": "Question", "name": q.strip(),
                      "acceptedAnswer": {"@type": "Answer", "text": text}})
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=2) + "\n</script>"


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC / "static", OUT)

    pages = []
    for src in sorted((SRC / "pages").rglob("*.html")):
        raw = src.read_text(encoding="utf-8")
        m = META_RE.match(raw)
        if not m:
            raise SystemExit(f"META がありません: {src}")
        meta = json.loads(m.group(1))
        body = raw[m.end():]
        if "<!--FAQ_JSONLD-->" in body:
            body = body.replace("<!--FAQ_JSONLD-->", faq_jsonld(body))
        path = meta["path"]
        canonical = SITE + path
        head = render(
            "head.html",
            TITLE=meta["title"],
            DESCRIPTION=meta["description"],
            CANONICAL=canonical,
            OG_TYPE=meta.get("og_type", "website"),
        )
        html = head + render("header.html") + body + render("contact.html") + render("footer.html")
        html = html.replace("{{MAILTO}}", MAILTO).replace("{{SITE}}", SITE).replace("{{UPDATED}}", meta["updated"])
        if "{{" in html:
            raise SystemExit(f"未置換のプレースホルダ: {src}")
        dest = OUT / src.relative_to(SRC / "pages")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        if not meta.get("noindex"):
            pages.append((canonical, meta["updated"], meta.get("priority", "0.7")))

    urls = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{d}</lastmod><priority>{p}</priority></url>" for u, d, p in pages
    )
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8",
    )
    print(f"built {len(pages)} pages -> {OUT}")


if __name__ == "__main__":
    build()
