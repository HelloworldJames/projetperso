from collector.providers.paruvendu import rechercher
from analyzer.components import detecter_composants


def main():

    annonces = rechercher()

    print()
    print("========================================")
    print("🧠 PC HUNTER - DÉTECTION COMPOSANTS")
    print("========================================")

    print()
    print(
        "📦 Annonces à analyser :",
        len(annonces)
    )

    for numero, annonce in enumerate(
        annonces,
        start=1
    ):

        composants = detecter_composants(
            annonce
        )

        print()
        print("########################################")
        print(
            f"🔎 {numero}/{len(annonces)}"
        )
        print(
            annonce.titre
        )
        print("########################################")

        print(
            "💵 Prix :",
            annonce.prix,
            "€"
        )

        print(
            "📍 Ville :",
            annonce.localisation
        )

        if not composants:

            print()
            print(
                "❌ Aucun composant précis détecté"
            )

            continue

        for categorie, valeurs in composants.items():

            print()
            print(
                f"🧩 {categorie.upper()}"
            )

            for valeur in valeurs:

                print(
                    "   -",
                    valeur
                )


if __name__ == "__main__":
    main()