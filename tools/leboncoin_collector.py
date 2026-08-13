"""CLI isolée du collecteur Leboncoin V1.5.

Exécution recommandée depuis la racine du projet :
    python -m tools.leboncoin_collector --observer-state ...
"""

from __future__ import annotations

import argparse
import json
import logging

from pathlib import Path

from collector.providers.leboncoin_collector import (
    charger_objets_json,
    collecter_depuis_etat_observateur,
    collecter_observations_leboncoin,
    comparer_couverture_leboncoin,
    identifiant_stable_leboncoin,
)


def _identifiants_connus(chemin: str | None) -> list[str]:
    if not chemin:
        return []
    identifiants = []
    for valeur in charger_objets_json(chemin):
        try:
            identifiants.append(identifiant_stable_leboncoin(valeur))
        except ValueError:
            continue
    return identifiants


def _ecrire_json_atomique(chemin: Path, contenu: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(f"{chemin.suffix}.tmp")
    temporaire.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporaire.replace(chemin)


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description=(
            "Normalise une sortie Leboncoin isolée et mesure sa couverture "
            "par rapport aux annonces vues par l'administrateur."
        ),
    )
    entree = parseur.add_mutually_exclusive_group(required=True)
    entree.add_argument(
        "--input",
        help="JSON contenant les observations détectées.",
    )
    entree.add_argument(
        "--observer-state",
        help=(
            "Dossier state de l'observateur Playwright. Un statut 403/429 "
            "est signalé BLOCKED sans réutiliser l'ancien snapshot."
        ),
    )
    parseur.add_argument(
        "--expected",
        help="JSON des annonces visibles/notifiées attendues.",
    )
    parseur.add_argument(
        "--previous",
        help="Ancien JSON détecté, utilisé uniquement pour compter les nouvelles.",
    )
    parseur.add_argument(
        "--report",
        help="Chemin facultatif du rapport JSON produit.",
    )
    return parseur


def main() -> int:
    arguments = construire_parseur().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    connus = _identifiants_connus(arguments.previous)
    try:
        if arguments.observer_state:
            collecte = collecter_depuis_etat_observateur(
                arguments.observer_state,
                identifiants_connus=connus,
            )
        else:
            collecte = collecter_observations_leboncoin(
                charger_objets_json(arguments.input),
                identifiants_connus=connus,
            )
    except (OSError, json.JSONDecodeError, ValueError) as erreur:
        print(f"Erreur de lecture : {erreur}")
        return 2

    print()
    print("LEBONCOIN COLLECTOR V1.5")
    print(f"Statut              : {collecte.statut}")
    print(f"Annonces trouvées   : {collecte.nombre_annonces}")
    print(f"Nouvelles annonces  : {collecte.nombre_nouvelles}")
    print(f"Doublons fusionnés  : {collecte.nombre_doublons}")
    print(f"Fiches incomplètes  : {collecte.nombre_incompletes}")
    print(f"Erreurs              : {len(collecte.erreurs)}")
    print(f"Temps de collecte    : {collecte.duree_secondes:.4f} s")

    rapport = {"collecte": collecte.vers_dict()}
    couverture = None
    if arguments.expected:
        try:
            attendues = charger_objets_json(arguments.expected)
        except (OSError, json.JSONDecodeError, ValueError) as erreur:
            print(f"Erreur du fichier attendu : {erreur}")
            return 2
        couverture = comparer_couverture_leboncoin(
            attendues,
            collecte.annonces,
        )
        rapport["couverture"] = couverture.vers_dict()
        print()
        print("COMPARAISON DE COUVERTURE")
        print(f"Visibles/notifiées   : {couverture.nombre_attendues}")
        print(f"Correspondances      : {couverture.nombre_correspondances}")
        print(f"Couverture           : {couverture.couverture_pourcentage:.2f} %")
        print(f"Manquantes           : {len(couverture.manquantes)}")

    if collecte.erreurs:
        print()
        print("ERREURS / BLOCAGES")
        for erreur in collecte.erreurs:
            print(f"- {erreur}")

    if arguments.report:
        chemin_rapport = Path(arguments.report).resolve()
        _ecrire_json_atomique(chemin_rapport, rapport)
        print(f"Rapport JSON         : {chemin_rapport}")

    if collecte.statut in {"BLOCKED", "FAILED"}:
        return 2
    if couverture is not None and not couverture.succes:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

