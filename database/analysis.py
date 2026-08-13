"""Persistance des analyses Hunter V1.5.

La table ne contient que les informations de l'annonce et le résultat Hunter.
Aucune donnée vendeur n'est acceptée ou enregistrée.
"""

import hashlib
import json
import sqlite3

from contextlib import closing
from datetime import datetime
from pathlib import Path

from database.listing import DB_PATH


def maintenant_iso():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _chemin_db(db_path):
    return Path(db_path) if db_path is not None else DB_PATH


def _connexion(db_path):
    connexion = sqlite3.connect(_chemin_db(db_path))
    connexion.row_factory = sqlite3.Row
    return connexion


def initialiser_analyses(db_path=DB_PATH):
    with closing(_connexion(db_path)) as connexion:
        with connexion:
            connexion.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses_hunter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT NOT NULL UNIQUE,
                    plateforme TEXT NOT NULL,
                    identifiant TEXT NOT NULL,
                    url TEXT,
                    titre TEXT NOT NULL,
                    prix REAL NOT NULL,
                    decision TEXT NOT NULL,
                    score_affaire REAL NOT NULL,
                    valeur_basse REAL,
                    valeur_probable REAL,
                    valeur_haute REAL,
                    prix_achat_max REAL,
                    marge_nette_prudente REAL,
                    confiance_score REAL,
                    analyse_json TEXT NOT NULL,
                    date_analyse TEXT NOT NULL
                )
                """
            )
            connexion.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analyses_hunter_classement
                ON analyses_hunter (
                    score_affaire DESC,
                    marge_nette_prudente DESC,
                    date_analyse DESC
                )
                """
            )


def _signature_analyse(annonce):
    donnees = {
        "plateforme": str(getattr(annonce, "plateforme", "")),
        "identifiant": str(getattr(annonce, "identifiant", "")),
        "url": str(getattr(annonce, "url", "") or ""),
        "titre": str(getattr(annonce, "titre", "")),
        "description": str(getattr(annonce, "description", "")),
        "localisation": str(getattr(annonce, "localisation", "")),
        "prix": float(getattr(annonce, "prix", 0)),
    }
    contenu = json.dumps(
        donnees,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def enregistrer_analyse(annonce, analyse, db_path=DB_PATH):
    initialiser_analyses(db_path)
    signature = _signature_analyse(annonce)
    date_analyse = maintenant_iso()
    estimation = analyse.get("estimation", {})

    with closing(_connexion(db_path)) as connexion:
        with connexion:
            connexion.execute(
                """
                INSERT OR IGNORE INTO analyses_hunter (
                    signature,
                    plateforme,
                    identifiant,
                    url,
                    titre,
                    prix,
                    decision,
                    score_affaire,
                    valeur_basse,
                    valeur_probable,
                    valeur_haute,
                    prix_achat_max,
                    marge_nette_prudente,
                    confiance_score,
                    analyse_json,
                    date_analyse
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signature,
                    str(annonce.plateforme),
                    str(annonce.identifiant),
                    annonce.url,
                    annonce.titre,
                    float(annonce.prix),
                    analyse["decision"],
                    float(analyse.get("score_affaire", 0)),
                    estimation.get("valeur_basse"),
                    estimation.get("valeur_probable"),
                    estimation.get("valeur_haute"),
                    analyse.get("prix_achat_max"),
                    analyse.get("marge_nette_prudente"),
                    estimation.get("confiance_score"),
                    json.dumps(analyse, ensure_ascii=False, default=str),
                    date_analyse,
                ),
            )

        ligne = connexion.execute(
            "SELECT * FROM analyses_hunter WHERE signature = ?",
            (signature,),
        ).fetchone()

    resultat = dict(ligne)
    resultat["analyse"] = json.loads(resultat.pop("analyse_json"))
    return resultat


def lister_analyses_recentes(limite=20, decisions=None, db_path=DB_PATH):
    initialiser_analyses(db_path)
    limite = max(1, min(int(limite), 100))
    parametres = []
    filtre = ""

    if decisions:
        decisions = tuple(str(decision) for decision in decisions)
        marqueurs = ", ".join("?" for _ in decisions)
        filtre = f"WHERE decision IN ({marqueurs})"
        parametres.extend(decisions)

    with closing(_connexion(db_path)) as connexion:
        lignes = connexion.execute(
            f"""
            SELECT *
            FROM analyses_hunter
            {filtre}
            ORDER BY score_affaire DESC,
                     marge_nette_prudente DESC,
                     date_analyse DESC,
                     id DESC
            """,
            tuple(parametres),
        ).fetchall()

    resultats = []
    references_vues = set()

    for ligne in lignes:
        reference = (
            ligne["plateforme"],
            ligne["identifiant"],
        )
        if reference in references_vues:
            continue
        references_vues.add(reference)
        resultat = dict(ligne)
        resultat["analyse"] = json.loads(resultat.pop("analyse_json"))
        resultats.append(resultat)
        if len(resultats) >= limite:
            break

    return resultats


def obtenir_derniere_analyse(reference, db_path=DB_PATH):
    texte = str(reference or "").strip()
    if not texte:
        return None

    initialiser_analyses(db_path)
    with closing(_connexion(db_path)) as connexion:
        ligne = connexion.execute(
            """
            SELECT *
            FROM analyses_hunter
            WHERE identifiant = ? OR url = ?
            ORDER BY date_analyse DESC, id DESC
            LIMIT 1
            """,
            (texte, texte),
        ).fetchone()

    if ligne is None:
        return None

    resultat = dict(ligne)
    resultat["analyse"] = json.loads(resultat.pop("analyse_json"))
    return resultat

