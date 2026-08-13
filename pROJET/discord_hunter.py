"""Vues Discord pures et testables pour Hunter V1.5."""

import sqlite3

from contextlib import closing

from collector.source_registry import lister_sources_hunter
from database.analysis import (
    lister_analyses_recentes,
    obtenir_derniere_analyse,
)
from database.listing import DB_PATH
from database.watchlist import lister_watchlist


def _prix(valeur):
    if valeur is None:
        return "?"
    nombre = float(valeur)
    return str(int(nombre)) if nombre.is_integer() else str(round(nombre, 2))


def _ligne_analyse(element, position=None):
    analyse = element["analyse"]
    prefixe = f"**#{position} — " if position else "**"
    lignes = [
        f"{prefixe}{element['titre']}**",
        f"Décision : **{element['decision']}** · score **{_prix(element['score_affaire'])}/100**",
        f"Prix : **{_prix(element['prix'])} €** · achat max **{_prix(element['prix_achat_max'])} €**",
    ]
    if element.get("valeur_probable") is not None:
        lignes.append(
            f"Estimation : **{_prix(element['valeur_probable'])} €** · "
            f"marge prudente **{_prix(element['marge_nette_prudente'])} €**"
        )
    lignes.append(f"Source : {element['plateforme']}")
    if element.get("url"):
        lignes.append(element["url"])
    action = analyse.get("action_recommandee")
    if action:
        lignes.append(f"Conseil : {action}")
    return lignes


def construire_message_pepites(limite=3, db_path=DB_PATH):
    resultats = lister_analyses_recentes(
        limite=limite,
        decisions=("PEPITE", "BONNE_AFFAIRE"),
        db_path=db_path,
    )
    if not resultats:
        return "💎 **Aucune pépite validée actuellement.** Hunter continue l'analyse."

    lignes = ["💎 **HUNTER — TOP 3 PÉPITES**", ""]
    for position, resultat in enumerate(resultats, start=1):
        lignes.extend(_ligne_analyse(resultat, position))
        lignes.append("")
    return "\n".join(lignes)[:1900]


def construire_message_analyse(reference, db_path=DB_PATH):
    resultat = obtenir_derniere_analyse(reference, db_path=db_path)
    if resultat is None:
        return (
            "🔎 Aucune analyse trouvée. Ouvrez l'annonce avec le Compagnon Hunter, "
            "puis utilisez son identifiant ou son URL."
        )
    return "\n".join(["🧠 **ANALYSE HUNTER V1.5**", "", *_ligne_analyse(resultat)])[:1900]


def construire_message_veille(limite=10, db_path=DB_PATH):
    annonces = lister_watchlist(actif=True, db_path=db_path)[:limite]
    if not annonces:
        return "📭 **Aucune annonce dans la veille.**"
    lignes = ["👁️ **VEILLE HUNTER**", ""]
    for annonce in annonces:
        manquants = [
            nom
            for cle, nom in (
                ("titre", "titre"),
                ("dernier_prix_connu", "prix"),
                ("description", "description"),
                ("localisation", "localisation"),
            )
            if annonce.get(cle) in (None, "")
        ]
        statut = "analyse disponible" if annonce.get("titre") and annonce.get("dernier_prix_connu") is not None else "capture attendue"
        lignes.append(
            f"**#{annonce['id']} · {annonce.get('titre') or 'Lien à capturer'}**\n"
            f"{annonce['plateforme']} · {_prix(annonce.get('dernier_prix_connu'))} € · {statut}"
        )
        if manquants:
            lignes.append("Qualité à améliorer : " + ", ".join(manquants))
        lignes.append(annonce["url"])
        lignes.append("")
    return "\n".join(lignes)[:1900]


def construire_message_disparues(limite=10, db_path=DB_PATH):
    with closing(sqlite3.connect(db_path)) as connexion:
        lignes_db = connexion.execute(
            """
            SELECT titre, prix, plateforme, url, date_disparition
            FROM presence_annonces
            WHERE active = 0
            ORDER BY date_disparition DESC
            LIMIT ?
            """,
            (max(1, min(int(limite), 20)),),
        ).fetchall()
    if not lignes_db:
        return "👻 **Aucune disparition mémorisée.**"

    lignes = [
        "👻 **ANNONCES DISPARUES DU RADAR**",
        "Une disparition signifie seulement « plus vue » : vente, retrait, expiration ou indisponibilité de la source restent possibles.",
        "",
    ]
    for titre, prix, plateforme, url, date_disparition in lignes_db:
        lignes.append(f"**{titre or 'Annonce'}** · {_prix(prix)} € · {plateforme}")
        lignes.append(f"Dernière disparition : {str(date_disparition).replace('T', ' ')[:16]}")
        if url:
            lignes.append(url)
        lignes.append("")
    return "\n".join(lignes)[:1900]


def construire_message_sources():
    icones = {
        "actif": "🟢",
        "assisté": "🟡",
        "optionnel": "⚪",
        "clé disponible": "🟡",
        "identifiants à valider": "🟠",
        "à configurer": "⚪",
        "inactif": "🔴",
    }
    lignes = ["🌐 **SOURCES HUNTER V1.5**", ""]
    for source in lister_sources_hunter():
        lignes.append(
            f"{icones.get(source['statut'], '⚪')} **{source['nom']}** — {source['statut']}\n"
            f"{source['mode']}"
        )
    return "\n\n".join(lignes)[:1900]

