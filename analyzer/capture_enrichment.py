"""Enrichissement prudent d'une capture visible avant analyse.

Le contexte brut sert uniquement en mémoire pour repérer les caractéristiques
techniques. Il n'est jamais retourné ni enregistré dans SQLite.
"""

import re

from analyzer.components import detecter_composants
from collector.models import Annonce


MOTIFS_SENSIBLES = (
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)"),
)


def _texte_propre(valeur, limite):
    texte = " ".join(str(valeur or "").split())
    for motif in MOTIFS_SENSIBLES:
        texte = motif.sub("[coordonnée retirée]", texte)
    return texte[:limite] or None


def _description_technique(titre, contexte):
    if not contexte:
        return None

    temporaire = Annonce(
        identifiant="capture-temporaire",
        titre=titre or "Annonce PC",
        prix=0,
        description=contexte,
    )
    detection = detecter_composants(temporaire)
    morceaux = []

    for cle, libelle in (
        ("cpu", "CPU"),
        ("gpu", "GPU"),
        ("ram", "RAM"),
        ("stockage", "Stockage"),
        ("apple_chip", "Puce Apple"),
    ):
        valeurs = detection.get(cle) or []
        if valeurs:
            morceaux.append(f"{libelle}: {', '.join(valeurs)}")

    return "Configuration détectée — " + "; ".join(morceaux) if morceaux else None


def enrichir_capture(payload):
    """Retourne uniquement les champs autorisés et utiles à Hunter."""
    titre = _texte_propre(payload.get("titre"), 500)
    description = _texte_propre(payload.get("description"), 10_000)
    contexte = _texte_propre(payload.get("contexte_technique"), 30_000)

    if not description:
        description = _description_technique(titre, contexte)

    return {
        "url": payload.get("url"),
        "plateforme": _texte_propre(payload.get("plateforme"), 100),
        "identifiant": _texte_propre(payload.get("identifiant"), 200),
        "titre": titre,
        "prix": payload.get("prix"),
        "description": description,
        "localisation": _texte_propre(payload.get("localisation"), 300),
        "date_publication": _texte_propre(payload.get("date_publication"), 100),
    }

