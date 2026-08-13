"""Observation prudente d'une recherche Leboncoin avec Playwright standard.

Le navigateur reste visible et utilise un profil dédié persistant. Le module
n'altère pas le user-agent, ne masque pas l'automatisation et ne tente jamais
de résoudre une vérification anti-robot. Dans ce cas il écrit un état lisible
et demande une intervention manuelle.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


DOSSIER_OUTIL = Path(__file__).resolve().parent
DOSSIER_PROFIL = DOSSIER_OUTIL / "profile"
DOSSIER_ETAT = DOSSIER_OUTIL / "state"
FICHIER_ANNONCES = DOSSIER_ETAT / "listings.json"
FICHIER_STATUT = DOSSIER_ETAT / "status.json"
FICHIER_EVENEMENTS = DOSSIER_ETAT / "events.jsonl"

DELAI_MINIMUM_SECONDES = 4 * 60
DELAI_MAXIMUM_SECONDES = 6 * 60

MOTIFS_VERIFICATION = (
    "captcha",
    "vérifiez que vous êtes humain",
    "verifiez que vous etes humain",
    "confirmez que vous êtes humain",
    "confirmez que vous etes humain",
    "activité inhabituelle",
    "activite inhabituelle",
    "détection de robots",
    "detection de robots",
    "access denied",
    "verify you are human",
    "security check",
    "just a moment",
)

SCRIPT_EXTRACTION = r"""
(liens) => {
  const annonces = new Map();
  const nettoyer = (valeur) => String(valeur || '').replace(/\s+/g, ' ').trim();
  const motifPrix = /(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:€|EUR)/i;

  for (const lien of liens) {
    const href = lien.getAttribute('href') || '';
    const identifiant = href.match(/\/ad\/[^/]+\/(\d+)/i)?.[1];
    if (!identifiant || annonces.has(identifiant)) continue;

    let conteneur = lien.closest(
      '[data-qa-id="aditem_container"], '
      + '[data-test-id="adcard"], '
      + 'article[data-testid*="adcard"]'
    );
    if (!conteneur) {
      conteneur = lien;
      for (let niveau = 0; niveau < 6 && conteneur; niveau += 1) {
        if (conteneur.querySelector?.(
          'p[data-qa-id="aditem_title"], p[data-test-id="adcard-title"]'
        )) break;
        conteneur = conteneur.parentElement;
      }
    }

    const lignes = String(conteneur?.innerText || lien.innerText || lien.textContent || '')
      .split(/\r?\n/)
      .map(nettoyer)
      .filter(Boolean);
    const prixElement = conteneur?.querySelector(
      'span[data-qa-id="aditem_price"], '
      + 'p[data-test-id="price"], '
      + '[data-testid="adcard-price"]'
    );
    const prixTrouve = nettoyer(
      prixElement?.innerText || prixElement?.textContent
    ).match(motifPrix);
    if (!prixTrouve) continue;

    const titreSelecteur = nettoyer(
      conteneur?.querySelector(
        'p[data-qa-id="aditem_title"], p[data-test-id="adcard-title"]'
      )?.textContent
    );
    const titre = /^(voir (?:l['’])?annonce|annonce|leboncoin)$/i.test(titreSelecteur)
      ? null
      : titreSelecteur || null;

    const localisationSelecteur = nettoyer(
      conteneur?.querySelector(
        '[data-qa-id="aditem_location"], '
        + '[data-test-id="location"], '
        + '[data-testid="adcard-location"]'
      )?.textContent
    );
    const datePublication = nettoyer(
      conteneur?.querySelector(
        '[data-qa-id="aditem_date"], [data-testid="adcard-date"]'
      )?.textContent
    ) || null;

    const url = new URL(href, location.origin);
    url.hash = '';
    const entier = prixTrouve[1].replace(/[ .\u00a0]/g, '');
    const decimal = prixTrouve[2] ? `.${prixTrouve[2]}` : '';
    const prix = Number(`${entier}${decimal}`);
    if (!Number.isFinite(prix) || prix < 0) continue;

    annonces.set(identifiant, {
      identifiant,
      titre: titre?.slice(0, 500) || null,
      prix,
      url: url.href,
      description: '',
      localisation: localisationSelecteur || 'Inconnue',
      date_publication: datePublication || null,
    });
  }
  return [...annonces.values()];
}
"""


@dataclass(frozen=True)
class AnnonceObservee:
    identifiant: str
    titre: str | None
    prix: float | int
    url: str
    description: str = ""
    localisation: str = "Inconnue"
    date_publication: str | None = None


@dataclass(frozen=True)
class ResultatPassage:
    statut: str
    date_observation: str
    url: str
    annonces: tuple[AnnonceObservee, ...]
    nouvelles: tuple[AnnonceObservee, ...]
    raison: str | None = None
    http_status: int | None = None


def maintenant_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def valider_url_leboncoin(url: str) -> str:
    valeur = str(url or "").strip()
    parties = urlsplit(valeur)
    hote = (parties.hostname or "").lower()
    if parties.scheme != "https" or not (
        hote == "leboncoin.fr" or hote.endswith(".leboncoin.fr")
    ):
        raise ValueError("L'URL doit être une page HTTPS Leboncoin.")
    if parties.username or parties.password:
        raise ValueError("L'URL ne doit contenir aucun identifiant de connexion.")
    return valeur


def detecter_intervention_manuelle(
    http_status: int | None,
    titre: str,
    texte_page: str,
    url: str,
) -> str | None:
    if http_status in {401, 403, 429}:
        return f"Leboncoin a répondu HTTP {http_status}."

    contenu = " ".join((titre, texte_page[:80_000], url)).casefold()
    motif = next((element for element in MOTIFS_VERIFICATION if element in contenu), None)
    if motif:
        return f"Page de vérification détectée ({motif})."
    return None


def normaliser_annonces(valeurs: list[dict]) -> tuple[AnnonceObservee, ...]:
    annonces = {}
    for valeur in valeurs:
        try:
            titre = " ".join(str(valeur.get("titre") or "").split())[:500]
            if titre.casefold() in {
                "annonce",
                "leboncoin",
                "titre non extrait",
                "voir annonce",
                "voir l’annonce",
            }:
                titre = ""
            annonce = AnnonceObservee(
                identifiant=str(valeur["identifiant"]).strip(),
                titre=titre or None,
                prix=float(valeur["prix"]),
                url=valider_url_leboncoin(valeur["url"]),
                description=" ".join(
                    str(valeur.get("description") or "").split()
                )[:2_000],
                localisation=" ".join(
                    str(valeur.get("localisation") or "Inconnue").split()
                )[:300],
                date_publication=(
                    " ".join(str(valeur.get("date_publication")).split())[:100]
                    if valeur.get("date_publication")
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if annonce.identifiant and annonce.prix >= 0:
            prix = int(annonce.prix) if annonce.prix.is_integer() else annonce.prix
            annonces[annonce.identifiant] = AnnonceObservee(
                identifiant=annonce.identifiant,
                titre=annonce.titre,
                prix=prix,
                url=annonce.url,
                description=annonce.description,
                localisation=annonce.localisation,
                date_publication=annonce.date_publication,
            )
    return tuple(annonces.values())


def charger_annonces_precedentes() -> tuple[AnnonceObservee, ...]:
    if not FICHIER_ANNONCES.exists():
        return ()
    try:
        contenu = json.loads(FICHIER_ANNONCES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return normaliser_annonces(contenu.get("annonces", []))


def comparer_nouvelles(
    precedentes: tuple[AnnonceObservee, ...],
    actuelles: tuple[AnnonceObservee, ...],
) -> tuple[AnnonceObservee, ...]:
    identifiants_connus = {annonce.identifiant for annonce in precedentes}
    return tuple(
        annonce for annonce in actuelles
        if annonce.identifiant not in identifiants_connus
    )


def ecrire_json_atomique(chemin: Path, contenu: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(f"{chemin.suffix}.tmp")
    temporaire.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporaire.replace(chemin)


def enregistrer_resultat(resultat: ResultatPassage) -> None:
    DOSSIER_ETAT.mkdir(parents=True, exist_ok=True)
    resume = {
        "statut": resultat.statut,
        "date_observation": resultat.date_observation,
        "url": resultat.url,
        "nombre_annonces": len(resultat.annonces),
        "nombre_nouvelles": len(resultat.nouvelles),
        "raison": resultat.raison,
        "http_status": resultat.http_status,
    }
    ecrire_json_atomique(FICHIER_STATUT, resume)

    with FICHIER_EVENEMENTS.open("a", encoding="utf-8") as fichier:
        fichier.write(json.dumps(resume, ensure_ascii=False) + "\n")

    if resultat.statut == "ok":
        ecrire_json_atomique(
            FICHIER_ANNONCES,
            {
                "date_observation": resultat.date_observation,
                "url": resultat.url,
                "annonces": [asdict(annonce) for annonce in resultat.annonces],
            },
        )


async def attendre_contenu(page: Page, nombre_defilements: int) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass

    try:
        await page.locator('a[href*="/ad/"]').first.wait_for(
            state="attached",
            timeout=20_000,
        )
    except PlaywrightTimeoutError:
        return

    taille_precedente = 0
    passages_stables = 0
    for _ in range(max(0, nombre_defilements)):
        taille = await page.locator('a[href*="/ad/"]').count()
        passages_stables = passages_stables + 1 if taille == taille_precedente else 0
        if passages_stables >= 2:
            break
        taille_precedente = taille
        await page.mouse.wheel(0, 2_000)
        await page.wait_for_timeout(1_200)


async def extraire_annonces(page: Page) -> tuple[AnnonceObservee, ...]:
    valeurs = await page.locator('a[href*="/ad/"]').evaluate_all(SCRIPT_EXTRACTION)
    return normaliser_annonces(valeurs)


async def effectuer_passage(
    page: Page,
    url: str,
    nombre_defilements: int,
) -> ResultatPassage:
    date_observation = maintenant_iso()
    try:
        reponse = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45_000,
        )
    except PlaywrightTimeoutError:
        return ResultatPassage(
            statut="erreur",
            date_observation=date_observation,
            url=url,
            annonces=(),
            nouvelles=(),
            raison="La page n'a pas chargé dans les 45 secondes.",
        )

    http_status = reponse.status if reponse else None
    try:
        texte_page = await page.locator("body").inner_text(timeout=10_000)
    except PlaywrightTimeoutError:
        texte_page = ""
    raison = detecter_intervention_manuelle(
        http_status,
        await page.title(),
        texte_page,
        page.url,
    )
    if raison:
        return ResultatPassage(
            statut="intervention_manuelle_requise",
            date_observation=date_observation,
            url=url,
            annonces=(),
            nouvelles=(),
            raison=raison,
            http_status=http_status,
        )

    await attendre_contenu(page, nombre_defilements)
    annonces = await extraire_annonces(page)
    precedentes = charger_annonces_precedentes()
    nouvelles = comparer_nouvelles(precedentes, annonces) if precedentes else ()
    return ResultatPassage(
        statut="ok" if annonces else "lecture_incomplete",
        date_observation=date_observation,
        url=url,
        annonces=annonces,
        nouvelles=nouvelles,
        raison=None if annonces else "Aucune carte d'annonce exploitable dans le DOM.",
        http_status=http_status,
    )


async def demander_intervention() -> None:
    print(
        "\n[INTERVENTION MANUELLE REQUISE] "
        "Terminez la vérification dans Chromium, puis appuyez sur Entrée ici.",
        flush=True,
    )
    await asyncio.to_thread(sys.stdin.readline)


async def lancer_observation(
    url: str,
    duree_minutes: float,
    delai_minimum: int,
    delai_maximum: int,
    nombre_defilements: int,
    une_fois: bool,
) -> int:
    url = valider_url_leboncoin(url)
    if delai_minimum < 1 or delai_maximum < delai_minimum:
        raise ValueError("L'intervalle de vérification est invalide.")

    DOSSIER_PROFIL.mkdir(parents=True, exist_ok=True)
    DOSSIER_ETAT.mkdir(parents=True, exist_ok=True)
    fin = time.monotonic() + max(0, duree_minutes) * 60
    dernier_statut = "erreur"

    async with async_playwright() as playwright:
        contexte: BrowserContext = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(DOSSIER_PROFIL),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = contexte.pages[0] if contexte.pages else await contexte.new_page()
        try:
            while True:
                resultat = await effectuer_passage(page, url, nombre_defilements)
                dernier_statut = resultat.statut
                enregistrer_resultat(resultat)
                print(
                    f"[{resultat.date_observation}] {resultat.statut} · "
                    f"{len(resultat.annonces)} annonce(s) · "
                    f"{len(resultat.nouvelles)} nouvelle(s)",
                    flush=True,
                )
                for annonce in resultat.nouvelles:
                    print(
                        f"[NOUVELLE] {annonce.titre or 'Titre non extrait'} · "
                        f"{annonce.prix} € · {annonce.url}",
                        flush=True,
                    )

                if resultat.statut == "intervention_manuelle_requise":
                    print(resultat.raison, flush=True)
                    if not une_fois:
                        await demander_intervention()

                if une_fois or time.monotonic() >= fin:
                    break

                delai = random.randint(delai_minimum, delai_maximum)
                restant = max(0, int(fin - time.monotonic()))
                if restant <= 0:
                    break
                delai = min(delai, restant)
                print(f"Prochain passage dans {delai} seconde(s).", flush=True)
                await asyncio.sleep(delai)
        finally:
            await contexte.close()
    if dernier_statut == "ok":
        return 0
    if dernier_statut == "intervention_manuelle_requise":
        return 2
    return 1


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description="Observe une recherche Leboncoin dans un Chromium visible.",
    )
    parseur.add_argument("--url", required=True, help="URL HTTPS Leboncoin déjà filtrée")
    parseur.add_argument("--duration-minutes", type=float, default=60)
    parseur.add_argument("--min-interval", type=int, default=DELAI_MINIMUM_SECONDES)
    parseur.add_argument("--max-interval", type=int, default=DELAI_MAXIMUM_SECONDES)
    parseur.add_argument("--scrolls", type=int, default=5)
    parseur.add_argument("--once", action="store_true")
    return parseur


def main() -> int:
    arguments = construire_parseur().parse_args()
    try:
        return asyncio.run(
            lancer_observation(
                url=arguments.url,
                duree_minutes=arguments.duration_minutes,
                delai_minimum=arguments.min_interval,
                delai_maximum=arguments.max_interval,
                nombre_defilements=arguments.scrolls,
                une_fois=arguments.once,
            )
        )
    except KeyboardInterrupt:
        print("Observation interrompue proprement.")
        return 130
    except ValueError as erreur:
        print(f"Configuration invalide : {erreur}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
