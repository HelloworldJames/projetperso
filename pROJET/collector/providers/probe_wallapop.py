import re
import time
from urllib.parse import quote_plus, urljoin

import requests


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://fr.wallapop.com"

RECHERCHES = [
    "pc",
    "ordinateur",
    "pc gamer",
    "ordinateur portable",
    "tour pc",
]

TIMEOUT = 20

PAUSE = 1.5


# ============================================================
# OUTILS
# ============================================================

def construire_url(recherche):

    mots = quote_plus(
        recherche
    )

    return (
        f"{BASE_URL}/search"
        f"?keywords={mots}"
        f"&order_by=most_relevance"
    )


def extraire_titre_page(html):

    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )

    if not match:
        return None

    titre = re.sub(
        r"\s+",
        " ",
        match.group(1),
    )

    return titre.strip()


def extraire_urls_items(
    html,
):

    # On recherche uniquement les URLs publiques
    # d'annonces Wallapop de type /item/...

    motifs = [

        r'href=["\']([^"\']*/item/[^"\']+)["\']',

        r'["\'](https://fr\.wallapop\.com/item/[^"\']+)["\']',

        r'["\'](/item/[^"\']+)["\']',

    ]

    resultats = []

    deja_vus = set()


    for motif in motifs:

        matches = re.findall(
            motif,
            html,
            flags=re.IGNORECASE,
        )


        for lien in matches:

            url = urljoin(
                BASE_URL,
                lien,
            )

            url = (
                url
                .replace(
                    "\\u002F",
                    "/"
                )
                .replace(
                    "\\/",
                    "/"
                )
            )

            url = url.split(
                "#"
            )[0]


            if url in deja_vus:
                continue


            deja_vus.add(
                url
            )

            resultats.append(
                url
            )


    return resultats


def extraire_identifiants(
    urls,
):

    identifiants = []


    for url in urls:

        match = re.search(
            r"-(\d+)"
            r"(?:[/?#]|$)",
            url,
        )

        if not match:
            continue


        identifiant = (
            match.group(1)
        )


        if identifiant not in identifiants:

            identifiants.append(
                identifiant
            )


    return identifiants


def compter_signaux(
    html,
):

    texte = html.lower()


    return {

        "pc": len(
            re.findall(
                r"\bpc\b",
                texte,
            )
        ),

        "ordinateur": (
            texte.count(
                "ordinateur"
            )
        ),

        "gaming": (
            texte.count(
                "gaming"
            )
        ),

        "portable": (
            texte.count(
                "portable"
            )
        ),

        "rtx": (
            texte.count(
                "rtx"
            )
        ),

        "gtx": (
            texte.count(
                "gtx"
            )
        ),

        "ryzen": (
            texte.count(
                "ryzen"
            )
        ),

        "intel": (
            texte.count(
                "intel"
            )
        ),

        "ssd": (
            texte.count(
                "ssd"
            )
        ),

        "prix": (
            texte.count(
                "price"
            )
            +
            html.count(
                "€"
            )
        ),

    }


def detecter_structure(
    html,
):

    texte = html.lower()


    return {

        "next_data": (
            "__next_data__"
            in texte
        ),

        "nuxt": (
            "__nuxt__"
            in texte
        ),

        "json_ld": (
            "application/ld+json"
            in texte
        ),

        "item": (
            "/item/"
            in texte
        ),

        "price_json": (
            '"price"'
            in texte
        ),

        "title_json": (
            '"title"'
            in texte
        ),

        "location_json": (
            '"location"'
            in texte
        ),

    }


# ============================================================
# TEST D'UNE RECHERCHE
# ============================================================

def tester_recherche(
    session,
    recherche,
):

    url = construire_url(
        recherche
    )


    print()
    print("=" * 65)

    print(
        "🔎 RECHERCHE :",
        recherche.upper(),
    )

    print("=" * 65)

    print()

    print(
        "🌐",
        url,
    )


    try:

        reponse = session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return None


    print(
        "HTTP :",
        reponse.status_code,
    )

    print(
        "Taille :",
        len(
            reponse.content
        ),
        "octets",
    )

    print(
        "URL finale :",
        reponse.url,
    )


    # ========================================================
    # REFUS
    # ========================================================

    if reponse.status_code in {
        401,
        403,
        429,
    }:

        print()

        print(
            "🔒 Recherche Wallapop "
            "refusée ou limitée."
        )

        print(
            "➡️ Aucun retry automatique "
            "et aucun contournement."
        )

        return {
            "bloque": True,
            "statut": reponse.status_code,
        }


    if reponse.status_code != 200:

        print(
            "⚠️ HTTP inattendu."
        )

        return {
            "bloque": False,
            "statut": reponse.status_code,
        }


    html = reponse.text


    titre = extraire_titre_page(
        html
    )


    urls = extraire_urls_items(
        html
    )


    identifiants = (
        extraire_identifiants(
            urls
        )
    )


    signaux = compter_signaux(
        html
    )


    structure = detecter_structure(
        html
    )


    print()

    print(
        "📝 Titre :",
        titre,
    )

    print()

    print(
        "📦 URLs /item/ :",
        len(
            urls
        ),
    )

    print(
        "🆔 Identifiants :",
        len(
            identifiants
        ),
    )

    print()


    print(
        "🧠 Signaux matériel :"
    )

    for nom, valeur in signaux.items():

        print(
            f"   {nom:<12} : {valeur}"
        )


    print()

    print(
        "🧩 Structure :"
    )


    for nom, valeur in structure.items():

        print(
            f"   {nom:<14} :",
            (
                "✅"
                if valeur
                else
                "❌"
            ),
        )


    if urls:

        print()

        print(
            "🔗 EXEMPLES D'ANNONCES"
        )

        print()


        for position, url_item in enumerate(
            urls[:10],
            start=1,
        ):

            print(
                f"{position:02d}.",
                url_item,
            )


    return {

        "bloque": False,

        "statut": (
            reponse.status_code
        ),

        "recherche": recherche,

        "nombre_urls": len(
            urls
        ),

        "nombre_ids": len(
            identifiants
        ),

        "urls": urls,

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("#" * 65)
    print("🧪 PC HUNTER — PROBE WALLAPOP")
    print("#" * 65)

    print()

    print(
        "Recherches testées :"
    )


    for recherche in RECHERCHES:

        print(
            "•",
            recherche,
        )


    print()

    print(
        "Une requête normale par recherche."
    )

    print(
        "Aucun compte, cookie privé, "
        "proxy ou contournement."
    )


    session = requests.Session()


    session.headers.update(
        {

            "User-Agent": (
                "PC-Hunter-Prototype/0.1 "
                "(marketplace compatibility research)"
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "fr-FR,fr;q=0.9"
            ),

        }
    )


    resultats = []


    for position, recherche in enumerate(
        RECHERCHES,
        start=1,
    ):

        resultat = tester_recherche(
            session=session,
            recherche=recherche,
        )


        if resultat:

            resultats.append(
                resultat
            )


            # Si Wallapop refuse clairement
            # les pages de recherche,
            # inutile d'insister 5 fois.

            if resultat.get(
                "bloque"
            ):

                print()

                print(
                    "⛔ Arrêt du probe Wallapop : "
                    "la recherche est protégée."
                )

                break


        if position < len(
            RECHERCHES
        ):

            time.sleep(
                PAUSE
            )


    # ========================================================
    # RESUME
    # ========================================================

    print()
    print()
    print("#" * 65)
    print("🏁 RÉSUMÉ WALLAPOP")
    print("#" * 65)
    print()


    for resultat in resultats:

        recherche = resultat.get(
            "recherche",
            "?",
        )

        statut = resultat.get(
            "statut",
            "?",
        )

        nombre = resultat.get(
            "nombre_urls",
            0,
        )


        print(
            f"{recherche:<22} "
            f"HTTP {statut} "
            f"→ {nombre} annonces"
        )


    print()

    print(
        "✅ Probe terminé."
    )


if __name__ == "__main__":

    main()