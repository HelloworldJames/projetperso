import re

import requests


URL = (
    "https://www.leboncoin.fr/"
    "ck/ordinateurs/pc-gamer"
)


def main():

    print()
    print("=" * 55)
    print("🔎 PROBE LEBONCOIN")
    print("=" * 55)
    print()

    headers = {
        "User-Agent": "PC-Hunter-Prototype/0.1"
    }

    try:

        reponse = requests.get(
            URL,
            headers=headers,
            timeout=20,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return


    print(
        "🌐 Statut HTTP :",
        reponse.status_code,
    )

    print(
        "📍 URL finale :",
        reponse.url,
    )

    print(
        "📦 Taille réponse :",
        len(reponse.content),
        "octets",
    )

    print(
        "📄 Content-Type :",
        reponse.headers.get(
            "Content-Type",
            "inconnu",
        ),
    )


    # ========================================================
    # AUCUN CONTOURNEMENT
    # ========================================================

    if reponse.status_code in {
        403,
        429,
    }:

        print()
        print(
            "⛔ Leboncoin refuse ou limite "
            "la requête automatique."
        )

        print(
            "PC Hunter ne tente aucun contournement."
        )

        return


    if reponse.status_code != 200:

        print()
        print(
            "⚠️ Réponse HTTP inattendue."
        )

        return


    html = reponse.text


    # ========================================================
    # TITRE DE LA PAGE
    # ========================================================

    match_titre = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )


    if match_titre:

        titre_page = re.sub(
            r"\s+",
            " ",
            match_titre.group(1),
        ).strip()

        print()
        print(
            "📝 Titre page :",
            titre_page,
        )


    # ========================================================
    # INDICES PRESENTS DANS LE HTML
    # ========================================================

    texte = html.lower()


    indices = {
        "pc gamer": "PC Gamer",
        "prix": "Prix",
        "livraison": "Livraison",
        "très bon état": "Très bon état",
        "bon état": "Bon état",
        "rtx": "RTX",
        "ryzen": "Ryzen",
        "geforce": "GeForce",
    }


    print()
    print("=" * 55)
    print("🧪 INDICES DANS LA REPONSE")
    print("=" * 55)
    print()


    for recherche, nom in indices.items():

        present = (
            recherche in texte
        )

        print(
            f"{nom:18} :",
            "✅" if present else "❌",
        )


    # ========================================================
    # COMPTEURS SIMPLES
    # ========================================================

    print()
    print("=" * 55)
    print("📊 COMPTEURS")
    print("=" * 55)
    print()


    print(
        "RTX :",
        texte.count(
            "rtx"
        ),
    )

    print(
        "Ryzen :",
        texte.count(
            "ryzen"
        ),
    )

    print(
        "Livraison :",
        texte.count(
            "livraison"
        ),
    )


    # ========================================================
    # VERIFICATION DONNEES STRUCTUREES
    # ========================================================

    motifs_structures = {
        "__NEXT_DATA__": "__next_data__",
        "JSON-LD": "application/ld+json",
        "Hydratation": "hydration",
    }


    print()
    print("=" * 55)
    print("🧩 DONNEES STRUCTUREES")
    print("=" * 55)
    print()


    for nom, motif in motifs_structures.items():

        print(
            f"{nom:18} :",
            (
                "✅"
                if motif in texte
                else
                "❌"
            ),
        )


    print()
    print("=" * 55)
    print("✅ PROBE TERMINE")
    print("=" * 55)
    print()

    print(
        "ℹ️ Une seule page publique a été demandée."
    )

    print(
        "ℹ️ Aucun compte, cookie privé "
        "ou donnée vendeur n'a été utilisé."
    )


if __name__ == "__main__":

    main()