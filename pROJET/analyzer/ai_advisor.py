"""Conseiller IA optionnel pour expliquer une analyse Hunter.

Le calcul financier reste déterministe. L'IA ne peut ni inventer une valeur,
ni remplacer les gardes de confiance du moteur.
"""

import json
import os

import requests


PROMPT_SYSTEME = """Tu es le conseiller PC Hunter. Tu reçois une annonce et
une analyse financière déjà calculée. Réponds uniquement en JSON avec les clés
resume, points_forts, risques, verification_prioritaire et conseil_negociation.
N'invente aucun composant, aucun prix et aucune donnée vendeur. Si une donnée
manque, indique-le clairement. Le verdict déterministe fourni fait foi."""


def _extraire_texte_openai(reponse):
    morceaux = []
    for element in reponse.get("output", []):
        for contenu in element.get("content", []):
            if contenu.get("type") == "output_text" and contenu.get("text"):
                morceaux.append(contenu["text"])
    return "\n".join(morceaux).strip()


def _appel_openai(contenu):
    cle = os.getenv("OPENAI_API_KEY")
    if not cle:
        return None

    modele = os.getenv("HUNTER_OPENAI_MODEL", "gpt-5-mini")
    reponse = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {cle}",
            "Content-Type": "application/json",
        },
        json={
            "model": modele,
            "instructions": PROMPT_SYSTEME,
            "input": json.dumps(contenu, ensure_ascii=False),
        },
        timeout=30,
    )
    reponse.raise_for_status()
    texte = _extraire_texte_openai(reponse.json())
    return json.loads(texte) if texte else None


def _appel_ollama(contenu):
    modele = os.getenv("HUNTER_OLLAMA_MODEL")
    if not modele:
        return None

    adresse = os.getenv("HUNTER_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    reponse = requests.post(
        f"{adresse}/api/chat",
        json={
            "model": modele,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": PROMPT_SYSTEME},
                {"role": "user", "content": json.dumps(contenu, ensure_ascii=False)},
            ],
        },
        timeout=60,
    )
    reponse.raise_for_status()
    texte = reponse.json().get("message", {}).get("content", "")
    return json.loads(texte) if texte else None


def conseiller_avec_ia(annonce, analyse):
    fournisseur = os.getenv("HUNTER_AI_PROVIDER", "auto").strip().lower()
    contenu = {
        "annonce": {
            "titre": annonce.titre,
            "prix": annonce.prix,
            "description": annonce.description,
            "localisation": annonce.localisation,
            "plateforme": annonce.plateforme,
        },
        "analyse_hunter": {
            "decision": analyse.get("decision"),
            "score_affaire": analyse.get("score_affaire"),
            "prix_achat_max": analyse.get("prix_achat_max"),
            "marge_nette_prudente": analyse.get("marge_nette_prudente"),
            "estimation": analyse.get("estimation"),
            "raisons": analyse.get("raisons"),
        },
    }

    try:
        if fournisseur == "openai":
            conseil = _appel_openai(contenu)
            nom = "OpenAI"
        elif fournisseur == "ollama":
            conseil = _appel_ollama(contenu)
            nom = "Ollama local"
        elif fournisseur == "auto" and os.getenv("OPENAI_API_KEY"):
            conseil = _appel_openai(contenu)
            nom = "OpenAI"
        elif fournisseur == "auto" and os.getenv("HUNTER_OLLAMA_MODEL"):
            conseil = _appel_ollama(contenu)
            nom = "Ollama local"
        else:
            return None
    except (requests.RequestException, ValueError, json.JSONDecodeError) as erreur:
        return {
            "actif": False,
            "fournisseur": fournisseur,
            "erreur": str(erreur)[:300],
        }

    if not isinstance(conseil, dict):
        return None

    return {
        "actif": True,
        "fournisseur": nom,
        **conseil,
    }

