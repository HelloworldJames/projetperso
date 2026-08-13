import re

import requests


BASE_URL = "https://bons-plans.easycash.fr"

PRODUCT_URL = (
    BASE_URL
    + "/pc/"
    + "cooler-master-i5-16-go-ram-2-to-hdd-500-go-ssd-005567364"
)

ROUTING_URL = (
    BASE_URL
    + "/js/routing?callback=fos.Router.setData"
)

PRODUCT_JS_URL = (
    BASE_URL
    + "/themes/js/product-buy.73205fd3.js"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": PRODUCT_URL,
}


MOTS_CLES = [
    "shop",
    "store",
    "magasin",
    "stock",
    "availability",
    "available",
    "product",
    "technical",
    "favorite_shop",
    "cart",
    "offer",
]


ROUTES_CIBLEES = [
    "easy_cash_front_header_get_shop_ajax",
]


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\\/", "/")
        .split()
    )


def afficher_contextes(
    contenu,
    recherches,
    longueur=500
):

    contenu_min = contenu.lower()

    deja_vus = set()


    for recherche in recherches:

        recherche_min = recherche.lower()

        depart = 0


        while True:

            position = contenu_min.find(
                recherche_min,
                depart
            )


            if position == -1:
                break


            debut = max(
                0,
                position - longueur
            )

            fin = min(
                len(contenu),
                position + longueur
            )


            extrait = nettoyer(
                contenu[
                    debut:fin
                ]
            )


            if extrait not in deja_vus:

                deja_vus.add(
                    extrait
                )

                print()
                print(
                    "🔎",
                    recherche
                )

                print(
                    extrait[:2000]
                )


            depart = (
                position
                + len(
                    recherche_min
                )
            )


def analyser_routing(
    session
):

    print()
    print("========================================")
    print("🗺️ ROUTES EASY CASH")
    print("========================================")


    try:

        reponse = session.get(
            ROUTING_URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur routing :",
            erreur
        )

        return


    print(
        "📡 HTTP routing :",
        reponse.status_code
    )

    print(
        "📦 Taille :",
        len(
            reponse.content
        )
    )


    if reponse.status_code != 200:

        print(
            "⚠️ Route map inaccessible."
        )

        return


    contenu = reponse.text


    print()
    print(
        "🎯 Recherche route magasin"
    )


    afficher_contextes(
        contenu,
        ROUTES_CIBLEES,
        longueur=700
    )


    print()
    print(
        "🔍 Recherche routes utiles"
    )


    afficher_contextes(
        contenu,
        MOTS_CLES,
        longueur=350
    )


def analyser_product_js(
    session
):

    print()
    print("========================================")
    print("🧠 PRODUCT-BUY.JS")
    print("========================================")


    try:

        reponse = session.get(
            PRODUCT_JS_URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur JS :",
            erreur
        )

        return


    print(
        "📡 HTTP JS :",
        reponse.status_code
    )

    print(
        "📦 Taille JS :",
        len(
            reponse.content
        )
    )


    if reponse.status_code != 200:

        print(
            "⚠️ JS inaccessible."
        )

        return


    contenu = reponse.text


    recherches = [
        "shop",
        "shopId",
        "shop_id",
        "favorite_shop",
        "stock",
        "availability",
        "productId",
        "technicalSheetId",
        "technical_sheet",
        "Router.generate",
    ]


    afficher_contextes(
        contenu,
        recherches,
        longueur=600
    )


def chercher_routes_ajax(
    session
):

    print()
    print("========================================")
    print("🌐 CHEMINS AJAX VISIBLES")
    print("========================================")


    try:

        reponse = session.get(
            PRODUCT_JS_URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException:
        return


    if reponse.status_code != 200:
        return


    contenu = (
        reponse.text
        .replace("\\/", "/")
    )


    motifs = [
        r'["\']([^"\']*ajax[^"\']*)["\']',
        r'["\']([^"\']*stock[^"\']*)["\']',
        r'["\']([^"\']*shop[^"\']*)["\']',
        r'Router\.generate\(["\']([^"\']+)["\']',
    ]


    trouves = []


    for motif in motifs:

        for resultat in re.findall(
            motif,
            contenu,
            flags=re.IGNORECASE
        ):

            resultat = nettoyer(
                resultat
            )


            if resultat not in trouves:

                trouves.append(
                    resultat
                )


    for resultat in trouves[:100]:

        print(
            "-",
            resultat
        )


def main():

    print()
    print("========================================")
    print("🧭 PC HUNTER - ROUTES EASY CASH")
    print("========================================")


    with requests.Session() as session:

        # Visite normale de la fiche d'abord.
        try:

            fiche = session.get(
                PRODUCT_URL,
                headers=HEADERS,
                timeout=20
            )

            print(
                "📡 HTTP fiche :",
                fiche.status_code
            )

        except requests.RequestException as erreur:

            print(
                "❌ Fiche inaccessible :",
                erreur
            )

            return


        if fiche.status_code != 200:

            return


        analyser_routing(
            session
        )

        analyser_product_js(
            session
        )

        chercher_routes_ajax(
            session
        )


    print()
    print("========================================")
    print("✅ INSPECTION TERMINÉE")
    print("========================================")
    print()
    print(
        "ℹ️ Aucune route AJAX n'a été appelée."
    )
    print(
        "ℹ️ Le script a uniquement lu les ressources "
        "publiques chargées par la fiche."
    )


if __name__ == "__main__":

    main()