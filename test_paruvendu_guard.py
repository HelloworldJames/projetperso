from collector.providers.paruvendu import rechercher
from analyzer.value import estimer_valeur


def afficher_liste(
    titre,
    valeurs
):

    print(
        titre
    )

    if not valeurs:

        print(
            "   - aucune"
        )

        return


    for valeur in valeurs:

        print(
            "   -",
            valeur
        )


def main():

    print()

    print(
        "========================================"
    )

    print(
        "🛡️ PC HUNTER - TEST GARDE PARUVENDU"
    )

    print(
        "========================================"
    )


    annonces = rechercher()


    print()

    print(
        "📦 Annonces à tester :",
        len(annonces)
    )


    autorisees = 0

    bloquees = 0


    # ========================================================
    # ANALYSE
    # ========================================================

    for numero, annonce in enumerate(
        annonces,
        start=1
    ):

        print()

        print(
            "########################################"
        )

        print(
            f"🔎 {numero}/{len(annonces)}"
        )

        print(
            annonce.titre
        )

        print(
            "########################################"
        )


        print(
            "💵 Prix :",
            annonce.prix,
            "€"
        )


        print(
            "📍 Ville :",
            annonce.localisation
        )


        # ====================================================
        # ESTIMATION
        # ====================================================

        try:

            (
                valeur,
                composants,
                estimation
            ) = estimer_valeur(
                annonce
            )


        except Exception as erreur:

            print(
                "❌ Erreur estimation :",
                erreur
            )

            continue


        # ====================================================
        # VALIDATION STRUCTURE
        # ====================================================

        if not isinstance(
            estimation,
            dict
        ):

            print(
                "⛔ Estimation invalide."
            )

            bloquees += 1

            continue


        # ====================================================
        # INFORMATIONS
        # ====================================================

        analyse_autorisee = (
            estimation.get(
                "analyse_autorisee",
                False
            )
        )


        statut = estimation.get(
            "statut",
            "INCONNU"
        )


        confiance = estimation.get(
            "confiance",
            "Inconnue"
        )


        critiques = estimation.get(
            "categories_critiques_non_fiables",
            []
        )


        non_valorises = estimation.get(
            "composants_non_valorises",
            []
        )


        raisons_blocage = estimation.get(
            "raisons_blocage",
            []
        )


        coherence = estimation.get(
            "coherence",
            {}
        )


        problemes_coherence = (
            coherence.get(
                "problemes",
                []
            )
        )


        # ====================================================
        # AFFICHAGE
        # ====================================================

        print()

        print(
            "📊 Statut :",
            statut
        )


        print(
            "🧠 Confiance :",
            confiance
        )


        print(
            "💰 Valeur calculée :",
            valeur,
            "€"
        )


        afficher_liste(
            "🧩 Composants reconnus :",
            composants
        )


        afficher_liste(
            "⚠️ Composants non valorisés :",
            non_valorises
        )


        afficher_liste(
            "🚨 Catégories critiques non fiables :",
            critiques
        )


        # ====================================================
        # COHÉRENCE MATÉRIEL
        # ====================================================

        if problemes_coherence:

            print()

            print(
                "⚠️ INCOHÉRENCES MATÉRIELLES :"
            )


            for probleme in (
                problemes_coherence
            ):

                print(
                    "   -",
                    probleme
                )


        # ====================================================
        # DÉCISION
        # ====================================================

        print()


        if analyse_autorisee:

            print(
                "✅ ANALYSE FINANCIÈRE AUTORISÉE"
            )

            autorisees += 1


        else:

            print(
                "⛔ ANALYSE FINANCIÈRE BLOQUÉE"
            )


            if raisons_blocage:

                print()

                print(
                    "📋 Raisons du blocage :"
                )


                for raison in raisons_blocage:

                    print(
                        "   -",
                        raison
                    )


            print()

            print(
                "➡️ Aucune marge, aucun score "
                "d'opportunité et aucune alerte "
                "ne doivent être calculés."
            )


            bloquees += 1


    # ========================================================
    # RÉSUMÉ
    # ========================================================

    print()

    print(
        "========================================"
    )

    print(
        "📊 RÉSUMÉ"
    )

    print(
        "========================================"
    )


    print(
        "✅ Autorisées :",
        autorisees
    )


    print(
        "⛔ Bloquées :",
        bloquees
    )


    print(
        "📦 Total :",
        len(annonces)
    )


if __name__ == "__main__":

    main()