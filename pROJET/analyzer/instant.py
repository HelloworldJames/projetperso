"""Analyse immédiate et explicable d'une annonce PC pour Hunter V1.5."""

from copy import deepcopy

from analyzer.ai_advisor import conseiller_avec_ia
from analyzer.classifier import classer_annonce
from analyzer.opportunity import analyser_opportunite
from analyzer.profit import calculer_rentabilite
from analyzer.ranking import calculer_score_classement
from analyzer.repair import diagnostiquer_reparation
from analyzer.scoring import analyser_annonce
from analyzer.value import estimer_valeur
from config import MARGE_MIN, PROFIL
from database.analysis import enregistrer_analyse
from database.listing import DB_PATH
from database.market import calculer_comparables_marche


TAUX_SECURITE_REVENTE = 0.08
FRAIS_FIXES_REVENTE = 20
POIDS_MARCHE_MAXIMUM = 0.35


def _json_compatible(valeur):
    if isinstance(valeur, dict):
        return {
            str(cle): _json_compatible(contenu)
            for cle, contenu in valeur.items()
        }
    if isinstance(valeur, (set, tuple)):
        return [_json_compatible(element) for element in sorted(valeur, key=str)]
    if isinstance(valeur, list):
        return [_json_compatible(element) for element in valeur]
    return valeur


def _finaliser(annonce, resultat, db_path, enregistrer):
    resultat = _json_compatible(resultat)
    if enregistrer:
        enregistrer_analyse(annonce, resultat, db_path=db_path)
    return resultat


def _comparables_vides():
    return {
        "nombre_comparables": 0,
        "prix_minimum": None,
        "prix_median": None,
        "prix_maximum": None,
    }


def _diagnostic_normalise(annonce):
    resultat = diagnostiquer_reparation(annonce)
    lignes = resultat.get("diagnostic") or resultat.get("diagnostics") or []
    if isinstance(lignes, str):
        lignes = [lignes]
    return {
        "cout_min": float(resultat.get("cout_min", 0) or 0),
        "cout_max": float(resultat.get("cout_max", 0) or 0),
        "diagnostic": lignes or ["Aucune panne identifiée"],
    }


def calibrer_estimation_marche(estimation, comparables):
    """Pondère prudemment la base interne avec au moins 3 prix comparables."""
    resultat = deepcopy(estimation)
    base = float(resultat.get("valeur_probable") or 0)
    nombre = int(comparables.get("nombre_comparables") or 0)
    mediane = comparables.get("prix_median")
    resultat["valeur_probable_base"] = base
    resultat["comparables_marche"] = comparables
    resultat["calibration_marche"] = False

    if base <= 0 or nombre < 3 or mediane is None:
        return resultat

    # Les comparables sont des prix affichés, pas des ventes confirmées.
    cible_prudente = float(mediane) * 0.92
    poids = min(POIDS_MARCHE_MAXIMUM, 0.20 + (nombre - 3) * 0.03)
    valeur = base * (1 - poids) + cible_prudente * poids
    valeur = max(base * 0.80, min(base * 1.20, valeur))
    valeur = round(valeur)

    resultat["valeur_probable"] = valeur
    resultat["valeur_basse"] = round(min(
        float(resultat.get("valeur_basse") or valeur),
        valeur * 0.90,
    ))
    resultat["valeur_haute"] = round(max(
        float(resultat.get("valeur_haute") or valeur),
        valeur * 1.08,
    ))
    resultat["calibration_marche"] = True
    resultat["poids_marche"] = round(poids, 2)
    resultat["prix_marche_prudent"] = round(cible_prudente)
    resultat["confiance_score"] = min(
        100,
        int(resultat.get("confiance_score") or 0) + min(10, nombre + 2),
    )
    return resultat


def _decision_hunter(score, marge, prix, prix_achat_max, analyse_autorisee):
    if not analyse_autorisee:
        return "INFORMATIONS_INSUFFISANTES"
    if score >= 85 and marge >= 100:
        return "PEPITE"
    if score >= 70 and marge >= 50:
        return "BONNE_AFFAIRE"
    if marge >= 0 and prix <= prix_achat_max:
        return "INTERESSANTE"
    if marge > -50:
        return "A_NEGOCIER"
    return "A_ECARTER"


def analyser_annonce_immediate(
    annonce,
    db_path=DB_PATH,
    enregistrer=True,
    inclure_ia=True,
):
    classification = classer_annonce(annonce)
    categorie = classification.get("categorie", "INCONNU")
    analyse_pc = bool(classification.get("analyse_pc"))
    resultat = {
        "version": "1.5",
        "categorie": categorie,
        "decision": "HORS_CIBLE",
        "score_affaire": 0,
        "prix_achat_max": None,
        "marge_nette_prudente": None,
        "roi_prudent": None,
        "raisons": [classification.get("raison") or "Annonce hors cible PC"],
        "estimation": {
            "analyse_autorisee": False,
            "confiance_score": 0,
        },
        "comparables_marche": _comparables_vides(),
        "diagnostic": _diagnostic_normalise(annonce),
    }

    if not analyse_pc:
        return _finaliser(annonce, resultat, db_path, enregistrer)

    score_materiel, raisons_materiel = analyser_annonce(annonce)
    valeur_estimee, composants, estimation = estimer_valeur(annonce)

    try:
        comparables = calculer_comparables_marche(annonce, estimation)
    except Exception:
        comparables = _comparables_vides()

    estimation = _json_compatible(
        calibrer_estimation_marche(estimation, comparables)
    )
    resultat.update({
        "composants": composants,
        "score_materiel": score_materiel,
        "raisons_materiel": raisons_materiel,
        "estimation": estimation,
        "comparables_marche": comparables,
    })

    if not estimation.get("analyse_autorisee", False):
        resultat["decision"] = "INFORMATIONS_INSUFFISANTES"
        resultat["raisons"] = list(estimation.get("raisons_blocage") or [
            "Configuration trop incomplète pour estimer sans inventer.",
        ])
        resultat["action_recommandee"] = (
            "Vérifier au minimum les références CPU/GPU, la RAM, le stockage et l'état."
        )
        if inclure_ia:
            resultat["conseil_ia"] = conseiller_avec_ia(annonce, resultat)
        return _finaliser(annonce, resultat, db_path, enregistrer)

    diagnostic = resultat["diagnostic"]
    valeur_probable = float(estimation["valeur_probable"])
    valeur_basse = float(estimation.get("valeur_basse") or valeur_probable)
    valeur_nette_revente = round(
        valeur_basse * (1 - TAUX_SECURITE_REVENTE) - FRAIS_FIXES_REVENTE
    )
    marge_nette = round(
        valeur_nette_revente - float(annonce.prix) - diagnostic["cout_max"]
    )
    prix_achat_max = max(
        0,
        round(valeur_nette_revente - diagnostic["cout_max"] - MARGE_MIN),
    )
    roi = round((marge_nette / float(annonce.prix)) * 100, 1) if annonce.prix else None

    rentabilite = calculer_rentabilite(
        annonce.prix,
        valeur_probable,
        diagnostic["cout_min"],
        diagnostic["cout_max"],
    )
    score_opportunite, raisons, verdict = analyser_opportunite(
        annonce,
        valeur_probable,
        score_materiel,
        diagnostic,
        rentabilite,
        estimation,
    )
    score_classement = calculer_score_classement(
        score_opportunite,
        rentabilite,
        diagnostic,
        estimation,
        PROFIL,
    )
    confiance = float(estimation.get("confiance_score") or 0)
    preuve_marche = min(100, int(comparables.get("nombre_comparables") or 0) * 20)
    score_affaire = round(
        score_opportunite * 0.45
        + score_classement * 0.30
        + confiance * 0.20
        + preuve_marche * 0.05
    )
    if marge_nette < 0:
        score_affaire = min(score_affaire, 45)
    score_affaire = max(0, min(score_affaire, 100))
    decision = _decision_hunter(
        score_affaire,
        marge_nette,
        float(annonce.prix),
        prix_achat_max,
        True,
    )

    resultat.update({
        "decision": decision,
        "score_affaire": score_affaire,
        "prix_achat_max": prix_achat_max,
        "valeur_nette_revente": valeur_nette_revente,
        "marge_nette_prudente": marge_nette,
        "roi_prudent": roi,
        "score_opportunite": score_opportunite,
        "score_classement": score_classement,
        "verdict_moteur": verdict,
        "rentabilite": rentabilite,
        "raisons": raisons,
        "action_recommandee": (
            "Contacter rapidement et vérifier la configuration sur place."
            if decision in {"PEPITE", "BONNE_AFFAIRE"}
            else "Négocier au prix d'achat maximum indiqué."
            if decision in {"INTERESSANTE", "A_NEGOCIER"}
            else "Écarter sauf nouvelle information ou baisse de prix."
        ),
    })

    if inclure_ia:
        resultat["conseil_ia"] = conseiller_avec_ia(annonce, resultat)
    return _finaliser(annonce, resultat, db_path, enregistrer)
