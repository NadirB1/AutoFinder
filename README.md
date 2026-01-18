AutoFinder - Assistant IA pour l’achat de voitures d’occasion
============================================================

Pré-requis
----------
- Système : Linux (Ubuntu recommandé)
- Python : 3.10 ou supérieur
- Connexion Internet requise au premier lancement (embeddings)

1) Création et activation de l’environnement virtuel
----------------------------------------------------
```bash
python -m venv venv
# ou :
python3 -m venv venv
```

Linux / Mac :
```bash
source venv/bin/activate
```

Windows :
```bat
venv\Scripts\activate
```

2) Installation des dépendances
-------------------------------
```bash
pip install -r requirements.txt
```

Si une erreur survient :
```bash
python -m pip install -r requirements.txt
```

3) Installation du modèle LLM (GGUF)
------------------------------------
Télécharger le modèle Optimus 7B (format GGUF) depuis :
https://huggingface.co/TheBloke/Optimus-7B-GGUF/blob/main/optimus-7b.Q5_K_M.gguf
(ou tout autre modèle GGUF compatible avec llama.cpp et supportant le français)

Placer le fichier sur le système, puis mettre à jour la variable MODEL_PATH
dans le fichier :
AutoFinder/llm_engine.py (ligne 6)

Exemple :
```python
MODEL_PATH = "/chemin/vers/optimus-7b.Q5_K_M.gguf"
```

4) RAG et base de données vectorielle
------------------------------------
- Le modèle d’embeddings (all-MiniLM-L6-v2) est téléchargé automatiquement au premier lancement.
- La base ChromaDB est persistée dans le dossier :
  AutoFinder/chroma_db
  (si introuvable ou si voitures.json change, elle est recréée automatiquement)

5) Lancement de l’application
-----------------------------
```bash
python app.py
```
(à exécuter depuis la racine du projet)  
⚠️ Le premier lancement peut prendre plusieurs minutes (chargement du modèle et génération des embeddings).

L’application est accessible via :  
http://127.0.0.1:5000
