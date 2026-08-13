import json
from datetime import datetime
from pathlib import Path


FICHIER_TOP = Path(
    "data/top_actuel.json"
)


def enregistrer_top_snapshot(
    top,
    profil,
    budget_max,
    marge_min,
):
    """
    Enregistre l'état courant du TOP PC Hunter.

    Ce fichier représente uniquement le dernier Top calculé.
    Ce n'est pas l'historique complet du marché.
    """

    FICHIER_TOP.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resultats = []

    for position, resultat in enumerate(
        top,
        start=1,
    ):

        annonce = resultat.get(
            "annonce"
        )

        rentabilite = resultat.get(
            "rentabilite",
            {},
        )

        estimation = resultat.get(
            "estimation",
            {},
        )

        fraicheur = resultat.get(
            "fraicheur",
            {},
        )

        element = {
            "position":
                position,

            "titre":
                getattr(
                    annonce,
                    "titre",
                    "Annonce inconnue",
                ),

            "prix":
                getattr(
                    annonce,
                    "prix",
                    None,
                ),

            "localisation":
                getattr(
                    annonce,
                    "localisation",
                    None,
                ),

            "plateforme":
                getattr(
                    annonce,
                    "plateforme",
                    None,
                ),

            "url":
                getattr(
                    annonce,
                    "url",
                    None,
                ),

            "distance_km":
                resultat.get(
                    "distance_km"
                ),

            "categorie":
                resultat.get(
                    "categorie"
                ),

            "score_materiel":
                resultat.get(
                    "score_materiel"
                ),

            "score_opportunite":
                resultat.get(
                    "score_opportunite"
                ),

            "score_classement":
                resultat.get(
                    "score_classement"
                ),

            "verdict":
                resultat.get(
                    "verdict_classement"
                ),

            "valeur_estimee":
                resultat.get(
                    "valeur_estimee"
                ),

            "benefice_min":
                rentabilite.get(
                    "benefice_min"
                ),

            "benefice_max":
                rentabilite.get(
                    "benefice_max"
                ),

            "valeur_probable":
                estimation.get(
                    "valeur_probable"
                ),

            "fraicheur":
                fraicheur.get(
                    "label"
                ),
        }

        resultats.append(
            element
        )

    donnees = {
        "date_generation":
            datetime.now().astimezone().isoformat(),

        "profil":
            profil,

        "budget_max":
            budget_max,

        "marge_min":
            marge_min,

        "nombre_resultats":
            len(resultats),

        "top":
            resultats,
    }

    # On écrit d'abord dans un fichier temporaire.
    # Cela évite que le bot lise un JSON à moitié écrit.

    fichier_temporaire = (
        FICHIER_TOP.with_suffix(
            ".tmp"
        )
    )

    with fichier_temporaire.open(
        "w",
        encoding="utf-8",
    ) as fichier:

        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    fichier_temporaire.replace(
        FICHIER_TOP
    )

    return FICHIER_TOP