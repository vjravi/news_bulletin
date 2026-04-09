import httpx
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone


TLDR_ARCHIVE = "https://tldr.tech/ai/archives"
HEADERS = {"User-Agent": "news-summarizer/1.0"}


async def scrape_tldr() -> list[dict]:
    async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
        # Get archives page to find the latest newsletter URL
        resp = await client.get(TLDR_ARCHIVE)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the most recent newsletter link
        today = date.today().isoformat()
        newsletter_url = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/ai/" in href and today in href:
                newsletter_url = href if href.startswith("http") else f"https://tldr.tech{href}"
                break

        # Fall back to first archive link if today's not found
        if not newsletter_url:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/ai/2" in href:
                    newsletter_url = href if href.startswith("http") else f"https://tldr.tech{href}"
                    break

        if not newsletter_url:
            return []

        resp2 = await client.get(newsletter_url)
        resp2.raise_for_status()
        soup2 = BeautifulSoup(resp2.text, "html.parser")

        items = []
        # TLDR articles are typically in article/section elements with a headline + blurb
        for article in soup2.find_all("article"):
            h3 = article.find(["h3", "h2"])
            if not h3:
                continue
            title = h3.get_text(strip=True)
            link_tag = article.find("a", href=True)
            url = link_tag["href"] if link_tag else newsletter_url
            blurb_tag = article.find("p")
            raw_text = blurb_tag.get_text(strip=True) if blurb_tag else title

            items.append({
                "id": f"tldr_{abs(hash(title)) % 10**8}",
                "title": title,
                "url": url,
                "source": "tldr",
                "category": "AI Newsletter",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "score": 0,
                "raw_text": raw_text,
            })

        return items
