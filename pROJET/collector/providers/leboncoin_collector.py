"""Collecteur Leboncoin isolé pour mesurer la couverture avant intégration.

Ce module ne réalise aucun accès réseau. Il transforme des observations issues
d'un canal autorisé (API/partenariat, capture navigateur visible ou fixture de
test), mesure les doublons et compare le résultat aux annonces vues par
l'administrateur. Il n'importe ni le pipeline d'analyse, ni SQLite, ni Discord.
"""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from collector.models import Annonce


LOGGER = logging.getLogger(__name__)

SOURCE = "Leboncoin"
PREFIXE_IDENTIFIANT = "LEBONCOIN-"

TITRES_GENERIQUES = {
    "annonce",
    "leboncoin",
    "titre non extrait",
    "voir annonce",
    "voir l annonce",
}

CHAMPS_VENDEUR_IGNORES = {
    "owner",
    "seller",
    "user",
    "phone",
    "telephone",
    "email",
    "contact",
    "has_phone",
}


@dataclass(frozen=True, slots=True)
class AnnonceLeboncoinCollectee:
    """Observation minimale, y compris lorsqu'elle reste incomplète."""

    identifiant: str
    source: str
    titre: str | None
    prix: int | float | None
    description: str
    localisation: str
    url: str
    date_detection: str
    date_publication: str | None = None
    etat: str | None = None
    marque: str | None = None
    annee: int | None = None
    ram_go: int | None = None
    stockage_go: int | None = None
    garantie_jusqu_au: str | None = None

    @property
    def identifiant_source(self) -> str:
        return self.identifiant.removeprefix(PREFIXE_IDENTIFIANT)

    @property
    def champs_manquants(self) -> tuple[str, ...]:
        manquants = []
        if not self.titre:
            manquants.append("titre")
        if self.prix is None:
            manquants.append("prix")
        if not self.description:
            manquants.append("description")
        if not self.localisation or self.localisation == "Inconnue":
            manquants.append("localisation")
        return tuple(manquants)

    @property
    def prete_pour_hunter(self) -> bool:
        return self.titre is not None and self.prix is not None

    @property
    def fiche_complete(self) -> bool:
        return not self.champs_manquants

    def vers_annonce(self) -> Annonce:
        """Construit le modèle commun sans lancer aucune analyse."""
        if not self.prete_pour_hunter:
            raise ValueError(
                "L'annonce Leboncoin doit avoir un titre et un prix avant "
                "d'être convertie pour Hunter."
            )

        annonce = Annonce(
            identifiant=self.identifiant,
            titre=self.titre,
            prix=self.prix,
            description=self.description,
            localisation=self.localisation,
            plateforme=self.source,
            url=self.url,
            date_publication=self.date_publication,
        )
        annonce.date_detection = self.date_detection
        annonce.etat = self.etat
        annonce.marque = self.marque
        annonce.annee = self.annee
        annonce.ram_go = self.ram_go
        annonce.stockage_go = self.stockage_go
        annonce.garantie_jusqu_au = self.garantie_jusqu_au
        return annonce


@dataclass(frozen=True, slots=True)
class RapportCollecteLeboncoin:
    statut: str
    annonces: tuple[AnnonceLeboncoinCollectee, ...]
    nouvelles: tuple[AnnonceLeboncoinCollectee, ...]
    nombre_doublons: int
    erreurs: tuple[str, ...]
    duree_secondes: float
    date_collecte: str

    @property
    def nombre_annonces(self) -> int:
        return len(self.annonces)

    @property
    def nombre_nouvelles(self) -> int:
        return len(self.nouvelles)

    @property
    def nombre_incompletes(self) -> int:
        return sum(not annonce.fiche_complete for annonce in self.annonces)

    def vers_dict(self) -> dict[str, Any]:
        return {
            "statut": self.statut,
            "date_collecte": self.date_collecte,
            "nombre_annonces": self.nombre_annonces,
            "nombre_nouvelles": self.nombre_nouvelles,
            "nombre_doublons": self.nombre_doublons,
            "nombre_incompletes": self.nombre_incompletes,
            "nombre_erreurs": len(self.erreurs),
            "duree_secondes": self.duree_secondes,
            "erreurs": list(self.erreurs),
            "annonces": [
                {
                    **asdict(annonce),
                    "champs_manquants": list(annonce.champs_manquants),
                }
                for annonce in self.annonces
            ],
        }


@dataclass(frozen=True, slots=True)
class ReferenceLeboncoin:
    identifiant: str | None = None
    titre: str | None = None
    prix: int | float | None = None
    localisation: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class RapportCouvertureLeboncoin:
    nombre_attendues: int
    nombre_detectees: int
    nombre_correspondances: int
    couverture_pourcentage: float
    correspondances: tuple[tuple[int, str], ...]
    manquantes: tuple[ReferenceLeboncoin, ...]
    inattendues: tuple[AnnonceLeboncoinCollectee, ...]

    @property
    def succes(self) -> bool:
        return (
            self.nombre_attendues > 0
            and self.nombre_correspondances == self.nombre_attendues
        )

    def vers_dict(self) -> dict[str, Any]:
        return {
            "nombre_attendues": self.nombre_attendues,
            "nombre_detectees": self.nombre_detectees,
            "nombre_correspondances": self.nombre_correspondances,
            "couverture_pourcentage": self.couverture_pourcentage,
            "succes": self.succes,
            "correspondances": [
                {
                    "index_reference": index,
                    "identifiant": identifiant,
                }
                for index, identifiant in self.correspondances
            ],
            "manquantes": [asdict(reference) for reference in self.manquantes],
            "inattendues": [asdict(annonce) for annonce in self.inattendues],
        }


def maintenant_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _lire(source: object, *noms: str) -> Any:
    for nom in noms:
        if isinstance(source, Mapping):
            if nom in source:
                return source[nom]
        elif hasattr(source, nom):
            return getattr(source, nom)
    return None


def _nettoyer_texte(valeur: Any, limite: int) -> str:
    return " ".join(str(valeur or "").split())[:limite]


def _cle_texte(valeur: Any) -> str:
    texte = unicodedata.normalize("NFKD", str(valeur or ""))
    texte = "".join(caractere for caractere in texte if not unicodedata.combining(caractere))
    texte = re.sub(r"[^a-z0-9]+", " ", texte.casefold())
    return " ".join(texte.split())


def _normaliser_titre(valeur: Any) -> str | None:
    titre = _nettoyer_texte(valeur, 500)
    if not titre or _cle_texte(titre) in TITRES_GENERIQUES:
        return None
    return titre


def _extraire_identifiant_brut(source: object) -> str:
    valeur = _lire(source, "identifiant", "id", "list_id")
    texte = str(valeur or "").strip().upper()
    texte = texte.removeprefix(PREFIXE_IDENTIFIANT)

    correspondance = re.search(r"\d{6,}", texte)
    if correspondance:
        return correspondance.group(0)

    url = str(_lire(source, "url") or "")
    correspondance = re.search(r"/ad/[^/?#]+/(\d{6,})", url, flags=re.IGNORECASE)
    if correspondance:
        return correspondance.group(1)

    raise ValueError("Identifiant Leboncoin absent ou invalide.")


def identifiant_stable_leboncoin(source: object) -> str:
    return f"{PREFIXE_IDENTIFIANT}{_extraire_identifiant_brut(source)}"


def _normaliser_url(source: object, identifiant_source: str) -> str:
    valeur = _nettoyer_texte(_lire(source, "url"), 2_000)
    if not valeur:
        return f"https://www.leboncoin.fr/ad/ordinateurs/{identifiant_source}"

    analyse = urlparse(valeur)
    hote = (analyse.hostname or "").lower()
    if analyse.scheme not in {"http", "https"} or not (
        hote == "leboncoin.fr" or hote.endswith(".leboncoin.fr")
    ):
        raise ValueError("URL Leboncoin invalide.")
    if analyse.username or analyse.password:
        raise ValueError("L'URL Leboncoin ne doit contenir aucun identifiant.")
    return valeur


def _premiere_valeur(valeur: Any) -> Any:
    if isinstance(valeur, Sequence) and not isinstance(
        valeur,
        (str, bytes, bytearray),
    ):
        return next((element for element in valeur if element is not None), None)
    return valeur


def _normaliser_prix(source: object) -> int | float | None:
    prix_cents = _lire(source, "price_cents")
    if prix_cents is not None:
        try:
            nombre = float(prix_cents) / 100
        except (TypeError, ValueError) as erreur:
            raise ValueError("Prix Leboncoin invalide.") from erreur
    else:
        valeur = _premiere_valeur(_lire(source, "prix", "price"))
        if valeur in (None, ""):
            return None
        texte = str(valeur).replace("\xa0", " ")
        correspondance = re.search(
            r"(\d{1,3}(?:[ .]\d{3})*|\d+)(?:[,.](\d{1,2}))?",
            texte,
        )
        if not correspondance:
            raise ValueError("Prix Leboncoin invalide.")
        entier = correspondance.group(1).replace(" ", "").replace(".", "")
        decimal = f".{correspondance.group(2)}" if correspondance.group(2) else ""
        nombre = float(f"{entier}{decimal}")

    if nombre <= 0:
        raise ValueError("Le prix Leboncoin doit être positif.")
    return int(nombre) if nombre.is_integer() else round(nombre, 2)


def _normaliser_localisation(source: object) -> str:
    valeur = _lire(source, "localisation", "location", "ville", "city")
    if isinstance(valeur, str):
        return _nettoyer_texte(valeur, 300) or "Inconnue"
    if not valeur:
        return "Inconnue"

    ville = _nettoyer_texte(
        _lire(valeur, "city", "city_label", "label", "ville"),
        200,
    )
    code_postal = _nettoyer_texte(_lire(valeur, "zipcode", "postal_code"), 10)
    departement = _nettoyer_texte(_lire(valeur, "department_id"), 5)
    if not departement and len(code_postal) == 5 and code_postal.isdigit():
        departement = code_postal[:3] if code_postal.startswith(("97", "98")) else code_postal[:2]
    if not ville:
        return "Inconnue"
    if departement and f"({departement})" not in ville:
        return f"{ville} ({departement})"
    return ville


def _normaliser_entier(valeur: Any) -> int | None:
    if valeur in (None, ""):
        return None
    correspondance = re.search(r"\d{1,4}", str(valeur))
    return int(correspondance.group(0)) if correspondance else None


def _normaliser_capacite_go(valeur: Any) -> int | None:
    if valeur in (None, ""):
        return None
    correspondance = re.search(r"(\d+(?:[,.]\d+)?)\s*(to|tb|go|gb)?", str(valeur), re.IGNORECASE)
    if not correspondance:
        return None
    nombre = float(correspondance.group(1).replace(",", "."))
    if (correspondance.group(2) or "").casefold() in {"to", "tb"}:
        nombre *= 1024
    return int(round(nombre))


def _extraire_specs(
    source: object,
    titre: str | None,
    description: str,
) -> dict[str, Any]:
    contexte = " ".join(
        element
        for element in (
            titre or "",
            description,
            _nettoyer_texte(_lire(source, "caracteristiques", "attributes"), 5_000),
        )
        if element
    )

    etat = _nettoyer_texte(_lire(source, "etat", "condition"), 100) or None
    if not etat:
        correspondance = re.search(
            r"\b(tr[eè]s bon [eé]tat|bon [eé]tat|[eé]tat neuf|comme neuf|satisfaisant)\b",
            contexte,
            re.IGNORECASE,
        )
        etat = correspondance.group(1) if correspondance else None

    marque = _nettoyer_texte(_lire(source, "marque", "brand"), 100) or None
    if not marque:
        marques = {
            "macbook": "Apple",
            "imac": "Apple",
            "apple": "Apple",
            "lenovo": "Lenovo",
            "thinkpad": "Lenovo",
            "dell": "Dell",
            "asus": "ASUS",
            "acer": "Acer",
            "hp": "HP",
            "msi": "MSI",
        }
        cle_contexte = _cle_texte(contexte)
        marque = next((nom for motif, nom in marques.items() if motif in cle_contexte), None)

    annee = _normaliser_entier(_lire(source, "annee", "year"))
    if annee is None:
        correspondance = re.search(r"\b(?:ann[eé]e|mod[eè]le)\s*[: -]?\s*(20\d{2})\b", contexte, re.IGNORECASE)
        annee = int(correspondance.group(1)) if correspondance else None

    ram_go = _normaliser_capacite_go(_lire(source, "ram_go", "ram", "memory"))
    stockage_go = _normaliser_capacite_go(
        _lire(source, "stockage_go", "stockage", "storage", "disk")
    )

    if ram_go is None:
        correspondance = re.search(
            r"\b(?:ram|m[eé]moire vive)\s*[: -]?\s*(\d+)\s*(?:go|gb)\b",
            contexte,
            re.IGNORECASE,
        )
        ram_go = int(correspondance.group(1)) if correspondance else None

    if stockage_go is None:
        correspondance = re.search(
            r"\b(?:stockage|ssd|nvme|disque(?: dur)?)\s*[: -]?\s*(\d+)\s*(to|tb|go|gb)\b",
            contexte,
            re.IGNORECASE,
        )
        if correspondance:
            stockage_go = _normaliser_capacite_go(
                f"{correspondance.group(1)} {correspondance.group(2)}"
            )

    if ram_go is None or stockage_go is None:
        paire = re.search(
            r"\b(\d+)\s*(?:go|gb)\s*/\s*(\d+)\s*(?:go|gb)\b",
            contexte,
            re.IGNORECASE,
        )
        if paire:
            valeurs = sorted((int(paire.group(1)), int(paire.group(2))))
            if ram_go is None and valeurs[0] <= 128:
                ram_go = valeurs[0]
            if stockage_go is None and valeurs[1] >= 64:
                stockage_go = valeurs[1]

    garantie = _nettoyer_texte(
        _lire(source, "garantie_jusqu_au", "warranty_until", "garantie"),
        100,
    ) or None
    if not garantie:
        correspondance = re.search(
            r"garantie\s+(?:jusqu['’]?[aà]|jusqu'au|jusqu’en|jusqu'en)\s*[: -]?\s*(\d{1,2}/\d{4})",
            contexte,
            re.IGNORECASE,
        )
        garantie = correspondance.group(1) if correspondance else None

    return {
        "etat": etat,
        "marque": marque,
        "annee": annee,
        "ram_go": ram_go,
        "stockage_go": stockage_go,
        "garantie_jusqu_au": garantie,
    }


def normaliser_observation_leboncoin(
    source: object,
    date_detection: str | None = None,
) -> AnnonceLeboncoinCollectee:
    """Normalise une observation sans conserver les données vendeur."""
    identifiant = identifiant_stable_leboncoin(source)
    identifiant_source = identifiant.removeprefix(PREFIXE_IDENTIFIANT)
    titre = _normaliser_titre(_lire(source, "titre", "subject", "title"))
    description = _nettoyer_texte(_lire(source, "description", "body"), 10_000)
    specs = _extraire_specs(source, titre, description)
    date_publication = _nettoyer_texte(
        _lire(source, "date_publication", "first_publication_date"),
        100,
    ) or None

    return AnnonceLeboncoinCollectee(
        identifiant=identifiant,
        source=SOURCE,
        titre=titre,
        prix=_normaliser_prix(source),
        description=description,
        localisation=_normaliser_localisation(source),
        url=_normaliser_url(source, identifiant_source),
        date_detection=date_detection or maintenant_iso(),
        date_publication=date_publication,
        **specs,
    )


def _fusionner(
    ancienne: AnnonceLeboncoinCollectee,
    nouvelle: AnnonceLeboncoinCollectee,
) -> AnnonceLeboncoinCollectee:
    """Conserve les champs les plus riches d'observations du même ID."""
    remplacements = {}
    for champ in (
        "titre",
        "prix",
        "description",
        "localisation",
        "date_publication",
        "etat",
        "marque",
        "annee",
        "ram_go",
        "stockage_go",
        "garantie_jusqu_au",
    ):
        valeur = getattr(nouvelle, champ)
        if valeur not in (None, "", "Inconnue"):
            remplacements[champ] = valeur
    remplacements["url"] = nouvelle.url or ancienne.url
    remplacements["date_detection"] = nouvelle.date_detection
    return replace(ancienne, **remplacements)


def _normaliser_identifiants_connus(valeurs: Iterable[object]) -> set[str]:
    connus = set()
    for valeur in valeurs:
        try:
            if isinstance(valeur, str):
                connus.add(identifiant_stable_leboncoin({"identifiant": valeur}))
            else:
                connus.add(identifiant_stable_leboncoin(valeur))
        except ValueError:
            continue
    return connus


def collecter_observations_leboncoin(
    observations: Iterable[object],
    identifiants_connus: Iterable[object] = (),
    date_detection: str | None = None,
) -> RapportCollecteLeboncoin:
    debut = time.perf_counter()
    annonces_par_id: dict[str, AnnonceLeboncoinCollectee] = {}
    erreurs = []
    doublons = 0

    for index, observation in enumerate(observations, start=1):
        try:
            annonce = normaliser_observation_leboncoin(observation, date_detection)
        except (TypeError, ValueError) as erreur:
            erreurs.append(f"observation {index}: {erreur}")
            continue

        if annonce.identifiant in annonces_par_id:
            doublons += 1
            annonce = _fusionner(annonces_par_id[annonce.identifiant], annonce)
        annonces_par_id[annonce.identifiant] = annonce

    annonces = tuple(annonces_par_id.values())
    connus = _normaliser_identifiants_connus(identifiants_connus)
    nouvelles = tuple(
        annonce for annonce in annonces if annonce.identifiant not in connus
    )

    if annonces and erreurs:
        statut = "PARTIAL"
    elif annonces:
        statut = "SUCCEEDED"
    elif erreurs:
        statut = "FAILED"
    else:
        statut = "EMPTY_CONFIRMED"

    duree = round(time.perf_counter() - debut, 4)
    rapport = RapportCollecteLeboncoin(
        statut=statut,
        annonces=annonces,
        nouvelles=nouvelles,
        nombre_doublons=doublons,
        erreurs=tuple(erreurs),
        duree_secondes=duree,
        date_collecte=date_detection or maintenant_iso(),
    )
    LOGGER.info(
        "Leboncoin | statut=%s trouvées=%s nouvelles=%s doublons=%s "
        "incomplètes=%s erreurs=%s durée=%.4fs",
        rapport.statut,
        rapport.nombre_annonces,
        rapport.nombre_nouvelles,
        rapport.nombre_doublons,
        rapport.nombre_incompletes,
        len(rapport.erreurs),
        rapport.duree_secondes,
    )
    return rapport


def charger_objets_json(chemin: str | Path) -> list[object]:
    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if isinstance(contenu, list):
        return contenu
    if isinstance(contenu, Mapping):
        for cle in ("annonces", "attendues", "items", "results"):
            valeur = contenu.get(cle)
            if isinstance(valeur, list):
                return valeur
    raise ValueError("Le JSON doit contenir une liste d'annonces.")


def collecter_depuis_etat_observateur(
    dossier_etat: str | Path,
    identifiants_connus: Iterable[object] = (),
) -> RapportCollecteLeboncoin:
    """Lit l'état isolé Playwright sans réutiliser un snapshot après blocage."""
    debut = time.perf_counter()
    dossier = Path(dossier_etat)
    statut = json.loads((dossier / "status.json").read_text(encoding="utf-8"))
    statut_observateur = str(statut.get("statut") or "").strip()

    if statut_observateur != "ok":
        if statut_observateur == "intervention_manuelle_requise":
            statut_collecte = "BLOCKED"
        elif statut_observateur == "lecture_incomplete":
            statut_collecte = "PARTIAL"
        else:
            statut_collecte = "FAILED"
        raison = _nettoyer_texte(statut.get("raison"), 500) or statut_observateur
        rapport = RapportCollecteLeboncoin(
            statut=statut_collecte,
            annonces=(),
            nouvelles=(),
            nombre_doublons=0,
            erreurs=(raison,),
            duree_secondes=round(time.perf_counter() - debut, 4),
            date_collecte=_nettoyer_texte(statut.get("date_observation"), 100)
            or maintenant_iso(),
        )
        LOGGER.warning(
            "Leboncoin | statut=%s trouvées=0 nouvelles=0 doublons=0 "
            "erreurs=1 durée=%.4fs raison=%s",
            rapport.statut,
            rapport.duree_secondes,
            raison,
        )
        return rapport

    observations = charger_objets_json(dossier / "listings.json")
    return collecter_observations_leboncoin(
        observations,
        identifiants_connus=identifiants_connus,
        date_detection=_nettoyer_texte(statut.get("date_observation"), 100) or None,
    )


def reference_leboncoin_depuis_source(source: object) -> ReferenceLeboncoin:
    identifiant = None
    try:
        identifiant = identifiant_stable_leboncoin(source)
    except ValueError:
        pass
    prix = None
    try:
        prix = _normaliser_prix(source)
    except ValueError:
        pass
    titre = _normaliser_titre(_lire(source, "titre", "subject", "title"))
    localisation = _normaliser_localisation(source)
    return ReferenceLeboncoin(
        identifiant=identifiant,
        titre=titre,
        prix=prix,
        localisation=None if localisation == "Inconnue" else localisation,
        url=_nettoyer_texte(_lire(source, "url"), 2_000) or None,
    )


def _reference_correspond(
    reference: ReferenceLeboncoin,
    annonce: AnnonceLeboncoinCollectee,
) -> bool:
    if reference.identifiant:
        return reference.identifiant == annonce.identifiant
    if not reference.titre or not annonce.titre:
        return False
    if _cle_texte(reference.titre) != _cle_texte(annonce.titre):
        return False
    if reference.prix is not None and reference.prix != annonce.prix:
        return False
    if reference.localisation and annonce.localisation != "Inconnue":
        ville_attendue = _cle_texte(reference.localisation).split("(")[0].strip()
        if ville_attendue and ville_attendue not in _cle_texte(annonce.localisation):
            return False
    return True


def comparer_couverture_leboncoin(
    attendues: Iterable[ReferenceLeboncoin | object],
    detectees: Iterable[AnnonceLeboncoinCollectee],
) -> RapportCouvertureLeboncoin:
    references = tuple(
        valeur
        if isinstance(valeur, ReferenceLeboncoin)
        else reference_leboncoin_depuis_source(valeur)
        for valeur in attendues
    )
    annonces = tuple(detectees)
    disponibles = set(range(len(annonces)))
    correspondances = []
    manquantes = []

    for index_reference, reference in enumerate(references, start=1):
        candidats = [
            index
            for index in disponibles
            if _reference_correspond(reference, annonces[index])
        ]
        if len(candidats) != 1:
            manquantes.append(reference)
            continue
        index_annonce = candidats[0]
        disponibles.remove(index_annonce)
        correspondances.append(
            (index_reference, annonces[index_annonce].identifiant)
        )

    nombre_attendues = len(references)
    pourcentage = (
        round(len(correspondances) * 100 / nombre_attendues, 2)
        if nombre_attendues
        else 0.0
    )
    return RapportCouvertureLeboncoin(
        nombre_attendues=nombre_attendues,
        nombre_detectees=len(annonces),
        nombre_correspondances=len(correspondances),
        couverture_pourcentage=pourcentage,
        correspondances=tuple(correspondances),
        manquantes=tuple(manquantes),
        inattendues=tuple(annonces[index] for index in sorted(disponibles)),
    )

