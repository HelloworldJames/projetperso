"""Provider eBay fondé exclusivement sur l'API Browse officielle."""

import base64
import os
import time

from pathlib import Path

from dotenv import load_dotenv

from collector.http import creer_session_http
from collector.models import Annonce


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

PORTEE_API = "https://api.ebay.com/oauth/api_scope"


def _texte(valeur, limite=10_000):
    texte = " ".join(str(valeur or "").split())
    return texte[:limite] or None


def _localisation(item):
    lieu = item.get("itemLocation") or {}
    morceaux = [
        lieu.get("city"),
        lieu.get("postalCode"),
        lieu.get("stateOrProvince"),
    ]
    propres = [_texte(element, 100) for element in morceaux if element]
    return " ".join(dict.fromkeys(propres)) if propres else "Inconnue"


class EbayProvider:
    nom = "eBay officiel"

    def __init__(self, session=None, client_id=None, client_secret=None, environnement=None):
        self.session = session or creer_session_http()
        self.client_id = client_id or os.getenv("EBAY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("EBAY_CLIENT_SECRET")
        self.environnement = (environnement or os.getenv("EBAY_ENV", "production")).lower()
        self._jeton = None
        self._expiration = 0

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Identifiants eBay API absents.")

        if self.environnement in {"sandbox", "test"}:
            self.auth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
            self.api_url = "https://api.sandbox.ebay.com/buy/browse/v1"
        else:
            self.auth_url = "https://api.ebay.com/identity/v1/oauth2/token"
            self.api_url = "https://api.ebay.com/buy/browse/v1"

    def _obtenir_jeton(self):
        if self._jeton and time.time() < self._expiration - 60:
            return self._jeton

        identifiants = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")
        reponse = self.session.post(
            self.auth_url,
            headers={
                "Authorization": f"Basic {identifiants}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": PORTEE_API,
            },
            timeout=20,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        self._jeton = donnees["access_token"]
        self._expiration = time.time() + int(donnees.get("expires_in", 7200))
        return self._jeton

    def _rechercher_une_requete(self, recherche, limite):
        reponse = self.session.get(
            f"{self.api_url}/item_summary/search",
            headers={
                "Authorization": f"Bearer {self._obtenir_jeton()}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR",
                "X-EBAY-C-ENDUSERCTX": (
                    "contextualLocation=country%3DFR%2Czip%3D17430"
                ),
            },
            params={
                "q": recherche,
                "limit": min(max(int(limite), 1), 50),
                "sort": "newlyListed",
                "fieldgroups": "EXTENDED",
                "filter": (
                    "price:[20..1500],priceCurrency:EUR,"
                    "buyingOptions:{FIXED_PRICE|BEST_OFFER}"
                ),
            },
            timeout=25,
        )
        reponse.raise_for_status()
        return reponse.json().get("itemSummaries", [])

    def rechercher(self, recherche=None, limite_par_recherche=30):
        if recherche is None:
            from config import EBAY_RECHERCHES
            recherches = EBAY_RECHERCHES
        elif isinstance(recherche, str):
            recherches = (recherche,)
        else:
            recherches = tuple(recherche)

        annonces = []
        identifiants = set()

        for requete in recherches:
            print(f"Recherche eBay officielle : {requete}")
            for item in self._rechercher_une_requete(requete, limite_par_recherche):
                identifiant = _texte(item.get("itemId"), 200)
                titre = _texte(item.get("title"), 500)
                prix = (item.get("price") or {}).get("value")
                url = item.get("itemWebUrl")

                if not identifiant or identifiant in identifiants or not titre or prix is None:
                    continue

                description = _texte(item.get("shortDescription"))
                etat = _texte(item.get("condition"), 200)
                if not description:
                    description = titre
                if etat:
                    description = f"{description} État eBay : {etat}."

                try:
                    annonce = Annonce(
                        identifiant=identifiant,
                        titre=titre,
                        prix=prix,
                        description=description,
                        localisation=_localisation(item),
                        plateforme="eBay",
                        url=url,
                        date_publication=item.get("itemCreationDate"),
                    )
                except (TypeError, ValueError):
                    continue

                identifiants.add(identifiant)
                annonces.append(annonce)

        return annonces
