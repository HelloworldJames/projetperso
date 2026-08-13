import requests
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


PAGE_URL = (
    "https://www.paruvendu.fr/"
    "annonces/informatique/"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


CIBLES = [
    "lo-bonsplans",
    "codeINSEE-bonsplans",
    "codeinsee-bonsplans",
    "cp-bonsplans",
    "pa-bonsplans",
    "activation-multi-geoloc",
    "codeINSEE",
    "codeinsee",
]


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\\/", "/")
        .replace("\xa0", " ")
        .split()
    )


def est_paruvendu(url):

    domaine = (
        urlparse(url)
        .netloc
        .lower()
    )

    return domaine.endswith(
        "paruvendu.fr"
    )


def trouver_scripts(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    scripts = []

    for script in soup.find_all(
        "script",
        src=True,
    ):

        src = script.get("src")

        if not src:
            continue

        url = urljoin(
            PAGE_URL,
            src,
        )

        if not est_paruvendu(url):
            continue

        if url not in scripts:
            scripts.append(url)

    return scripts


def afficher_contextes(
    contenu,
    cible,
):

    contenu_min = contenu.lower()
    cible_min = cible.lower()

    depart = 0
    trouves = 0

    while True:

        position = contenu_min.find(
            cible_min,
            depart,
        )

        if position == -1:
            break

        debut = max(
            0,
            position - 1200,
        )

        fin = min(
            len(contenu),
            position + 2200,
        )

        extrait = nettoyer(
            contenu[
                debut:fin
            ]
        )

        print()
        print(
            "🔎",
            cible,
        )

        print(
            extrait[:5000]
        )

        trouves += 1

        depart = (
            position
            + len(cible)
        )

        if trouves >= 5:
            break

    return trouves


def main():

    print()
    print(
        "========================================"
    )
    print(
        "🎯 PC HUNTER - LOCALISATION PARUVENDU"
    )
    print(
        "========================================"
    )

    with requests.Session() as session:

        try:

            page = session.get(
                PAGE_URL,
                headers=HEADERS,
                timeout=20,
            )

        except requests.RequestException as erreur:

            print(
                "❌ Page :",
                erreur,
            )

            return

        print(
            "📡 HTTP page :",
            page.status_code,
        )

        if page.status_code != 200:
            return

        scripts = trouver_scripts(
            page.text
        )

        print(
            "📦 Scripts :",
            len(scripts),
        )

        total_scripts = 0

        for numero, url in enumerate(
            scripts,
            start=1,
        ):

            try:

                response = session.get(
                    url,
                    headers={
                        **HEADERS,
                        "Referer": PAGE_URL,
                    },
                    timeout=20,
                )

            except requests.RequestException:
                continue

            if response.status_code in {
                403,
                429,
            }:

                print(
                    "⛔ Blocage sur :",
                    url,
                )

                continue

            if response.status_code != 200:
                continue

            contenu = response.text

            cibles_presentes = [
                cible
                for cible in CIBLES
                if cible.lower()
                in contenu.lower()
            ]

            if not cibles_presentes:
                continue

            total_scripts += 1

            print()
            print(
                "========================================"
            )

            print(
                f"📜 SCRIPT CIBLE {numero}"
            )

            print(
                "🌐",
                url,
            )

            print(
                "🎯 Cibles :",
                cibles_presentes,
            )

            print(
                "========================================"
            )

            for cible in cibles_presentes:

                afficher_contextes(
                    contenu,
                    cible,
                )

        print()
        print(
            "========================================"
        )

        print(
            "📊 Scripts réellement utiles :",
            total_scripts,
        )

        print(
            "========================================"
        )


if __name__ == "__main__":
    main()