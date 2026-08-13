"""Lecture conservative de robots.txt avant tout chargement Playwright."""

from __future__ import annotations

import urllib.error
import urllib.request
import urllib.robotparser
import ssl
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import certifi
import truststore

from . import BOT_USER_AGENT


INTERDICTIONS_EXPLICITES = (
    "it's forbidden to use search robots or other automatic methods to access",
    "access is only permitted with special permission",
)


@dataclass(frozen=True)
class RobotsDecision:
    autorise: bool
    url: str
    robots_url: str
    user_agent: str
    raison: str
    delai_exploration: float | None = None


def valider_url_http(url: str) -> str:
    valeur = str(url or "").strip()
    parties = urlsplit(valeur)
    if parties.scheme not in {"http", "https"} or not parties.hostname:
        raise ValueError("L'URL doit etre une adresse HTTP(S) complete.")
    if parties.username or parties.password:
        raise ValueError("L'URL ne doit contenir aucun identifiant de connexion.")
    if parties.hostname.casefold() == "localhost":
        raise ValueError("Les adresses locales ne sont pas acceptees.")
    return valeur


def construire_url_robots(url: str) -> str:
    parties = urlsplit(valider_url_http(url))
    return urlunsplit((parties.scheme, parties.netloc, "/robots.txt", "", ""))


def _telecharger_robots(robots_url: str, user_agent: str, timeout: float) -> tuple[int, str]:
    requete = urllib.request.Request(
        robots_url,
        headers={"User-Agent": user_agent},
        method="GET",
    )
    try:
        try:
            contexte_tls = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:
            contexte_tls = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(
            requete,
            timeout=timeout,
            context=contexte_tls,
        ) as reponse:
            contenu = reponse.read(1_000_000).decode("utf-8", errors="replace")
            return int(reponse.status), contenu
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            return 404, ""
        raise


def _decrire_erreur_reseau(erreur: Exception) -> str:
    if isinstance(erreur, urllib.error.HTTPError):
        return f"HTTP {erreur.code}: {erreur.reason}"
    cause = getattr(erreur, "reason", erreur)
    message = " ".join(str(cause).split())[:240]
    return f"{type(cause).__name__}: {message}" if message else type(cause).__name__


def verifier_robots(
    url: str,
    user_agent: str = BOT_USER_AGENT,
    timeout: float = 10,
) -> RobotsDecision:
    url = valider_url_http(url)
    robots_url = construire_url_robots(url)
    try:
        statut, contenu = _telecharger_robots(robots_url, user_agent, timeout)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as erreur:
        return RobotsDecision(
            False,
            url,
            robots_url,
            user_agent,
            "robots.txt inaccessible; refus prudent "
            f"({_decrire_erreur_reseau(erreur)}).",
        )

    if statut == 404:
        return RobotsDecision(
            True,
            url,
            robots_url,
            user_agent,
            "Aucun robots.txt publie (HTTP 404).",
        )
    if statut != 200:
        return RobotsDecision(
            False,
            url,
            robots_url,
            user_agent,
            f"robots.txt a repondu HTTP {statut}; refus prudent.",
        )

    contenu_minuscule = contenu.casefold()
    interdiction = next(
        (marqueur for marqueur in INTERDICTIONS_EXPLICITES if marqueur in contenu_minuscule),
        None,
    )
    if interdiction:
        return RobotsDecision(
            False,
            url,
            robots_url,
            user_agent,
            "Le fichier robots.txt exige une autorisation speciale pour les acces automatises.",
        )

    analyseur = urllib.robotparser.RobotFileParser()
    analyseur.set_url(robots_url)
    analyseur.parse(contenu.splitlines())
    autorise = analyseur.can_fetch(user_agent, url)
    delai = analyseur.crawl_delay(user_agent)
    if delai is None:
        delai = analyseur.crawl_delay("*")
    return RobotsDecision(
        autorise,
        url,
        robots_url,
        user_agent,
        "Autorise par robots.txt." if autorise else "Interdit par une regle robots.txt.",
        float(delai) if delai is not None else None,
    )
