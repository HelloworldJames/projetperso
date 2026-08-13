"""Diagnostic visible et ponctuel des URL manuelles de PC Hunter.

Le script attend explicitement apres DOMContentLoaded et ne conserve ni HTML,
ni cookie, ni donnee vendeur. Il enregistre seulement les signaux techniques
necessaires pour expliquer une lecture incomplete.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright


DOSSIER_OUTIL = Path(__file__).resolve().parent
DOSSIER_PROFIL = DOSSIER_OUTIL / "profile"
DOSSIER_RESULTATS = DOSSIER_OUTIL / "results"

MOTIFS_CONTROLE = (
    "captcha",
    "verify you are human",
    "verifiez que vous etes humain",
    "vérifiez que vous êtes humain",
    "activite inhabituelle",
    "activité inhabituelle",
    "access denied",
    "security check",
    "just a moment",
)


def maintenant_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def valider_url(url: str) -> str:
    valeur = str(url or "").strip()
    parties = urlsplit(valeur)
    if parties.scheme not in {"http", "https"} or not parties.hostname:
        raise ValueError("Chaque URL doit etre une adresse HTTP(S) complete.")
    if parties.username or parties.password:
        raise ValueError("Une URL de diagnostic ne doit contenir aucun identifiant.")
    return valeur


def url_sans_requete(url: str) -> str:
    """Retire requete, fragment et identifiants de challenge du diagnostic."""
    parties = urlsplit(url)
    chemin = parties.path
    if "/cdn-cgi/challenge-platform/" in chemin:
        chemin = "/cdn-cgi/challenge-platform/[MASQUE]"
    else:
        segments = [
            "[MASQUE]" if len(segment) > 80 else segment
            for segment in chemin.split("/")
        ]
        chemin = "/".join(segments)
    return urlunsplit((parties.scheme, parties.netloc, chemin, "", ""))


def detecter_controle(titre: str, texte: str, url: str) -> str | None:
    contenu = " ".join((titre, texte[:80_000], url)).casefold()
    return next((motif for motif in MOTIFS_CONTROLE if motif in contenu), None)


def classer_comportement(
    statut_http: int | None,
    erreur_navigation: str | None,
    motif_controle: str | None,
    nombre_liens_annonce: int,
    nombre_prix_visibles: int,
) -> str:
    if erreur_navigation:
        return "erreur_navigation"
    if statut_http in {401, 403, 429}:
        return "acces_refuse"
    if motif_controle:
        return "verification_interactive"
    if nombre_liens_annonce > 0 and nombre_prix_visibles > 0:
        return "contenu_annonce_visible"
    return "lecture_incomplete"


def nom_resultat(url: str) -> str:
    chemin = urlsplit(url).path.rstrip("/")
    identifiant = re.search(r"(\d{6,})", chemin)
    suffixe = identifiant.group(1) if identifiant else "url"
    return f"diagnostic_{suffixe}.json"


async def diagnostiquer_page(page, url: str, attente_secondes: float) -> dict:
    echecs_requetes: list[dict] = []
    reponses_erreur: list[dict] = []
    erreurs_console: list[str] = []

    def noter_echec(requete) -> None:
        if len(echecs_requetes) >= 30:
            return
        echecs_requetes.append(
            {
                "type": requete.resource_type,
                "url": url_sans_requete(requete.url),
                "erreur": str(requete.failure or "echec sans detail")[:300],
            }
        )

    def noter_reponse(reponse) -> None:
        if reponse.status < 400 or len(reponses_erreur) >= 30:
            return
        reponses_erreur.append(
            {
                "statut": reponse.status,
                "type": reponse.request.resource_type,
                "url": url_sans_requete(reponse.url),
            }
        )

    def noter_console(message) -> None:
        if message.type == "error" and len(erreurs_console) < 20:
            erreurs_console.append(message.text[:300])

    page.on("requestfailed", noter_echec)
    page.on("response", noter_reponse)
    page.on("console", noter_console)

    debut = maintenant_iso()
    reponse_principale = None
    erreur_navigation = None
    try:
        reponse_principale = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45_000,
        )
    except PlaywrightTimeoutError as erreur:
        erreur_navigation = f"timeout_navigation: {erreur}"
    except Exception as erreur:  # Playwright fournit ici son message technique exact.
        erreur_navigation = f"{type(erreur).__name__}: {erreur}"

    url_apres_navigation = page.url
    statut_http = reponse_principale.status if reponse_principale else None

    # Attente volontaire, meme si la reponse initiale est une page d'erreur.
    await page.wait_for_timeout(max(0, attente_secondes) * 1_000)

    try:
        titre_page = await page.title()
    except Exception:
        titre_page = ""
    try:
        texte_page = await page.locator("body").inner_text(timeout=5_000)
    except Exception:
        texte_page = ""

    compteurs = await page.evaluate(
        r"""
        () => {
          const visible = (element) => Boolean(
            element && (element.offsetWidth || element.offsetHeight || element.getClientRects().length)
          );
          const texte = String(document.body?.innerText || '');
          const prix = texte.match(/\d[\d .\u00a0]*(?:[,.]\d{1,2})?\s*(?:€|EUR)/gi) || [];
          return {
            liens_annonce: [...document.querySelectorAll('a[href*="/ad/"], a[href*="/items/"]')]
              .filter(visible).length,
            titres_h1: [...document.querySelectorAll('h1')].filter(visible).length,
            prix_visibles: prix.length,
            json_ld: document.querySelectorAll('script[type="application/ld+json"]').length,
            meta_og_title: document.querySelectorAll('meta[property="og:title"]').length,
            longueur_texte_visible: texte.length,
          };
        }
        """
    )
    motif_controle = detecter_controle(titre_page, texte_page, page.url)
    comportement = classer_comportement(
        statut_http,
        erreur_navigation,
        motif_controle,
        compteurs["liens_annonce"],
        compteurs["prix_visibles"],
    )
    return {
        "date_debut": debut,
        "url_demandee": url_sans_requete(url),
        "url_apres_navigation": url_sans_requete(url_apres_navigation),
        "url_apres_attente": url_sans_requete(page.url),
        "attente_explicite_secondes": attente_secondes,
        "statut_http_navigation": statut_http,
        "titre_page_apres_attente": titre_page[:500],
        "erreur_navigation": erreur_navigation,
        "motif_controle": motif_controle,
        "comportement": comportement,
        "dom": compteurs,
        "reponses_http_en_erreur": reponses_erreur,
        "requetes_echouees": echecs_requetes,
        "erreurs_console": erreurs_console,
    }


async def lancer(urls: list[str], attente_secondes: float) -> int:
    urls = [valider_url(url) for url in urls]
    if attente_secondes < 0 or attente_secondes > 120:
        raise ValueError("L'attente doit etre comprise entre 0 et 120 secondes.")

    DOSSIER_PROFIL.mkdir(parents=True, exist_ok=True)
    DOSSIER_RESULTATS.mkdir(parents=True, exist_ok=True)
    code_retour = 0
    async with async_playwright() as playwright:
        contexte = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(DOSSIER_PROFIL),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        try:
            for index, url in enumerate(urls):
                page = contexte.pages[0] if index == 0 and contexte.pages else await contexte.new_page()
                resultat = await diagnostiquer_page(page, url, attente_secondes)
                chemin = DOSSIER_RESULTATS / nom_resultat(url)
                chemin.write_text(
                    json.dumps(resultat, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(json.dumps(resultat, ensure_ascii=False, indent=2), flush=True)
                if resultat["comportement"] != "contenu_annonce_visible":
                    code_retour = 1
                await page.close()
        finally:
            await contexte.close()
    return code_retour


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description="Diagnostique des URL Hunter dans un Chromium visible."
    )
    parseur.add_argument("--url", action="append", required=True)
    parseur.add_argument("--wait-seconds", type=float, default=12)
    return parseur


def main() -> int:
    arguments = construire_parseur().parse_args()
    try:
        return asyncio.run(lancer(arguments.url, arguments.wait_seconds))
    except ValueError as erreur:
        print(f"Configuration invalide : {erreur}")
        return 2
    except KeyboardInterrupt:
        print("Diagnostic interrompu proprement.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
