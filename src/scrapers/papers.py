import httpx
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone


HEADERS = {"User-Agent": "news-summarizer/1.0"}
BASE_URL = "https://huggingface.co/papers"


async def scrape_huggingface_papers(filter_type: str = "date") -> list[dict]:
    if filter_type == "date":
        url = f"{BASE_URL}/date/{date.today().isoformat()}"
    elif filter_type == "week":
        url = f"{BASE_URL}?week=true"
    elif filter_type == "month":
        url = f"{BASE_URL}?month=true"
    else:
        url = BASE_URL

    async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    for article in soup.find_all("article"):
        h3 = article.find("h3")
        if not h3:
            continue
        title = h3.get_text(strip=True)
        link_tag = article.find("a", href=True)
        href = link_tag["href"] if link_tag else ""
        paper_url = href if href.startswith("http") else f"https://huggingface.co{href}"
        abstract_tag = article.find("p")
        raw_text = abstract_tag.get_text(strip=True) if abstract_tag else title

        items.append({
            "id": f"paper_{abs(hash(title)) % 10**8}",
            "title": title,
            "url": paper_url,
            "source": "papers",
            "category": "Research Papers",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "score": 0,
            "raw_text": raw_text,
        })

    return items
