import hashlib
import json
import re
import time

from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from collector.models import Annonce


# ============================================================
# CONFIGURATION
# ============================================================

CATALOGUE_URL = (
    "https://bons-plans.easycash.fr/"
    "informatique/ordinateur-bureau/pc-gaming"
)

BASE_URL = "https://bons-plans.easycash.fr"


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)


CACHE_FILE = (
    BASE_DIR
    / "data"
    / "easycash_cache.json"
)


# Durée pendant laquelle on ne recharge pas
# la fiche détaillée d'un produit déjà connu.
CACHE_HEURES = 12


# Petite pause uniquement lorsqu'une vraie
# fiche doit être téléchargée.
PAUSE_FICHE = 0.5


# ============================================================
# OUTILS TEXTE
# ============================================================

def nettoyer_texte(texte):

    if texte is None:
        return ""

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def convertir_prix(texte):

    if not texte:
        return None

    texte = nettoyer_texte(
        texte
    )

    correspondances = re.findall(
        r"(\d{1,4}(?:[\s\u00a0]\d{3})*[.,]\d{2})\s*€?",
        texte
    )

    if not correspondances:
        return None

    try:

        valeur = (
            correspondances[0]
            .replace(" ", "")
            .replace("\xa0", "")
            .replace(",", ".")
        )

        prix = float(
            valeur
        )

        if prix.is_integer():
            return int(prix)

        return prix

    except ValueError:

        return None


# ============================================================
# IDENTIFIANT STABLE
# ============================================================

def generer_identifiant(
    url
):

    # Easy Cash termine généralement
    # ses URLs par un code produit.
    correspondance = re.search(
        r"(\d{9})/?$",
        url or ""
    )

    if correspondance:

        return (
            "EASYCASH-"
            + correspondance.group(1)
        )


    empreinte = hashlib.sha1(
        str(url).encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    return (
        f"EASYCASH-{empreinte}"
    )


# ============================================================
# EXTRACTION CHAMP → VALEUR
# ============================================================

def extraire_valeur_champ(
    soup,
    nom_champ
):

    resultats = soup.find_all(
        string=lambda texte:
            texte
            and nettoyer_texte(
                texte
            ).lower()
            ==
            nom_champ.lower()
    )


    for texte in resultats:

        element = texte.parent

        if element is None:
            continue


        # Le probe a montré que le parent suivant
        # contient :
        #
        # Carte graphique | NVIDIA RTX 2060
        #
        bloc = element.parent

        if bloc is None:
            continue


        valeurs = [
            nettoyer_texte(x)
            for x
            in bloc.stripped_strings
        ]


        for index, valeur in enumerate(
            valeurs
        ):

            if (
                valeur.lower()
                ==
                nom_champ.lower()
            ):

                if (
                    index + 1
                    <
                    len(valeurs)
                ):

                    candidat = valeurs[
                        index + 1
                    ]

                    if (
                        candidat.lower()
                        !=
                        nom_champ.lower()
                    ):

                        return candidat


    return None


# ============================================================
# CACHE
# ============================================================

def charger_cache():

    if not CACHE_FILE.exists():

        return {}


    try:

        return json.loads(
            CACHE_FILE.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        OSError
    ):

        return {}


def sauvegarder_cache(
    cache
):

    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    CACHE_FILE.write_text(
        json.dumps(
            cache,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def cache_valide(
    entree
):

    date_texte = entree.get(
        "date_cache"
    )

    if not date_texte:
        return False


    try:

        date_cache = (
            datetime.fromisoformat(
                date_texte
            )
        )

    except ValueError:

        return False


    maintenant = (
        datetime.now()
        .astimezone()
    )


    if date_cache.tzinfo is None:

        date_cache = (
            date_cache.replace(
                tzinfo=maintenant.tzinfo
            )
        )


    expiration = (
        date_cache
        +
        timedelta(
            hours=CACHE_HEURES
        )
    )


    return (
        maintenant
        <
        expiration
    )


# ============================================================
# EXTRACTION CATALOGUE
# ============================================================

def extraire_catalogue(
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    produits = []

    deja_vus = set()


    for h2 in soup.find_all(
        "h2"
    ):

        titre = nettoyer_texte(
            h2.get_text(
                " ",
                strip=True
            )
        )


        if not titre.lower().startswith(
            "pc "
        ):
            continue


        # Cherche un lien produit
        lien = h2.find_parent(
            "a",
            href=True
        )

        if lien is None:

            parent = h2.parent

            for _ in range(6):

                if parent is None:
                    break

                lien = parent.find(
                    "a",
                    href=True
                )

                if lien:
                    break

                parent = parent.parent


        if lien is None:
            continue


        url = urljoin(
            BASE_URL,
            lien.get(
                "href"
            )
        )


        identifiant = (
            generer_identifiant(
                url
            )
        )


        if identifiant in deja_vus:
            continue


        # Remonte pour trouver un bloc
        # contenant le prix.
        bloc = h2

        prix = None


        for _ in range(8):

            if bloc is None:
                break

            texte_bloc = nettoyer_texte(
                bloc.get_text(
                    " ",
                    strip=True
                )
            )

            prix = convertir_prix(
                texte_bloc
            )

            if prix is not None:
                break

            bloc = bloc.parent


        if prix is None:
            continue


        deja_vus.add(
            identifiant
        )


        produits.append(
            {
                "identifiant":
                    identifiant,

                "titre":
                    titre,

                "prix":
                    prix,

                "url":
                    url,
            }
        )


    return produits


# ============================================================
# ANALYSE FICHE PRODUIT
# ============================================================

def analyser_fiche(
    session,
    produit,
    cache
):

    identifiant = produit[
        "identifiant"
    ]


    entree_cache = cache.get(
        identifiant
    )


    if (
        entree_cache
        and
        cache_valide(
            entree_cache
        )
    ):

        return entree_cache[
            "details"
        ]


    try:

        reponse = session.get(
            produit[
                "url"
            ],
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException:

        return {}


    if reponse.status_code != 200:

        return {}


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    details = {

        "gpu":
            extraire_valeur_champ(
                soup,
                "Carte graphique"
            ),

        "cpu":
            extraire_valeur_champ(
                soup,
                "Gamme de processeur"
            ),

        "cpu_vitesse":
            extraire_valeur_champ(
                soup,
                "Vitesse du processeur"
            ),

        "ram":
            extraire_valeur_champ(
                soup,
                "Mémoire vive"
            ),

        "ssd":
            extraire_valeur_champ(
                soup,
                "Capacité SSD"
            ),

        "hdd":
            extraire_valeur_champ(
                soup,
                "Capacité HDD"
            ),

        "stockage_type":
            extraire_valeur_champ(
                soup,
                "Type de support de stockage"
            ),

        "vram":
            extraire_valeur_champ(
                soup,
                "Taille de la mémoire vidéo"
            ),

        "coeurs":
            extraire_valeur_champ(
                soup,
                "Nombre de coeurs"
            ),

        "systeme":
            extraire_valeur_champ(
                soup,
                "Syst. exploit."
            ),
    }


    cache[
        identifiant
    ] = {

        "date_cache":
            (
                datetime.now()
                .astimezone()
                .isoformat()
            ),

        "details":
            details,
    }


    return details


# ============================================================
# DESCRIPTION PC HUNTER
# ============================================================

def construire_description(
    produit,
    details
):

    parties = []


    correspondances = [

        (
            "GPU",
            details.get(
                "gpu"
            )
        ),

        (
            "CPU",
            details.get(
                "cpu"
            )
        ),

        (
            "CPU vitesse",
            details.get(
                "cpu_vitesse"
            )
        ),

        (
            "RAM",
            details.get(
                "ram"
            )
        ),

        (
            "SSD",
            details.get(
                "ssd"
            )
        ),

        (
            "HDD",
            details.get(
                "hdd"
            )
        ),

        (
            "VRAM",
            details.get(
                "vram"
            )
        ),

        (
            "Coeurs",
            details.get(
                "coeurs"
            )
        ),

        (
            "OS",
            details.get(
                "systeme"
            )
        ),
    ]


    for nom, valeur in correspondances:

        if valeur:

            parties.append(
                f"{nom}: {valeur}"
            )


    if not parties:

        return produit[
            "titre"
        ]


    return (
        produit[
            "titre"
        ]
        +
        " | "
        +
        " | ".join(
            parties
        )
    )


# ============================================================
# PROVIDER PUBLIC
# ============================================================

def rechercher(
    limite=None
):

    print(
        "📡 Chargement source : Easy Cash"
    )


    try:

        reponse = requests.get(
            CATALOGUE_URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Easy Cash inaccessible :",
            erreur
        )

        return []


    if reponse.status_code != 200:

        print(
            "⚠️ Easy Cash HTTP :",
            reponse.status_code
        )

        return []


    produits = extraire_catalogue(
        reponse.text
    )


    print(
        "📥",
        len(produits),
        "produits Easy Cash trouvés"
    )


    if limite is not None:

        produits = produits[
            :limite
        ]


    annonces = []

    cache = charger_cache()


    with requests.Session() as session:

        for numero, produit in enumerate(
            produits,
            start=1
        ):

            print(
                f"🔬 Easy Cash "
                f"{numero}/{len(produits)} : "
                f"{produit['titre'][:55]}"
            )


            details = analyser_fiche(
                session,
                produit,
                cache
            )


            description = (
                construire_description(
                    produit,
                    details
                )
            )


            annonce = Annonce(
                identifiant=produit[
                    "identifiant"
                ],

                titre=produit[
                    "titre"
                ],

                prix=produit[
                    "prix"
                ],

                description=description,

                # PAS encore trouvé proprement.
                # On ne fabrique aucune ville.
                localisation="Inconnue",

                plateforme="Easy Cash",

                url=produit[
                    "url"
                ],

                date_publication=None
            )


            annonces.append(
                annonce
            )


            # Pause uniquement si nécessaire.
            time.sleep(
                PAUSE_FICHE
            )


    sauvegarder_cache(
        cache
    )


    print(
        "✅ Easy Cash :",
        len(annonces),
        "annonces réelles prêtes"
    )


    return annonces


# ============================================================
# TEST DIRECT
# ============================================================

if __name__ == "__main__":

    annonces = rechercher(
        limite=5
    )


    print()
    print(
        "========================================"
    )

    print(
        "🖥️ TEST PROVIDER EASY CASH"
    )

    print(
        "========================================"
    )


    for annonce in annonces:

        print()
        print(
            "ID :",
            annonce.identifiant
        )

        print(
            "📝",
            annonce.titre
        )

        print(
            "💵",
            annonce.prix,
            "€"
        )

        print(
            "📄",
            annonce.description
        )

        print(
            "📍",
            annonce.localisation
        )

        print(
            "🔗",
            annonce.url
        )