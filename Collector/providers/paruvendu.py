import math
import re

import requests
from bs4 import BeautifulSoup
from collector.http import creer_session_http
from collector.providers.paruvendu_detail import recuperer_details
from collector.models import Annonce


# ============================================================
# CONFIG PARUVENDU
# ============================================================

BASE_URL = "https://www.paruvendu.fr"

PAGE_URL = (
    BASE_URL
    + "/annonces/informatique/"
)

SEARCH_URL = (
    BASE_URL
    + "/mondebarras/listefo/default/default/"
)


# Localisation officielle retournée
# par l'autocomplete ParuVendu.
VILLE_CIBLE = "Tonnay-Charente"
CODE_INSEE = "17449"
CODE_POSTAL = "17430"
RAYON_KM = 50


# Sécurité : évite un parcours infini
# si ParuVendu change son système.
MAX_PAGES = 10


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


MOTS_CLES_PC = [
    # PC complets
    "pc gamer",
    "pc gaming",
    "ordinateur gamer",
    "ordinateur gaming",
    "setup gaming",
    "tour gamer",
    "tour gaming",
    "unité centrale",
    "unite centrale",

    # GPU
    "rtx",
    "gtx",
    "radeon",
    "rx 5",
    "rx 6",
    "rx 7",
    "rx 8",
    "carte graphique",
    "gpu",

    # CPU
    "ryzen",
    "core i5",
    "core i7",
    "core i9",
    "intel i5",
    "intel i7",
    "intel i9",

    # composants
    "processeur",
    "carte mère",
    "carte mere",
    "mémoire vive",
    "memoire vive",
    "ssd",
    "nvme",

    # portables intéressants
    "asus rog",
    "msi katana",
    "msi pulse",
    "lenovo legion",
    "hp omen",
    "hp victus",
    "acer nitro",
]


# ============================================================
# OUTILS
# ============================================================

def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def convertir_prix(texte):

    valeur = (
        str(texte)
        .replace("€", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )

    try:
        prix = float(valeur)

    except ValueError:
        return None

    if prix.is_integer():
        return int(prix)

    return prix


# ============================================================
# URL ANNONCE
# ============================================================

def extraire_lien(bloc):

    for lien in bloc.find_all(
        "a",
        href=True,
    ):

        href = lien.get(
            "href",
            "",
        )

        if re.search(
            r"/annonces/high-tech/.+/\d+[A-Z0-9]+/?$",
            href,
            flags=re.IGNORECASE,
        ):
            return lien

    return None


# ============================================================
# PRIX
# ============================================================

def extraire_prix(bloc):

    # Cherche d'abord une chaîne HTML
    # qui correspond exactement à un prix.
    for chaine in bloc.stripped_strings:

        texte = nettoyer(
            chaine
        )

        match = re.fullmatch(
            r"(\d[\d\s]*(?:[.,]\d+)?)\s*€",
            texte,
        )

        if not match:
            continue

        prix = convertir_prix(
            match.group(1)
        )

        if prix is not None:
            return prix

    # Fallback sur les petits éléments HTML.
    candidats = []

    for element in bloc.find_all(True):

        texte = nettoyer(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if re.fullmatch(
            r"\d[\d\s]*(?:[.,]\d+)?\s*€",
            texte,
        ):
            candidats.append(
                texte
            )

    candidats.sort(
        key=len
    )

    for candidat in candidats:

        prix = convertir_prix(
            candidat
        )

        if prix is not None:
            return prix

    return None


# ============================================================
# LOCALISATION
# ============================================================

def extraire_localisation(bloc):

    # Méthode 1 :
    # ville dans une chaîne indépendante.
    for chaine in bloc.stripped_strings:

        texte = nettoyer(
            chaine
        )

        match = re.fullmatch(
            r"(.+?)\s+\((\d{2,3})\)",
            texte,
        )

        if not match:
            continue

        ville = nettoyer(
            match.group(1)
        )

        departement = (
            match.group(2)
        )

        if len(ville) <= 80:

            return (
                ville,
                departement,
            )

    # Méthode 2 :
    # prix + ville dans le texte complet.
    texte_bloc = nettoyer(
        bloc.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"\d[\d\s]*(?:[.,]\d+)?\s*€\s+"
        r"(.+?)\s+\((\d{2,3})\)",
        texte_bloc,
    )

    if match:

        ville = nettoyer(
            match.group(1)
        )

        departement = (
            match.group(2)
        )

        if len(ville) <= 80:

            return (
                ville,
                departement,
            )

    return (
        "Inconnue",
        None,
    )


# ============================================================
# TITRE
# ============================================================

def extraire_titre(
    lien,
    ville,
    departement,
):

    titre = nettoyer(
        lien.get(
            "title",
            "",
        )
    )

    if not titre:

        return "Annonce ParuVendu"

    if (
        ville != "Inconnue"
        and departement
    ):

        suffixe = (
            f" {ville} ({departement})"
        )

        if titre.lower().endswith(
            suffixe.lower()
        ):

            titre = titre[
                :-len(suffixe)
            ].strip()

    return titre


# ============================================================
# DESCRIPTION
# ============================================================

def extraire_description(
    bloc,
    titre,
):

    candidats = []

    titre_min = (
        titre.lower()
    )

    for chaine in bloc.stripped_strings:

        texte = nettoyer(
            chaine
        )

        if len(texte) < 15:
            continue

        texte_min = (
            texte.lower()
        )

        if texte_min == titre_min:
            continue

        if texte_min in {
            "particulier",
            "professionnel",
            "voir l'annonce",
        }:
            continue

        if (
            "5 niveaux d'expérience"
            in texte_min
        ):
            continue

        if (
            "il est calculé automatiquement"
            in texte_min
        ):
            continue

        if re.fullmatch(
            r"\d[\d\s]*(?:[.,]\d+)?\s*€",
            texte,
        ):
            continue

        candidats.append(
            texte
        )

    if not candidats:

        return ""

    candidats.sort(
        key=len,
        reverse=True,
    )

    return candidats[0][:1500]


# ============================================================
# FILTRES
# ============================================================

def est_particulier(bloc):

    texte = nettoyer(
        bloc.get_text(
            " ",
            strip=True,
        )
    )

    return bool(
        re.search(
            r"\bParticulier\b",
            texte,
            flags=re.IGNORECASE,
        )
    )


def est_interessant(
    titre,
    description,
):

    texte = (
        f"{titre} "
        f"{description}"
    ).lower()

    return any(
        mot.lower() in texte
        for mot in MOTS_CLES_PC
    )


# ============================================================
# PARSE UNE ANNONCE
# ============================================================

def parser_annonce(bloc):

    identifiant_brut = bloc.get(
        "data-id"
    )

    if not identifiant_brut:
        return None

    if not est_particulier(
        bloc
    ):
        return None


    lien = extraire_lien(
        bloc
    )

    if lien is None:
        return None


    prix = extraire_prix(
        bloc
    )

    if prix is None:
        return None


    ville, departement = (
        extraire_localisation(
            bloc
        )
    )


    titre = extraire_titre(
        lien,
        ville,
        departement,
    )


    # ========================================================
    # PRÉ-FILTRE
    #
    # On utilise d'abord uniquement le résumé de la liste.
    # Aucune fiche détaillée n'est appelée si l'annonce
    # ne semble pas intéressante.
    # ========================================================

    description_courte = (
        extraire_description(
            bloc,
            titre,
        )
    )


    if not est_interessant(
        titre,
        description_courte,
    ):
        return None


    identifiant = (
        f"PARUVENDU-{identifiant_brut}"
    )


    # ========================================================
    # ENRICHISSEMENT
    #
    # Seulement maintenant on ouvre / utilise le cache
    # de la fiche complète.
    # ========================================================

    details = recuperer_details(
        identifiant=identifiant,
        url=lien.get("href"),
    )


    description_complete = (
        details.get(
            "description",
            ""
        )
    )


    if description_complete:

        description = (
            description_complete
        )

    else:

        description = (
            description_courte
        )


    return Annonce(
        identifiant=identifiant,
        titre=titre,
        prix=prix,
        description=description,
        localisation=ville,
        plateforme="ParuVendu",
        url=lien.get("href"),
        date_publication=None,
    )


# ============================================================
# PARAMÈTRES RECHERCHE LOCALE
# ============================================================

def construire_params(
    page=1,
):

    params = {
        "codPro": "",
        "filtre": "",
        "tri": "",

        # catégorie informatique
        "idtag": "1789",
        "r": "BMUMI000",

        # localisation officielle ParuVendu
        "codeinsee": (
            CODE_INSEE + ","
        ),

        "lo": (
            CODE_POSTAL + ","
        ),

        "pa": "",

        # rayon
        "ray": str(
            RAYON_KM
        ),

        "elargrayon": "1",

        # uniquement vente
        "zmd[]": "VENTE",
    }

    if page > 1:

        params["p"] = str(
            page
        )

    return params


# ============================================================
# RÉCUPÈRE UNE PAGE
# ============================================================

def recuperer_page(
    session,
    numero_page,
):

    try:

        response = session.get(
            SEARCH_URL,
            params=construire_params(
                numero_page
            ),
            headers={
                **HEADERS,
                "Referer": PAGE_URL,
            },
            timeout=20,
        )

    except requests.RequestException as erreur:

        print(
            f"❌ ParuVendu page "
            f"{numero_page} :",
            erreur,
        )

        return None

    if response.status_code in {
        403,
        429,
    }:

        print(
            "⛔ ParuVendu refuse "
            "ou limite les requêtes."
        )

        return None

    if response.status_code != 200:

        print(
            f"⚠️ ParuVendu page "
            f"{numero_page} HTTP :",
            response.status_code,
        )

        return None

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


# ============================================================
# TOTAL RÉSULTATS
# ============================================================

def extraire_total(soup):

    texte = nettoyer(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    match = re.search(
        r"([\d\s]+)\s+annonces?",
        texte,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    valeur = (
        match.group(1)
        .replace(" ", "")
    )

    try:
        return int(valeur)

    except ValueError:
        return None


# ============================================================
# COLLECTE LOCALE
# ============================================================

def rechercher(
    limite=None,
):

    annonces = []

    ids_vus = set()

    with creer_session_http() as session:

        premiere_page = recuperer_page(
            session,
            1,
        )

        if premiere_page is None:
            return []

        total = extraire_total(
            premiere_page
        )

        if total is not None:

            pages_estimees = max(
                1,
                math.ceil(
                    total / 30
                ),
            )

            pages_a_lire = min(
                pages_estimees,
                MAX_PAGES,
            )

        else:

            pages_a_lire = (
                MAX_PAGES
            )

        print(
            f"📍 ParuVendu : "
            f"{VILLE_CIBLE} + "
            f"{RAYON_KM} km"
        )

        if total is not None:

            print(
                "📊 Résultats source :",
                total,
            )

            print(
                "📄 Pages prévues :",
                pages_a_lire,
            )

        for numero_page in range(
            1,
            pages_a_lire + 1,
        ):

            if numero_page == 1:

                soup = (
                    premiere_page
                )

            else:

                soup = recuperer_page(
                    session,
                    numero_page,
                )

                if soup is None:
                    break

            blocs = soup.select(
                "div.debarras-annonce[data-id]"
            )

            if not blocs:
                break

            nouveaux_ids_page = 0

            for bloc in blocs:

                identifiant_brut = (
                    bloc.get(
                        "data-id"
                    )
                )

                if not identifiant_brut:
                    continue

                cle = (
                    f"PARUVENDU-"
                    f"{identifiant_brut}"
                )

                if cle in ids_vus:
                    continue

                ids_vus.add(
                    cle
                )

                nouveaux_ids_page += 1

                annonce = (
                    parser_annonce(
                        bloc
                    )
                )

                if annonce is None:
                    continue

                annonces.append(
                    annonce
                )

                if (
                    limite is not None
                    and
                    len(annonces)
                    >= limite
                ):

                    return annonces

            print(
                f"📄 Page {numero_page} : "
                f"{len(blocs)} annonces "
                f"brutes / "
                f"{nouveaux_ids_page} nouvelles"
            )

            # Si une page entière ne contient
            # aucun nouvel ID, on arrête.
            if nouveaux_ids_page == 0:
                break

    return annonces


# ============================================================
# TEST MANUEL
# ============================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "🟠 PC HUNTER - PARUVENDU LOCAL"
    )

    print(
        "========================================"
    )

    annonces = rechercher()

    print()
    print(
        "💻 Annonces PC retenues :",
        len(annonces),
    )

    for numero, annonce in enumerate(
        annonces,
        start=1,
    ):

        print()
        print(
            "----------------------------------------"
        )

        print(
            f"#{numero}"
        )

        print(
            "🆔",
            annonce.identifiant,
        )

        print(
            "🖥️",
            annonce.titre,
        )

        print(
            "💰",
            annonce.prix,
            "€",
        )

        print(
            "📍",
            annonce.localisation,
        )

        print(
            "📝",
            annonce.description[:300],
        )

        print(
            "🔗",
            annonce.url,
        )


if __name__ == "__main__":
    main()
