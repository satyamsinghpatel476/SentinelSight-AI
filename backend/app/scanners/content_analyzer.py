from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ContentAnalysis:
    page_title: str | None
    visible_text: str
    visible_text_hash: str
    html_hash: str
    external_script_domains: list[str]
    external_iframe_domains: list[str]


def analyze_html_content(
    html: str,
    final_url: str,
    visible_text_max_chars: int,
) -> ContentAnalysis:
    """Extract bounded display-safe metadata from target HTML."""

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    visible_text = extract_visible_text(soup)[:visible_text_max_chars]
    return ContentAnalysis(
        page_title=title[:512] if title else None,
        visible_text=visible_text,
        visible_text_hash=sha256_text(visible_text),
        html_hash=sha256_text(html),
        external_script_domains=external_domains(soup, final_url, "script", "src"),
        external_iframe_domains=external_domains(soup, final_url, "iframe", "src"),
    )


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Return page text with script and style-like content removed."""

    for element in soup(["script", "style", "noscript", "template"]):
        element.decompose()
    source = soup.body if soup.body else soup
    words = " ".join(source.get_text(separator=" ").split())
    return words


def external_domains(
    soup: BeautifulSoup,
    base_url: str,
    tag_name: str,
    attribute_name: str,
) -> list[str]:
    domains: set[str] = set()
    base_hostname = (urlsplit(base_url).hostname or "").lower()
    for tag in soup.find_all(tag_name):
        raw_value = tag.get(attribute_name)
        if not raw_value:
            continue
        absolute_url = urljoin(base_url, str(raw_value))
        hostname = urlsplit(absolute_url).hostname
        if hostname and hostname.lower() != base_hostname:
            domains.add(hostname.lower())
    return sorted(domains)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
