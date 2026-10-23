import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
import feedparser
from ruamel.yaml import YAML

# Initialize pure-Python YAML loader
yaml_engine = YAML(typ='safe')

app = FastAPI(
    title="EPL Content Ingestion API",
    description="Backend microservice for scraping, parsing feeds, and serving club configurations.",
    version="1.0.0"
)

# Enable CORS for local UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve configuration path relative to backend directory
CONFIG_PATH = Path(__file__).parent.parent / "config" / "teams_config.yaml"


# --- PYDANTIC SCHEMAS ---

class ScrapedArticle(BaseModel):
    id: str
    club_key: str
    title: str
    source_domain: str
    published_time: Optional[str] = "Recently"
    summary: str
    article_url: str
    image_url: Optional[str] = None
    full_text: Optional[str] = None


class FeedRequest(BaseModel):
    club_key: str
    urls: List[str]
    limit: Optional[int] = 5


# --- CRAWLER HELPERS ---

def extract_article_details(url: str) -> dict:
    """Extracts metadata and text content from a web URL using Trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {}
        extracted_json = trafilatura.extract(
            downloaded,
            output_format="json",
            with_metadata=True,
            include_images=True
        )
        if extracted_json:
            return json.loads(extracted_json)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return {}


def parse_rss_or_web(club_key: str, urls: List[str], limit: int) -> List[ScrapedArticle]:
    """Processes RSS feeds or scrapes articles directly from target URLs."""
    results = []
    for source_url in urls:
        if len(results) >= limit:
            break

        feed = feedparser.parse(source_url)
        if feed.entries:
            for entry in feed.entries[:limit]:
                if len(results) >= limit:
                    break
                link = entry.get("link", source_url)
                title = entry.get("title", "EPL Match Update")
                summary = entry.get("summary", entry.get("description", ""))
                clean_summary = trafilatura.html2txt(summary) if summary else ""

                results.append(
                    ScrapedArticle(
                        id=f"rss_{abs(hash(link))}",
                        club_key=club_key,
                        title=title,
                        source_domain=entry.get("author", "RSS Feed"),
                        published_time=entry.get("published", "Recently"),
                        summary=clean_summary[:300] if clean_summary else "Click to read full story.",
                        article_url=link,
                        image_url=None,
                        full_text=clean_summary
                    )
                )
        else:
            data = extract_article_details(source_url)
            if data and data.get("title"):
                text_body = data.get("text", "")
                results.append(
                    ScrapedArticle(
                        id=f"web_{abs(hash(source_url))}",
                        club_key=club_key,
                        title=data.get("title"),
                        source_domain=data.get("hostname", "News Outlet"),
                        published_time=data.get("date", "Today"),
                        summary=text_body[:300] + "..." if len(text_body) > 300 else text_body,
                        article_url=source_url,
                        image_url=data.get("image"),
                        full_text=text_body
                    )
                )
    return results


# --- API ENDPOINTS ---

@app.get("/")
def root():
    return {"status": "online", "service": "EPL Social Content Manager API"}


@app.get("/api/config")
def get_config():
    """Reads and returns the local teams_config.yaml file."""
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="teams_config.yaml configuration file not found.")
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml_engine.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load YAML config: {str(e)}")


@app.get("/api/scrape-url", response_model=ScrapedArticle)
def scrape_url(url: str = Query(..., description="Target article URL"), club_key: str = "general"):
    """Scrapes a single article URL and returns structured data for post composition."""
    data = extract_article_details(url)
    if not data or not data.get("title"):
        raise HTTPException(status_code=400, detail="Could not extract content from the provided URL.")

    text_body = data.get("text", "")
    return ScrapedArticle(
        id=f"custom_{abs(hash(url))}",
        club_key=club_key,
        title=data.get("title", "Premier League Article"),
        source_domain=data.get("hostname", "Web Source"),
        published_time=data.get("date", "Today"),
        summary=text_body[:280] + "..." if len(text_body) > 280 else text_body,
        article_url=url,
        image_url=data.get("image"),
        full_text=text_body
    )


@app.post("/api/ingest-feed", response_model=List[ScrapedArticle])
def ingest_feed(request: FeedRequest):
    """Ingests RSS or direct web sources for a given club and returns scraped posts."""
    return parse_rss_or_web(request.club_key, request.urls, request.limit)