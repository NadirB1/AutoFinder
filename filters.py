import re
from typing import Any, Dict, Optional

FUEL_KEYWORDS = {
    "diesel": "diesel",
    "essence": "essence",
    "hybride": "electrique",
    "electrique": "electrique",
    "électrique": "electrique",
    "electric": "electrique",
}

BRAND_MAP = {
    "audi": "Audi",
    "bmw": "BMW",
    "chevrolet": "Chevrolet",
    "datsun": "Datsun",
    "fiat": "Fiat",
    "force": "Force",
    "ford": "Ford",
    "hindustan": "Hindustan",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "isuzu": "Isuzu",
    "jaguar": "Jaguar",
    "jeep": "Jeep",
    "land": "Land",
    "mahindra": "Mahindra",
    "maruti": "Maruti",
    "mercedes": "Mercedes",
    "mercedes-benz": "Mercedes-Benz",
    "mercedes benz": "Mercedes-Benz",
    "mini": "Mini",
    "mitsubishi": "Mitsubishi",
    "nissan": "Nissan",
    "opel": "Opel",
    "renault": "Renault",
    "skoda": "Skoda",
    "ssangyong": "Ssangyong",
    "tata": "Tata",
    "toyota": "Toyota",
    "volkswagen": "Volkswagen",
    "volvo": "Volvo",
}

def _brand_pattern(keys: list) -> str:
    parts = []
    for k in keys:
        if re.fullmatch(r"[a-z0-9]+", k):
            parts.append(rf"\b{re.escape(k)}\b")
        else:
            parts.append(re.escape(k))
    return "|".join(parts)

def _to_int(s: str) -> Optional[int]:
    s = s.replace(" ", "").replace("_", "")
    try:
        return int(s)
    except:
        return None

def extract_constraints(text: str) -> Dict[str, Any]:
    """
    Extrait des contraintes simples depuis le texte:
    - prix_max / prix_min (DHS)
    - km_max
    - annee_min / annee_max
    - carburant
    - transmission
    - marque (si mentionnée explicitement)
    """
    t = (text or "").lower()

    c: Dict[str, Any] = {}

    # modele + annee: "modele 2020" ou "modele 2018 et 2020"
    m = re.search(
        r"\bmod[eè]le\s*(20\d{2}|19\d{2})(?:\s*(?:et|à|-|–)\s*(20\d{2}|19\d{2}))?",
        t,
    )
    if m:
        y1 = int(m.group(1))
        y2 = int(m.group(2)) if m.group(2) else None
        if y2 is not None:
            c["annee_min"] = min(y1, y2)
            c["annee_max"] = max(y1, y2)
        else:
            c["annee_min"] = y1
            c["annee_max"] = y1

    # carburant
    for fuel in ["diesel", "essence", "hybride", "electrique", "électrique", "electric"]:
        if fuel in t:
            c["carburant"] = FUEL_KEYWORDS[fuel]
            break

    # transmission
    if any(k in t for k in ["automatique", "boite auto", "boîte auto", "bva"]):
        c["transmission"] = "automatique"
    elif any(k in t for k in ["manuelle", "boite manuelle", "boîte manuelle", "bvm"]):
        c["transmission"] = "manuelle"

    # prix entre: "entre 50000 et 90000 dh"
    m = re.search(
        r"entre\s*(\d[\d\s]{2,})\s*et\s*(\d[\d\s]{2,})\s*(dh|dhs|mad)\b",
        t,
    )
    if m:
        val_min = _to_int(m.group(1))
        val_max = _to_int(m.group(2))
        if val_min is not None and val_max is not None:
            c["prix_min"] = min(val_min, val_max)
            c["prix_max"] = max(val_min, val_max)

    # prix max: "moins de 80000", "< 80000", "max 80000", "budget 80000", "80000 dh"
    m = re.search(r"(moins de|<=|<|max|budget)\s*(\d[\d\s]{2,})", t)
    if m:
        val = _to_int(m.group(2))
        if val is not None:
            c["prix_max"] = val

    # prix avec DH/DHS/MAD: "100000 dh" -> intervalle +- 10000
    m = re.search(r"\b(\d[\d\s]{4,})\s*(dh|dhs|mad)\b", t)
    if m and "prix_min" not in c and "prix_max" not in c:
        val = _to_int(m.group(1))
        if val is not None and val >= 10000:
            c["prix_min"] = max(val - 10000, 0)
            c["prix_max"] = val + 10000

    # km max: "moins de 100000 km", "< 120000 km"
    m = re.search(r"(moins de|<=|<|max)\s*(\d[\d\s]{2,})\s*(km|kms)\b", t)
    if m:
        val = _to_int(m.group(2))
        if val is not None:
            c["km_max"] = val
    else:
        m = re.search(r"\b(\d[\d\s]{2,})\s*(km|kms)\b", t)
        if m:
            val = _to_int(m.group(1))
            if val is not None:
                c["km_max"] = val

    # annee entre: "entre 2015 et 2020"
    m = re.search(r"entre\s*(20\d{2}|19\d{2})\s*et\s*(20\d{2}|19\d{2})", t)
    if m:
        val_min = int(m.group(1))
        val_max = int(m.group(2))
        c["annee_min"] = min(val_min, val_max)
        c["annee_max"] = max(val_min, val_max)

    # annee: "a partir de 2018", ">= 2017", "apres 2016"
    m = re.search(r"(>=|à partir de|apres|après)\s*(20\d{2}|19\d{2})", t)
    if m:
        c["annee_min"] = int(m.group(2))

    # année max: "<= 2019", "avant 2018"
    m = re.search(r"(<=|avant)\s*(20\d{2}|19\d{2})", t)
    if m:
        c["annee_max"] = int(m.group(2))

    # recent/recente: impose annee_min=2020 si pas deja defini
    if any(k in t for k in ["recent", "recente", "récente", "récent"]):
        if "annee_min" not in c:
            c["annee_min"] = 2020

    # marque (liste basée sur voitures.json)
    brand_pattern = _brand_pattern(sorted(BRAND_MAP.keys(), key=len, reverse=True))
    m = re.search(brand_pattern, t)
    if m:
        c["marque"] = BRAND_MAP[m.group(0)]

    return c


def apply_filters(cars: list, constraints: Dict[str, Any]) -> list:
    """
    Filtre une liste de voitures (dicts) selon les contraintes extraites.
    """
    out = []
    for v in cars:
        if "carburant" in constraints and str(v.get("carburant", "")).lower() != constraints["carburant"]:
            continue
        if "transmission" in constraints and str(v.get("transmission", "")).lower() != constraints["transmission"]:
            continue
        if "marque" in constraints and str(v.get("marque", "")).lower() != constraints["marque"].lower():
            continue

        prix = v.get("prix")
        km = v.get("kilometrage_km")
        annee = v.get("annee")

        if "prix_min" in constraints and isinstance(prix, (int, float)) and prix < constraints["prix_min"]:
            continue
        if "prix_max" in constraints and isinstance(prix, (int, float)) and prix > constraints["prix_max"]:
            continue
        if "km_max" in constraints and isinstance(km, (int, float)) and km > constraints["km_max"]:
            continue
        if "annee_min" in constraints and isinstance(annee, int) and annee < constraints["annee_min"]:
            continue
        if "annee_max" in constraints and isinstance(annee, int) and annee > constraints["annee_max"]:
            continue

        out.append(v)
    return out
