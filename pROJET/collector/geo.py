import math
import re
import unicodedata
from functools import lru_cache

import requests

from collector.http import creer_session_http


API_COMMUNES = "https://geo.api.gouv.fr/communes"
SESSION_HTTP = creer_session_http()

ALIASES_COMMUNES = {
    "saint denis du pin": "Essouvert",
    "mortain": "Mortain-Bocage",
    "conde sur l escaut": "Condé-sur-l'Escaut",
}


def normaliser_nom(texte):
    if not texte:
        return ""

    texte = unicodedata.normalize("NFKD", str(texte).strip())

    texte = "".join(
        c
        for c in texte
        if not unicodedata.combining(c)
    )

    texte = texte.lower()
    texte = re.sub(r"[^a-z0-9]+", " ", texte)

    return re.sub(
        r"\s+",
        " ",
        texte,
    ).strip()


def simplifier_arrondissement(ville):
    """
    Exemples :
    Paris 12Eme Ardt -> Paris
    Lyon 3Eme Ardt -> Lyon
    Marseille 8Eme Ardt -> Marseille
    """

    if not ville:
        return ville

    nom = normaliser_nom(ville)

    for grande_ville in (
        "paris",
        "lyon",
        "marseille",
    ):
        motif = (
            rf"^{grande_ville}\s+\d{{1,2}}"
            r"(?:er|e|eme)?"
            r"(?:\s+(?:arrondissement|ardt))?$"
        )

        if re.fullmatch(
            motif,
            nom,
        ):
            return grande_ville.title()

    return ville


def analyser_localisation(localisation):
    if not localisation:
        return None, None

    texte = str(
        localisation
    ).strip()

    match = re.match(
        r"^\s*(.+?)\s*\((\d{2,3}|2A|2B)\)\s*$",
        texte,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            match.group(1).strip(),
            match.group(2).upper().strip(),
        )

    return (
        texte,
        None,
    )


def appliquer_alias(ville):
    if not ville:
        return ville

    ville = simplifier_arrondissement(
        ville
    )

    return ALIASES_COMMUNES.get(
        normaliser_nom(ville),
        ville,
    )


def calculer_distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    rayon_terre = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return rayon_terre * c


@lru_cache(maxsize=1000)
def rechercher_communes_api(
    nom_commune,
    departement=None,
):
    if not nom_commune:
        return []

    params = {
        "nom":
            nom_commune,

        "fields":
            "nom,code,centre,departement",

        "format":
            "json",

        "geometry":
            "centre",
    }

    if departement:
        params[
            "codeDepartement"
        ] = str(
            departement
        )

    try:
        reponse = SESSION_HTTP.get(
            API_COMMUNES,
            params=params,
            timeout=10,
        )

        reponse.raise_for_status()

        donnees = reponse.json()

    except (
        requests.RequestException,
        ValueError,
    ) as erreur:

        print(
            f"⚠️ Géolocalisation impossible pour "
            f"{nom_commune} : {erreur}"
        )

        return []

    if not isinstance(
        donnees,
        list,
    ):
        return []

    resultats = []

    for commune in donnees:
        centre = (
            commune.get("centre")
            or {}
        )

        coordonnees = centre.get(
            "coordinates"
        )

        if (
            not coordonnees
            or
            len(coordonnees) < 2
        ):
            continue

        departement_info = (
            commune.get(
                "departement"
            )
            or {}
        )

        resultats.append(
            {
                "nom":
                    commune.get(
                        "nom",
                        nom_commune,
                    ),

                "code":
                    commune.get(
                        "code"
                    ),

                "departement":
                    departement_info.get(
                        "code"
                    ),

                "latitude":
                    coordonnees[1],

                "longitude":
                    coordonnees[0],
            }
        )

    return resultats


def rechercher_communes_exactes(
    ville,
    departement=None,
):
    if not ville:
        return []

    ville_recherchee = appliquer_alias(
        ville
    )

    resultats = rechercher_communes_api(
        ville_recherchee,
        departement,
    )

    nom_exact = normaliser_nom(
        ville_recherchee
    )

    return [
        commune
        for commune in resultats
        if normaliser_nom(
            commune.get("nom")
        )
        == nom_exact
    ]


def choisir_commune_plus_proche(
    communes,
    origine=None,
):
    if not communes:
        return None

    if (
        len(communes) == 1
        or
        origine is None
    ):
        return communes[0]

    return min(
        communes,
        key=lambda commune: calculer_distance_km(
            origine["latitude"],
            origine["longitude"],
            commune["latitude"],
            commune["longitude"],
        ),
    )


def obtenir_coordonnees_commune(
    ville,
    departement=None,
    origine=None,
):
    communes = rechercher_communes_exactes(
        ville,
        departement,
    )

    return choisir_commune_plus_proche(
        communes,
        origine,
    )


def filtrer_par_distance(
    annonces,
    ville_origine,
    rayon_km,
):
    print()
    print(
        f"📍 Filtre géographique : "
        f"{rayon_km} km autour de "
        f"{ville_origine}"
    )

    origine = obtenir_coordonnees_commune(
        ville_origine
    )

    if origine is None:
        print(
            "⚠️ Ville d'origine introuvable."
        )

        print(
            "⛔ Scan local annulé : "
            "aucune annonce n'est transmise "
            "à l'analyse."
        )

        return []

    annonces_dans_rayon = []

    hors_rayon = 0
    inconnues = 0
    homonymes_resolus = 0
    aliases_utilises = 0

    for annonce in annonces:
        localisation = getattr(
            annonce,
            "localisation",
            None,
        )

        (
            ville,
            departement,
        ) = analyser_localisation(
            localisation
        )

        if not ville:
            inconnues += 1

            print(
                "❓ Localisation absente "
                "→ rejetée du radar local"
            )

            continue

        ville_corrigee = appliquer_alias(
            ville
        )

        alias_utilise = (
            normaliser_nom(ville)
            !=
            normaliser_nom(
                ville_corrigee
            )
        )

        communes = rechercher_communes_exactes(
            ville_corrigee,
            departement,
        )

        if not communes:
            inconnues += 1

            print(
                f"❓ {localisation} : "
                "commune exacte introuvable "
                "→ rejetée du radar local"
            )

            continue

        if len(communes) > 1:
            homonymes_resolus += 1

        commune = choisir_commune_plus_proche(
            communes,
            origine,
        )

        if commune is None:
            inconnues += 1

            print(
                f"❓ {localisation} : "
                "coordonnées introuvables "
                "→ rejetée du radar local"
            )

            continue

        if alias_utilise:
            aliases_utilises += 1

        distance = calculer_distance_km(
            origine["latitude"],
            origine["longitude"],
            commune["latitude"],
            commune["longitude"],
        )

        annonce.distance_km = round(
            distance,
            1,
        )

        suffixe = ""

        if alias_utilise:
            suffixe = (
                f" → {commune['nom']}"
            )

            if commune.get(
                "departement"
            ):
                suffixe += (
                    f" ({commune['departement']})"
                )

        elif len(communes) > 1:
            suffixe = (
                f" → homonyme choisi : "
                f"{commune['nom']}"
            )

            if commune.get(
                "departement"
            ):
                suffixe += (
                    f" ({commune['departement']})"
                )

        if distance <= rayon_km:
            annonces_dans_rayon.append(
                annonce
            )

            print(
                f"✅ {localisation}{suffixe} : "
                f"{annonce.distance_km} km"
            )

        else:
            hors_rayon += 1

            print(
                f"❌ {localisation}{suffixe} : "
                f"{annonce.distance_km} km "
                "→ hors rayon"
            )

    print()
    print(
        f"🗺️ Filtre géographique : "
        f"{len(annonces)} → "
        f"{len(annonces_dans_rayon)} annonces"
    )

    print(
        "   ❌ Hors rayon :",
        hors_rayon,
    )

    print(
        "   ❓ Localisations inconnues rejetées :",
        inconnues,
    )

    print(
        "   🧭 Homonymes exacts résolus :",
        homonymes_resolus,
    )

    print(
        "   🏘️ Anciens noms / variantes résolus :",
        aliases_utilises,
    )

    return annonces_dans_rayon
