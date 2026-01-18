import csv
import json
import random

"""
Script de transformation des données.

Ce fichier permet d'adapter un dataset CSV brut (issu de Kaggle)
en un catalogue de voitures exploitable par l'application AutoFinder.

Objectifs :
- nettoyer et normaliser les données d'origine,
- adapter les prix et les catégories au contexte local,
- enrichir les véhicules avec des informations réalistes,
- produire un fichier JSON cohérent utilisé par le moteur RAG.
source: https://www.kaggle.com/datasets/kumar009/used-car-datasets
"""


INPUT_CSV = "datasets3.csv"
OUTPUT_JSON = "voitures.json"

PRIX_COEF = 0.22

OPTIONS_BY_YEAR = {
    "old": ["direction assistée", "climatisation", "vitres électriques"],
    "mid": ["bluetooth", "radar de recul", "régulateur de vitesse"],
    "recent": ["écran tactile", "caméra de recul", "démarrage sans clé"],
    "modern": ["carplay", "aides conduite", "caméra 360"]
}

def clean(value):
    if value is None:
        return ""
    return value.strip()

def pick_options(year):
    if year <= 2010:
        pool = OPTIONS_BY_YEAR["old"]
    elif year <= 2015:
        pool = OPTIONS_BY_YEAR["old"] + OPTIONS_BY_YEAR["mid"]
    elif year <= 2020:
        pool = OPTIONS_BY_YEAR["mid"] + OPTIONS_BY_YEAR["recent"]
    else:
        pool = OPTIONS_BY_YEAR["recent"] + OPTIONS_BY_YEAR["modern"]

    return random.sample(pool, random.randint(2, min(5, len(pool))))

def pick_transmission(year):
    if year < 2012:
        return "manuelle" if random.random() < 0.7 else "automatique"
    else:
        return "automatique" if random.random() < 0.55 else "manuelle"

voitures = []

with open(INPUT_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for idx, row in enumerate(reader, start=1):
        try:
            year = int(float(clean(row["Manufacturing Year"])))
            km = int(float(clean(row["Distance(km)"])))
            price_inr = float(clean(row["Price in INR"]))

            transmission = pick_transmission(year)
            prix = int(price_inr * PRIX_COEF)
            if transmission == "automatique":
                prix = int(prix * 1.07)

            modele = clean(row["Model"]) or "Modèle inconnu"
            carburant = clean(row["Fuel Type"]).lower()
            if carburant == "petrol":
                carburant = "essence"
            nom = f"{clean(row['Make'])} {modele}".lower()
            if "hybride" in nom or "hybrid" in nom:
                carburant = "electrique"

            voiture = {
                "id": idx,
                "marque": clean(row["Make"]),
                "modele": modele,
                "annee": year,
                "kilometrage_km": km,
                "carburant": carburant,
                "transmission": transmission,
                "prix": prix,
                "options": pick_options(year)
            }

            voitures.append(voiture)

        except Exception as e:
            # on ignore les lignes cassées sans faire planter tout
            continue

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(voitures, f, ensure_ascii=False, indent=2)

print(f"{len(voitures)} voitures générées dans {OUTPUT_JSON}")
