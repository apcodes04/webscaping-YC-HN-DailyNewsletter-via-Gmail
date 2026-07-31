from bs4 import BeautifulSoup  # Parses raw HTML into navigable structure
import requests                 # Fetches live webpage over HTTP

def scrape_hn():
    """Scrape Hacker News and return a ranked list of (upvotes, title, link) tuples."""

    # Fetch the live page; User-Agent header prevents HN from blocking the request
    response = requests.get(
        "https://news.ycombinator.com/news",
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML into BeautifulSoup object

    article_texts = []
    article_links = []

    # HN wraps each article title in <span class="titleline">
    for span in soup.find_all(name="span", class_="titleline"):
        article_tag = span.find("a")      # First <a> inside span is the article link
        if article_tag:
            article_texts.append(article_tag.getText())       # Visible title text
            article_links.append(article_tag.get("href"))     # URL from href attribute

    # Extract upvote counts from <span class="score"> e.g. "254 points" → 254
    article_upvotes = [
        int(score.getText().split()[0])
        for score in soup.find_all(name="span", class_="score")
    ]

    # Zip stops at shortest list — safely excludes job posts (no score)
    paired = list(zip(article_upvotes, article_texts, article_links))

    # Sort descending by upvotes (first element of each tuple)
    ranked = sorted(paired, key=lambda x: x[0], reverse=True)

    return ranked  # List of (upvotes, title, link)
