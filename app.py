from flask import Flask, request, jsonify
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser
import time

app = Flask(__name__)

RSS_FEEDS = [
    "https://thehackernews.com/feeds/posts/default?alt=rss",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/rss/feeds/32/",
    "https://www.zdnet.com/topic/security/rss.xml",
    "https://www.schneier.com/blog/atom.xml",
    "https://www.securityweek.com/feed",
]

CACHE = {"items": [], "fetched_at": 0}
CACHE_TTL = 300

HEADERS = {"User-Agent": "CyberNewsScraper/1.0"}


def polite_get(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except:
        return None


def parse_feed(url):
    try:
        feed = feedparser.parse(url)
        entries = []
        for e in feed.entries[:20]:
            title = e.get("title", "").strip()
            link = e.get("link", "")
            summary = BeautifulSoup(e.get("summary", "") or "", "html.parser").get_text()[:500]
            pub = e.get("published", "") or e.get("updated", "")

            try:
                pub_dt = dateparser.parse(pub) if pub else None
            except:
                pub_dt = None

            entries.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": pub_dt.isoformat() if pub_dt else None,
                "source": feed.feed.get("title", url)
            })
        return entries
    except:
        return []


def fetch_news():
    items = []
    for feed in RSS_FEEDS:
        try:
            items += parse_feed(feed)
        except:
            pass

    def get_dt(it):
        try:
            return dateparser.parse(it["published"]) if it["published"] else datetime(1970, 1, 1)
        except:
            return datetime(1970, 1, 1)

    items = sorted(items, key=get_dt, reverse=True)

    seen = set()
    final = []

    for it in items:
        k = it["title"] + it["link"]
        if k not in seen:
            seen.add(k)
            final.append(it)

    return final[:100]


def get_cached_news(force=False):
    now = time.time()
    if not force and (now - CACHE["fetched_at"]) < CACHE_TTL and CACHE["items"]:
        return CACHE["items"], CACHE["fetched_at"]

    data = fetch_news()
    CACHE["items"] = data
    CACHE["fetched_at"] = now
    return data, now


@app.route("/")
def index():
    force = request.args.get("refresh") == "1"
    items, fetched = get_cached_news(force)
    fetched_at = datetime.fromtimestamp(fetched).strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <html>
    <head>
        <title>Cyber News Scraper</title>
        <style>
            body {{
                margin: 0;
                padding: 40px 0;
                font-family: Arial;
                background: linear-gradient(120deg, #e3f2fd, #fde2e4);
                display: flex;
                justify-content: center;
            }}

            .main {{
                width: 600px;
            }}

            .card {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 0 18px rgba(0,0,0,0.15);
                margin-bottom: 25px;
            }}

            h2 {{
                text-align: center;
                margin-bottom: 15px;
                color: #333;
            }}

            .btn {{
                width: 100%;
                padding: 10px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                cursor: pointer;
                margin-bottom: 20px;
            }}

            .btn:hover {{
                background: #0067d6;
            }}

            .news-card {{
                background: white;
                padding: 18px;
                border-radius: 10px;
                box-shadow: 0 0 12px rgba(0,0,0,0.12);
                margin-top: 18px;
            }}

            .title {{
                font-size: 18px;
                font-weight: bold;
                color: #007bff;
                text-decoration: none;
            }}

            .summary {{
                margin-top: 8px;
                color: #444;
            }}

            .meta {{
                font-size: 13px;
                color: #888;
                margin-top: 5px;
            }}
        </style>
    </head>

    <body>
        <div class="main">
            <div class="card">
                <h2>📰 Cyber News Scraper</h2>
                <p style="text-align:center; color:#666; margin-bottom:15px;">
                    Last Updated: {fetched_at}
                </p>
                <button class="btn" onclick="location.href='/?refresh=1'">Refresh News</button>
            </div>
    """

    for it in items:
        html += f"""
            <div class="news-card">
                <a class="title" href="{it['link']}" target="_blank">{it['title']}</a>
                <div class="meta">{it['source']} • {it['published']}</div>
                <div class="summary">{it['summary']}</div>
            </div>
        """

    html += """
        </div>
    </body>
    </html>
    """

    return html


@app.route("/api/news")
def api():
    items, fetched = get_cached_news()
    return jsonify({"count": len(items), "items": items})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
