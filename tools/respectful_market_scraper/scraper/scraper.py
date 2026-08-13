"""Chargement Playwright sans connexion, contournement ni nouvelle tentative."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from . import BOT_USER_AGENT
from .rate_limiter import wait_human
from .robots_checker import RobotsDecision, verifier_robots


STATUTS_ARRET = {401, 403, 429}
MOTIFS_CONTROLE = (
    "captcha",
    "verify you are human",
    "vérifiez que vous êtes humain",
    "security check",
    "just a moment",
    "un instant",
)


class ScrapingRefuse(RuntimeError):
    """Arret attendu lorsqu'une regle ou la plateforme refuse l'acces."""


@dataclass(frozen=True)
class PageChargee:
    url_demandee: str
    url_finale: str
    statut_http: int | None
    titre: str
    html: str
    robots: RobotsDecision
    delai_applique: float


def fetch_page(
    url: str,
    *,
    headless: bool = True,
    delai_minimum: float = 3,
    delai_maximum: float = 8,
    timeout_ms: int = 45_000,
) -> PageChargee:
    decision = verifier_robots(url, BOT_USER_AGENT)
    if not decision.autorise:
        raise ScrapingRefuse(f"robots.txt: {decision.raison}")

    delai = wait_human(delai_minimum, delai_maximum, decision.delai_exploration)
    with sync_playwright() as playwright:
        navigateur = playwright.chromium.launch(headless=headless)
        contexte = navigateur.new_context(user_agent=BOT_USER_AGENT)
        page = contexte.new_page()
        try:
            try:
                reponse = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except PlaywrightTimeoutError as erreur:
                raise ScrapingRefuse(f"Timeout de navigation apres {timeout_ms} ms.") from erreur

            statut = reponse.status if reponse else None
            if statut in STATUTS_ARRET:
                raise ScrapingRefuse(f"La page principale a repondu HTTP {statut}.")

            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except PlaywrightTimeoutError:
                pass

            titre = page.title()
            texte = page.locator("body").inner_text(timeout=5_000)
            contenu_controle = f"{titre} {texte[:80_000]} {page.url}".casefold()
            motif = next((m for m in MOTIFS_CONTROLE if m in contenu_controle), None)
            if motif:
                raise ScrapingRefuse(f"Verification interactive detectee ({motif}).")

            return PageChargee(
                url_demandee=url,
                url_finale=page.url,
                statut_http=statut,
                titre=titre[:500],
                html=page.content(),
                robots=decision,
                delai_applique=delai,
            )
        finally:
            contexte.close()
            navigateur.close()
