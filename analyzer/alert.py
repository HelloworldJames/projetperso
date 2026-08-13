def evaluer_alerte_immediate(
    annonce,
    est_nouvelle,
    score_opportunite,
    score_classement,
    rentabilite,
    diagnostic,
    estimation,
    fraicheur,
    budget_max,
    marge_min,
    accepter_reparations
):

    # Une annonce déjà connue ne déclenche
    # jamais une nouvelle alerte immédiate.
    if not est_nouvelle:
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Annonce déjà connue"
        }

    # Hors budget
    if annonce.prix > budget_max:
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Hors budget"
        }

    # Profil trop peu intéressé
    if score_classement < 85:
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Score personnalisé insuffisant"
        }

    # Analyse économique insuffisante
    if score_opportunite < 70:
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Score opportunité insuffisant"
        }

    # Marge prudente insuffisante
    if rentabilite["benefice_min"] < marge_min:
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Marge minimale insuffisante"
        }

    # Réparation interdite par le profil
    if (
        not accepter_reparations
        and diagnostic["cout_max"] > 0
    ):
        return {
            "declencher": False,
            "niveau": None,
            "raison": "Réparation non acceptée"
        }

    # --------------------------------------------------------
    # NIVEAU DE L'ALERTE
    # --------------------------------------------------------

    if (
        score_opportunite >= 80
        and score_classement >= 90
    ):
        niveau = "PEPITE"

    else:
        niveau = "PRIORITE"

    return {
        "declencher": True,
        "niveau": niveau,

        "titre": annonce.titre,
        "prix": annonce.prix,

        "distance_km": getattr(
            annonce,
            "distance_km",
            None
        ),

        "valeur_probable":
            estimation["valeur_probable"],

        "benefice_min":
            rentabilite["benefice_min"],

        "benefice_max":
            rentabilite["benefice_max"],

        "score_opportunite":
            score_opportunite,

        "score_classement":
            score_classement,

        "fraicheur":
            fraicheur,

        "url":
            annonce.url
    }


def afficher_alerte_immediate(alerte):

    if not alerte["declencher"]:
        return

    print()
    print(
        "========================================"
    )

    if alerte["niveau"] == "PEPITE":
        print(
            "🚨💎 PÉPITE PC HUNTER DÉTECTÉE"
        )
    else:
        print(
            "🚨 OPPORTUNITÉ PRIORITAIRE DÉTECTÉE"
        )

    print(
        "========================================"
    )

    print()
    print(
        "📝",
        alerte["titre"]
    )

    print(
        "💵 Prix :",
        alerte["prix"],
        "€"
    )

    print(
        "🎯 Valeur probable :",
        alerte["valeur_probable"],
        "€"
    )

    if (
        alerte["benefice_min"]
        ==
        alerte["benefice_max"]
    ):
        print(
            "💰 Marge estimée :",
            alerte["benefice_min"],
            "€"
        )

    else:
        print(
            "💰 Marge estimée :",
            alerte["benefice_min"],
            "à",
            alerte["benefice_max"],
            "€"
        )

    if alerte["distance_km"] is not None:
        print(
            "🚗 Distance :",
            alerte["distance_km"],
            "km"
        )

    print(
        "💎 Opportunité :",
        alerte["score_opportunite"],
        "/100"
    )

    print(
        "🎯 Score profil :",
        alerte["score_classement"],
        "/100"
    )

    print(
        "⏱️",
        alerte["fraicheur"]["label"]
    )

    if (
        alerte["fraicheur"]["age_secondes"]
        is not None
    ):
        print(
            "🕒 Publiée il y a :",
            alerte["fraicheur"]["age_texte"]
        )

    if alerte["url"]:
        print(
            "🔗",
            alerte["url"]
        )

    print()
    print(
        "⚡ À VÉRIFIER RAPIDEMENT"
    )

    print(
        "========================================"
    )
    # ============================================================
# ALERTE BAISSE DE PRIX
# ============================================================

def evaluer_alerte_baisse_prix(
    annonce,
    resultat_memoire,
    score_opportunite,
    score_classement,
    rentabilite,
    estimation
):

    if not isinstance(
        resultat_memoire,
        dict
    ):
        return {
            "declencher": False
        }

    statut = resultat_memoire.get(
        "statut"
    )

    # Seulement lorsqu'une vraie baisse
    # vient d'être détectée.
    if statut != "baisse":
        return {
            "declencher": False
        }


    ancien_prix = resultat_memoire.get(
        "ancien_prix"
    )

    nouveau_prix = resultat_memoire.get(
        "nouveau_prix"
    )


    if (
        ancien_prix is None
        or nouveau_prix is None
    ):
        return {
            "declencher": False
        }


    ancien_prix = float(
        ancien_prix
    )

    nouveau_prix = float(
        nouveau_prix
    )


    baisse_euros = (
        ancien_prix
        - nouveau_prix
    )


    if ancien_prix > 0:

        baisse_pourcentage = (
            baisse_euros
            / ancien_prix
            * 100
        )

    else:

        baisse_pourcentage = 0


    # Niveau de l'événement
    if (
        baisse_pourcentage >= 15
        or baisse_euros >= 75
    ):

        niveau = (
            "BAISSE_IMPORTANTE"
        )

    else:

        niveau = "BAISSE"


    return {
        "declencher": True,

        "niveau": niveau,

        "titre":
            annonce.titre,

        "plateforme":
            annonce.plateforme,

        "ancien_prix":
            ancien_prix,

        "nouveau_prix":
            nouveau_prix,

        "baisse_euros":
            baisse_euros,

        "baisse_pourcentage":
            baisse_pourcentage,

        "valeur_probable":
            estimation[
                "valeur_probable"
            ],

        "benefice_min":
            rentabilite[
                "benefice_min"
            ],

        "benefice_max":
            rentabilite[
                "benefice_max"
            ],

        "score_opportunite":
            score_opportunite,

        "score_classement":
            score_classement,

        "distance_km":
            getattr(
                annonce,
                "distance_km",
                None
            ),

        "url":
            annonce.url
    }