import re
import requests
from bs4 import BeautifulSoup


URL = "https://www.paruvendu.fr/annonces/informatique/"


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
        .split()
    )


def est_url_annonce(href):

    if not href:
        return False

    return bool(
        re.search(
            r"/annonces/high-tech/.+/\d+[A-Z0-9]+/?$",
            href,
            flags=re.IGNORECASE,
        )
    )


def main():

    print()
    print("========================================")
    print("🔬 PC HUNTER - STRUCTURE PARUVENDU")
    print("========================================")
    print()


    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException as erreur:

        print("❌ Erreur :", erreur)
        return


    print(
        "📡 HTTP :",
        response.status_code,
    )


    if response.status_code != 200:

        return


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )


    annonces = []

    urls_vues = set()


    for lien in soup.find_all(
        "a",
        href=True,
    ):

        href = lien.get(
            "href"
        )


        if not est_url_annonce(
            href
        ):
            continue


        if href in urls_vues:
            continue


        urls_vues.add(
            href
        )


        annonces.append(
            lien
        )


    print(
        "📦 Annonces uniques détectées :",
        len(annonces),
    )


    # On inspecte seulement les 5 premières.
    for numero, lien in enumerate(
        annonces[:5],
        start=1,
    ):

        print()
        print("========================================")
        print(
            f"📦 ANNONCE {numero}"
        )
        print("========================================")


        print(
            "🔗 URL :",
            lien.get("href"),
        )


        print(
            "🏷️ TAG :",
            lien.name,
        )


        print(
            "🧩 ATTR LIEN :",
            lien.attrs,
        )


        texte_lien = nettoyer(
            lien.get_text(
                " ",
                strip=True,
            )
        )


        print(
            "📝 TEXTE LIEN :",
            texte_lien[:1000],
        )


        parent = lien


        for niveau in range(
            1,
            6,
        ):

            parent = parent.parent


            if parent is None:
                break


            print()
            print(
                f"⬆️ PARENT {niveau}"
            )


            print(
                "TAG :",
                parent.name,
            )


            print(
                "ATTR :",
                parent.attrs,
            )


            texte_parent = nettoyer(
                parent.get_text(
                    " ",
                    strip=True,
                )
            )


            print(
                "TEXTE :",
                texte_parent[:2000],
            )


    print()
    print("========================================")
    print("✅ STRUCTURE TERMINÉE")
    print("========================================")


if __name__ == "__main__":
    main()