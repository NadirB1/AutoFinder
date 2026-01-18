import re
from typing import Literal

Intent = Literal["car_search", "smalltalk", "other"]

_SMALLTALK = [
    "bonjour", "salut", "coucou", "hello", "hey",
    "merci", "thanks", "au revoir", "aurevoir", "bye",
    "ça va", "cv", "salam", "slm"
]

# Mots typiques d'une recherche voiture/location
_CAR_KEYWORDS = [
    "voiture", "auto", "véhicule", "location", "louer", "rent",
    "diesel", "essence", "hybride", "electrique", "électrique",
    "automatique", "manuelle", "boite", "boîte",
    "prix", "budget", "dh", "dhs", "mad",
    "km", "kilomet", "kilomèt", "kilométr",
    "suv", "berline", "citadine", "4x4",
    "marque", "modèle", "modele"
]

def detect_intent(text: str) -> Intent:
    t = (text or "").strip().lower()
    if not t:
        return "smalltalk"

    # Smalltalk très évident
    if any(k in t for k in _SMALLTALK):
        # Si le message contient aussi des indices voiture, on préfère car_search
        if any(k in t for k in _CAR_KEYWORDS):
            return "car_search"
        return "smalltalk"

    # Si on voit un nombre + "km" ou "dh"/"dhs" => très probablement recherche voiture
    if re.search(r"\b\d{2,}\s*(km|kms|kilom)", t) or re.search(r"\b\d{2,}\s*(dh|dhs|mad)\b", t):
        return "car_search"

    # Mots-clés voiture
    if any(k in t for k in _CAR_KEYWORDS):
        return "car_search"

    return "other"