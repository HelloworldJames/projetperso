import hashlib
import json
import re

from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = (
    "https://bons-plans.easycash.fr/"
    "informatique/ordinateur-bureau/pc-gaming"
)

BASE_URL = "https://bons-plans.easycash.fr"


USER_AGENT = (
    "PC-Hunter/0.1 "
    "(personal second-hand market monitor)"
)


PRIX_REGEX = re.compile(
    r"(\d{1,4}(?:[\s\u00a0]\d{3})*[.,]\d{2})\s*€?"
)


def nettoyer_texte(texte):

    return " ".join(
        texte
        .replace("\xa0", " ")
        .split()
    )


def convertir_prix(texte):

    correspondance = PRIX_REGEX.search(
        texte
    )

    if not correspondance:
        return None

    prix_texte = (
        correspondance
        .group(1)
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    try:

        prix = float(
            prix_texte
        )

        if prix.is_integer():
            return int(prix)

        return prix

    except ValueError:

        return None


def generer_identifiant(
    titre,
    prix,
    url
):

    base = (
        url
        or
        f"{titre}|{prix}"
    )

    empreinte = hashlib.sha1(
        base.encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    return (
        f"EASYCASH-{empreinte}"
    )


def trouver_conteneur_produit(
    titre_html
):

    element = titre_html

    # On remonte progressivement dans le HTML
    # pour trouver le bloc contenant aussi le prix.

    for _ in range(8):

        if element is None:
            break

        texte = nettoyer_texte(
            element.get_text(
                " ",
                strip=True
            )
        )

        prix = convertir_prix(
            texte
        )

        if prix is not None:
            return element

        element = element.parent

    return titre_html.parent


def trouver_url(
    titre_html,
    conteneur
):

    lien = titre_html.find_parent(
        "a",
        href=True
    )

    if lien is None and conteneur:

        lien = conteneur.find(
            "a",
            href=True
        )

    if lien is None:
        return None

    href = lien.get(
        "href"
    )

    if not href:
        return None

    return urljoin(
        BASE_URL,
        href
    )


def extraire_annonces(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    annonces = []

    deja_vues = set()


    # Les titres produits Easy Cash
    # apparaissent actuellement dans des H2.

    for h2 in soup.find_all(
        "h2"
    ):

        titre = nettoyer_texte(
            h2.get_text(
                " ",
                strip=True
            )
        )


        # Sur la page PC Gaming,
        # les vrais produits commencent généralement par PC.

        if not titre.lower().startswith(
            "pc "
        ):
            continue


        conteneur = (
            trouver_conteneur_produit(
                h2
            )
        )


        texte_conteneur = nettoyer_texte(
            conteneur.get_text(
                " ",
                strip=True
            )
        )


        prix = convertir_prix(
            texte_conteneur
        )


        if prix is None:
            continue


        url = trouver_url(
            h2,
            conteneur
        )


        identifiant = (
            generer_identifiant(
                titre=titre,
                prix=prix,
                url=url
            )
        )


        # Évite les doublons HTML
        if identifiant in deja_vues:
            continue


        deja_vues.add(
            identifiant
        )


        annonces.append(
            {
                "identifiant":
                    identifiant,

                "titre":
                    titre,

                "prix":
                    prix,

                # Pour le moment on utilise le titre
                # comme description minimale.
                # Le prochain module ira chercher
                # les caractéristiques détaillées.
                "description":
                    titre,

                "localisation":
                    "Inconnue",

                "plateforme":
                    "Easy Cash",

                "url":
                    url,

                "date_publication":
                    None,
            }
        )


    return annonces


def tester_extraction():

    print()
    print(
        "========================================"
    )

    print(
        "🧪 EXTRACTION RÉELLE EASY CASH"
    )

    print(
        "========================================"
    )

    print()


    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            "text/html,application/xhtml+xml",

        "Accept-Language":
            "fr-FR,fr;q=0.9",
    }


    try:

        reponse = requests.get(
            URL,
            headers=headers,
            timeout=20,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Easy Cash inaccessible :",
            erreur
        )

        return


    print(
        "📡 HTTP :",
        reponse.status_code
    )


    if reponse.status_code != 200:

        print(
            "❌ Extraction annulée."
        )

        return


    annonces = extraire_annonces(
        reponse.text
    )


    print(
        "📦 Produits réels extraits :",
        len(annonces)
    )

    print()


    for numero, annonce in enumerate(
        annonces[:15],
        start=1
    ):

        print(
            f"#{numero}"
        )

        print(
            "📝",
            annonce[
                "titre"
            ]
        )

        print(
            "💵",
            annonce[
                "prix"
            ],
            "€"
        )

        print(
            "🔗",
            annonce[
                "url"
            ]
        )

        print()


    # ========================================================
    # SAUVEGARDE DU TEST
    # ========================================================

    racine = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    fichier = (
        racine
        / "data"
        / "easycash_real.json"
    )


    fichier.write_text(
        json.dumps(
            annonces,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print(
        "💾 Données enregistrées :",
        fichier
    )

    print()

    print(
        "✅ Aucune information vendeur collectée."
    )


if __name__ == "__main__":

    tester_extraction()