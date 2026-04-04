from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from dotenv import load_dotenv
import io
import json
import re
from contextlib import redirect_stdout
import mimetypes
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Disable caching for static files so the browser reloads app.js/style.css immediately
@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Configuration API
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise ValueError("La variable d'environnement GENAI_API_KEY n'est pas définie.")
client = genai.Client(api_key=api_key)


def extract_json_from_text(text: str) -> Optional[str]:
    start = text.find('{')
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=0):
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:start + i + 1]
    return None


def verifier_information(file_paths=None, url=None, texte_info=None):
    print("--- 🔍 Analyse Menacraft en cours ---")
    
    # Le prompt est conçu pour répondre aux exigences de ton projet (Axes 1, 2 et 3)
    prompt = """
    Tu es un expert en vérification de faits pour le projet Menacraft.
    Analyse les éléments fournis (image, vidéo, URL et/ou texte) :
    1. Si une URL est fournie, vérifie qu'elle existe et est publiquement accessible. Si c'est YouTube, renvoie "video existe".
    2. Utilise Google Search pour vérifier si le contenu a déjà été publié.
    3. Identifie le type de contenu : image, vidéo, article web, etc.
    4. Compare le texte fourni par l'utilisateur avec les faits trouvés sur le web.
    5. Identifie la nature exacte du contenu en entrée.
    6. Si le contenu existe déjà sur internet, indique l'URL source.
    7. Indique si l'image est purement réelle, générée par IA, ou modifiée par IA.

    Réponds uniquement par un objet JSON valide et rien d'autre, sans texte additionnel.
    Exemple pour un lien YouTube qui existe :
    {"nature":"video","exists_on_internet":"oui","status":"Publié","confidence":95,"source_url":"https://www.youtube.com/watch?v=...","message":"video existe"}

    Règles de réponse :
    - Pour une URL YouTube qui existe : nature="video", message="video existe", exists_on_internet="oui", status="Publié".
    - Pour une URL web existante : nature="url", message="url existe", exists_on_internet="oui", status="Publié".
    - Pour une image réelle publiée : nature="image", message="image réelle", exists_on_internet="oui", status="Publié".
    - Pour une image générée par IA : nature="image", message="image générer en ai", status="IA généré", exists_on_internet="non" ou "oui".
    - Pour une image modifiée par IA : nature="image", message="image peut étre modifiée par l'ia", status="Suspect", exists_on_internet="oui" ou "non".
    - le champ "confidence" doit être un entier entre 0 et 100.
    - le champ "exists_on_internet" doit être "oui" ou "non".
    """

    contenu = [prompt]
    
    # Gestion des fichiers (image/vidéo)
    if file_paths:
        for index, path in enumerate(file_paths, start=1):
            try:
                with open(path, "rb") as f:
                    file_data = f.read()
            except FileNotFoundError:
                print(f"❌ Erreur : Le fichier '{path}' n'existe pas dans le dossier.")
                return

            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = "application/octet-stream"

            contenu.append(f"Fichier {index} : {os.path.basename(path)}, type = {mime_type}")
            contenu.append(types.Part.from_bytes(data=file_data, mime_type=mime_type))

    # Gestion de l'URL (Axe 1 : Authenticité)
    if url:
        contenu.append(f"URL à analyser : {url}")

    # Gestion du texte (Axe 2 : Consistance contextuelle)
    if texte_info:
        contenu.append(f"Information à vérifier : {texte_info}")

    try:
        # Appel à Gemini avec l'outil de recherche Google intégré
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contenu,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())]
            )
        )

        print("\n--- ✅ RÉSULTATS DE VÉRIFICATION ---")
        print(response.text)
        return response.text

    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")
        return f"Erreur : {e}"

@app.get("/")
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/verify")
async def verify_content(
    files: List[UploadFile] = File(default=[]),
    claim: str = Form(default=""),
    url: str = Form(default="")
):
    # Save uploaded files temporarily if provided
    file_paths = []
    if files:
        for upload in files:
            temp_path = f"temp_{upload.filename}"
            with open(temp_path, "wb") as f:
                f.write(await upload.read())
            file_paths.append(temp_path)

    # Capture the output of verifier_information
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        result = verifier_information(
            file_paths=file_paths,
            url=url or None,
            texte_info=claim or ""
        )
    output = output_buffer.getvalue()

    # Clean up temp files
    for temp_path in file_paths:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    status = "Non trouvé"
    source_url = ""
    message = "Aucune information trouvée."
    nature = "inconnue"
    exists_on_internet = False
    confidence = None

    if result:
        raw = result.strip()
        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            body = extract_json_from_text(raw)
            if body:
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = None

        if parsed:
            status = parsed.get("status", status)
            source_url = parsed.get("source_url", "")
            message = parsed.get("message", message)
            nature = parsed.get("nature", nature)
            exists_val = parsed.get("exists_on_internet", "non")
            exists_on_internet = str(exists_val).lower().startswith("o")
            confidence = parsed.get("confidence", confidence)
        else:
            lines = raw.split("\n")
            for line in lines:
                if "nature" in line.lower() and ":" in line:
                    nature = line.split(":", 1)[1].strip()
                elif "source_url" in line.lower() and ":" in line:
                    source_url = line.split(":", 1)[1].strip()
                elif "status" in line.lower() and ":" in line:
                    status = line.split(":", 1)[1].strip()
                elif "message" in line.lower() and ":" in line:
                    message = line.split(":", 1)[1].strip()
                elif "existe sur internet" in line.lower() and ":" in line:
                    exists_on_internet = line.split(":", 1)[1].strip().lower().startswith("o")

    if source_url:
        exists_on_internet = True

    if nature == "inconnue":
        if file_paths:
            guessed_mime = mimetypes.guess_type(file_paths[0])[0] or ""
            if guessed_mime.startswith("image"):
                nature = "image"
            elif guessed_mime.startswith("video"):
                nature = "video"
            elif guessed_mime.startswith("text"):
                nature = "texte"
            else:
                nature = "fichier"
        elif url:
            if "youtube.com" in url.lower() or "youtu.be" in url.lower():
                nature = "video"
            elif "facebook.com" in url.lower() or "instagram.com" in url.lower() or "tiktok.com" in url.lower():
                nature = "video"
            else:
                nature = "url"
        elif claim:
            nature = "texte"

    normalized_message = message.lower().replace("é", "e").replace("è", "e").replace("ê", "e")
    if "image reelle" in normalized_message:
        message = "image réelle"
        status = status if status in ["Publié", "IA généré", "Suspect"] else ("Publié" if exists_on_internet else "Publié")
        if confidence is None:
            confidence = 95
    elif "image generer en ai" in normalized_message or "image genere en ai" in normalized_message or "image générer en ai" in normalized_message or "ia generate" in normalized_message or "ai generated" in normalized_message:
        message = "image générer en ai"
        status = "IA généré"
        if confidence is None:
            confidence = 80
    elif "image peut etre modifiee par l ia" in normalized_message or "image peut etre modifiee par l'ia" in normalized_message or "modifiee par ia" in normalized_message or "modifiee par ai" in normalized_message:
        message = "image peut étre modifiée par l'ia"
        status = "Suspect"
        if confidence is None:
            confidence = 65
    elif "video existe" in normalized_message or "url existe" in normalized_message or ("existe" in normalized_message and nature in ["video", "url"]):
        if nature == "video" or "youtube" in (url or "").lower():
            message = "video existe"
        else:
            message = "url existe"
        status = "Publié"
        exists_on_internet = True
        if confidence is None:
            confidence = 90
    else:
        if confidence is None:
            confidence = 50
        if status not in ["Publié", "IA généré", "Suspect"]:
            if exists_on_internet:
                status = "Publié"
            else:
                status = "Suspect"

    if not message:
        message = "Aucune information trouvée."

    return JSONResponse({
        "status": status,
        "confidence": confidence,
        "source_url": source_url,
        "message": message,
        "nature": nature,
        "exists_on_internet": exists_on_internet,
        "full_output": result
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
