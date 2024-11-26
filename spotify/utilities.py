import re
import requests
from bs4 import BeautifulSoup
from spotify.exceptions import URLError


def extract_spotify_type_id(link):
    # Use a regular expression to match the pattern
    pattern = r"https://open\.spotify\.com/([^/]+)/([a-zA-Z0-9]+)"
    match = re.match(pattern, link)

    if match:
        return match.groups()
    else:
        raise URLError("Invalid Spotify URL")


def build_soup(url: str) -> BeautifulSoup:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    response = requests.get(url, headers = headers)
    if response.status_code != 200:
        raise RuntimeError("Failed to retrieve track page")

    return BeautifulSoup(response.text, "html.parser")
