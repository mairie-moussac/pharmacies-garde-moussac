#!/usr/bin/env python3
"""
Récupère la liste des pharmacies de garde du Gard depuis
https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/
et génère un fichier index.html prêt à être affiché en iframe.

Cette version extrait uniquement le TEXTE VISIBLE de la page (peu
importe les balises HTML utilisées : div, p, li, strong, etc.),
ce qui la rend robuste même si le site change sa mise en page.
"""

import re
import sys
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/"
OUTPUT_FILE = "index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MairieMoussacBot/1.0)"
}

LABEL_ADRESSE = ("adresse",)
LABEL_TEL = ("téléphone", "telephone", "tél", "tel :", "tel:")
LABEL_ITINERAIRE = ("itinéraire", "itineraire")


def fetch_page(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_text_lines(soup: BeautifulSoup):
    """Texte visible de la page, une entrée par ligne, sans dépendre
    des balises HTML précises."""
    raw = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", l).strip() for l in raw.split("\n")]
    return [l for l in lines if l]


def extract_pharmacies(soup: BeautifulSoup):
    lines = get_text_lines(soup)

    start_idx = None
    garde_date = None
    for i, l in enumerate(lines):
        if l.lower().startswith("liste des pharmacies de garde"):
            start_idx = i
            m = re.search(r"(\d{2}/\d{2}/\d{4})", l)
            if m:
                garde_date = m.group(1)
            break

    if start_idx is None:
        raise RuntimeError(
            "Ligne 'Liste des pharmacies de garde' introuvable — "
            "la page source a peut-être changé de structure."
        )

    end_markers = ("pour choisir la pharmacie de garde", "quel est le numéro")
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        low = lines[i].lower()
        if any(low.startswith(m) for m in end_markers):
            end_idx = i
            break

    section = lines[start_idx + 1:end_idx]

    pharmacies = []
    current = None
    i = 0
    while i < len(section):
        line = section[i]
        low = line.lower()

        if low.startswith("pharmacie de garde"):
            if current:
                pharmacies.append(current)
            name = re.sub(r"(?i)^pharmacie de garde\s*[:\-]?\s*", "", line).strip()
            current = {"name": name, "secteur": "", "address": "", "phone": ""}
            i += 1
            continue

        if current is not None:
            if low.startswith(LABEL_ADRESSE):
                value = line.split(":", 1)[-1].strip() if ":" in line else ""
                if not value and i + 1 < len(section):
                    i += 1
                    value = section[i]
                current["address"] = value

            elif low.startswith(LABEL_TEL):
                value = line.split(":", 1)[-1].strip() if ":" in line else ""
                if not value and i + 1 < len(section):
                    i += 1
                    value = section[i]
                current["phone"] = value

            elif any(k in low for k in LABEL_ITINERAIRE):
                pass  # le lien Maps est régénéré à partir de l'adresse

            elif not current["secteur"]:
                current["secteur"] = line

        i += 1

    if current:
        pharmacies.append(current)

    return garde_date, pharmacies


def render_html(garde_date: str, pharmacies: list) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    rows = []
    for p in pharmacies:
        tel_digits = re.sub(r"[^0-9+]", "", p["phone"]) if p["phone"] else ""
        phone_html = f'<a href="tel:{tel_digits}">{p["phone"]}</a>' if p["phone"] else ""

        maps_html = ""
        if p["address"]:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(p['address'])}"
            maps_html = f'<a href="{maps_url}" target="_blank" rel="noopener">Itinéraire</a>'

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
