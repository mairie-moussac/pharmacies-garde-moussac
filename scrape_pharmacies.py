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
    cards = []
    for p in pharmacies:
        tel_digits = re.sub(r"[^0-9+]", "", p["phone"]) if p["phone"] else ""
        phone_html = (
            f'<p style="margin:4px 0 0 0;"><a href="tel:{tel_digits}" style="color:#2980b9; text-decoration:none; font-weight:bold;">📞 {p["phone"]}</a></p>'
            if p["phone"] else ""
        )

        maps_html = ""
        if p["address"]:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(p['address'])}"
            maps_html = (
                f'<p style="margin-top:12px;"><a href="{maps_url}" target="_blank" rel="noopener" '
                f'style="display:inline-block; padding:8px 15px; background-color:#2980b9; color:#fff; '
                f'text-decoration:none; border-radius:4px; font-size:14px;">Voir sur la carte</a></p>'
            )

        secteur_html = (
            f'<p style="margin:0 0 8px 0; color:#666; font-style:italic; font-size:0.9em;">{p["secteur"]}</p>'
            if p["secteur"] else ""
        )

        cards.append(f"""
        <div style="background:#f9f9f9; border-radius:8px; border:1px solid #e0e0e0; box-sizing:border-box; display:flex; flex-direction:column; justify-content:flex-start; padding:20px; text-align:left;">
          <h3 style="margin:0 0 6px 0;">💊 {p['name']}</h3>
          {secteur_html}
          <p style="margin:0;">{p['address']}</p>
          {phone_html}
          {maps_html}
        </div>""")

    date_line = (
        f"<p style=\"margin-left:auto; margin-right:auto; font-size:1.4em; font-weight:bold;\">💊 Pharmacies de garde ouvertes le {garde_date} (dimanches et jours fériés).</p>"
        if garde_date else "<p style=\"margin-left:auto; margin-right:auto; font-size:1.4em; font-weight:bold;\">💊 Pharmacies de garde ouvertes les dimanches et jours fériés.</p>"
    )

    cards_html = (
        ''.join(cards) if cards
        else '<p style="margin-left:auto; margin-right:auto;">Aucune donnée disponible pour le moment.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pharmacie de garde du Gard</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 16px; color: #222; background:#fff; }}
  footer {{ font-size: 0.75em; color: #888; margin-top: 20px; text-align:center; }}
</style>
</head>
<body>
  <div style="margin-bottom:30px; text-align:center">
    {date_line}
  </div>
  <div style="align-items:stretch; display:grid; gap:20px; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); margin-bottom:20px">
    {cards_html}
  </div>
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