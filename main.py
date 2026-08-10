from collector.scraper import rechercher_annonces

from analyzer.scoring import analyser_annonce
from analyzer.value import estimer_valeur
from analyzer.profit import calculer_rentabilite
from analyzer.opportunity import analyser_opportunite
from analyzer.repair import diagnostiquer_reparation
from analyzer.ranking import (
    calculer_score_classement,
    obtenir_verdict_classement
)

from database.listing import (
    initialiser_database,
    enregistrer_annonce,
    obtenir_historique_prix
)

from config import (
    PROFIL,
    TOP_N,
    BUDGET_MAX,
    MARGE_MIN,
    ACCEPTER_REPARATIONS
)


# ============================================================
# DÉMARRAGE PC HUNTER
# ============================================================

print("🚀 PC Hunter AI démarré")

initialiser_database()

annonces = rechercher_annonces()

classement = []


# ============================================================
# ANALYSE DES ANNONCES
# ============================================================

for index, annonce in enumerate(annonces, start=1):

    print("\n################################")
    print(f"🔎 ANALYSE ANNONCE {index}")
    print("################################")


    # --------------------------------------------------------
    # MÉMOIRE DE L'ANNONCE
    # --------------------------------------------------------

    memoire = enregistrer_annonce(annonce)


    if memoire["statut"] == "nouvelle":

        print("\n🆕 NOUVELLE ANNONCE DÉTECTÉE")


    elif memoire["statut"] == "baisse":

        ancien_prix = memoire["ancien_prix"]
        nouveau_prix = memoire["nouveau_prix"]

        baisse = ancien_prix - nouveau_prix

        print("\n📉 BAISSE DE PRIX DÉTECTÉE")

        print(
            "💵 Ancien prix :",
            int(ancien_prix),
            "€"
        )

        print(
            "💵 Nouveau prix :",
            int(nouveau_prix),
            "€"
        )

        print(
            "💰 Baisse :",
            int(baisse),
            "€"
        )


    elif memoire["statut"] == "hausse":

        ancien_prix = memoire["ancien_prix"]
        nouveau_prix = memoire["nouveau_prix"]

        print("\n📈 HAUSSE DE PRIX DÉTECTÉE")

        print(
            "💵 Ancien prix :",
            int(ancien_prix),
            "€"
        )

        print(
            "💵 Nouveau prix :",
            int(nouveau_prix),
            "€"
        )


    else:

        print("\n♻️ Annonce déjà connue")


    # --------------------------------------------------------
    # HISTORIQUE DES PRIX
    # --------------------------------------------------------

    historique = obtenir_historique_prix(
        annonce.identifiant
    )


    if len(historique) > 1:

        print("\n📜 HISTORIQUE DES PRIX")

        for entree in historique:

            prix = entree["prix"]

            if float(prix).is_integer():
                prix = int(prix)

            print(
                "-",
                prix,
                "€",
                "|",
                entree["date"]
            )


    # --------------------------------------------------------
    # RÉCAPITULATIF
    # --------------------------------------------------------

    print("\n--------------------------------")

    print("\n📋 RÉCAPITULATIF DE L'ANNONCE")

    print("\n--------------------------------")

    print(
        "\n📝 Titre :",
        annonce.titre
    )

    print(
        "💵 Prix de vente :",
        annonce.prix,
        "€"
    )

    print(
        "📍 Localisation :",
        annonce.localisation
    )

    print(
        "🌐 Plateforme :",
        annonce.plateforme
    )

    print(
        "📄 Description :",
        annonce.description
    )


    if annonce.url:

        print(
            "🔗 Lien :",
            annonce.url
        )


    if annonce.date_publication:

        print(
            "🕒 Publication :",
            annonce.date_publication
        )


    print("\n--------------------------------")


    # --------------------------------------------------------
    # SCORE MATÉRIEL
    # --------------------------------------------------------

    score_materiel, raisons_materiel = analyser_annonce(
        annonce
    )


    # --------------------------------------------------------
    # ESTIMATION DE VALEUR
    # --------------------------------------------------------

    valeur, composants, estimation = estimer_valeur(
        annonce
    )


    # --------------------------------------------------------
    # DIAGNOSTIC RÉPARATION
    # --------------------------------------------------------

    diagnostic = diagnostiquer_reparation(
        annonce
    )


    # --------------------------------------------------------
    # RENTABILITÉ
    # --------------------------------------------------------

    rentabilite = calculer_rentabilite(
        annonce.prix,
        valeur,
        diagnostic["cout_min"],
        diagnostic["cout_max"]
    )


    # --------------------------------------------------------
    # SCORE OPPORTUNITÉ GÉNÉRAL
    # --------------------------------------------------------

    (
        score_opportunite,
        raisons_opportunite,
        verdict_general
    ) = analyser_opportunite(
        annonce,
        valeur,
        score_materiel,
        diagnostic,
        rentabilite,
        estimation
    )


    # --------------------------------------------------------
    # SCORE PERSONNALISÉ
    # --------------------------------------------------------

    score_classement = calculer_score_classement(
        score_opportunite,
        rentabilite,
        diagnostic,
        estimation,
        PROFIL
    )


    verdict_classement = obtenir_verdict_classement(
        score_classement,
        PROFIL
    )


    # --------------------------------------------------------
    # FILTRES PC HUNTER
    # --------------------------------------------------------

    respecte_budget = (
        annonce.prix <= BUDGET_MAX
    )

    respecte_marge = (
        rentabilite["benefice_max"] >= MARGE_MIN
    )

    respecte_reparation = (
        ACCEPTER_REPARATIONS
        or diagnostic["cout_max"] == 0
    )


    # --------------------------------------------------------
    # AJOUT AU CLASSEMENT
    # --------------------------------------------------------

    if (
        respecte_budget
        and respecte_marge
        and respecte_reparation
    ):

        classement.append({

            "annonce": annonce,

            "score": score_classement,

            "score_analyse": score_opportunite,

            "verdict": verdict_general,

            "verdict_classement": verdict_classement,

            "benefice_min":
                rentabilite["benefice_min"],

            "benefice_max":
                rentabilite["benefice_max"],

            "benefice_moyen":
                rentabilite["benefice_moyen"],

            "valeur_probable":
                estimation["valeur_probable"],

            "confiance":
                estimation["confiance_score"],

            "cout_reparation_max":
                diagnostic["cout_max"]
        })


    # ========================================================
    # AFFICHAGE DE L'ANALYSE
    # ========================================================


    # --------------------------------------------------------
    # SCORE MATÉRIEL
    # --------------------------------------------------------

    print(
        "\n📊 SCORE MATÉRIEL :",
        score_materiel,
        "/100"
    )


    print("\n✅ Critères détectés :")


    if raisons_materiel:

        for raison in raisons_materiel:
            print("-", raison)

    else:

        print("- Aucun")


    # --------------------------------------------------------
    # COMPOSANTS
    # --------------------------------------------------------

    print("\n🧩 Composants détectés :")


    if composants:

        for composant in composants:
            print("-", composant)

    else:

        print("- Aucun")


    # --------------------------------------------------------
    # VALEUR DU PC
    # --------------------------------------------------------

    print(
        "\n💰 Valeur composants confirmés :",
        estimation["valeur_composants"],
        "€"
    )

    print(
        "📉 Valeur basse estimée :",
        estimation["valeur_basse"],
        "€"
    )

    print(
        "🎯 Valeur probable :",
        estimation["valeur_probable"],
        "€"
    )

    print(
        "📈 Valeur haute estimée :",
        estimation["valeur_haute"],
        "€"
    )

    print(
        "🧠 Confiance estimation :",
        estimation["confiance"],
        f'({estimation["confiance_score"]}/100)'
    )

    print(
        "💵 Prix de vente :",
        annonce.prix,
        "€"
    )


    # --------------------------------------------------------
    # BÉNÉFICE POTENTIEL
    # --------------------------------------------------------

    if (
        rentabilite["benefice_min"]
        == rentabilite["benefice_max"]
    ):

        print(
            "📈 Bénéfice potentiel :",
            rentabilite["benefice_min"],
            "€"
        )

    else:

        print(
            "📈 Bénéfice potentiel :",
            rentabilite["benefice_min"],
            "à",
            rentabilite["benefice_max"],
            "€"
        )


    print(
        "💰 Bénéfice moyen estimé :",
        rentabilite["benefice_moyen"],
        "€"
    )


    # --------------------------------------------------------
    # RÉPARATION
    # --------------------------------------------------------

    if (
        diagnostic["cout_min"] == 0
        and diagnostic["cout_max"] == 0
    ):

        print(
            "🔧 Coût de réparation estimé : 0 €"
        )

    else:

        print(
            "🔧 Réparation estimée :",
            diagnostic["cout_min"],
            "-",
            diagnostic["cout_max"],
            "€"
        )


    print("\n🔧 DIAGNOSTIC RÉPARATION :")


    for ligne_diagnostic in diagnostic["diagnostics"]:

        print(
            "-",
            ligne_diagnostic
        )


    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    print(
        "\n💎 SCORE OPPORTUNITÉ :",
        score_opportunite,
        "/100"
    )

    print(
        "🎯 SCORE CLASSEMENT :",
        score_classement,
        "/100",
        f"({PROFIL.upper()})"
    )


    # --------------------------------------------------------
    # ANALYSE PÉPITE
    # --------------------------------------------------------

    print("\n🚨 Analyse pépite :")


    if raisons_opportunite:

        for raison in raisons_opportunite:
            print("-", raison)

    else:

        print("- Aucun signal")


    # --------------------------------------------------------
    # VERDICTS
    # --------------------------------------------------------

    print(
        "\n🔬 Verdict général :",
        verdict_general
    )

    print(
        "🎯 Verdict personnalisé :",
        verdict_classement
    )


# ============================================================
# TRI DU TOP PC HUNTER
# ============================================================

classement = sorted(
    classement,
    key=lambda resultat: resultat["score"],
    reverse=True
)


# ============================================================
# TOP PC HUNTER
# ============================================================

print("\n")
print("################################")
print("🏆 TOP PC HUNTER")
print("################################")


print(
    "\n🎯 Profil actif :",
    PROFIL.upper()
)

print(
    "💳 Budget maximum :",
    BUDGET_MAX,
    "€"
)

print(
    "💰 Marge minimum :",
    MARGE_MIN,
    "€"
)

print(
    "🔧 Réparations acceptées :",
    "OUI"
    if ACCEPTER_REPARATIONS
    else "NON"
)


# ------------------------------------------------------------
# AUCUNE ANNONCE
# ------------------------------------------------------------

if not classement:

    print(
        "\n❌ Aucune annonce ne respecte les critères."
    )


# ------------------------------------------------------------
# AFFICHAGE TOP N
# ------------------------------------------------------------

for position, resultat in enumerate(
    classement[:TOP_N],
    start=1
):

    annonce = resultat["annonce"]


    if position == 1:

        print(
            f"\n🥇 #{position}"
        )

    elif position == 2:

        print(
            f"\n🥈 #{position}"
        )

    elif position == 3:

        print(
            f"\n🥉 #{position}"
        )

    else:

        print(
            f"\n#{position}"
        )


    print(
        "📝",
        annonce.titre
    )

    print(
        "📍",
        annonce.localisation
    )

    print(
        "🌐",
        annonce.plateforme
    )

    print(
        "💵 Prix :",
        annonce.prix,
        "€"
    )

    print(
        "🎯 Valeur probable :",
        resultat["valeur_probable"],
        "€"
    )


    # --------------------------------------------------------
    # BÉNÉFICE TOP
    # --------------------------------------------------------

    if (
        resultat["benefice_min"]
        == resultat["benefice_max"]
    ):

        print(
            "💰 Bénéfice potentiel :",
            resultat["benefice_min"],
            "€"
        )

    else:

        print(
            "💰 Bénéfice potentiel :",
            resultat["benefice_min"],
            "à",
            resultat["benefice_max"],
            "€"
        )


    # --------------------------------------------------------
    # SCORES TOP
    # --------------------------------------------------------

    print(
        "💎 Score classement :",
        resultat["score"],
        "/100"
    )

    print(
        "🔬 Score analyse :",
        resultat["score_analyse"],
        "/100"
    )


    # --------------------------------------------------------
    # VERDICTS TOP
    # --------------------------------------------------------

    print(
        "🔬 Verdict général :",
        resultat["verdict"]
    )

    print(
        "🎯 Pour ton profil :",
        resultat["verdict_classement"]
    )


    # --------------------------------------------------------
    # LIEN FUTURE ANNONCE
    # --------------------------------------------------------

    if annonce.url:

        print(
            "🔗",
            annonce.url
        )


print("\n✅ Analyse terminée")