import re
import requests
from bs4 import BeautifulSoup

def extract_text_from_html(html: str) -> str:
    """Pure function, no network — easy to unit test with a raw HTML string."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("could not extract any readable text from that page")
    return text

def fetch_url_text(url: str) -> str:
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return extract_text_from_html(resp.text)