import os, hashlib, time, asyncio
from dataclasses import dataclass
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from readability import Document

SNAP_DIR = os.getenv("SNAP_DIR", "data/snapshots")

@dataclass
class Snapshot:
    url: str
    path_html: str
    path_txt: str
    sha256: str
    http_status: int | None
    charset: str | None

async def fetch_and_snapshot(url: str) -> Snapshot:
    os.makedirs(SNAP_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS","true")=="true")
        ctx = await browser.new_context(user_agent=os.getenv("USER_AGENT", "Autoparser/1.0 (+contact@example.com)"))
        page = await ctx.new_page()
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=int(os.getenv("REQUEST_TIMEOUT_MS","30000")))
        html = await page.content()
        await browser.close()

    sha = hashlib.sha256(html.encode("utf-8","ignore")).hexdigest()
    ts = int(time.time())
    host = urlparse(url).netloc.replace(":","_")
    base = f"{SNAP_DIR}/{host}_{ts}_{sha[:8]}"
    path_html = base + ".html"
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(html)

    # Clean: readability + BS4 fallback
    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text("\n")
    except Exception:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n")

    path_txt = base + ".txt"
    with open(path_txt, "w", encoding="utf-8") as f:
        f.write(text)

    return Snapshot(
        url=url, path_html=path_html, path_txt=path_txt,
        sha256=sha, http_status=(resp.status if resp else None),
        charset="utf-8"
    )
