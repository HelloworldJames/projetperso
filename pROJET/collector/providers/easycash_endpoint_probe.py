import re

import requests
from bs4 import BeautifulSoup


URL = (
    "https://bons-plans.easycash.fr/pc/"
    "cooler-master-i5-16-go-ram-2-to-hdd-500-go-ssd-005567364"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


MOTS_CLES = (
    "shop",
    "store",
    "magasin",
    "stock",
    "availability",
    "available",
    "pickup",
    "retrait",
    "product",
    "offer",
    "offre",
    "ajax",
    "api",
)


def nettoyer(texte):
    return " ".join(
        str(texte)
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\xa0", " ")
        .split()
    )


def interessant(texte):
    texte = str(texte).lower()

    return any(
        mot in texte
        for mot in MOTS_CLES
    )


# ============================================================
# META
# ============================================================

def afficher_meta(soup):

    print()
    print("========================================")
    print("📦 META PRODUIT")
    print("========================================")

    for meta in soup.find_all("meta"):

        attributs = meta.attrs

        texte = str(attributs)

        if interessant(texte):

            print(attributs)


# ============================================================
# FORMULAIRES
# ============================================================

def afficher_formulaires(soup):

    print()
    print("========================================")
    print("📝 FORMULAIRES")
    print("========================================")

    formulaires = soup.find_all("form")

    print(
        "Nombre de formulaires :",
        len(formulaires)
    )

    for numero, form in enumerate(
        formulaires,
        start=1
    ):

        action = form.get(
            "action"
        )

        method = form.get(
            "method"
        )

        texte = nettoyer(
            form.get_text(
                " ",
                strip=True
            )
        )

        ensemble = (
            str(form.attrs)
            + " "
            + str(action)
            + " "
            + texte
        )

        if not interessant(
            ensemble
        ):
            continue

        print()
        print(
            f"--- FORMULAIRE {numero} ---"
        )

        print(
            "ACTION :",
            action
        )

        print(
            "METHOD :",
            method
        )

        print(
            "ATTR :",
            form.attrs
        )

        if texte:

            print(
                "TEXTE :",
                texte[:500]
            )


# ============================================================
# INPUTS CACHÉS
# ============================================================

def afficher_inputs(soup):

    print()
    print("========================================")
    print("🔑 INPUTS / IDENTIFIANTS")
    print("========================================")

    compteur = 0

    for element in soup.find_all(
        ["input", "select", "button"]
    ):

        attributs = element.attrs

        representation = str(
            attributs
        )

        if not interessant(
            representation
        ):
            continue

        print()
        print(
            element.name.upper(),
            ":",
            representation[:1000]
        )

        compteur += 1

        if compteur >= 40:
            break


# ============================================================
# ATTRIBUTS DATA-*
# ============================================================

def afficher_data_attributes(soup):

    print()
    print("========================================")
    print("🧠 ATTRIBUTS DATA-*")
    print("========================================")

    compteur = 0

    for element in soup.find_all(True):

        data_attrs = {
            cle: valeur
            for cle, valeur
            in element.attrs.items()
            if str(cle).startswith(
                "data-"
            )
        }

        if not data_attrs:
            continue

        representation = str(
            data_attrs
        )

        if not interessant(
            representation
        ):
            continue

        print()
        print(
            "TAG :",
            element.name
        )

        print(
            "DATA :",
            representation[:1500]
        )

        compteur += 1

        if compteur >= 50:
            break


# ============================================================
# SCRIPTS EXTERNES
# ============================================================

def afficher_scripts_src(soup):

    print()
    print("========================================")
    print("📜 SCRIPTS JS")
    print("========================================")

    for script in soup.find_all(
        "script",
        src=True
    ):

        src = script.get(
            "src"
        )

        print(
            "-",
            src
        )


# ============================================================
# URLS / ENDPOINTS POTENTIELS
# ============================================================

def afficher_endpoints(html):

    print()
    print("========================================")
    print("🌐 ENDPOINTS POTENTIELS")
    print("========================================")

    html_nettoye = (
        html
        .replace("\\/", "/")
        .replace("\\u002F", "/")
    )

    motifs = [
        r'https?://[^"\'\s<>]+',
        r'["\'](/[^"\']*(?:api|ajax|stock|shop|store|magasin|availability|pickup|offer)[^"\']*)["\']',
    ]

    resultats = []

    for motif in motifs:

        for correspondance in re.findall(
            motif,
            html_nettoye,
            flags=re.IGNORECASE
        ):

            if isinstance(
                correspondance,
                tuple
            ):
                valeur = correspondance[0]
            else:
                valeur = correspondance

            valeur = nettoyer(
                valeur
            )

            if not interessant(
                valeur
            ):
                continue

            if valeur not in resultats:

                resultats.append(
                    valeur
                )


    for resultat in resultats[:80]:

        print(
            "-",
            resultat[:1000]
        )


# ============================================================
# CONTEXTE AUTOUR DES MOTS CLÉS
# ============================================================

def afficher_contextes(html):

    print()
    print("========================================")
    print("🔬 CONTEXTES HTML")
    print("========================================")

    html_min = html.lower()

    recherches = [
        "005567364",
        "availability",
        "stock",
        "shopid",
        "shop_id",
        "storeid",
        "store_id",
        "magasin",
        "pickup",
        "retrait",
    ]

    deja_vus = set()

    for recherche in recherches:

        position = html_min.find(
            recherche.lower()
        )

        if position == -1:
            continue

        debut = max(
            0,
            position - 300
        )

        fin = min(
            len(html),
            position + 700
        )

        extrait = nettoyer(
            html[
                debut:fin
            ]
        )

        if extrait in deja_vus:
            continue

        deja_vus.add(
            extrait
        )

        print()
        print(
            "🔎",
            recherche.upper()
        )

        print(
            extrait[:1200]
        )


# ============================================================
# PROGRAMME
# ============================================================

def main():

    print()
    print("========================================")
    print("🛰️ PC HUNTER - ENDPOINT PROBE EASY CASH")
    print("========================================")
    print()

    session = requests.Session()

    try:

        reponse = session.get(
            URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur :",
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
        ),
        "octets"
    )


    if reponse.status_code != 200:

        return


    print()
    print(
        "🍪 Cookies reçus :",
        list(
            session.cookies.keys()
        )
    )


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    afficher_meta(
        soup
    )

    afficher_formulaires(
        soup
    )

    afficher_inputs(
        soup
    )

    afficher_data_attributes(
        soup
    )

    afficher_scripts_src(
        soup
    )

    afficher_endpoints(
        reponse.text
    )

    afficher_contextes(
        reponse.text
    )


    print()
    print("========================================")
    print("✅ PROBE TERMINÉ")
    print("========================================")


if __name__ == "__main__":
    main()