import json
import os
import shutil
import time
from typing import Any, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# ----------------------------
# Chargement des données
# ----------------------------

_BASE_DIR = os.path.dirname(__file__)
_VOITURES_PATH = os.path.join(_BASE_DIR, "voitures.json")
_CHROMA_DIR = os.path.join(_BASE_DIR, "chroma_db")
_SIGNATURE_PATH = os.path.join(_CHROMA_DIR, "voitures.sig")

_embedding_model = None
_collection = None

def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        print("[rag] loading embedding model...")
        t0 = time.perf_counter()
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        ms = (time.perf_counter() - t0) * 1000
        print(f"[rag] embedding model loaded | ms={ms:.1f}")
    return _embedding_model

def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    # Signature simple: mtime + taille (suffisant ici)
    try:
        stat = os.stat(_VOITURES_PATH)
        current_sig = f"{int(stat.st_mtime)}:{stat.st_size}"
    except FileNotFoundError:
        raise FileNotFoundError(f"voitures.json introuvable: {_VOITURES_PATH}")

    previous_sig = None
    if os.path.isfile(_SIGNATURE_PATH):
        with open(_SIGNATURE_PATH, "r", encoding="utf-8") as f:
            previous_sig = f.read().strip() or None

    if previous_sig != current_sig and os.path.isdir(_CHROMA_DIR):
        print("[rag] voitures.json a changé, suppression de la base Chroma...")
        shutil.rmtree(_CHROMA_DIR, ignore_errors=True)
    elif previous_sig == current_sig and os.path.isdir(_CHROMA_DIR):
        print("[rag] voitures.json inchangé, réutilisation de la base Chroma.")

    print(f"[rag] opening Chroma collection... path={_CHROMA_DIR}")
    t0 = time.perf_counter()
    client = chromadb.PersistentClient(
        path=_CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        collection = client.get_collection("voitures")
        print("[rag] collection existing, embeddings réutilisés.")
    except:
        print("[rag] collection missing, creating + adding documents...")
        collection = client.create_collection("voitures")

        print("[rag] loading voitures.json...")
        t1 = time.perf_counter()
        with open(_VOITURES_PATH, "r", encoding="utf-8") as f:
            voitures = json.load(f)
        ms = (time.perf_counter() - t1) * 1000
        print(f"[rag] voitures.json loaded | ms={ms:.1f} count={len(voitures)}")

        embedding_model = _get_embedding_model()

        print("[rag] building descriptions + embeddings...")
        t2 = time.perf_counter()
        descriptions = [
            f"{v['marque']} {v['modele']}, "
            f"{v['carburant']}, "
            f"{v['transmission']}, "
            f"{v['kilometrage_km']} km, "
            f"{v['prix']} DHS"
            for v in voitures
        ]

        embeddings = embedding_model.encode(descriptions, convert_to_numpy=True)
        ms = (time.perf_counter() - t2) * 1000
        print(f"[rag] embeddings ready | ms={ms:.1f}")

        for i, v in enumerate(voitures):
            meta = v.copy()
            if isinstance(meta.get("options"), list):
                meta["options"] = ", ".join(meta["options"])

            collection.add(
                ids=[str(v["id"])],
                embeddings=[embeddings[i].tolist()],
                documents=[descriptions[i]],
                metadatas=[meta]
            )

        if hasattr(client, "persist"):
            print("[rag] persisting Chroma data to disk...")
            client.persist()
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        with open(_SIGNATURE_PATH, "w", encoding="utf-8") as f:
            f.write(current_sig)

    ms = (time.perf_counter() - t0) * 1000
    print(f"[rag] chroma ready | ms={ms:.1f}")

    _collection = collection
    return _collection

def warmup() -> None:
    _get_collection()

# ----------------------------
# Fonction RAG principale
# ----------------------------

def _build_where(constraints: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not constraints:
        return None

    conditions = []

    if "carburant" in constraints:
        conditions.append({"carburant": constraints["carburant"]})
    if "transmission" in constraints:
        conditions.append({"transmission": constraints["transmission"]})
    if "marque" in constraints:
        conditions.append({"marque": constraints["marque"]})

    if "prix_min" in constraints:
        conditions.append({"prix": {"$gte": constraints["prix_min"]}})
    if "prix_max" in constraints:
        conditions.append({"prix": {"$lte": constraints["prix_max"]}})
    if "km_max" in constraints:
        conditions.append({"kilometrage_km": {"$lte": constraints["km_max"]}})
    if "annee_min" in constraints:
        conditions.append({"annee": {"$gte": constraints["annee_min"]}})
    if "annee_max" in constraints:
        conditions.append({"annee": {"$lte": constraints["annee_max"]}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def search_voitures(query: str, k: int = 5, constraints: Optional[Dict[str, Any]] = None):
    embedding_model = _get_embedding_model()
    collection = _get_collection()
    print(f"[rag] search | k={k} query={query!r}")
    query_embedding = embedding_model.encode([query], convert_to_numpy=True)[0]
    where = _build_where(constraints)
    print(f"[rag] where={where}")

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=k,
        where=where,
    )

    return results["metadatas"][0]
