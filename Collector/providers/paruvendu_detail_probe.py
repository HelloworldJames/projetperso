import re
import requests

from bs4 import BeautifulSoup


URL = (
    "https://www.paruvendu.fr/annonces/high-tech/"
    "ensemble-ordinateur-gaming--pont-l-abbe-d-arnoult-17250/"
    "1292920574A1KBMUMI000"
)


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


def main():

    print()
    print("========================================")
    print("🔬 PARUVENDU - FICHE DÉTAILLÉE")
    print("========================================")

    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException as erreur:

        print("❌", erreur)
        return


    print()
    print("📡 HTTP :", response.status_code)
    print("📦 Taille :", len(response.content))


    if response.status_code in {403, 429}:

        print("⛔ Accès refusé / limité.")
        return


    if response.status_code != 200:

        return


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )


    lignes = [
        nettoyer(texte)
        for texte in soup.stripped_strings
        if nettoyer(texte)
    ]


    # ========================================================
    # DESCRIPTION
    # ========================================================

    debut = None
    fin = None


    for index, ligne in enumerate(lignes):

        if (
            ligne.lower()
            == "description de l'annonce"
        ):
            debut = index + 1

        if (
            debut is not None
            and ligne.lower().startswith(
                "référence :"
            )
        ):
            fin = index
            break


    description = ""


    if (
        debut is not None
        and fin is not None
    ):

        morceaux = []

        for ligne in lignes[
            debut:fin
        ]:

            if ligne.lower().startswith(
                "lire la suite"
            ):
                continue

            # Évite le titre SEO ajouté
            # sous la description.
            if (
                "occasion à vendre à"
                in ligne.lower()
            ):
                continue

            morceaux.append(
                ligne
            )

        description = nettoyer(
            " ".join(morceaux)
        )


    # ========================================================
    # RÉFÉRENCE + ANCIENNETÉ
    # ========================================================

    reference = None
    publication = None


    for index, ligne in enumerate(lignes):

        if ligne.lower().startswith(
            "référence :"
        ):

            reference = ligne

            # Cherche juste après la référence.
            for suivante in lignes[
                index + 1:
                index + 8
            ]:

                if re.match(
                    r"^il y a\b",
                    suivante,
                    flags=re.IGNORECASE,
                ):

                    publication = suivante
                    break

            break


    print()
    print("========================================")
    print("📄 DONNÉES UTILES")
    print("========================================")

    print()
    print("📝 DESCRIPTION COMPLÈTE :")
    print(description or "Inconnue")

    print()
    print(
        "🆔",
        reference or "Référence inconnue",
    )

    print(
        "🕐 Publication :",
        publication or "Inconnue",
    )


    print()
    print("========================================")
    print("🔒 DONNÉES VENDEUR")
    print("========================================")

    print(
        "Non collectées volontairement."
    )


if __name__ == "__main__":
    main()