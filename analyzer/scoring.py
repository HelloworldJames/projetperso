from database.price import PRIX_COMPOSANTS


def analyser_annonce(annonce):

    score = 0
    raisons = []

    texte = (
        annonce.titre + " " +
        annonce.description
    ).lower()

    categories_trouvees = set()

    for composant, infos in PRIX_COMPOSANTS.items():

        categorie = infos["categorie"]
        aliases = infos["aliases"]

        # On a déjà trouvé un composant
        # de cette catégorie
        if categorie in categories_trouvees:
            continue

        detecte = False

        for alias in aliases:

            if alias in texte:
                detecte = True
                break

        if detecte:

            score += infos["score"]

            raisons.append(
                infos["label"] + " détecté"
            )

            categories_trouvees.add(
                categorie
            )

    # Sécurité
    score = max(
        0,
        min(score, 100)
    )

    return score, raisons