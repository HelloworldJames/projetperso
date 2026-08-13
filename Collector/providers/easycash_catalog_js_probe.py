import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://bons-plans.easycash.fr"

CATALOGUE_URL = (
    BASE_URL
    + "/informatique/ordinateur-bureau/pc-gaming"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


RECHERCHES = [
    "catalog_search_render_products_by_positions",
    "catalog_search_render_shop_by_positions",

    "/ajax/catalog/search/shop",
    "/ajax/catalog/search",

    "getCurrentPosition",
    "geolocation",

    "data-hash",
    "searchHash",
    "search_hash",

    "latitude",
    "longitude",

    "Routing.generate",
]


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\\/", "/")
        .replace("\xa0", " ")
        .split()
    )


def meme_domaine(url):

    domaine = urlparse(
        url
    ).netloc.lower()

    return (
        domaine
        ==
        "bons-plans.easycash.fr"
    )


def contexte(
    contenu,
    position,
    avant=700,
    apres=1200
):

    debut = max(
        0,
        position - avant
    )

    fin = min(
        len(contenu),
        position + apres
    )

    return nettoyer(
        contenu[
            debut:fin
        ]
    )


# ============================================================
# INSPECTION HTML
# ============================================================

def analyser_html(html):

    print()
    print(
        "========================================"
    )

    print(
        "🧩 INDICES DANS LE HTML"
    )

    print(
        "========================================"
    )


    html_min = html.lower()

    termes = [
        "catalog_search_render_products_by_positions",
        "catalog_search_render_shop_by_positions",
        "data-hash",
        "searchhash",
        "search_hash",
        "/ajax/catalog/search",
        "geolocation",
        "getcurrentposition",
    ]


    trouve = False


    for terme in termes:

        depart = 0


        while True:

            position = html_min.find(
                terme.lower(),
                depart
            )


            if position == -1:
                break


            trouve = True


            print()
            print(
                "🔎",
                terme
            )

            print(
                contexte(
                    html,
                    position
                )[:2500]
            )


            depart = (
                position
                + len(terme)
            )


    if not trouve:

        print(
            "ℹ️ Aucun mécanisme géographique "
            "évident dans le HTML initial."
        )


# ============================================================
# RÉCUPÉRATION DES JS
# ============================================================

def trouver_scripts(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    scripts = []


    for script in soup.find_all(
        "script",
        src=True
    ):

        src = script.get(
            "src"
        )


        if not src:
            continue


        url = urljoin(
            CATALOGUE_URL,
            src
        )


        if not meme_domaine(
            url
        ):

            continue


        if url not in scripts:

            scripts.append(
                url
            )


    return scripts


# ============================================================
# ANALYSE JS
# ============================================================

def analyser_script(
    session,
    numero,
    total,
    url
):

    print()
    print(
        "----------------------------------------"
    )

    print(
        f"📜 JS {numero}/{total}"
    )

    print(
        url
    )


    try:

        reponse = session.get(
            url,
            headers={
                **HEADERS,
                "Referer":
                    CATALOGUE_URL,
            },
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌",
            erreur
        )

        return False


    print(
        "📡 HTTP :",
        reponse.status_code
    )

    print(
        "📦",
        len(
            reponse.content
        ),
        "octets"
    )


    if reponse.status_code in {
        403,
        429,
    }:

        print(
            "⛔ Accès refusé / limité."
        )

        return False


    if reponse.status_code != 200:

        return False


    contenu = reponse.text

    contenu_min = (
        contenu.lower()
    )


    correspondances = []


    for terme in RECHERCHES:

        position = contenu_min.find(
            terme.lower()
        )


        if position == -1:
            continue


        correspondances.append(
            (
                terme,
                position
            )
        )


    if not correspondances:

        print(
            "➖ Rien d'intéressant."
        )

        return False


    print()
    print(
        "🎯 SCRIPT INTÉRESSANT"
    )


    for terme, position in correspondances:

        print()
        print(
            "🔎",
            terme
        )

        print(
            contexte(
                contenu,
                position
            )[:3500]
        )


    return True


# ============================================================
# CHERCHE LES ROUTES UTILISÉES PAR ROUTING.GENERATE
# ============================================================

def extraire_noms_routes(
    contenu
):

    motifs = [
        (
            r'Routing\.generate\('
            r'["\']([^"\']+)["\']'
        ),

        (
            r'window\.Routing\.generate\('
            r'["\']([^"\']+)["\']'
        ),
    ]


    routes = []


    for motif in motifs:

        resultats = re.findall(
            motif,
            contenu,
            flags=re.IGNORECASE
        )


        for route in resultats:

            if route not in routes:

                routes.append(
                    route
                )


    return routes


# ============================================================
# PROGRAMME
# ============================================================

def main():

    print()
    print(
        "========================================"
    )

    print(
        "🔬 PC HUNTER - JS CATALOGUE EASY CASH"
    )

    print(
        "========================================"
    )


    with requests.Session() as session:

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


        print()
        print(
            "📡 HTTP catalogue :",
            catalogue.status_code
        )


        if catalogue.status_code != 200:

            return


        print(
            "📦 Taille :",
            len(
                catalogue.content
            )
        )


        analyser_html(
            catalogue.text
        )


        scripts = trouver_scripts(
            catalogue.text
        )


        print()
        print(
            "========================================"
        )

        print(
            "📚 JAVASCRIPT EASY CASH"
        )

        print(
            "========================================"
        )

        print(
            "📦 Scripts internes trouvés :",
            len(scripts)
        )


        scripts_interessants = 0


        for numero, url in enumerate(
            scripts,
            start=1
        ):

            interessant = analyser_script(
                session,
                numero,
                len(scripts),
                url
            )


            if interessant:

                scripts_interessants += 1


        print()
        print(
            "========================================"
        )

        print(
            "📊 RÉSULTAT"
        )

        print(
            "========================================"
        )

        print(
            "🎯 Scripts intéressants :",
            scripts_interessants
        )


    print()
    print(
        "✅ Inspection terminée."
    )

    print(
        "ℹ️ Aucune route catalogue "
        "n'a été appelée."
    )

    print(
        "ℹ️ Seuls le HTML et les fichiers JS "
        "publics de la page ont été lus."
    )


if __name__ == "__main__":
    main()