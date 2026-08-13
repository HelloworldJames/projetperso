"""Sauvegarde JSON atomique sans donnees de vendeur."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .parser import AnnonceExtraite


def maintenant_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def sauvegarder_annonces(annonces: tuple[AnnonceExtraite, ...], chemin: Path) -> dict:
    chemin = Path(chemin)
    existantes = {}
    if chemin.exists():
        try:
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
            existantes = {
                str(element["identifiant"]): element
                for element in contenu.get("annonces", [])
                if isinstance(element, dict) and element.get("identifiant")
            }
        except (OSError, json.JSONDecodeError, KeyError):
            existantes = {}

    date = maintenant_iso()
    nouvelles = 0
    for annonce in annonces:
        ancienne = existantes.get(annonce.identifiant)
        nouvelles += int(ancienne is None)
        element = asdict(annonce)
        element["premiere_observation"] = (
            ancienne.get("premiere_observation", date) if ancienne else date
        )
        element["derniere_observation"] = date
        existantes[annonce.identifiant] = element

    resultat = {
        "derniere_mise_a_jour": date,
        "annonces": list(existantes.values()),
    }
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(f"{chemin.suffix}.tmp")
    temporaire.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(chemin)
    return {"total": len(existantes), "nouvelles": nouvelles}
