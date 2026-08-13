import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from collector.http import creer_session_http


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CACHE_FILE = str(
    PROJECT_ROOT
    / "data"
    / "paruvendu_cache.json"
)

CACHE_DURATION = 12 * 60 * 60


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .replace("", "")
        .split()
    )


def charger_cache():

    if not os.path.exists(
        CACHE_FILE
    ):
        return {}

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8",
        ) as fichier:

            data = json.load(
                fichier
            )

        if isinstance(
            data,
            dict,
        ):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def sauvegarder_cache(
    cache
):

    try:

        os.makedirs(
            os.path.dirname(
                CACHE_FILE
            ),
            exist_ok=True,
        )

        with open(
            CACHE_FILE,
            "w",
            encoding="utf-8",
        ) as fichier:

            json.dump(
                cache,
                fichier,
                ensure_ascii=False,
                indent=2,
            )

    except OSError as erreur:

        print(
            "ParuVendu : cache indisponible, "
            "collecte conservée sans cache :",
            erreur,
        )

        return False

    return True


def cache_valide(
    entree
):

    if not isinstance(
        entree,
        dict,
    ):
        return False

    timestamp = entree.get(
        "timestamp"
    )

    if timestamp is None:
        return False

    try:

        age = (
            time.time()
            - float(timestamp)
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        age
        < CACHE_DURATION
    )


def extraire_details_html(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    lignes = [
        nettoyer(texte)
        for texte
        in soup.stripped_strings
        if nettoyer(texte)
    ]

    description = ""

    debut = None
    fin = None

    for index, ligne in enumerate(
        lignes
    ):

        if (
            ligne.lower()
            == "description de l'annonce"
        ):

            debut = (
                index + 1
            )

            continue

        if (
            debut is not None
            and ligne.lower().startswith(
                "référence :"
            )
        ):

            fin = index
            break

    if debut is not None:

        if fin is None:
            fin = min(
                len(lignes),
                debut + 20,
            )

        morceaux = []

        for ligne in lignes[
            debut:fin
        ]:

            ligne_min = (
                ligne.lower()
            )

            if (
                ligne_min
                == "lire la suite"
            ):
                continue

            if (
                "occasion à vendre à"
                in ligne_min
            ):
                continue

            morceaux.append(
                ligne
            )

        description = nettoyer(
            " ".join(
                morceaux
            )
        )

    publication = None

    for ligne in lignes:

        if re.match(
            r"^il y a\b",
            ligne,
            flags=re.IGNORECASE,
        ):

            publication = ligne
            break

    return {
        "description": description,
        "publication_source": publication,
    }


def recuperer_details(
    identifiant,
    url,
    session=None,
):

    cache = charger_cache()

    entree = cache.get(
        identifiant
    )

    if cache_valide(
        entree
    ):

        return {
            "description": (
                entree.get(
                    "description",
                    "",
                )
            ),
            "publication_source": (
                entree.get(
                    "publication_source"
                )
            ),
            "depuis_cache": True,
        }

    session_propre = False

    if session is None:

        session = creer_session_http()

        session_propre = True

    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException:

        return {
            "description": "",
            "publication_source": None,
            "depuis_cache": False,
        }

    finally:

        if (
            session_propre
            and session is not None
        ):
            session.close()

    if response.status_code in {
        403,
        429,
    }:

        print(
            "⛔ ParuVendu détail : "
            "accès refusé / limité."
        )

        return {
            "description": "",
            "publication_source": None,
            "depuis_cache": False,
        }

    if response.status_code != 200:

        return {
            "description": "",
            "publication_source": None,
            "depuis_cache": False,
        }

    details = (
        extraire_details_html(
            response.text
        )
    )

    cache[
        identifiant
    ] = {
        "timestamp": time.time(),
        "description": (
            details.get(
                "description",
                "",
            )
        ),
        "publication_source": (
            details.get(
                "publication_source"
            )
        ),
    }

    sauvegarder_cache(
        cache
    )

    return {
        **details,
        "depuis_cache": False,
    }
