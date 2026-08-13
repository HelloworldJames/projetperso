"""Extraction minimale : identifiant public, titre, prix et URL uniquement."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


MOTIF_PRIX = re.compile(
    r"(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:€|EUR)",
    re.IGNORECASE,
)
MOTIF_IDENTIFIANT = re.compile(r"/(?:ad/[^/]+|items)/(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class AnnonceExtraite:
    identifiant: str
    titre: str
    prix: float | int
    url: str


def _nettoyer(valeur) -> str:
    return " ".join(str(valeur or "").split())


def _lire_prix(texte: str) -> float | int | None:
    trouve = MOTIF_PRIX.search(texte)
    if not trouve:
        return None
    entier = re.sub(r"[ .\u00a0]", "", trouve.group(1))
    decimal = f".{trouve.group(2)}" if trouve.group(2) else ""
    prix = float(f"{entier}{decimal}")
    return int(prix) if prix.is_integer() else prix


def _identifiant(url: str) -> str:
    trouve = MOTIF_IDENTIFIANT.search(urlsplit(url).path)
    return trouve.group(1) if trouve else url


class _CollecteurHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ancres: list[dict] = []
        self.meta: dict[str, str] = {}
        self.h1: list[str] = []
        self.json_ld: list[str] = []
        self._ancre: dict | None = None
        self._dans_h1 = 0
        self._dans_json_ld = 0

    def handle_starttag(self, tag, attrs):
        attributs = dict(attrs)
        if tag == "a" and self._ancre is None:
            self._ancre = {
                "href": attributs.get("href", ""),
                "titre": attributs.get("aria-label") or attributs.get("title") or "",
                "texte": [],
            }
        elif self._ancre is not None and tag == "img" and attributs.get("alt"):
            self._ancre["texte"].append(attributs["alt"])
        if tag == "meta":
            cle = attributs.get("property") or attributs.get("name")
            if cle and attributs.get("content"):
                self.meta[cle.casefold()] = attributs["content"]
        if tag == "h1":
            self._dans_h1 += 1
            self.h1.append("")
        if tag == "script" and attributs.get("type", "").casefold() == "application/ld+json":
            self._dans_json_ld += 1
            self.json_ld.append("")

    def handle_endtag(self, tag):
        if tag == "a" and self._ancre is not None:
            self.ancres.append(self._ancre)
            self._ancre = None
        if tag == "h1" and self._dans_h1:
            self._dans_h1 -= 1
        if tag == "script" and self._dans_json_ld:
            self._dans_json_ld -= 1

    def handle_data(self, data):
        if self._ancre is not None:
            self._ancre["texte"].append(data)
        if self._dans_h1 and self.h1:
            self.h1[-1] += data
        if self._dans_json_ld and self.json_ld:
            self.json_ld[-1] += data


def _titre_depuis_texte(texte: str) -> str:
    titre = re.sub(r"^image\s*:\s*", "", _nettoyer(texte), flags=re.IGNORECASE)
    titre = re.split(
        r",\s*(?:marque|etat|état|taille|prix)\s*:",
        titre,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    if MOTIF_PRIX.fullmatch(titre):
        return ""
    return titre[:500]


def _ajouter_json_ld(valeur, base_url: str, annonces: dict[str, AnnonceExtraite]) -> None:
    if isinstance(valeur, list):
        for element in valeur:
            _ajouter_json_ld(element, base_url, annonces)
        return
    if not isinstance(valeur, dict):
        return

    type_schema = valeur.get("@type")
    if type_schema == "Product" or (isinstance(type_schema, list) and "Product" in type_schema):
        offre = valeur.get("offers") or {}
        if isinstance(offre, list):
            offre = offre[0] if offre else {}
        titre = _nettoyer(valeur.get("name"))
        url = urljoin(base_url, valeur.get("url") or valeur.get("@id") or base_url)
        prix_brut = offre.get("price") if isinstance(offre, dict) else None
        try:
            prix_float = float(str(prix_brut).replace(",", "."))
        except (TypeError, ValueError):
            prix_float = None
        if titre and prix_float is not None:
            prix = int(prix_float) if prix_float.is_integer() else prix_float
            identifiant = str(valeur.get("productID") or valeur.get("sku") or _identifiant(url))
            annonces[identifiant] = AnnonceExtraite(identifiant, titre[:500], prix, url)

    for element in valeur.values():
        if isinstance(element, (dict, list)):
            _ajouter_json_ld(element, base_url, annonces)


def extraire_annonces(html: str, base_url: str) -> tuple[AnnonceExtraite, ...]:
    collecteur = _CollecteurHTML()
    collecteur.feed(str(html or ""))
    annonces: dict[str, AnnonceExtraite] = {}

    for bloc in collecteur.json_ld:
        try:
            valeur = json.loads(bloc)
        except json.JSONDecodeError:
            continue
        _ajouter_json_ld(valeur, base_url, annonces)

    for ancre in collecteur.ancres:
        url = urljoin(base_url, ancre["href"])
        if not MOTIF_IDENTIFIANT.search(urlsplit(url).path):
            continue
        texte = _nettoyer(" ".join(ancre["texte"]))
        titre = _titre_depuis_texte(ancre["titre"] or texte)
        prix = _lire_prix(texte)
        if not titre or prix is None:
            continue
        identifiant = _identifiant(url)
        annonces[identifiant] = AnnonceExtraite(identifiant, titre, prix, url)

    if not annonces:
        titre = _nettoyer(
            collecteur.meta.get("og:title")
            or next((valeur for valeur in collecteur.h1 if _nettoyer(valeur)), "")
        )
        prix_meta = (
            collecteur.meta.get("product:price:amount")
            or collecteur.meta.get("og:price:amount")
        )
        try:
            prix_float = float(str(prix_meta).replace(",", "."))
        except (TypeError, ValueError):
            prix_float = None
        if titre and prix_float is not None:
            identifiant = _identifiant(base_url)
            prix = int(prix_float) if prix_float.is_integer() else prix_float
            annonces[identifiant] = AnnonceExtraite(identifiant, titre[:500], prix, base_url)

    return tuple(annonces.values())
