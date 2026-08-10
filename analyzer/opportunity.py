def analyser_opportunite(
    annonce,
    valeur_estimee,
    score_materiel,
    diagnostic,
    rentabilite,
    estimation
):

    score_opportunite = 0
    raisons = []

    texte = (
        annonce.titre + " " +
        annonce.description
    ).lower()

    benefice_min = rentabilite["benefice_min"]
    benefice_max = rentabilite["benefice_max"]

    # --------------------------------
    # 1. BÉNÉFICE NET PRUDENT
    # --------------------------------

    if benefice_min >= 250:
        score_opportunite += 45
        raisons.append(
            "🔥 Très forte marge nette potentielle"
        )

    elif benefice_min >= 150:
        score_opportunite += 35
        raisons.append(
            "💰 Forte marge nette potentielle"
        )

    elif benefice_min >= 100:
        score_opportunite += 25
        raisons.append(
            "Bonne marge nette potentielle"
        )

    elif benefice_min >= 50:
        score_opportunite += 15
        raisons.append(
            "Petite marge nette possible"
        )

    elif benefice_min > 0:
        score_opportunite += 5
        raisons.append(
            "Marge faible"
        )

    else:
        score_opportunite -= 25
        raisons.append(
            "❌ Pas de marge nette prudente"
        )

    # --------------------------------
    # 2. ROI PAR RAPPORT AU PRIX
    # --------------------------------

    if annonce.prix > 0:

        roi_prudent = (
            benefice_min / annonce.prix
        ) * 100

        if roi_prudent >= 100:
            score_opportunite += 20
            raisons.append(
                "🚀 ROI potentiel supérieur à 100%"
            )

        elif roi_prudent >= 50:
            score_opportunite += 15
            raisons.append(
                "📈 ROI potentiel supérieur à 50%"
            )

        elif roi_prudent >= 25:
            score_opportunite += 10
            raisons.append(
                "ROI potentiel intéressant"
            )

    # --------------------------------
    # 3. QUALITÉ MATÉRIEL
    # --------------------------------

    if score_materiel >= 80:
        score_opportunite += 15
        raisons.append(
            "✅ Configuration matérielle très intéressante"
        )

    elif score_materiel >= 60:
        score_opportunite += 10
        raisons.append(
            "Configuration matérielle intéressante"
        )

    elif score_materiel >= 40:
        score_opportunite += 5

    # --------------------------------
    # 4. CONFIANCE DE L'ESTIMATION
    # --------------------------------

    confiance = estimation["confiance_score"]

    if confiance >= 80:
        score_opportunite += 10
        raisons.append(
            "🧠 Estimation suffisamment documentée"
        )

    elif confiance >= 60:
        raisons.append(
            "🧠 Estimation moyennement fiable"
        )

    elif confiance >= 40:
        score_opportunite -= 10
        raisons.append(
            "⚠️ Informations insuffisantes pour une estimation fiable"
        )

    else:
        score_opportunite -= 20
        raisons.append(
            "🚨 Estimation très incertaine"
        )

    # --------------------------------
    # 5. RISQUE RÉPARATION
    # --------------------------------

    cout_max = diagnostic["cout_max"]

    if cout_max == 0:

        score_opportunite += 5

        raisons.append(
            "✅ Aucun coût de réparation détecté"
        )

    elif cout_max <= 50:

        score_opportunite -= 5

        raisons.append(
            "🔧 Risque de réparation faible"
        )

    elif cout_max <= 150:

        score_opportunite -= 15

        raisons.append(
            "⚠️ Risque de réparation modéré"
        )

    elif cout_max <= 300:

        score_opportunite -= 30

        raisons.append(
            "⚠️ Risque de réparation important"
        )

    else:

        score_opportunite -= 45

        raisons.append(
            "🚨 Risque de réparation très important"
        )

    # --------------------------------
    # 6. CONDITIONS RISQUÉES
    # --------------------------------

    expressions_risque = [
        "vendu en l'etat",
        "vendu en l'état",
        "pour pieces",
        "pour pièces",
        "non teste",
        "non testé"
    ]

    for expression in expressions_risque:

        if expression in texte:

            score_opportunite -= 10

            raisons.append(
                "⚠️ Vente présentant un risque supplémentaire"
            )

            break

    # --------------------------------
    # 7. PRIX ANORMALEMENT BAS
    # --------------------------------

    if (
        valeur_estimee > 0
        and annonce.prix < valeur_estimee * 0.5
    ):

        raisons.append(
            "🔍 Prix anormalement bas : vérification vendeur/annonce recommandée"
        )

    # --------------------------------
    # SCORE FINAL
    # --------------------------------

    score_opportunite = max(
        0,
        min(score_opportunite, 100)
    )

    # --------------------------------
    # VERDICT
    # --------------------------------

    if score_opportunite >= 80:
        verdict = "🔥 PÉPITE PC HUNTER"

    elif score_opportunite >= 60:
        verdict = "🟢 Opportunité intéressante"

    elif score_opportunite >= 35:
        verdict = "🟡 À surveiller"

    else:
        verdict = "🔴 Peu intéressant"

    return score_opportunite, raisons, verdict