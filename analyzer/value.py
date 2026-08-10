from database.price import PRIX_COMPOSANTS


def estimer_valeur(annonce):

    texte = (
        annonce.titre + " " +
        annonce.description
    ).lower()

    valeur_composants = 0
    composants = []

    categories_trouvees = set()

    for composant, infos in PRIX_COMPOSANTS.items():

        if composant in texte:

            categorie = infos["categorie"]
            prix = infos["prix"]

            # Évite de compter deux composants
            # appartenant à la même catégorie
            if categorie not in categories_trouvees:

                valeur_composants += prix
                composants.append(composant)
                categories_trouvees.add(categorie)


    # Catégories principales attendues dans un PC
    categories_principales = {
        "gpu",
        "cpu",
        "ram",
        "stockage"
    }

    categories_manquantes = (
        categories_principales - categories_trouvees
    )


    # --------------------------------
    # ESTIMATION DU RESTE DU PC
    # --------------------------------
    # Carte mère, alimentation,
    # boîtier, refroidissement, etc.

    if valeur_composants > 0:

        valeur_basse = valeur_composants + 50

        valeur_probable = valeur_composants + 100

        valeur_haute = (
            valeur_composants
            + 150
            + (len(categories_manquantes) * 50)
        )

    else:

        valeur_basse = 0
        valeur_probable = 0
        valeur_haute = 0


    # --------------------------------
    # NIVEAU DE CONFIANCE
    # --------------------------------

    nombre_categories = len(categories_trouvees)

    if nombre_categories >= 4:

        confiance = "🟢 BONNE"
        confiance_score = 80

    elif nombre_categories == 3:

        confiance = "🟡 MOYENNE"
        confiance_score = 60

    elif nombre_categories == 2:

        confiance = "🟠 FAIBLE"
        confiance_score = 40

    else:

        confiance = "🔴 TRÈS FAIBLE"
        confiance_score = 20


    estimation = {
        "valeur_composants": valeur_composants,
        "valeur_basse": valeur_basse,
        "valeur_probable": valeur_probable,
        "valeur_haute": valeur_haute,
        "confiance": confiance,
        "confiance_score": confiance_score,
        "categories_trouvees": categories_trouvees,
        "categories_manquantes": categories_manquantes
    }


    # On garde valeur_probable comme valeur principale
    # pour ne pas casser profit.py et opportunity.py
    return valeur_probable, composants, estimation