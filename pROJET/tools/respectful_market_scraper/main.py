"""Orchestration du collecteur prudent, independante de PC Hunter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scraper.parser import extraire_annonces
from scraper.robots_checker import verifier_robots
from scraper.scraper import ScrapingRefuse, fetch_page
from scraper.storage import sauvegarder_annonces
from scraper.vpn_manager import VpnManuelRequis, exiger_vpn_manuel, lire_statut_vpn


DOSSIER_OUTIL = Path(__file__).resolve().parent


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(description="Lecture prudente d'une page publique.")
    parseur.add_argument("url")
    parseur.add_argument("--visible", action="store_true")
    parseur.add_argument("--robots-only", action="store_true")
    parseur.add_argument(
        "--vpn-status",
        action="store_true",
        help="Afficher uniquement l'etat VPN detecte, sans acces reseau.",
    )
    parseur.add_argument(
        "--require-manual-vpn",
        action="store_true",
        help="Refuser la session si NordVPN n'est pas deja connecte manuellement.",
    )
    parseur.add_argument(
        "--output",
        type=Path,
        default=DOSSIER_OUTIL / "state" / "listings.json",
    )
    return parseur


def main() -> int:
    arguments = construire_parseur().parse_args()
    if arguments.vpn_status:
        statut_vpn = lire_statut_vpn()
        print(json.dumps(statut_vpn.__dict__, ensure_ascii=False, indent=2))
        return 0 if statut_vpn.connecte else 4

    if arguments.require_manual_vpn:
        try:
            exiger_vpn_manuel()
        except VpnManuelRequis as erreur:
            print(f"ARRET VPN: {erreur}")
            return 4

    if arguments.robots_only:
        decision = verifier_robots(arguments.url)
        print(json.dumps(decision.__dict__, ensure_ascii=False, indent=2))
        return 0 if decision.autorise else 3

    try:
        page = fetch_page(arguments.url, headless=not arguments.visible)
    except (ValueError, ScrapingRefuse) as erreur:
        print(f"ARRET: {erreur}")
        return 3

    annonces = extraire_annonces(page.html, page.url_finale)
    resume = sauvegarder_annonces(annonces, arguments.output)
    print(
        json.dumps(
            {
                "statut": "ok" if annonces else "lecture_incomplete",
                "url_finale": page.url_finale,
                "statut_http": page.statut_http,
                "robots": page.robots.raison,
                "delai_applique": round(page.delai_applique, 2),
                "annonces_extraites": len(annonces),
                **resume,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if annonces else 1


if __name__ == "__main__":
    raise SystemExit(main())
