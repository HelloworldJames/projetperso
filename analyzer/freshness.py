from datetime import datetime


def convertir_date(date_publication):

    if not date_publication:
        return None

    texte = str(date_publication).strip()

    # Compatibilité avec les dates ISO finissant par Z
    if texte.endswith("Z"):
        texte = texte[:-1] + "+00:00"

    try:
        date = datetime.fromisoformat(texte)
    except ValueError:
        return None

    # Si aucune timezone n'est fournie,
    # on utilise la timezone locale du PC
    if date.tzinfo is None:
        timezone_locale = datetime.now().astimezone().tzinfo
        date = date.replace(tzinfo=timezone_locale)

    return date


def formater_age(secondes):

    minutes = int(secondes // 60)

    if minutes < 1:
        return "moins d'une minute"

    if minutes < 60:
        return f"{minutes} min"

    heures = minutes // 60
    minutes_restantes = minutes % 60

    if heures < 24:

        if minutes_restantes == 0:
            return f"{heures} h"

        return (
            f"{heures} h "
            f"{minutes_restantes} min"
        )

    jours = heures // 24
    heures_restantes = heures % 24

    if heures_restantes == 0:
        return f"{jours} jour(s)"

    return (
        f"{jours} jour(s) "
        f"{heures_restantes} h"
    )


def analyser_fraicheur(date_publication):

    date = convertir_date(
        date_publication
    )

    if date is None:

        return {
            "score": 0,
            "age_secondes": None,
            "age_texte": "inconnu",
            "label": "❓ Date de publication inconnue"
        }


    maintenant = datetime.now().astimezone()

    date = date.astimezone(
        maintenant.tzinfo
    )

    difference = maintenant - date

    secondes = max(
        0,
        difference.total_seconds()
    )

    minutes = secondes / 60
    heures = minutes / 60
    jours = heures / 24


    # ========================================================
    # SCORE DE FRAÎCHEUR
    # ========================================================

    if minutes <= 15:

        score = 100
        label = "🚨 ULTRA RÉCENTE"

    elif minutes <= 60:

        score = 95
        label = "🆕 TRÈS RÉCENTE"

    elif heures <= 3:

        score = 85
        label = "🟢 RÉCENTE"

    elif heures <= 6:

        score = 75
        label = "🟢 ASSEZ RÉCENTE"

    elif heures <= 12:

        score = 60
        label = "🟡 QUELQUES HEURES"

    elif heures <= 24:

        score = 45
        label = "🟡 AUJOURD'HUI"

    elif jours <= 3:

        score = 30
        label = "⚪ 1 À 3 JOURS"

    elif jours <= 7:

        score = 15
        label = "⚪ ANNONCE ANCIENNE"

    else:

        score = 5
        label = "🔘 TRÈS ANCIENNE"


    return {
        "score": score,
        "age_secondes": secondes,
        "age_texte": formater_age(secondes),
        "label": label
    }