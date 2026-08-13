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


CHAMPS = [
    "Carte graphique",
    "Gamme de processeur",
    "Vitesse du processeur",
    "Mémoire vive",
    "Capacité SSD",
    "Type de support de stockage",
    "Taille de la mémoire vidéo",
    "Magasin",
]


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def afficher_structure(
    soup,
    champ
):

    print()
    print("=" * 70)
    print("🔎 CHAMP :", champ)
    print("=" * 70)

    resultats = soup.find_all(
        string=re.compile(
            re.escape(champ),
            re.IGNORECASE
        )
    )

    if not resultats:

        print("❌ Champ non trouvé")
        return


    for numero, texte in enumerate(
        resultats[:3],
        start=1
    ):

        element = texte.parent

        print()
        print(
            f"--- occurrence {numero} ---"
        )

        print(
            "Texte détecté :",
            nettoyer(texte)
        )


        # On regarde plusieurs niveaux autour
        # du champ pour découvrir la structure HTML.

        courant = element

        for niveau in range(4):

            if courant is None:
                break

            contenu = nettoyer(
                courant.get_text(
                    " | ",
                    strip=True
                )
            )

            print()
            print(
                f"NIVEAU {niveau}:"
            )

            print(
                contenu[:700]
            )

            courant = courant.parent


def main():

    print()
    print(
        "🔬 PC HUNTER - STRUCTURE EASY CASH"
    )

    reponse = requests.get(
        URL,
        headers=HEADERS,
        timeout=20
    )

    print(
        "📡 HTTP :",
        reponse.status_code
    )

    if reponse.status_code != 200:

        return


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    for champ in CHAMPS:

        afficher_structure(
            soup,
            champ
        )


if __name__ == "__main__":

    main()