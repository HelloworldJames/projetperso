def calculer_score_classement(
    score_opportunite,
    rentabilite,
    diagnostic,
    estimation,
    profil="equilibre"
):

    score = score_opportunite

    benefice_min = rentabilite["benefice_min"]
    cout_reparation_max = diagnostic["cout_max"]
    confiance = estimation["confiance_score"]

    # PROFIL PRUDENT
    if profil == "prudent":

        if cout_reparation_max == 0:
            score += 15

        elif cout_reparation_max <= 50:
            score -= 5

        elif cout_reparation_max <= 150:
            score -= 20

        else:
            score -= 35

        if confiance >= 80:
            score += 10

    # PROFIL ÉQUILIBRÉ
    elif profil == "equilibre":

        if benefice_min >= 150:
            score += 10

        if cout_reparation_max >= 150:
            score -= 5

        if confiance >= 80:
            score += 5

    # PROFIL RÉPARATION
    elif profil == "reparation":

        if benefice_min >= 200:
            score += 25

        elif benefice_min >= 150:
            score += 20

        elif benefice_min >= 100:
            score += 10

        if cout_reparation_max > 0:
            score += 10

        if cout_reparation_max > 300:
            score -= 20

    return max(0, min(score, 100))
def obtenir_verdict_classement(score, profil):

    if score >= 85:
        verdict = "🔥 PRIORITÉ"

    elif score >= 70:
        verdict = "🟢 TRÈS ADAPTÉE"

    elif score >= 50:
        verdict = "🟡 INTÉRESSANTE"

    elif score >= 30:
        verdict = "🟠 FAIBLE PRIORITÉ"

    else:
        verdict = "🔴 À ÉCARTER"

    return f"{verdict} pour le profil {profil.upper()}"