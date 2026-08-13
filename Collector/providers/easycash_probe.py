from pathlib import Path

import requests


URL = (
    "https://bons-plans.easycash.fr/"
    "informatique/ordinateur"
)

USER_AGENT = (
    "PC-Hunter/0.1 "
    "(personal second-hand market monitor)"
)


def tester_easycash():

    print("========================================")
    print("🧪 TEST CONNEXION EASY CASH")
    print("========================================")
    print()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }

    try:

        reponse = requests.get(
            URL,
            headers=headers,
            timeout=15,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Impossible de contacter Easy Cash :",
            erreur,
        )

        return


    print(
        "🌐 URL finale :",
        reponse.url,
    )

    print(
        "📡 HTTP :",
        reponse.status_code,
    )

    print(
        "📦 Taille :",
        len(reponse.content),
        "octets",
    )

    print(
        "📄 Type :",
        reponse.headers.get(
            "Content-Type",
            "inconnu",
        ),
    )

    print()


    if reponse.status_code == 200:

        print(
            "✅ Catalogue Easy Cash accessible"
        )

        dossier_data = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "data"
        )

        dossier_data.mkdir(
            exist_ok=True
        )

        fichier = (
            dossier_data
            / "easycash_probe.html"
        )

        fichier.write_text(
            reponse.text,
            encoding="utf-8",
        )

        print(
            "💾 Copie HTML enregistrée :",
            fichier,
        )

        print()
        print(
            "➡️ Prochaine étape : "
            "extraire les vraies annonces."
        )


    elif reponse.status_code in (
        403,
        429,
    ):

        print(
            "⛔ Easy Cash refuse "
            "l'accès automatisé."
        )

        print(
            "PC Hunter ne tentera "
            "aucun contournement."
        )

        print(
            "➡️ On essayera alors "
            "Cash Converters ou une autre source."
        )


    else:

        print(
            "⚠️ Réponse inattendue."
        )

        print(
            "On vérifiera avant "
            "d'intégrer cette source."
        )


if __name__ == "__main__":

    tester_easycash()