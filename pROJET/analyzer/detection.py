from datetime import datetime


def convertir_date_detection(date_texte):

    if not date_texte:
        return None

    try:
        date = datetime.fromisoformat(
            str(date_texte)
        )

        if date.tzinfo is None:
            timezone_locale = (
                datetime.now()
                .astimezone()
                .tzinfo
            )

            date = date.replace(
                tzinfo=timezone_locale
            )

        return date

    except ValueError:
        return None


def formater_age_detection(date_texte):

    date = convertir_date_detection(
        date_texte
    )

    if date is None:
        return "inconnue"

    maintenant = (
        datetime.now()
        .astimezone()
    )

    date = date.astimezone(
        maintenant.tzinfo
    )

    secondes = max(
        0,
        (
            maintenant - date
        ).total_seconds()
    )

    minutes = int(
        secondes // 60
    )

    if minutes < 1:
        return "à l'instant"

    if minutes < 60:
        return f"il y a {minutes} min"

    heures = minutes // 60
    minutes_restantes = minutes % 60

    if heures < 24:

        if minutes_restantes == 0:
            return f"il y a {heures} h"

        return (
            f"il y a {heures} h "
            f"{minutes_restantes} min"
        )

    jours = heures // 24
    heures_restantes = heures % 24

    if heures_restantes == 0:
        return f"il y a {jours} jour(s)"

    return (
        f"il y a {jours} jour(s) "
        f"{heures_restantes} h"
    )