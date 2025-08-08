from duckduckgo_search import DDGS
from urllib.parse import urlparse, urlunparse
from typing import List
import re

OFFICIAL_PATTERNS = [
    r"\.gov\.ru$", r"\.gosuslugi\.ru$",
    r"\.tatarstan\.ru$", r"\.mos\.ru$", r"\.spb\.ru$",
    r"moibiznes", r"мойбизнес", r"moibusiness", r"mb\d+",
    r"min\w+\.ru$", r"fond\w*\.ru$", r"invest\w*\.ru$",
    r"support\w*\.ru$", r"grant\w*\.ru$", r"\.edu\.ru$"
]

def is_official(domain: str) -> bool:
    d = domain.lower()
    return any(re.search(pat, d) for pat in OFFICIAL_PATTERNS)

def canonicalize(url: str) -> str:
    # strip fragments/query for canonical comparison; keep https if possible
    p = urlparse(url)
    scheme = "https" if p.scheme in ("http", "https") else "https"
    return urlunparse((scheme, p.netloc.lower(), p.path, "", "", ""))

def search_official_urls(region: str, max_results: int = 10) -> List[str]:
    queries = [
        f"меры поддержки бизнес {region} официальный сайт",
        f"субсидии гранты {region} мой бизнес официальный сайт",
        f"фонд поддержки предпринимательства {region} программа положение pdf",
        f"постановление правительства {region} субсидия 2025 site:*.ru"
    ]
    urls = []
    seen = set()
    with DDGS() as ddgs:
        for q in queries:
            for r in ddgs.text(q, max_results=20, safesearch="off", region="ru-ru"):
                u = r.get("href") or r.get("link") or r.get("url")
                if not u: continue
                cu = canonicalize(u)
                if cu in seen: continue
                dom = urlparse(cu).netloc
                if is_official(dom):
                    seen.add(cu); urls.append(cu)
                if len(urls) >= max_results:
                    return urls
    return urls
