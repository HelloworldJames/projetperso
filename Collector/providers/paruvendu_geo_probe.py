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


MOTS = [
    "50km",
    "50 km",
    "distance",
    "rayon",
    "ville",
    "localisation",
    "location",
    "zipcode",
    "postal",
    "codepostal",
]


def nettoyer(texte):
    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def main():

    print()
    print("========================================")
    print("📍 PC HUNTER - GÉO PARUVENDU")
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

    print("📡 HTTP :", response.status_code)

    if response.status_code != 200:
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    print()
    print("========================================")
    print("📝 FORMULAIRES")
    print("========================================")

    for numero, form in enumerate(
        soup.find_all("form"),
        start=1,
    ):

        texte = nettoyer(
            form.get_text(
                " ",
                strip=True,
            )
        )

        html = str(form)

        ensemble = (
            texte
            + " "
            + html
        ).lower()

        if not any(
            mot.lower() in ensemble
            for mot in MOTS
        ):
            continue

        print()
        print(
            f"--- FORM {numero} ---"
        )

        print(
            "ACTION :",
            form.get("action"),
        )

        print(
            "METHOD :",
            form.get("method"),
        )

        print(
            "ATTR :",
            form.attrs,
        )

        print()
        print("CHAMPS :")

        for champ in form.find_all(
            ["input", "select", "button"]
        ):

            print({
                "tag": champ.name,
                "name": champ.get("name"),
                "value": champ.get("value"),
                "id": champ.get("id"),
                "type": champ.get("type"),
                "class": champ.get("class"),
            })


    print()
    print("========================================")
    print("🔎 ÉLÉMENTS 50 KM")
    print("========================================")

    for element in soup.find_all(True):

        texte = nettoyer(
            element.get_text(
                " ",
                strip=True,
            )
        )

        attrs = str(
            element.attrs
        )

        contenu = (
            texte
            + " "
            + attrs
        ).lower()

        if (
            "50km" not in contenu
            and
            "50 km" not in contenu
        ):
            continue

        print()
        print(
            "TAG :",
            element.name
        )

        print(
            "ATTR :",
            element.attrs
        )

        print(
            "TEXTE :",
            texte[:1000]
        )


    print()
    print("========================================")
    print("✅ PROBE TERMINÉ")
    print("========================================")


if __name__ == "__main__":
    main()