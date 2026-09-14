#!/usr/bin/env python3
"""
Récupère la liste des pharmacies de garde du Gard depuis
https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/
et génère un fichier index.html prêt à être affiché en iframe
(ex. sur le site de la mairie de Moussac).

Ce script est destiné à être lancé automatiquement (voir
.github/workflows/update.yml), mais peut aussi être lancé à la main :
    python scrape_pharmacies.py
"""

import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/"
OUTPUT_FILE = "index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MairieMoussacBot/1.0)"
}


def fetch_page(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def find_list_heading(soup: BeautifulSoup):
    """Trouve le titre 'Liste des pharmacies de garde le JJ/MM/AAAA'."""
    for tag in soup.find_all(["h1", "h2", "h3"]):
        if tag.get_text(strip=True).lower().startswith("liste des pharmacies de garde"):
            return tag
    return None


def extract_pharmacies(soup: BeautifulSoup):
    heading = find_list_heading(soup)
    if heading is None:
        raise RuntimeError(
            "Titre 'Liste des pharmacies de garde' introuvable — "
            "la page source a peut-être changé de structure."
        )

    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", heading.get_text())
    garde_date = date_match.group(1) if date_match else None

    pharmacies = []
    current = heading.find_next_sibling()

    # On s'arrête au prochain titre de même niveau (h2), qui marque
    # la fin de la liste hebdomadaire sur la page source.
    while current is not None and current.name != "h2":
        if current.name == "h3":
            name = current.get_text(strip=True).replace("Pharmacie de garde ", "")
            secteur = ""
            address = ""
            phone = ""
            maps_link = ""

            node = current.find_next_sibling()

            # Le secteur couvert est dans un <p><strong>...</strong></p>
            if node and node.name == "p":
                strong = node.find("strong")
                if strong:
                    secteur = strong.get_text(strip=True)
                node = node.find_next_sibling()

            # Adresse / téléphone / lien Maps sont dans le <ul> suivant
            if node and node.name == "ul":
                for li in node.find_all("li"):
                    text = li.get_text(" ", strip=True)
                    lower = text.lower()
                    if lower.startswith("adresse"):
                        address = text.split(":", 1)[-1].strip()
                    elif lower.startswith("téléphone") or lower.startswith("telephone"):
                        a = li.find("a")
                        phone = a.get_text(strip=True) if a else text.split(":", 1)[-1].strip()
                    elif "itinéraire" in lower or "itineraire" in lower:
                        a = li.find("a", href=True)
                        if a:
                            maps_link = a["href"]

            pharmacies.append({
                "name": name,
                "secteur": secteur,
                "address": address,
                "phone": phone,
                "maps_link": maps_link,
            })

        current = current.find_next_sibling()

    return garde_date, pharmacies


def render_html(garde_date: str, pharmacies: list) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    rows = []
    for p in pharmacies:
        maps_html = (
            f'<a href="{p["maps_link"]}" target="_blank" rel="noopener">Itinéraire</a>'
            if p["maps_link"] else ""
        )
        tel_digits = re.sub(r"[^0-9+]", "", p["phone"]) if p["phone"] else ""
        phone_html = f'<a href="tel:{tel_digits}">{p["phone"]}</a>' if p["phone"] else ""

        rows.append(f"""
        <div class="pharmacie">
          <h3>{p['name']}</h3>
          <p class="secteur">{p['secteur']}</p>
          <p class="adresse">{p['address']}</p>
          <p class="tel">{phone_html}</p>
          <p class="maps">{maps_html}</p>
        </div>""")

    date_html = (
        f"<h2>Pharmacies de garde du {garde_date}</h2>"
        if garde_date else "<h2>Pharmacies de garde</h2>"
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pharmacies de garde - Gard</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 12px; color: #222; }}
  h2 {{ font-size: 1.1em; margin-bottom: 12px; }}
  .pharmacie {{ border: 1px solid #ddd; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; }}
  .pharmacie h3 {{ margin: 0 0 4px 0; font-size: 1em; }}
  .secteur {{ color: #555; font-style: italic; margin: 2px 0; }}
  .adresse, .tel {{ margin: 2px 0; }}
  .maps a, .tel a {{ color: #0a6ebd; text-decoration: none; }}
  footer {{ font-size: 0.75em; color: #888; margin-top: 12px; }}
</style>
</head>
<body>
  {date_html}
  {''.join(rows) if rows else '<p>Aucune donnée disponible pour le moment.</p>'}
  <footer>Source : gard30.fr — page régénérée automatiquement le {generated_at}</footer>
</body>
</html>"""


def main():
    try:
        soup = fetch_page(SOURCE_URL)
        garde_date, pharmacies = extract_pharmacies(soup)
        if not pharmacies:
            raise RuntimeError("Aucune pharmacie extraite — vérifier la structure de la page source.")
        html = render_html(garde_date, pharmacies)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"OK — {len(pharmacies)} pharmacies extraites pour le {garde_date}.")
    except Exception as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
