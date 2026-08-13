from collector.scraper import rechercher_annonces

from database.presence import (
    mettre_a_jour_presence,
    afficher_evenements_presence,
)

from database.listing import (
    initialiser_database,
    enregistrer_annonce,
    obtenir_historique_prix,
)
from database.market import (
    calculer_comparables_marche,
    enregistrer_observations,
)
from database.top_snapshot import (
    enregistrer_top_snapshot,
)
from database.watchlist import (
    marquer_notification_detection_envoyee,
)
from analyzer.scoring import analyser_annonce
from analyzer.value import estimer_valeur
from analyzer.profit import calculer_rentabilite
from analyzer.opportunity import analyser_opportunite

from analyzer.ranking import (
    calculer_score_classement,
    obtenir_verdict_classement,
)

from analyzer.freshness import analyser_fraicheur

from analyzer.detection import (
    formater_age_detection,
)

from analyzer.classifier import (
    classer_annonce,
)

from analyzer.alert import (
    evaluer_alerte_immediate,
    afficher_alerte_immediate,
    evaluer_alerte_baisse_prix,
)

import analyzer.repair as repair_module

from notifications.discord import (
    envoyer_alerte_discord,
    envoyer_baisse_prix_discord,
    envoyer_nouvelles_annonces_discord,
)

from config import (
    PROFIL,
    TOP_N,
    BUDGET_MAX,
    MARGE_MIN,
    ACCEPTER_REPARATIONS,
)


# ============================================================
# OUTILS
# ============================================================

def formater_prix(valeur):

    if valeur is None:
        return "?"

    try:

        nombre = float(
            valeur
        )

        if nombre.is_integer():

            return str(
                int(nombre)
            )

        return str(
            round(
                nombre,
                2
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return str(
            valeur
        )


def formater_benefice(
    rentabilite
):

    if not isinstance(
        rentabilite,
        dict
    ):

        return "?"

    benefice_min = (
        rentabilite.get(
            "benefice_min"
        )
    )

    benefice_max = (
        rentabilite.get(
            "benefice_max"
        )
    )

    if (
        benefice_min is None
        or
        benefice_max is None
    ):

        return "?"

    if benefice_min == benefice_max:

        return (
            f"{formater_prix(benefice_min)} €"
        )

    return (
        f"{formater_prix(benefice_min)} "
        f"à "
        f"{formater_prix(benefice_max)} €"
    )


def verdict_general_depuis_score(
    score
):

    try:

        score = int(
            score
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    if score >= 80:

        return (
            "🔥 PÉPITE PC HUNTER"
        )

    if score >= 60:

        return (
            "🟢 Opportunité intéressante"
        )

    if score >= 35:

        return (
            "🟡 À surveiller"
        )

    return (
        "🔴 Peu intéressant"
    )


# ============================================================
# RÉPARATION
# ============================================================

def analyser_reparation_compatible(
    annonce
):

    noms_possibles = (
        "analyser_reparation",
        "diagnostiquer_reparation",
        "estimer_reparation",
        "analyser_panne",
        "diagnostiquer_panne",
        "estimer_cout_reparation",
        "diagnostiquer",
    )

    for nom in noms_possibles:

        fonction = getattr(
            repair_module,
            nom,
            None,
        )

        if callable(
            fonction
        ):

            return fonction(
                annonce
            )

    raise ImportError(
        "Aucune fonction de réparation trouvée "
        "dans analyzer/repair.py"
    )


def normaliser_diagnostic(
    diagnostic
):

    if diagnostic is None:

        return {
            "cout_min": 0,
            "cout_max": 0,
            "diagnostic": [
                "Aucune panne identifiée"
            ],
        }

    if not isinstance(
        diagnostic,
        dict
    ):

        return {
            "cout_min": 0,
            "cout_max": 0,
            "diagnostic": [
                str(
                    diagnostic
                )
            ],
        }

    cout_min = diagnostic.get(
        "cout_min",
        0,
    )

    cout_max = diagnostic.get(
        "cout_max",
        0,
    )

    lignes = (
        diagnostic.get(
            "diagnostic"
        )
        or
        diagnostic.get(
            "diagnostics"
        )
        or
        diagnostic.get(
            "raisons"
        )
        or
        diagnostic.get(
            "problemes"
        )
        or
        diagnostic.get(
            "pannes"
        )
    )

    if not lignes:

        lignes = [
            "Aucune panne identifiée"
        ]

    if isinstance(
        lignes,
        str
    ):

        lignes = [
            lignes
        ]

    diagnostic[
        "cout_min"
    ] = cout_min

    diagnostic[
        "cout_max"
    ] = cout_max

    diagnostic[
        "diagnostic"
    ] = lignes

    return diagnostic


# ============================================================
# OPPORTUNITÉ
# ============================================================

def normaliser_resultat_opportunite(
    resultat
):

    if isinstance(
        resultat,
        tuple
    ):

        if len(resultat) >= 3:

            return (
                resultat[0],
                resultat[1],
                resultat[2],
            )

        if len(resultat) == 2:

            score = resultat[0]

            raisons = resultat[1]

            return (
                score,
                raisons,
                verdict_general_depuis_score(
                    score
                ),
            )

        if len(resultat) == 1:

            score = resultat[0]

            return (
                score,
                [],
                verdict_general_depuis_score(
                    score
                ),
            )

    if isinstance(
        resultat,
        dict
    ):

        score = resultat.get(
            "score",
            resultat.get(
                "score_opportunite",
                0,
            ),
        )

        raisons = resultat.get(
            "raisons",
            resultat.get(
                "analyse",
                [],
            ),
        )

        verdict = resultat.get(
            "verdict",
            verdict_general_depuis_score(
                score
            ),
        )

        return (
            score,
            raisons,
            verdict,
        )

    try:

        score = int(
            resultat or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    return (
        score,
        [],
        verdict_general_depuis_score(
            score
        ),
    )


# ============================================================
# MÉMOIRE
# ============================================================

def obtenir_statut_memoire(
    resultat
):

    if not isinstance(
        resultat,
        dict
    ):

        return "connue"

    return str(
        resultat.get(
            "statut",
            resultat.get(
                "status",
                "connue",
            ),
        )
    ).lower()


def afficher_statut_memoire(
    resultat
):

    if not isinstance(
        resultat,
        dict
    ):

        print(
            "♻️ Annonce déjà connue"
        )

        return

    statut = (
        obtenir_statut_memoire(
            resultat
        )
    )

    ancien_prix = resultat.get(
        "ancien_prix",
        resultat.get(
            "prix_avant"
        ),
    )

    nouveau_prix = resultat.get(
        "nouveau_prix",
        resultat.get(
            "prix_apres"
        ),
    )


    # ========================================================
    # NOUVELLE
    # ========================================================

    if statut in {
        "nouvelle",
        "nouveau",
        "new",
    }:

        print(
            "🆕 NOUVELLE ANNONCE DÉTECTÉE"
        )

        return


    # ========================================================
    # BAISSE
    # ========================================================

    if statut in {
        "baisse",
        "baisse_prix",
        "price_drop",
    }:

        print(
            "📉 BAISSE DE PRIX DÉTECTÉE"
        )

        if ancien_prix is not None:

            print(
                "💵 Ancien prix :",
                formater_prix(
                    ancien_prix
                ),
                "€",
            )

        if nouveau_prix is not None:

            print(
                "💵 Nouveau prix :",
                formater_prix(
                    nouveau_prix
                ),
                "€",
            )

        if (
            ancien_prix is not None
            and
            nouveau_prix is not None
        ):

            try:

                baisse = (
                    float(
                        ancien_prix
                    )
                    -
                    float(
                        nouveau_prix
                    )
                )

                print(
                    "💰 Baisse :",
                    formater_prix(
                        baisse
                    ),
                    "€",
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

        return


    # ========================================================
    # HAUSSE
    # ========================================================

    if statut in {
        "hausse",
        "hausse_prix",
        "price_increase",
    }:

        print(
            "📈 HAUSSE DE PRIX DÉTECTÉE"
        )

        if ancien_prix is not None:

            print(
                "💵 Ancien prix :",
                formater_prix(
                    ancien_prix
                ),
                "€",
            )

        if nouveau_prix is not None:

            print(
                "💵 Nouveau prix :",
                formater_prix(
                    nouveau_prix
                ),
                "€",
            )

        return


    print(
        "♻️ Annonce déjà connue"
    )


def afficher_historique(
    identifiant
):

    try:

        historique = (
            obtenir_historique_prix(
                identifiant
            )
        )

    except Exception as erreur:

        print(
            "⚠️ Historique indisponible :",
            erreur,
        )

        return

    if (
        not historique
        or
        len(historique) <= 1
    ):

        return

    print()

    print(
        "📜 HISTORIQUE DES PRIX"
    )

    for entree in historique:

        if isinstance(
            entree,
            dict
        ):

            prix = entree.get(
                "prix",
                "?",
            )

            date = entree.get(
                "date",
                "?",
            )

        else:

            prix = str(
                entree
            )

            date = ""

        print(
            "-",
            formater_prix(
                prix
            ),
            "€",
            "|",
            date,
        )


# ============================================================
# AFFICHAGE LISTE
# ============================================================

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
            valeur,
        )


# ============================================================
# ESTIMATION BLOQUÉE
# ============================================================

def afficher_bloc_estimation_bloquee(
    valeur_estimee,
    composants,
    estimation,
    diagnostic,
):

    print()

    print(
        "🛡️ ANALYSE FINANCIÈRE BLOQUÉE"
    )

    print(
        "📊 Statut :",
        estimation.get(
            "statut",
            "INCOMPLETE",
        ),
    )

    print(
        "🧠 Confiance :",
        estimation.get(
            "confiance",
            "?",
        ),
    )

    print(
        "💰 Valeur partielle calculée :",
        formater_prix(
            valeur_estimee
        ),
        "€",
    )

    print()

    afficher_liste(
        "🧩 Composants reconnus :",
        composants,
    )

    print()

    afficher_liste(
        "⚠️ Composants non valorisés :",
        estimation.get(
            "composants_non_valorises",
            [],
        ),
    )

    print()

    afficher_liste(
        "🚨 Catégories critiques non fiables :",
        estimation.get(
            "categories_critiques_non_fiables",
            [],
        ),
    )


    coherence = estimation.get(
        "coherence",
        {},
    )

    problemes = coherence.get(
        "problemes",
        [],
    )

    if problemes:

        print()

        afficher_liste(
            "⚠️ Incohérences matérielles :",
            problemes,
        )


    raisons_blocage = estimation.get(
        "raisons_blocage",
        [],
    )

    if raisons_blocage:

        print()

        afficher_liste(
            "📋 Raisons du blocage :",
            raisons_blocage,
        )


    print()

    print(
        "🔧 Diagnostic réparation :"
    )

    for ligne in diagnostic.get(
        "diagnostic",
        [],
    ):

        print(
            "   -",
            ligne,
        )

    print()

    print(
        "➡️ PC Hunter conserve l'annonce, "
        "son historique et sa présence, "
        "mais ne calcule aucune marge, "
        "aucun score d'opportunité, "
        "aucun classement et aucune alerte d'achat."
    )


# ============================================================
# MÉDAILLES
# ============================================================

def obtenir_medaille(
    position
):

    if position == 1:
        return "🥇"

    if position == 2:
        return "🥈"

    if position == 3:
        return "🥉"

    return "🔹"


# ============================================================
# CLÉ DE TRI
# ============================================================

def cle_classement(
    resultat
):

    score = resultat.get(
        "score_classement",
        0,
    )

    fraicheur = resultat.get(
        "fraicheur",
        {},
    )

    score_fraicheur = fraicheur.get(
        "score",
        0,
    )

    if score_fraicheur is None:

        score_fraicheur = 0


    distance = resultat.get(
        "distance_km"
    )

    if distance is None:

        distance = 999999


    return (
        score,
        score_fraicheur,
        -distance,
    )


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print()

    print(
        "🚀 PC Hunter AI démarré"
    )

    print()


    # ========================================================
    # BASE
    # ========================================================

    initialiser_database()


    # ========================================================
    # COLLECTE
    # ========================================================

    annonces = (
        rechercher_annonces()
    )

    print()

    print(
        "🔎",
        len(annonces),
        "annonces envoyées à PC Hunter"
    )


    # ========================================================
    # OBSERVATIONS MARCHE
    #
    # La liste a deja ete dedupliquee et filtree par
    # rechercher_annonces(). Cet appel reste unique pour
    # chaque scan complet.
    # ========================================================

    try:

        nouvelles_observations = (
            enregistrer_observations(
                annonces
            )
        )

        print()

        print(
            "📊",
            nouvelles_observations,
            "nouvelles observations marché enregistrées",
        )

    except Exception as erreur:

        print()

        print(
            "⚠️ Enregistrement des observations marché "
            "impossible :",
            erreur,
        )


    # ========================================================
    # PRÉSENCE
    # ========================================================

    evenements_presence = (
        mettre_a_jour_presence(
            annonces
        )
    )

    afficher_evenements_presence(
        evenements_presence
    )


    # ========================================================
    # TOP
    # ========================================================

    classement = []
    nouvelles_detectees = []


    # ========================================================
    # BOUCLE ANNONCES
    # ========================================================

    for numero, annonce in enumerate(
        annonces,
        start=1,
    ):

        print()

        print(
            "########################################"
        )

        print(
            f"🔎 ANALYSE ANNONCE "
            f"{numero}/{len(annonces)}"
        )

        print(
            "########################################"
        )

        print()


        # ====================================================
        # MÉMOIRE
        # ====================================================

        resultat_memoire = (
            enregistrer_annonce(
                annonce
            )
        )


        if not isinstance(
            resultat_memoire,
            dict
        ):

            resultat_memoire = {}


        afficher_statut_memoire(
            resultat_memoire
        )


        afficher_historique(
            annonce.identifiant
        )


        premiere_detection = (
            resultat_memoire.get(
                "premiere_detection"
            )
        )


        derniere_detection = (
            resultat_memoire.get(
                "derniere_detection"
            )
        )


        est_nouvelle = (
            resultat_memoire.get(
                "est_nouvelle",
                False,
            )
        )


        if not est_nouvelle:

            statut_memoire = (
                obtenir_statut_memoire(
                    resultat_memoire
                )
            )

            est_nouvelle = (
                statut_memoire
                in {
                    "nouvelle",
                    "nouveau",
                    "new",
                }
            )


        # ====================================================
        # CLASSIFICATION
        # ====================================================

        try:

            classification = (
                classer_annonce(
                    annonce
                )
            )

        except Exception as erreur:

            print()

            print(
                "❌ Erreur classification :",
                erreur,
            )

            classification = {
                "categorie":
                    "INCONNU",

                "analyse_pc":
                    False,

                "raison":
                    "Classification impossible",
            }


        categorie_annonce = (
            classification.get(
                "categorie",
                "INCONNU",
            )
        )


        analyse_pc = (
            classification.get(
                "analyse_pc",
                False,
            )
        )


        raison_classification = (
            classification.get(
                "raison",
                "",
            )
        )


        print()

        print(
            "🏷️ Type d'annonce :",
            categorie_annonce,
        )


        if raison_classification:

            print(
                "   -",
                raison_classification,
            )
        # ====================================================
        # ÉVÉNEMENT COMMUN : NOUVELLE ANNONCE
        #
        # La détection est indépendante du verdict financier.
        # Les messages sont regroupés après la boucle.
        # ====================================================

        if (
            est_nouvelle
            and
            not getattr(
                annonce,
                "notification_detection_deja_envoyee",
                False,
            )
        ):

            nouvelles_detectees.append(
                {
                    "identifiant":
                        annonce.identifiant,

                    "titre":
                        annonce.titre,

                    "prix":
                        annonce.prix,

                    "plateforme":
                        annonce.plateforme,

                    "localisation":
                        annonce.localisation,

                    "description":
                        annonce.description,

                    "categorie":
                        categorie_annonce,

                    "url":
                        annonce.url,

                    "origine_watchlist":
                        bool(
                            getattr(
                                annonce,
                                "origine_watchlist",
                                False,
                            )
                        ),
                }
            )

        # ====================================================
        # COMPOSANT / ACCESSOIRE / INCONNU
        #
        # On conserve l'annonce dans SQLite et le suivi
        # de présence, mais elle ne pollue pas le moteur PC.
        # ====================================================

        if not analyse_pc:

            print()

            print(
                "⏭️ Analyse PC ignorée."
            )

            print(
                "➡️ Annonce conservée en mémoire "
                "mais exclue de l'analyse "
                "des PC complets."
            )

            continue


        # ====================================================
        # DÉTECTION MÉMOIRE
        # ====================================================

        if est_nouvelle:

            print()

            print(
                "🆕 PC Hunter : "
                "PREMIÈRE DÉTECTION"
            )

        else:

            if premiere_detection:

                print()

                print(
                    "Première détection :",
                    formater_age_detection(
                        premiere_detection
                    ),
                )

            if derniere_detection:

                print(
                    "Dernière détection :",
                    formater_age_detection(
                        derniere_detection
                    ),
                )


        # ====================================================
        # FRAÎCHEUR
        # ====================================================

        fraicheur = (
            analyser_fraicheur(
                annonce.date_publication
            )
        )


        # ====================================================
        # SCORE MATÉRIEL
        # ====================================================

        try:

            (
                score_materiel,
                raisons_materiel,
            ) = analyser_annonce(
                annonce
            )

        except Exception as erreur:

            print(
                "❌ Erreur score matériel :",
                erreur,
            )

            score_materiel = 0

            raisons_materiel = []


        # ====================================================
        # ESTIMATION
        # ====================================================

        try:

            (
                valeur_estimee,
                composants,
                estimation,
            ) = estimer_valeur(
                annonce
            )

        except Exception as erreur:

            print(
                "❌ Erreur estimation :",
                erreur,
            )

            continue


        if not isinstance(
            estimation,
            dict
        ):

            print(
                "⛔ Estimation invalide."
            )

            continue


        # ====================================================
        # COMPARABLES DE MARCHE - INFORMATIF UNIQUEMENT
        # ====================================================

        try:

            comparables_marche = (
                calculer_comparables_marche(
                    annonce,
                    estimation,
                )
            )

        except Exception as erreur:

            print(
                "⚠️ Comparables marché indisponibles :",
                erreur,
            )

            comparables_marche = {
                "nombre_comparables": 0,
                "prix_minimum": None,
                "prix_median": None,
                "prix_maximum": None,
            }

        estimation[
            "comparables_marche"
        ] = comparables_marche


        # ====================================================
        # RÉPARATION
        # ====================================================

        try:

            diagnostic = (
                analyser_reparation_compatible(
                    annonce
                )
            )


            diagnostic = (
                normaliser_diagnostic(
                    diagnostic
                )
            )

        except Exception as erreur:

            print(
                "⚠️ Diagnostic réparation indisponible :",
                erreur,
            )


            diagnostic = (
                normaliser_diagnostic(
                    None
                )
            )


        # ====================================================
        # RÉCAPITULATIF
        # ====================================================

        print()

        print(
            "----------------------------------------"
        )

        print(
            "📋 RÉCAPITULATIF DE L'ANNONCE"
        )

        print(
            "----------------------------------------"
        )

        print()


        print(
            "🏷️ Type :",
            categorie_annonce,
        )


        print(
            "📝 Titre :",
            annonce.titre,
        )


        print(
            "💵 Prix de vente :",
            formater_prix(
                annonce.prix
            ),
            "€",
        )


        print(
            "📍 Localisation :",
            annonce.localisation,
        )


        print(
            "🌐 Plateforme :",
            annonce.plateforme,
        )


        if getattr(
            annonce,
            "distance_km",
            None,
        ) is not None:

            print(
                "🚗 Distance :",
                annonce.distance_km,
                "km",
            )


        if getattr(
            annonce,
            "url",
            None,
        ):

            print(
                "🔗 URL :",
                annonce.url,
            )


        print(
            "📄 Description :",
            annonce.description,
        )


        print(
            "⏱️ Fraîcheur :",
            fraicheur.get(
                "label",
                "?",
            ),
        )


        if (
            fraicheur.get(
                "age_secondes"
            )
            is not None
        ):

            print(
                "🕒 Publiée il y a :",
                fraicheur.get(
                    "age_texte",
                    "?",
                ),
            )

            print(
                "⚡ Score fraîcheur :",
                fraicheur.get(
                    "score",
                    0,
                ),
                "/100",
            )


        print()

        print(
            "📊 SCORE MATÉRIEL :",
            score_materiel,
            "/100",
        )


        if raisons_materiel:

            print()

            print(
                "✅ Critères détectés :"
            )

            for raison in raisons_materiel:

                print(
                    "   -",
                    raison,
                )


        # ====================================================
        # GARDE FINANCIER
        # ====================================================

        analyse_autorisee = (
            estimation.get(
                "analyse_autorisee",
                False,
            )
        )


        if not analyse_autorisee:

            afficher_bloc_estimation_bloquee(
                valeur_estimee,
                composants,
                estimation,
                diagnostic,
            )

            continue


        # ====================================================
        # ANALYSE FINANCIÈRE AUTORISÉE
        # ====================================================

        print()

        print(
            "✅ ANALYSE FINANCIÈRE AUTORISÉE"
        )

        print()

        afficher_liste(
            "🧩 Composants détectés :",
            composants,
        )


        print()

        print(
            "💰 Valeur composants :",
            formater_prix(
                estimation.get(
                    "valeur_composants",
                    0,
                )
            ),
            "€",
        )


        print(
            "📉 Valeur basse estimée :",
            formater_prix(
                estimation.get(
                    "valeur_basse",
                    0,
                )
            ),
            "€",
        )


        print(
            "🎯 Valeur probable :",
            formater_prix(
                estimation.get(
                    "valeur_probable",
                    valeur_estimee,
                )
            ),
            "€",
        )


        print(
            "📈 Valeur haute estimée :",
            formater_prix(
                estimation.get(
                    "valeur_haute",
                    0,
                )
            ),
            "€",
        )


        print(
            "🧠 Confiance estimation :",
            estimation.get(
                "confiance",
                "?",
            ),
        )


        # ====================================================
        # RENTABILITÉ
        # ====================================================

        try:

            rentabilite = (
                calculer_rentabilite(
                    annonce.prix,
                    valeur_estimee,
                    diagnostic[
                        "cout_min"
                    ],
                    diagnostic[
                        "cout_max"
                    ],
                )
            )

        except Exception as erreur:

            print(
                "❌ Erreur rentabilité :",
                erreur,
            )

            continue


        # ====================================================
        # OPPORTUNITÉ
        # ====================================================

        try:

            resultat_opportunite = (
                analyser_opportunite(
                    annonce,
                    valeur_estimee,
                    score_materiel,
                    diagnostic,
                    rentabilite,
                    estimation,
                )
            )

        except Exception as erreur:

            print(
                "❌ Erreur analyse opportunité :",
                erreur,
            )

            continue


        (
            score_opportunite,
            raisons_opportunite,
            verdict_general,
        ) = (
            normaliser_resultat_opportunite(
                resultat_opportunite
            )
        )


        # ====================================================
        # CLASSEMENT PERSONNALISÉ
        # ====================================================

        try:

            score_classement = (
                calculer_score_classement(
                    score_opportunite,
                    rentabilite,
                    diagnostic,
                    estimation,
                    PROFIL,
                )
            )

        except Exception as erreur:

            print(
                "❌ Erreur classement :",
                erreur,
            )

            score_classement = 0


        try:

            verdict_classement = (
                obtenir_verdict_classement(
                    score_classement,
                    PROFIL,
                )
            )

        except Exception:

            verdict_classement = (
                "Classement indisponible"
            )


        # ====================================================
        # AFFICHAGE FINANCIER
        # ====================================================

        print()

        print(
            "💵 Prix demandé :",
            formater_prix(
                annonce.prix
            ),
            "€",
        )


        print(
            "💰 Bénéfice potentiel :",
            formater_benefice(
                rentabilite
            ),
        )


        print(
            "🔧 Coût réparation :",
            formater_prix(
                diagnostic.get(
                    "cout_min",
                    0,
                )
            ),
            "à",
            formater_prix(
                diagnostic.get(
                    "cout_max",
                    0,
                )
            ),
            "€",
        )


        print()

        if "comparables_marche" in estimation:

            comparables_affichage = estimation[
                "comparables_marche"
            ]

            nombre_comparables = (
                comparables_affichage.get(
                    "nombre_comparables",
                    0,
                )
            )

            print(
                "📊 MARCHÉ OBSERVÉ"
            )

            print(
                "Comparables stricts :",
                nombre_comparables,
            )

            if nombre_comparables > 0:

                print(
                    "- Minimum :",
                    formater_prix(
                        comparables_affichage.get(
                            "prix_minimum"
                        )
                    ),
                    "€",
                )

                print(
                    "- Médiane :",
                    formater_prix(
                        comparables_affichage.get(
                            "prix_median"
                        )
                    ),
                    "€",
                )

                print(
                    "- Maximum :",
                    formater_prix(
                        comparables_affichage.get(
                            "prix_maximum"
                        )
                    ),
                    "€",
                )

            else:

                print(
                    "- Aucun comparable strict "
                    "disponible actuellement"
                )

            print()

        print(
            "🔧 DIAGNOSTIC RÉPARATION :"
        )


        for ligne in diagnostic.get(
            "diagnostic",
            [],
        ):

            print(
                "   -",
                ligne,
            )


        print()

        print(
            "💎 SCORE OPPORTUNITÉ :",
            score_opportunite,
            "/100",
        )


        print(
            "🎯 SCORE CLASSEMENT :",
            score_classement,
            "/100",
            f"({PROFIL.upper()})",
        )


        print(
            "🔬 Verdict général :",
            verdict_general,
        )


        print(
            "🎯 Verdict personnalisé :",
            verdict_classement,
        )


        if raisons_opportunite:

            print()

            print(
                "📋 Analyse opportunité :"
            )

            for raison in raisons_opportunite:

                print(
                    "   -",
                    raison,
                )


        # ====================================================
        # AJOUT AU TOP
        # ====================================================

        classement.append(
            {
                "annonce":
                    annonce,

                "categorie":
                    categorie_annonce,

                "score_materiel":
                    score_materiel,

                "score_opportunite":
                    score_opportunite,

                "score_classement":
                    score_classement,

                "verdict_general":
                    verdict_general,

                "verdict_classement":
                    verdict_classement,

                "valeur_estimee":
                    valeur_estimee,

                "rentabilite":
                    rentabilite,

                "diagnostic":
                    diagnostic,

                "estimation":
                    estimation,

                "fraicheur":
                    fraicheur,

                "distance_km":
                    getattr(
                        annonce,
                        "distance_km",
                        None,
                    ),
            }
        )
        # ====================================================
        # GARDE D'ENTRÉE DANS LE TOP
        # ====================================================

        benefice_prudent = rentabilite.get(
            "benefice_min"
        )

        prix_dans_budget = (
            annonce.prix <= BUDGET_MAX
        )

        marge_suffisante = (
            benefice_prudent is not None
            and
            benefice_prudent >= MARGE_MIN
        )

        if not (
            prix_dans_budget
            and
            marge_suffisante
        ):

            classement.pop()

            print()
            print(
                "🚫 Exclue du TOP PC Hunter : "
                "budget ou marge insuffisante"
            )

        # ====================================================
        # ALERTE IMMÉDIATE
        # ====================================================

        try:

            alerte = (
                evaluer_alerte_immediate(
                    annonce=annonce,
                    est_nouvelle=est_nouvelle,
                    score_opportunite=score_opportunite,
                    score_classement=score_classement,
                    rentabilite=rentabilite,
                    diagnostic=diagnostic,
                    estimation=estimation,
                    fraicheur=fraicheur,
                    budget_max=BUDGET_MAX,
                    marge_min=MARGE_MIN,
                    accepter_reparations=ACCEPTER_REPARATIONS,
                )
            )


            afficher_alerte_immediate(
                alerte
            )


            envoyer_alerte_discord(
                alerte
            )

        except Exception as erreur:

            print(
                "⚠️ Alerte immédiate indisponible :",
                erreur,
            )


        # ====================================================
        # ALERTE BAISSE DE PRIX
        # ====================================================

        try:

            alerte_baisse = (
                evaluer_alerte_baisse_prix(
                    annonce=annonce,
                    resultat_memoire=resultat_memoire,
                    score_opportunite=score_opportunite,
                    score_classement=score_classement,
                    rentabilite=rentabilite,
                    estimation=estimation,
                )
            )


            envoyer_baisse_prix_discord(
                alerte_baisse
            )

        except Exception as erreur:

            print(
                "⚠️ Alerte baisse de prix indisponible :",
                erreur,
            )


    # ========================================================
    # DISCORD : RÉSUMÉ DES NOUVELLES ANNONCES
    # ========================================================

    try:

        resume_envoye = (
            envoyer_nouvelles_annonces_discord(
                nouvelles_detectees
            )
        )

        if resume_envoye:
            references_watchlist = [
                annonce["identifiant"]
                for annonce in nouvelles_detectees
                if annonce.get(
                    "origine_watchlist",
                    False,
                )
            ]

            marquer_notification_detection_envoyee(
                references_watchlist
            )

    except Exception as erreur:

        print(
            "⚠️ Résumé des nouvelles annonces indisponible :",
            erreur,
        )


    # ========================================================
    # TOP PC HUNTER
    # ========================================================

    print()

    print(
        "########################################"
    )

    print(
        "🏆 TOP PC HUNTER"
    )

    print(
        "########################################"
    )

    print()


    print(
        "🎯 Profil actif :",
        PROFIL.upper(),
    )


    print(
        "💳 Budget maximum :",
        BUDGET_MAX,
        "€",
    )


    print(
        "💰 Marge minimum :",
        MARGE_MIN,
        "€",
    )


    print(
        "🔧 Réparations acceptées :",
        (
            "OUI"
            if ACCEPTER_REPARATIONS
            else
            "NON"
        ),
    )


    # ========================================================
    # TRI
    # ========================================================

    classement.sort(
    key=cle_classement,
    reverse=True,
)


    top = classement[
        :TOP_N
    ]


    # ========================================================
    # SNAPSHOT DU TOP POUR DISCORD
    # ========================================================

    try:

        chemin_top = enregistrer_top_snapshot(
            top=top,
            profil=PROFIL,
            budget_max=BUDGET_MAX,
            marge_min=MARGE_MIN,
        )

        print()

        print(
            "💾 Snapshot TOP enregistré :",
            chemin_top,
        )

    except Exception as erreur:

        print()

        print(
            "⚠️ Snapshot TOP indisponible :",
            erreur,
        )


    # ========================================================
    # AUCUN RÉSULTAT
    # ========================================================

    if not top:

        print()

        print(
            "⛔ Aucun PC ne possède actuellement "
            "une analyse financière suffisamment fiable "
            "pour entrer dans le Top."
        )

        print()

        print(
            "ℹ️ Les annonces bloquées, les composants "
            "et les accessoires restent en mémoire."
        )

        print()

        print(
            "✅ Analyse terminée"
        )

        return

    # ========================================================
    # AFFICHAGE TOP
    # ========================================================

    for position, resultat in enumerate(
        top,
        start=1,
    ):

        annonce = resultat[
            "annonce"
        ]


        print()

        print(
            obtenir_medaille(
                position
            ),
            f"#{position}",
        )


        print(
            "🏷️",
            resultat.get(
                "categorie",
                "PC",
            ),
        )


        print(
            "📝",
            annonce.titre,
        )


        print(
            "📍",
            annonce.localisation,
        )


        print(
            "🌐",
            annonce.plateforme,
        )


        print(
            "💵 Prix :",
            formater_prix(
                annonce.prix
            ),
            "€",
        )


        print(
            "🎯 Valeur probable :",
            formater_prix(
                resultat[
                    "valeur_estimee"
                ]
            ),
            "€",
        )


        print(
            "💰 Bénéfice potentiel :",
            formater_benefice(
                resultat[
                    "rentabilite"
                ]
            ),
        )


        print(
            "💎 Score classement :",
            resultat[
                "score_classement"
            ],
            "/100",
        )


        print(
            "🔬 Score analyse :",
            resultat[
                "score_opportunite"
            ],
            "/100",
        )


        print(
            "🔬 Verdict général :",
            resultat[
                "verdict_general"
            ],
        )


        print(
            "🎯 Pour ton profil :",
            resultat[
                "verdict_classement"
            ],
        )


        if (
            resultat[
                "distance_km"
            ]
            is not None
        ):

            print(
                "🚗 Distance :",
                resultat[
                    "distance_km"
                ],
                "km",
            )


        fraicheur = resultat[
            "fraicheur"
        ]


        print(
            "⏱️",
            fraicheur.get(
                "label",
                "?",
            ),
        )


        if (
            fraicheur.get(
                "age_secondes"
            )
            is not None
        ):

            print(
                "🕒 Âge annonce :",
                fraicheur.get(
                    "age_texte",
                    "?",
                ),
            )


        if getattr(
            annonce,
            "url",
            None,
        ):

            print(
                "🔗",
                annonce.url,
            )


    print()

    print(
        "✅ Analyse terminée"
    )


if __name__ == "__main__":

    main()
