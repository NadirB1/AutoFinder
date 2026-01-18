from flask import Flask, render_template, jsonify, request
import json
import os
import threading
import time
from llm_engine import generate_response, get_max_tokens, warmup as warmup_llm
from intent_detector import detect_intent
from rag_engine import search_voitures, warmup as warmup_rag
from filters import extract_constraints, apply_filters

app = Flask(__name__)

_BASE_DIR = os.path.dirname(__file__)
_VOITURES_PATH = os.path.join(_BASE_DIR, "voitures.json")

# Charger les voitures
with open(_VOITURES_PATH, "r", encoding="utf-8") as f:
    voitures = json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/catalogue")
def catalogue():
    return render_template("catalogue.html", voitures=voitures)

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
def chat():
    start_ts = time.perf_counter()
    data = request.get_json() or {}
    history = data.get("history", [])
    print(f"[chat] request received | history_len={len(history)}")
    print(f"[chat] history={history}")

    # ---- helpers locaux ----
    def last_user_message(hist):
        for m in reversed(hist):
            if m.get("role") == "user":
                return m.get("content", "")
        return ""

    def prev_user_message(hist):
        seen_last = False
        for m in reversed(hist):
            if m.get("role") == "user":
                if not seen_last:
                    seen_last = True
                else:
                    return m.get("content", "")
        return ""

    def format_car(v: dict) -> str:
        options = v.get("options", "")
        if isinstance(options, list):
            options = ", ".join(options)
        return (
            f"- ID: {v.get('id')} | {v.get('marque')} {v.get('modele')} | "
            f"{v.get('carburant')} | {v.get('transmission')} | "
            f"{v.get('kilometrage_km')} km | {v.get('prix')} DHS"
            + (f" | Options: {options}" if options else "")
        )

    # ---- intent ----
    last_user_msg = last_user_message(history).strip()
    prev_user_msg = prev_user_message(history).strip()

    intent = detect_intent(last_user_msg)
    prev_intent = detect_intent(prev_user_msg) if prev_user_msg else "smalltalk"
    user_msgs = [
        m.get("content", "").strip() for m in history if m.get("role") == "user"
    ]
    already_car_search = any(
        detect_intent(msg) == "car_search" for msg in user_msgs[:-1]
    )
    if already_car_search and intent in ("smalltalk", "other"):
        intent = "car_search"

    # ---- reset serveur si entrée en car_search ----
    reset_context = (
        last_user_msg != ""
        and (prev_intent in ("smalltalk", "other"))
        and (intent == "car_search")
        and (not already_car_search)
    )

    if reset_context:
        effective_history = [{"role": "user", "content": last_user_msg}]
    else:
        effective_history = history

    # garde-fou contexte (n_ctx=768)
    effective_history = effective_history[-12:]

    # ---- prompts (achat voiture + push vers recherche) ----
    if intent == "smalltalk":
        system_prompt = (
            "Tu es un assistant spécialisé pour aider l'utilisateur à trouver une voiture d'occasion à acheter. "
            "Réponds brièvement au small talk, puis ramène la discussion vers la recherche de voiture "
            "en posant UNE question simple (budget, carburant, boîte, usage, ville)."
        )
        rag_context = ""

    elif intent == "car_search":
        # ---- extraire contraintes utilisateur ----
        constraints = extract_constraints(last_user_msg)
        print(f"[filters] constraints={constraints}")

        system_prompt = (
            "Tu es un assistant expert pour aider l'utilisateur à trouver une voiture à acheter. "
            "Tu reçois: (1) des FILTRES extraits du message utilisateur, (2) un CATALOGUE filtré. "
            "Règles strictes: "
            "1) Ne propose QUE des voitures présentes dans le CATALOGUE FILTRÉ. "
            "2) Ne contredis pas les FILTRES. "
            "3) Si le CATALOGUE FILTRÉ n'est pas vide, commence toujours par lister TOUTES les voitures "
            "   (ne saute aucun ID), même si des filtres sont manquants. "
            "   Mets UNE voiture par ligne. "
            "4) Après la liste, dis que des critères plus précis donnent des résultats plus précis, "
            "   puis pose AU PLUS UNE question de précision. "
            "4) Si le CATALOGUE FILTRÉ est vide, explique clairement qu'aucune voiture ne correspond. "
            "   Propose de 'rafraîchir la conversation' (repartir de zéro) ET demande UN ajustement concret "
            "   (ex: augmenter budget, changer carburant, augmenter km, élargir marque). "
            "5) Quand tu proposes une voiture, mentionne toujours son ID. "
            "6) N'invente aucune voiture ni caractéristique."
        )

        # ---- filtrage puis RAG ----
        candidates = search_voitures(last_user_msg, k=5, constraints=constraints)
        candidates_lines = "\n".join(format_car(v) for v in candidates)
        print(f"[rag] candidates (top {len(candidates)}):\n{candidates_lines}")
        filtered = apply_filters(candidates, constraints)

        # ---- contexte filtres ----
        filters_text = (
            "FILTRES APPLIQUÉS:\n"
            f"- marque: {constraints.get('marque', 'non spécifiée')}\n"
            f"- carburant: {constraints.get('carburant', 'non spécifié')}\n"
            f"- transmission: {constraints.get('transmission', 'non spécifiée')}\n"
            f"- prix_max: {constraints.get('prix_max', 'non spécifié')}\n"
            f"- km_max: {constraints.get('km_max', 'non spécifié')}\n"
            f"- annee_min: {constraints.get('annee_min', 'non spécifiée')}\n"
            f"- annee_max: {constraints.get('annee_max', 'non spécifiée')}\n"
        )

        # ---- IMPORTANT: le LLM ne voit QUE le catalogue filtré ----
        if filtered:
            cars_for_prompt = filtered[:5]
            rag_lines = "\n".join(format_car(v) for v in cars_for_prompt)
            rag_context = (
                filters_text
                + "\nCATALOGUE FILTRÉ:\n"
                + rag_lines
                + "\n"
            )
        else:
            rag_context = (
                filters_text
                + "\nCATALOGUE FILTRÉ:\n"
                "- (Aucun résultat)\n"
            )

    else:
        system_prompt = (
            "Tu es un assistant spécialisé pour aider l'utilisateur à trouver une voiture à acheter. "
            "Même si la question est hors sujet, réponds brièvement puis oriente vers la recherche de voiture "
            "en demandant ce que l'utilisateur cherche (budget, type, carburant, boîte, usage)."
        )
        rag_context = ""

    # ---- construire prompt final ----
    prompt = system_prompt.strip() + "\n\n"
    if rag_context:
        prompt += rag_context + "\n"

    for msg in effective_history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            prompt += f"Utilisateur: {content}\n"
        else:
            prompt += f"Assistant: {content}\n"
    prompt += "Assistant:"

    print(f"[chat] calling LLM | max_tokens={get_max_tokens()}")
    llm_start = time.perf_counter()
    llm_reply = generate_response(prompt)
    llm_ms = (time.perf_counter() - llm_start) * 1000
    total_ms = (time.perf_counter() - start_ts) * 1000
    print(f"[chat] LLM done | llm_ms={llm_ms:.1f} total_ms={total_ms:.1f}")
    return jsonify({"reply": llm_reply})

def _warmup_heavy() -> None:
    print("[warmup] starting heavy loads in background...")
    t0 = time.perf_counter()
    try:
        warmup_rag()
        warmup_llm()
    finally:
        ms = (time.perf_counter() - t0) * 1000
        print(f"[warmup] done | ms={ms:.1f}")


if __name__ == "__main__":
    # Evite le double warmup quand le reloader Flask relance le process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        threading.Thread(target=_warmup_heavy, daemon=True).start()
    app.run(debug=False)
