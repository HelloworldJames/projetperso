"""Observe une categorie Vinted avec un Chromium Playwright standard.

Ce prototype effectue un seul passage visible. Il conserve un profil dedie,
mais ne modifie pas le user-agent, ne masque pas l'automatisation et ne tente
pas de contourner une verification du site.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright


DOSSIER_OUTIL = Path(__file__).resolve().parent
DOSSIER_PROFIL = DOSSIER_OUTIL / "profile"
DOSSIER_ETAT = DOSSIER_OUTIL / "state"
FICHIER_ANNONCES = DOSSIER_ETAT / "listings.json"
FICHIER_STATUT = DOSSIER_ETAT / "status.json"

MOTIFS_VERIFICATION = (
    "captcha",
    "verifiez que vous etes humain",
    "vérifiez que vous êtes humain",
    "confirmez que vous etes humain",
    "confirmez que vous êtes humain",
    "activite inhabituelle",
    "activité inhabituelle",
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

  const lireTitre = (lien, conteneur) => {
    const imageAlt = nettoyer(lien.querySelector('img[alt]')?.getAttribute('alt'));
    const attribut = nettoyer(lien.getAttribute('aria-label') || lien.getAttribute('title'));
    let titre = imageAlt || attribut;
    titre = titre.replace(/^image\s*:\s*/i, '');
    titre = titre.split(/,\s*(?:marque|état|etat|taille|prix)\s*:/i)[0];
    if (titre && !motifPrix.test(titre)) return titre;

    const lignes = String(conteneur?.innerText || lien.innerText || '')
      .split(/\r?\n/)
      .map(nettoyer)
      .filter(Boolean);
    return lignes.find((ligne) => {
      if (motifPrix.test(ligne)) return false;
      if (/^(favori|favoris|protection acheteurs|incluse?)$/i.test(ligne)) return false;
      return ligne.length >= 4;
    }) || '';
  };

  for (const lien of liens) {
    const href = lien.getAttribute('href') || '';
    const identifiant = href.match(/\/items\/(\d+)/i)?.[1];
    if (!identifiant || annonces.has(identifiant)) continue;

    let conteneur = lien;
    for (let niveau = 0; niveau < 7 && conteneur; niveau += 1) {
      const texte = nettoyer(conteneur.innerText || conteneur.textContent);
      if (motifPrix.test(texte) && conteneur.querySelector('img')) break;
      conteneur = conteneur.parentElement;
    }

    const texte = nettoyer(
      conteneur?.innerText ||
      conteneur?.textContent ||
      lien.querySelector('img[alt]')?.getAttribute('alt') ||
      ''
    );
    const prixTrouve = texte.match(motifPrix);
    const titre = nettoyer(lireTitre(lien, conteneur));
    if (!prixTrouve || !titre) continue;

    const entier = prixTrouve[1].replace(/[ .\u00a0]/g, '');
    const decimal = prixTrouve[2] ? `.${prixTrouve[2]}` : '';
    const prix = Number(`${entier}${decimal}`);
    if (!Number.isFinite(prix) || prix < 0) continue;

    const url = new URL(href, location.origin);
    url.hash = '';
    annonces.set(identifiant, {
      identifiant,
      titre: titre.slice(0, 500),
      prix,
      url: url.href,
    });
  }
  return [...annonces.values()];
}
"""


@dataclass(frozen=True)
class AnnonceObservee:
    identifiant: str
    titre: str
    prix: float | int
    url: str


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


def valider_url_vinted(url: str) -> str:
    valeur = str(url or "").strip()
    parties = urlsplit(valeur)
    hote = (parties.hostname or "").lower()
    if parties.scheme != "https" or not (hote == "vinted.fr" or hote.endswith(".vinted.fr")):
        raise ValueError("L'URL doit etre une page HTTPS Vinted.")
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
        return f"Vinted a repondu HTTP {http_status}."
    contenu = " ".join((titre, texte_page[:80_000], url)).casefold()
    motif = next((motif for motif in MOTIFS_VERIFICATION if motif in contenu), None)
    if motif:
        return f"Page de verification detectee ({motif})."
    return None


def normaliser_annonces(valeurs: list[dict]) -> tuple[AnnonceObservee, ...]:
    annonces: dict[str, AnnonceObservee] = {}
    for valeur in valeurs:
        try:
            identifiant = str(valeur["identifiant"]).strip()
            titre = " ".join(str(valeur["titre"]).split())[:500]
            prix_float = float(valeur["prix"])
            url = valider_url_vinted(valeur["url"])
        except (KeyError, TypeError, ValueError):
            continue
        if not identifiant or not titre or prix_float < 0:
            continue
        prix: float | int = int(prix_float) if prix_float.is_integer() else prix_float
        annonces[identifiant] = AnnonceObservee(identifiant, titre, prix, url)
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
    return tuple(a for a in actuelles if a.identifiant not in identifiants_connus)


def ecrire_json_atomique(chemin: Path, contenu: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(f"{chemin.suffix}.tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(chemin)


def enregistrer_resultat(resultat: ResultatPassage) -> None:
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
        await page.locator('a[href*="/items/"]').first.wait_for(state="attached", timeout=20_000)
    except PlaywrightTimeoutError:
        return

    nombre_precedent = -1
    passages_stables = 0
    for _ in range(max(0, nombre_defilements)):
        nombre = await page.locator('a[href*="/items/"]').count()
        passages_stables = passages_stables + 1 if nombre == nombre_precedent else 0
        if passages_stables >= 2:
            break
        nombre_precedent = nombre
        await page.mouse.wheel(0, 2_000)
        await page.wait_for_timeout(1_200)


async def effectuer_passage(page: Page, url: str, nombre_defilements: int) -> ResultatPassage:
    date_observation = maintenant_iso()
    try:
        reponse = await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    except PlaywrightTimeoutError:
        return ResultatPassage(
            "erreur", date_observation, url, (), (),
            "La page n'a pas charge dans les 45 secondes.",
        )

    http_status = reponse.status if reponse else None
    try:
        texte_page = await page.locator("body").inner_text(timeout=10_000)
    except PlaywrightTimeoutError:
        texte_page = ""
    raison = detecter_intervention_manuelle(
        http_status, await page.title(), texte_page, page.url
    )
    if raison:
        return ResultatPassage(
            "intervention_manuelle_requise", date_observation, url, (), (), raison, http_status
        )

    await attendre_contenu(page, nombre_defilements)
    valeurs = await page.locator('a[href*="/items/"]').evaluate_all(SCRIPT_EXTRACTION)
    annonces = normaliser_annonces(valeurs)
    precedentes = charger_annonces_precedentes()
    nouvelles = comparer_nouvelles(precedentes, annonces) if precedentes else ()
    return ResultatPassage(
        "ok" if annonces else "lecture_incomplete",
        date_observation,
        url,
        annonces,
        nouvelles,
        None if annonces else "Aucune carte d'annonce exploitable dans le DOM.",
        http_status,
    )


async def lancer_observation(url: str, nombre_defilements: int) -> int:
    url = valider_url_vinted(url)
    DOSSIER_PROFIL.mkdir(parents=True, exist_ok=True)
    DOSSIER_ETAT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        contexte = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(DOSSIER_PROFIL),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = contexte.pages[0] if contexte.pages else await contexte.new_page()
        try:
            resultat = await effectuer_passage(page, url, nombre_defilements)
            enregistrer_resultat(resultat)
            print(
                f"[{resultat.date_observation}] {resultat.statut} - "
                f"{len(resultat.annonces)} annonce(s) - "
                f"{len(resultat.nouvelles)} nouvelle(s)",
                flush=True,
            )
            if resultat.raison:
                print(resultat.raison, flush=True)
            for annonce in resultat.nouvelles:
                print(f"[NOUVELLE] {annonce.titre} - {annonce.prix} EUR - {annonce.url}")
        finally:
            await contexte.close()
    return 0 if resultat.statut == "ok" else 1


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        description="Observe une categorie Vinted une fois dans un Chromium visible."
    )
    parseur.add_argument("--url", required=True, help="URL HTTPS Vinted deja filtree")
    parseur.add_argument("--scrolls", type=int, default=5)
    return parseur


def main() -> int:
    arguments = construire_parseur().parse_args()
    try:
        return asyncio.run(lancer_observation(arguments.url, arguments.scrolls))
    except KeyboardInterrupt:
        print("Observation interrompue proprement.")
        return 130
    except ValueError as erreur:
        print(f"Configuration invalide : {erreur}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
