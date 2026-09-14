#!/usr/bin/env python3
"""
Récupère la liste des pharmacies de garde du Gard depuis
https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/
et génère un fichier index.html prêt à être affiché dans Intramuros.
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
                pass

            elif not current["secteur"]:
                current["secteur"] = line

        i += 1

    if current:
        pharmacies.append(current)

    return garde_date, pharmacies


def render_html(garde_date: str, pharmacies: list) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    date_str = f"du {garde_date}" if garde_date else ""

    rows = []
    for p in pharmacies:
        tel_digits = re.sub(r"[^0-9+]", "", p["phone"]) if p["phone"] else ""
        
        phone_html = ""
        if p["phone"]:
            phone_html = f'<a href="tel:{tel_digits}" style="color: #0056b3; font-weight: bold; text-decoration: none;">📞 {p["phone"]}</a>'

        maps_html = ""
        if p["address"]:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(p['address'])}"
            maps_html = f'<a href="{maps_url}" target="_blank" rel="noopener" style="display: inline-block; background-color: #0056b3; color: #ffffff; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 0.85rem; font-weight: bold; margin-top: 6px;">📍 Itinéraire Google Maps</a>'

        secteur_html = f'<div style="color: #666666; font-style: italic; font-size: 0.85rem; margin-bottom: 4px;">Secteur : {p["secteur"]}</div>' if p["secteur"] else ""

        rows.append(f"""
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-left: 4px solid #0056b3; border-radius: 6px; padding: 12px 15px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <h3 style="margin: 0 0 4px 0; color: #0056b3; font-size: 1.05rem;">{p['name']}</h3>
          {secteur_html}
          <div style="margin: 4px 0; font-size: 0.9rem; color: #333333;">🏠 {p['address']}</div>
          <div style="margin: 6px 0 4px 0; font-size: 0.9rem;">{phone_html}</div>
          <div>{maps_html}</div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pharmacies de garde - Gard</title>
</head>
<body style="margin: 0; padding: 10px; font-family: Arial, sans-serif; background-color: #ffffff; color: #333333;">

  <div style="width: 100%; max-width: 100%; box-sizing: border-box;">

    <!-- En-tête Moussac -->
    <div style="background-color: #f0f7ff; border: 1px solid #cce3ff; border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 15px;">
      <h2 style="color: #0056b3; margin: 0 0 6px 0; font-size: 1.3rem;">
        🏥 Pharmacies de garde {date_str}
      </h2>
      <p style="margin: 0; color: #555555; font-size: 0.95rem;">
        Mairie de Moussac — Information Santé
      </p>
    </div>

    <!-- Consignes / Informations complémentaires -->
    <div style="background-color: #fff9e6; border-left: 4px solid #ffc107; padding: 12px 15px; margin-bottom: 15px; border-radius: 4px; font-size: 0.88rem; line-height: 1.5;">
      <strong>Information :</strong> La nuit, les dimanches et jours fériés, vous pouvez également composer le <strong>3237</strong> (0,35 € / min) ou contacter la Gendarmerie. En cas d'urgence vitale, composez le <strong>15</strong> (SAMU).
    </div>

    <!-- Liste des pharmacies -->
    <div style="width: 100%;">
      {''.join(rows) if rows else '<p style="text-align: center; color: #666666;">Aucune pharmacie de garde répertoriée pour le moment.</p>'}
    </div>

    <!-- Pied de page -->
    <div style="text-align: center; font-size: 0.78rem; color: #888888; margin-top: 15px; border-top: 1px solid #eeeeee; padding-top: 10px;">
      Source : gard30.fr — Mise à jour automatique le {generated_at}
    </div>

  </div>

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
