"""Transforme une capture minimale du navigateur en entree de watchlist.

Ce module ne contacte jamais la plateforme d'origine. Le navigateur transmet
uniquement les champs de l'annonce que l'utilisateur a choisi d'analyser.
"""

import hashlib
import json

from database.watchlist import (
    ajouter_watchlist,
    lister_watchlist,
    normaliser_url,
)
from database.analysis import obtenir_derniere_analyse
from database.listing import DB_PATH
from analyzer.capture_enrichment import enrichir_capture
from analyzer.instant import analyser_annonce_immediate
from collector.models import Annonce


LIMITES_TEXTE = {
    "titre": 500,
    "description": 10_000,
    "localisation": 300,
    "date_publication": 100,
}


def _nettoyer_texte(valeur, champ):
    if valeur is None:
        return None

    texte = " ".join(str(valeur).split())

    if not texte:
        return None

    return texte[:LIMITES_TEXTE[champ]]


def _annonce_existante(url, db_path):
    for annonce in lister_watchlist(
        actif=None,
        db_path=db_path,
    ):
        if annonce["url"] == url:
            return annonce

    return None


def _champs_manquants(annonce):
    champs_requis = (
        ("titre", "titre"),
        ("dernier_prix_connu", "prix"),
        ("description", "description"),
        ("localisation", "localisation"),
    )
    return [
        libelle
        for champ, libelle in champs_requis
        if annonce.get(champ) in (None, "")
    ]


def _identifiant_capture(annonce, analyse):
    if analyse:
        empreinte = analyse["signature"]
    else:
        donnees = {
            "url": annonce.get("url"),
            "titre": annonce.get("titre"),
            "prix": annonce.get("dernier_prix_connu"),
            "description": annonce.get("description"),
            "localisation": annonce.get("localisation"),
        }
        contenu = json.dumps(
            donnees,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        empreinte = hashlib.sha256(
            contenu.encode("utf-8")
        ).hexdigest()

    return f"companion-{annonce['id']}-{empreinte[:20]}"


def lister_resultats_companion(limite=50, db_path=None):
    """Expose les captures Companion locales sans aucune donnee vendeur."""
    db_path = db_path or DB_PATH
    limite = max(1, min(int(limite), 100))
    resultats = []

    for annonce in lister_watchlist(actif=None, db_path=db_path):
        if annonce.get("mode_acquisition") != "companion_local":
            continue

        analyse = obtenir_derniere_analyse(
            annonce["url"],
            db_path=db_path,
        )
        date_analyse = analyse.get("date_analyse") if analyse else None
        resultat = {
            "capture_id": _identifiant_capture(annonce, analyse),
            "mode_acquisition": "companion_local",
            "watchlist_id": annonce["id"],
            "plateforme": annonce["plateforme"],
            "identifiant": annonce.get("identifiant"),
            "url": annonce["url"],
            "titre": annonce.get("titre"),
            "prix": annonce.get("dernier_prix_connu"),
            "description": annonce.get("description"),
            "localisation": annonce.get("localisation"),
            "date_publication": annonce.get("date_publication"),
            "date_capture": annonce.get("date_ajout"),
            "derniere_observation": annonce.get("derniere_observation"),
            "date_analyse": date_analyse,
            "actif": annonce.get("actif", True),
            "statut": "analyse_disponible" if analyse else "en_etude",
            "champs_manquants": _champs_manquants(annonce),
            "analyse_hunter": analyse.get("analyse") if analyse else None,
            "notification_detection_envoyee": annonce.get(
                "notification_detection_envoyee",
                False,
            ),
        }
        resultat["date_evenement"] = (
            date_analyse
            or resultat["derniere_observation"]
            or resultat["date_capture"]
        )
        resultats.append(resultat)

    resultats.sort(
        key=lambda resultat: resultat.get("date_evenement") or "",
        reverse=True,
    )
    return resultats[:limite]


def importer_capture_navigateur(payload, db_path=None):
    """Enregistre une annonce visible sans conserver de donnee vendeur."""
    db_path = db_path or DB_PATH
    if not isinstance(payload, dict):
        raise ValueError("La capture doit etre un objet JSON.")

    capture = enrichir_capture(payload)
    url = normaliser_url(capture.get("url"))
    existante = _annonce_existante(
        url,
        db_path,
    )
    ancien_prix = (
        existante.get("dernier_prix_connu")
        if existante
        else None
    )

    annonce = ajouter_watchlist(
        url=url,
        plateforme=capture.get("plateforme"),
        identifiant=capture.get("identifiant"),
        titre=_nettoyer_texte(capture.get("titre"), "titre"),
        prix_connu=capture.get("prix"),
        description=_nettoyer_texte(
            capture.get("description"),
            "description",
        ),
        localisation=_nettoyer_texte(
            capture.get("localisation"),
            "localisation",
        ),
        date_publication=_nettoyer_texte(
            capture.get("date_publication"),
            "date_publication",
        ),
        db_path=db_path,
        mode_acquisition=(
            capture.get("mode_acquisition")
            or "companion_local"
        ),
    )

    nouveau_prix = annonce.get("dernier_prix_connu")
    champs_manquants = _champs_manquants(annonce)

    analyse = None
    if annonce.get("titre") and nouveau_prix is not None:
        fiche = Annonce(
            identifiant=annonce.get("identifiant") or f"watchlist-{annonce['id']}",
            titre=annonce["titre"],
            prix=nouveau_prix,
            description=annonce.get("description") or annonce["titre"],
            localisation=annonce.get("localisation") or "Inconnue",
            plateforme=annonce["plateforme"],
            url=annonce["url"],
            date_publication=annonce.get("date_publication"),
        )
        fiche.origine_watchlist = True
        analyse = analyser_annonce_immediate(
            fiche,
            db_path=db_path,
        )

    return {
        "ok": True,
        "watchlist_id": annonce["id"],
        "plateforme": annonce["plateforme"],
        "identifiant": annonce.get("identifiant"),
        "url": annonce["url"],
        "cree": annonce["cree"],
        "statut": "analyse_disponible" if analyse else "en_etude",
        "champs_manquants": champs_manquants,
        "analyse": analyse,
        "ancien_prix": ancien_prix,
        "nouveau_prix": nouveau_prix,
        "prix_change": (
            ancien_prix is not None
            and nouveau_prix is not None
            and ancien_prix != nouveau_prix
        ),
    }
