from llama_cpp import Llama
import os
import time

# Chemin vers ton modèle (déjà testé, fonctionnel)
MODEL_PATH = "/home/nadirb/.cache/huggingface/hub/models--TheBloke--Optimus-7B-GGUF/snapshots/0ee06ec1196c3985775957c783c413a3e576ef11/optimus-7b.Q5_K_M.gguf"
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))

_llm = None

def _get_llm() -> Llama:
    global _llm
    if _llm is None:
        print("[llm] loading model...")
        t0 = time.perf_counter()
        _llm = Llama(
            model_path=MODEL_PATH,
            n_threads=4,
            n_ctx=2048,
            n_batch=128,
            verbose=False
        )
        ms = (time.perf_counter() - t0) * 1000
        print(f"[llm] model loaded | ms={ms:.1f}")
    return _llm

def warmup() -> None:
    _get_llm()

def get_max_tokens() -> int:
    return MAX_TOKENS

def generate_response(prompt: str) -> str:
    """
    Envoie un prompt complet au LLM et retourne la réponse texte.
    """
    llm = _get_llm()
    output = llm(
        prompt,
        max_tokens=MAX_TOKENS,
        stop=["\nUtilisateur:", "\nUser:", "\n###", "</s>"]
    )
    return output["choices"][0]["text"].strip()
