"""Contrat de données pour un futur provider Leboncoin autorisé.

Ce module ne réalise aucun appel réseau. Il accepte uniquement un résultat
déjà obtenu par une source autorisée et le transforme en ``Annonce``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse

from collector.models import Annonce


@dataclass(frozen=True, slots=True)
class LeboncoinResult:
    """Sous-ensemble strictement nécessaire à PC Hunter."""

    id: str | int
    titre: str
    prix: int | float
    description: str = ""
    localisation: str = "Inconnue"
    url: str | None = None
    date_publication: str | datetime | None = None


class ProviderLeboncoinAutorise(Protocol):
    """Interface attendue d'un futur connecteur officiel/partenaire."""

    def rechercher(
        self,
        limite: int | None = None,
    ) -> Iterable[LeboncoinResult]: ...


def _lire(source: object, *noms: str) -> Any:
    for nom in noms:
        if isinstance(source, Mapping):
            if nom in source:
                return source[nom]
        elif hasattr(source, nom):
            return getattr(source, nom)

    return None


def _premiere_valeur_prix(valeur: Any) -> Any:
    if (
        isinstance(valeur, Sequence)
        and not isinstance(valeur, (str, bytes, bytearray))
    ):
        return next(
            (element for element in valeur if element is not None),
            None,
        )

    return valeur


def _normaliser_prix(source: object) -> int | float:
    prix_cents = _lire(source, "price_cents")

    if prix_cents is not None:
        try:
            prix = float(prix_cents) / 100
        except (TypeError, ValueError) as erreur:
            raise ValueError("Prix Leboncoin invalide.") from erreur
    else:
        valeur = _premiere_valeur_prix(
            _lire(source, "prix", "price")
        )

        try:
            prix = float(valeur)
        except (TypeError, ValueError) as erreur:
            raise ValueError("Prix Leboncoin absent ou invalide.") from erreur

    if prix <= 0:
        raise ValueError("Le prix Leboncoin doit être positif.")

    if prix.is_integer():
        return int(prix)

    return round(prix, 2)


def _departement_depuis_code_postal(code_postal: Any) -> str | None:
    code = str(code_postal or "").strip()

    if len(code) != 5 or not code.isdigit():
        return None

    if code.startswith(("97", "98")):
        return code[:3]

    if code.startswith("20"):
        return None

    return code[:2]


def _normaliser_localisation(source: object) -> str:
    localisation = _lire(source, "localisation", "location")

    if isinstance(localisation, str):
        texte = " ".join(localisation.split())
        return texte or "Inconnue"

    if localisation is None:
        return "Inconnue"

    ville = _lire(
        localisation,
        "city",
        "city_label",
        "label",
    )
    ville = " ".join(str(ville or "").split())

    if not ville:
        return "Inconnue"

    departement = _lire(localisation, "department_id")
    departement = str(departement or "").strip()

    if not departement:
        departement = _departement_depuis_code_postal(
            _lire(localisation, "zipcode")
        ) or ""

    if departement and f"({departement})" not in ville:
        return f"{ville} ({departement})"

    return ville


def _normaliser_url(url: Any, identifiant: str) -> str:
    if not url:
        return (
            "https://www.leboncoin.fr/ad/ordinateurs/"
            f"{identifiant}"
        )

    texte = str(url).strip()
    analyse = urlparse(texte)
    hote = (analyse.hostname or "").lower()

    if (
        analyse.scheme not in {"http", "https"}
        or not (
            hote == "leboncoin.fr"
            or hote.endswith(".leboncoin.fr")
        )
    ):
        raise ValueError("URL Leboncoin invalide.")

    return texte


def resultat_leboncoin_depuis_source(
    source: object,
) -> LeboncoinResult:
    """Adapte les formes publiques observées sans conserver le vendeur."""

    identifiant_brut = _lire(source, "id", "list_id", "identifiant")
    identifiant = str(identifiant_brut or "").strip()

    if not identifiant:
        raise ValueError("Identifiant Leboncoin absent.")

    titre = str(
        _lire(source, "titre", "subject", "title") or ""
    ).strip()

    if not titre:
        raise ValueError("Titre Leboncoin absent.")

    description = str(
        _lire(source, "description", "body") or ""
    ).strip()

    date_publication = _lire(
        source,
        "date_publication",
        "first_publication_date",
    )

    return LeboncoinResult(
        id=identifiant,
        titre=titre,
        prix=_normaliser_prix(source),
        description=description,
        localisation=_normaliser_localisation(source),
        url=_normaliser_url(
            _lire(source, "url"),
            identifiant,
        ),
        date_publication=date_publication,
    )


def normaliser_leboncoin(
    resultat: LeboncoinResult | object,
) -> Annonce:
    """Transforme un résultat autorisé en modèle commun PC Hunter."""

    if not isinstance(resultat, LeboncoinResult):
        resultat = resultat_leboncoin_depuis_source(resultat)

    identifiant = str(resultat.id).strip()

    if not identifiant:
        raise ValueError("Identifiant Leboncoin absent.")

    titre = str(resultat.titre or "").strip()

    if not titre:
        raise ValueError("Titre Leboncoin absent.")

    prix = _normaliser_prix(resultat)
    url = _normaliser_url(resultat.url, identifiant)

    return Annonce(
        identifiant=identifiant,
        titre=titre,
        prix=prix,
        description=str(resultat.description or ""),
        localisation=str(resultat.localisation or "Inconnue"),
        plateforme="Leboncoin",
        url=url,
        date_publication=resultat.date_publication,
    )


def normaliser_resultats_leboncoin(
    resultats: Iterable[LeboncoinResult | object],
) -> list[Annonce]:
    return [
        normaliser_leboncoin(resultat)
        for resultat in resultats
    ]

