def calculer_rentabilite(
    prix_vente,
    valeur_estimee,
    cout_reparation_min=0,
    cout_reparation_max=0
):

    benefice_max = (
        valeur_estimee
        - prix_vente
        - cout_reparation_min
    )

    benefice_min = (
        valeur_estimee
        - prix_vente
        - cout_reparation_max
    )

    benefice_moyen = round(
        (benefice_min + benefice_max) / 2
    )

    if benefice_min >= 200:
        verdict = "🔥 TRÈS RENTABLE"

    elif benefice_min >= 100:
        verdict = "🟢 BONNE MARGE"

    elif benefice_min >= 50:
        verdict = "🟡 MARGE POSSIBLE"

    elif benefice_max > 0:
        verdict = "⚠️ RENTABILITÉ INCERTAINE"

    else:
        verdict = "🔴 NON RENTABLE"

    return {
        "benefice_min": benefice_min,
        "benefice_max": benefice_max,
        "benefice_moyen": benefice_moyen,
        "reparation_min": cout_reparation_min,
        "reparation_max": cout_reparation_max,
        "verdict": verdict
    }