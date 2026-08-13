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


def main():

    print()
    print("========================================")
    print("🛰️ PC HUNTER - PROBE PARUVENDU")
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

    print("📡 HTTP :", response.status_code)
    print("📦 Taille :", len(response.content), "octets")
    print(
        "📄 Content-Type :",
        response.headers.get("Content-Type"),
    )

    if response.status_code in {403, 429}:

        print()
        print("⛔ Accès refusé ou limité.")
        print("➡️ Aucun contournement.")
        return

    if response.status_code != 200:

        print()
        print("⚠️ Réponse non exploitable.")
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    titre = (
        soup.title.get_text(
            " ",
            strip=True,
        )
        if soup.title
        else "Inconnu"
    )

    print()
    print("📑 Titre :", titre)

    texte = " ".join(
        soup.get_text(
            " ",
            strip=True,
        ).split()
    )

    mots = [
        "RTX",
        "Ryzen",
        "PC gamer",
        "Ordinateur",
        "Particulier",
    ]

    print()
    print("🔎 Signaux trouvés :")

    for mot in mots:

        nombre = (
            texte.lower()
            .count(
                mot.lower()
            )
        )

        print(
            f"- {mot} : {nombre}"
        )

    liens = []

    for balise in soup.find_all(
        "a",
        href=True,
    ):

        href = balise.get("href")

        label = " ".join(
            balise.get_text(
                " ",
                strip=True,
            ).split()
        )

        if not href:
            continue

        contenu = (
            href
            + " "
            + label
        ).lower()

        if any(
            mot in contenu
            for mot in [
                "informatique",
                "ordinateur",
                "pc",
                "annonce",
            ]
        ):

            ligne = (
                label[:100],
                href,
            )

            if ligne not in liens:
                liens.append(ligne)

    print()
    print(
        "🔗 Liens potentiellement utiles :",
        len(liens),
    )

    for label, href in liens[:20]:

        print()
        print(
            "-",
            label or "(sans texte)",
        )
        print(
            " ",
            href[:300],
        )

    print()
    print("========================================")
    print("✅ PROBE TERMINÉ")
    print("========================================")


if __name__ == "__main__":
    main()