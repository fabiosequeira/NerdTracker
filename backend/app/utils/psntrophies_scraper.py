import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import re

def format_game_title_for_url(title: str) -> str:
    """
    Convert game title to PlayStationTrophies.org URL format.
    Lowercase, remove special chars, spaces -> hyphens.
    """
    title = title.lower()
    title = re.sub(r'[:&]', '', title)  # remove colon & ampersand
    title = re.sub(r'\s+', '-', title)  # spaces -> hyphens
    title = re.sub(r'[^a-z0-9-]', '', title)  # remove anything else
    return title

def get_trophies_from_psntrophies(game_title: str) -> List[Dict]:
    """
    Scrape PlayStationTrophies.org for a game's trophies
    and return a list of dicts compatible with your Trophy model.
    """
    base_url = "https://www.playstationtrophies.org/game/"
    game_url = f"{base_url}{format_game_title_for_url(game_title)}/trophies/"

    with httpx.Client(timeout=10) as client:
        resp = client.get(game_url)
        if resp.status_code != 200:
            return []  # fallback if page not found
        soup = BeautifulSoup(resp.text, "html.parser")

    trophy_list = []
    trophy_items = soup.select("li.trophy")  # update selector if site changes

    for order, li in enumerate(trophy_items, start=1):
        name_tag = li.select_one(".trophy-title") or li.select_one("h3")
        desc_tag = li.select_one(".trophy-description") or li.select_one("p")
        type_tag = li.select_one(".trophy-type") or li.select_one(".trophy-icon img")

        if not name_tag:
            continue

        trophy_type = type_tag.text.strip().lower() if type_tag and type_tag.text else "bronze"
        trophy = {
            "name": name_tag.text.strip(),
            "description": desc_tag.text.strip() if desc_tag else "",
            "type": trophy_type,
            "order": order,
            "unlocked": False,
            "date_unlocked": None
        }
        trophy_list.append(trophy)

    return trophy_list
