import json
import requests


BASE_URL = "https://www.paruvendu.fr"

AUTOCOMPLETE_URL = (
    BASE_URL
    + "/communfo/defaultcommunfo/defaultcommunfo/"
    + "autocompleteLocalisation"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": "application/json,text/javascript,*/*;q=0.01",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": (
        "https://www.paruvendu.fr/"
        "annonces/informatique/"
    ),
}


def main():

    print()
    print("========================================")
    print("📍 PC HUNTER - VILLE PARUVENDU")
    print("========================================")

    params = {
        "avecCodePostal": "1",
        "term": "Tonnay-Charente",
    }

    try:

        response = requests.get(
            AUTOCOMPLETE_URL,
            params=params,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException as erreur:

        print("❌ Erreur :", erreur)
        return

    print()
    print("🌐 URL :", response.url)
    print("📡 HTTP :", response.status_code)
    print("📦 Taille :", len(response.content))

    if response.status_code in {
        403,
        429,
    }:

        print()
        print("⛔ Accès refusé ou limité.")
        print("➡️ Aucun contournement.")
        return

    if response.status_code != 200:

        print()
        print("⚠️ Réponse non exploitable.")
        return

    print()
    print("📄 Content-Type :", response.headers.get("Content-Type"))

    try:

        data = response.json()

    except ValueError:

        print()
        print("⚠️ La réponse n'est pas du JSON.")
        print()
        print(response.text[:3000])
        return

    print()
    print("========================================")
    print("🎯 RÉSULTATS")
    print("========================================")

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("========================================")
    print("✅ TEST TERMINÉ")
    print("========================================")


if __name__ == "__main__":
    main()