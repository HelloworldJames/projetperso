import re

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://bons-plans.easycash.fr"

CATALOGUE_URL = (
    BASE_URL
    + "/informatique/ordinateur-bureau/pc-gaming"
)


# La Rochelle pour le test
LONGITUDE = -1.1765
LATITUDE = 46.1620


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


AJAX_HEADERS = {
    **HEADERS,
    "Accept": "*/*",
    "X-Requested-With": "CustomXMLHttpRequest",
    "Referer": CATALOGUE_URL,
}


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


# ============================================================
# RECHERCHE HASH 64 CARACTÈRES
# ============================================================

def trouver_hashes(html):

    hashes = re.findall(
        r"\b[a-z0-9]{64}\b",
        html,
        flags=re.IGNORECASE
    )

    uniques = []

    for valeur in hashes:

        valeur = valeur.lower()

        if valeur not in uniques:
            uniques.append(
                valeur
            )

    return uniques


# ============================================================
# RECHERCHE DATA ATTRIBUTES
# ============================================================

def analyser_data_attributes(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print()
    print(
        "========================================"
    )

    print(
        "🧩 DATA ATTRIBUTES CATALOGUE"
    )

    print(
        "========================================"
    )


    compteur = 0


    for element in soup.find_all(True):

        data = {
            cle: valeur
            for cle, valeur
            in element.attrs.items()
            if str(cle).startswith(
                "data-"
            )
        }

        if not data:
            continue


        representation = str(
            data
        ).lower()


        if not any(
            mot in representation
            for mot in [
                "catalog",
                "search",
                "position",
                "latitude",
                "longitude",
                "hash",
                "shop",
                "store",
                "product",
            ]
        ):
            continue


        print()
        print(
            "TAG :",
            element.name
        )

        print(
            "DATA :",
            data
        )


        compteur += 1


        if compteur >= 30:
            break


# ============================================================
# TEST ROUTE MAGASINS
# ============================================================

def tester_route_magasins(
    session
):

    url = (
        BASE_URL
        + "/ajax/catalog/search/shop"
        + f"/{LONGITUDE}"
        + f"/{LATITUDE}"
    )


    print()
    print(
        "========================================"
    )

    print(
        "🏪 ROUTE MAGASINS"
    )

    print(
        "========================================"
    )

    print(
        "🌐",
        url
    )


    try:

        reponse = session.get(
            url,
            headers=AJAX_HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌",
            erreur
        )

        return


    print(
        "📡 HTTP :",
        reponse.status_code
    )

    print(
        "📦 Taille :",
        len(
            reponse.content
        )
    )


    print(
        "📄 Réponse :"
    )


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    texte = nettoyer(
        soup.get_text(
            " ",
            strip=True
        )
    )


    print(
        texte[:2000]
    )


# ============================================================
# TEST ROUTE PRODUITS
# ============================================================

def tester_route_produits(
    session,
    hash_catalogue
):

    url = (
        BASE_URL
        + "/ajax/catalog/search"
        + f"/{hash_catalogue}"
        + f"/{LATITUDE}"
        + f"/{LONGITUDE}"
    )


    print()
    print(
        "========================================"
    )

    print(
        "🖥️ ROUTE PRODUITS GÉOLOCALISÉS"
    )

    print(
        "========================================"
    )

    print(
        "🌐 Hash :",
        hash_catalogue
    )

    print(
        "🌐",
        url
    )


    try:

        reponse = session.get(
            url,
            headers=AJAX_HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌",
            erreur
        )

        return


    print(
        "📡 HTTP :",
        reponse.status_code
    )

    print(
        "📦 Taille :",
        len(
            reponse.content
        )
    )

    print(
        "📄 Type :",
        reponse.headers.get(
            "Content-Type"
        )
    )


    if reponse.status_code in {
        403,
        429
    }:

        print(
            "⛔ Blocage détecté."
        )

        print(
            "➡️ Aucun contournement."
        )

        return


    if reponse.status_code != 200:
        return


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    titres = []


    for h2 in soup.find_all(
        "h2"
    ):

        titre = nettoyer(
            h2.get_text(
                " ",
                strip=True
            )
        )

        if titre:

            titres.append(
                titre
            )


    print()
    print(
        "📝 Produits détectés :",
        len(titres)
    )


    for titre in titres[:15]:

        print(
            "-",
            titre
        )


    texte = nettoyer(
        soup.get_text(
            " ",
            strip=True
        )
    )


    if not titres:

        print()
        print(
            "📋 Aperçu réponse :"
        )

        print(
            texte[:3000]
        )


# ============================================================
# PROGRAMME
# ============================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "🛰️ PC HUNTER - CATALOGUE GÉO EASY CASH"
    )

    print(
        "========================================"
    )


    with requests.Session() as session:

        # ----------------------------------------------------
        # 1. VISITE NORMALE DU CATALOGUE
        # ----------------------------------------------------

        print()
        print(
            "📡 Chargement catalogue PC Gaming..."
        )


        try:

            catalogue = session.get(
                CATALOGUE_URL,
                headers=HEADERS,
                timeout=20
            )

        except requests.RequestException as erreur:

            print(
                "❌ Catalogue :",
                erreur
            )

            return


        print(
            "📡 HTTP catalogue :",
            catalogue.status_code
        )

        print(
            "📦 Taille catalogue :",
            len(
                catalogue.content
            )
        )

        print(
            "🍪 Cookies session :",
            session.cookies.get_dict()
        )


        if catalogue.status_code != 200:
            return


        # ----------------------------------------------------
        # 2. RECHERCHE DES HASHES
        # ----------------------------------------------------

        hashes = trouver_hashes(
            catalogue.text
        )


        print()
        print(
            "🔑 Hashes 64 caractères trouvés :",
            len(hashes)
        )


        for numero, valeur in enumerate(
            hashes[:10],
            start=1
        ):

            print(
                f"{numero}.",
                valeur
            )


        analyser_data_attributes(
            catalogue.text
        )


        # ----------------------------------------------------
        # 3. ROUTE MAGASIN AVEC LA SESSION
        # ----------------------------------------------------

        tester_route_magasins(
            session
        )


        # ----------------------------------------------------
        # 4. ROUTE PRODUITS AVEC HASH
        # ----------------------------------------------------

        if hashes:

            # On teste seulement le premier hash
            # pour commencer.
            tester_route_produits(
                session,
                hashes[0]
            )

        else:

            print()
            print(
                "⚠️ Aucun hash catalogue trouvé."
            )


    print()
    print(
        "========================================"
    )

    print(
        "✅ TEST TERMINÉ"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()