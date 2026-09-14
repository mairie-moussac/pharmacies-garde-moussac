# Pharmacies de garde – Gard (pour le site de Moussac)

Ce dépôt génère automatiquement, chaque jour, une page HTML listant les
pharmacies de garde du Gard, à partir de
https://www.gard30.fr/pharmacies-de-garde-dans-le-gard/

Gratuit, hébergé sur GitHub Pages, adresse en **https** (compatible iframe).

## Mise en place (une seule fois, ~10 minutes)

1. Créez un compte GitHub gratuit : https://github.com/join
2. Créez un nouveau dépôt **public**, par exemple nommé
   `pharmacies-garde-moussac`.
3. Déposez-y les fichiers de ce dossier en conservant l'arborescence :
   - `scrape_pharmacies.py`
   - `.github/workflows/update.yml`
   - `index.html`
   - `README.md`
4. Dans le dépôt : **Settings → Pages**, section "Build and deployment",
   choisissez la branche `main` et le dossier `/ (root)`, puis
   enregistrez.
5. GitHub affiche alors une adresse du type :
   `https://<votre-compte>.github.io/pharmacies-garde-moussac/`
   → c'est bien en **https**, donc utilisable dans l'iframe Intramuros.
6. (Optionnel mais recommandé) Onglet **Actions** du dépôt → sélectionnez
   le workflow "Mise à jour pharmacies de garde" → bouton **Run workflow**
   pour déclencher une première génération immédiatement, sans attendre
   le lendemain matin.

## Fonctionnement au quotidien

Chaque jour vers 7h-8h (heure de Paris), GitHub exécute automatiquement
le script, qui :
1. va chercher la page gard30.fr,
2. extrait la liste des pharmacies de garde du jour,
3. régénère `index.html`,
4. publie la mise à jour → visible immédiatement sur la page GitHub Pages.

Aucune action manuelle nécessaire ensuite.

## Intégration sur le site de la mairie (Intramuros)

Dans le bloc HTML de la page concernée, insérez :

```html
<iframe src="https://<votre-compte>.github.io/pharmacies-garde-moussac/"
        style="width:100%; height:600px; border:none;">
</iframe>
```

(Remplacez `<votre-compte>` par le nom réel du compte GitHub utilisé.)

## En cas de panne

Si gard30.fr modifie la mise en page de sa page, l'extraction peut
échouer et la page affichée restera celle de la dernière extraction
réussie (pas de page cassée). Pour vérifier :

- Onglet **Actions** du dépôt GitHub → si la dernière exécution est
  marquée en rouge (❌), cela signale un problème à corriger dans
  `scrape_pharmacies.py`.

## Limite à connaître

gard30.fr est un site privé qui agrège lui-même ces informations
(probablement à partir de 3237/RESOGARDES) — ce n'est pas une source
officielle garantie. En cas de doute pour un usage critique, le numéro
3237 (0,35 €/min) reste la référence officielle à afficher en
complément.
