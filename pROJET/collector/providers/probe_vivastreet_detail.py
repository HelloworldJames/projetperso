import html
import json
import re
import time

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests


# ============================================================
# CONFIGURATION
# ============================================================

TIMEOUT = 20
PAUSE = 1.5

FICHIER_RESULTATS = Path(
    "data/probe_vivastreet_detail.json"
)

URLS_TEST = [

    # COMPOSANT
    (
        "https://www.vivastreet.com/"
        "achat-vente-informatique/eybens-38320/"
        "nvidia-rtx-3050-6go/341967230"
    ),

    # PORTABLE GAMING
    (
        "https://www.vivastreet.com/"
        "achat-vente-informatique/lyon-69001/"
        "laptop-asus-tuf-gaming-a17/347897046"
    ),

    # PC COMPLET
    (
        "https://www.vivastreet.com/"
        "achat-vente-informatique/houplin-ancoisne-59263/"
        "hp-prodesk-600-g4-sff--i5---ssd-256-go---hdd-500-go-16-go-wi/"
        "346464136"
    ),

]


# ============================================================
# OUTILS TEXTE
# ============================================================

def nettoyer_texte(valeur):

    if valeur is None:
        return None

    valeur = html.unescape(
        str(valeur)
    )

    valeur = re.sub(
        r"<[^>]+>",
        " ",
        valeur,
    )

    valeur = re.sub(
        r"\s+",
        " ",
        valeur,
    )

    valeur = valeur.strip()

    return valeur or None


# ============================================================
# IDENTIFIANT
# ============================================================

def extraire_identifiant(url):

    chemin = urlparse(
        url
    ).path.rstrip("/")

    match = re.search(
        r"/(\d+)$",
        chemin,
    )

    if match:

        return match.group(1)

    return None


# ============================================================
# META HTML
# ============================================================

def extraire_meta(
    html_source,
    nom,
):

    motifs = [

        rf'<meta[^>]+property=["\']{re.escape(nom)}["\'][^>]+content=["\']([^"\']*)',

        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']{re.escape(nom)}["\']',

        rf'<meta[^>]+name=["\']{re.escape(nom)}["\'][^>]+content=["\']([^"\']*)',

        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(nom)}["\']',

    ]


    for motif in motifs:

        match = re.search(
            motif,
            html_source,
            flags=re.IGNORECASE,
        )

        if match:

            return nettoyer_texte(
                match.group(1)
            )

    return None


# ============================================================
# TITLE HTML
# ============================================================

def extraire_title_html(
    html_source
):

    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html_source,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )

    if not match:

        return None

    return nettoyer_texte(
        match.group(1)
    )


# ============================================================
# JSON-LD
# ============================================================

def extraire_json_ld(
    html_source
):

    scripts = re.findall(
        (
            r'<script[^>]+'
            r'type=["\']application/ld\+json["\']'
            r'[^>]*>'
            r'(.*?)'
            r'</script>'
        ),
        html_source,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )


    resultats = []


    for script in scripts:

        contenu = html.unescape(
            script.strip()
        )

        try:

            donnees = json.loads(
                contenu
            )

        except json.JSONDecodeError:

            continue

        resultats.append(
            donnees
        )


    return resultats


# ============================================================
# PARCOURS JSON
# ============================================================

def chercher_valeurs(
    objet,
    cles_recherchees,
):

    resultats = []


    if isinstance(
        objet,
        dict,
    ):

        for cle, valeur in objet.items():

            if (
                str(cle).lower()
                in cles_recherchees
            ):

                resultats.append(
                    valeur
                )


            resultats.extend(
                chercher_valeurs(
                    valeur,
                    cles_recherchees,
                )
            )


    elif isinstance(
        objet,
        list,
    ):

        for element in objet:

            resultats.extend(
                chercher_valeurs(
                    element,
                    cles_recherchees,
                )
            )


    return resultats


def premiere_valeur_simple(
    objets,
    cles,
):

    cles = {
        cle.lower()
        for cle in cles
    }


    for objet in objets:

        valeurs = chercher_valeurs(
            objet,
            cles,
        )


        for valeur in valeurs:

            if isinstance(
                valeur,
                (
                    str,
                    int,
                    float,
                ),
            ):

                valeur = nettoyer_texte(
                    valeur
                )

                if valeur:

                    return valeur


    return None


# ============================================================
# PRIX
# ============================================================

def convertir_prix(
    valeur
):

    if valeur is None:
        return None


    texte = str(
        valeur
    )


    texte = (
        texte
        .replace(
            "\u00a0",
            " "
        )
        .replace(
            ",",
            "."
        )
    )


    match = re.search(
        r"(\d+(?:\.\d{1,2})?)",
        texte,
    )


    if not match:

        return None


    try:

        prix = float(
            match.group(1)
        )

    except ValueError:

        return None


    if (
        prix <= 0
        or
        prix > 100_000
    ):

        return None


    if prix.is_integer():

        return int(
            prix
        )


    return round(
        prix,
        2,
    )


def extraire_prix(
    html_source,
    json_ld,
):

    # --------------------------------------------------------
    # 1. JSON-LD
    # --------------------------------------------------------

    valeur_json = premiere_valeur_simple(
        json_ld,
        {
            "price",
            "lowPrice",
            "highPrice",
        },
    )


    prix = convertir_prix(
        valeur_json
    )


    if prix is not None:

        return prix, "JSON-LD"


    # --------------------------------------------------------
    # 2. META PRODUIT
    # --------------------------------------------------------

    for nom_meta in (

        "product:price:amount",

        "og:price:amount",

    ):

        valeur = extraire_meta(
            html_source,
            nom_meta,
        )


        prix = convertir_prix(
            valeur
        )


        if prix is not None:

            return prix, (
                f"META {nom_meta}"
            )


    # --------------------------------------------------------
    # 3. TEXTE HTML
    # --------------------------------------------------------

    texte = html.unescape(
        html_source
    )


    motifs = [

        r"(\d{1,5}(?:[.,]\d{1,2})?)\s*(?:€|EUR)",

        r"(?:€|EUR)\s*(\d{1,5}(?:[.,]\d{1,2})?)",

    ]


    for motif in motifs:

        matches = re.findall(
            motif,
            texte,
            flags=re.IGNORECASE,
        )


        for valeur in matches:

            prix = convertir_prix(
                valeur
            )


            if prix is not None:

                return prix, "HTML"


    return None, None


# ============================================================
# LOCALISATION DEPUIS URL
# ============================================================

def localisation_depuis_url(
    url
):

    chemin = urlparse(
        url
    ).path


    match = re.search(
        r"/achat-vente-informatique/"
        r"([^/]+)-(\d{5})/",
        chemin,
        flags=re.IGNORECASE,
    )


    if not match:

        return None, None


    ville_slug = match.group(
        1
    )

    code_postal = match.group(
        2
    )


    ville = (
        ville_slug
        .replace(
            "-",
            " "
        )
        .strip()
        .title()
    )


    return (
        ville,
        code_postal,
    )


# ============================================================
# LOCALISATION JSON
# ============================================================

def extraire_localisation(
    url,
    json_ld,
):

    ville_json = premiere_valeur_simple(
        json_ld,
        {
            "addressLocality",
        },
    )


    code_json = premiere_valeur_simple(
        json_ld,
        {
            "postalCode",
        },
    )


    if ville_json:

        return (
            ville_json,
            code_json,
            "JSON-LD",
        )


    ville_url, code_url = (
        localisation_depuis_url(
            url
        )
    )


    if ville_url:

        return (
            ville_url,
            code_url,
            "URL",
        )


    return (
        None,
        None,
        None,
    )


# ============================================================
# DESCRIPTION
# ============================================================

def extraire_description(
    html_source,
    json_ld,
):

    description_json = (
        premiere_valeur_simple(
            json_ld,
            {
                "description",
            },
        )
    )


    if description_json:

        return (
            description_json,
            "JSON-LD",
        )


    for meta in (

        "og:description",

        "description",

    ):

        valeur = extraire_meta(
            html_source,
            meta,
        )


        if valeur:

            return (
                valeur,
                f"META {meta}",
            )


    return (
        None,
        None,
    )


# ============================================================
# TITRE ANNONCE
# ============================================================

def extraire_titre(
    html_source,
    json_ld,
):

    titre_json = (
        premiere_valeur_simple(
            json_ld,
            {
                "name",
                "headline",
            },
        )
    )


    if titre_json:

        return (
            titre_json,
            "JSON-LD",
        )


    og_title = extraire_meta(
        html_source,
        "og:title",
    )


    if og_title:

        return (
            og_title,
            "META og:title",
        )


    titre_html = (
        extraire_title_html(
            html_source
        )
    )


    if titre_html:

        return (
            titre_html,
            "TITLE HTML",
        )


    return (
        None,
        None,
    )


# ============================================================
# TYPES JSON-LD
# ============================================================

def extraire_types_json(
    json_ld
):

    valeurs = []


    for objet in json_ld:

        types = chercher_valeurs(
            objet,
            {
                "@type",
            },
        )


        for valeur in types:

            if isinstance(
                valeur,
                list,
            ):

                for element in valeur:

                    element = str(
                        element
                    )

                    if element not in valeurs:

                        valeurs.append(
                            element
                        )

            else:

                valeur = str(
                    valeur
                )

                if valeur not in valeurs:

                    valeurs.append(
                        valeur
                    )


    return valeurs


# ============================================================
# ANALYSE D'UNE ANNONCE
# ============================================================

def analyser_annonce(
    session,
    url,
):

    print()
    print("=" * 70)
    print("🔬 ANNONCE VIVASTREET")
    print("=" * 70)

    print()
    print(
        "🌐",
        url,
    )


    try:

        reponse = session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return {
            "url": url,
            "erreur": str(
                erreur
            ),
        }


    print(
        "HTTP :",
        reponse.status_code,
    )

    print(
        "Taille :",
        len(
            reponse.content
        ),
        "octets",
    )


    if reponse.status_code in {
        401,
        403,
        429,
    }:

        print(
            "⛔ Accès refusé ou limité."
        )

        return {
            "url": url,
            "statut_http": (
                reponse.status_code
            ),
        }


    if reponse.status_code != 200:

        print(
            "⚠️ Réponse HTTP inattendue."
        )

        return {
            "url": url,
            "statut_http": (
                reponse.status_code
            ),
        }


    html_source = reponse.text


    identifiant = (
        extraire_identifiant(
            reponse.url
        )
    )


    json_ld = (
        extraire_json_ld(
            html_source
        )
    )


    types_json = (
        extraire_types_json(
            json_ld
        )
    )


    titre, source_titre = (
        extraire_titre(
            html_source,
            json_ld,
        )
    )


    prix, source_prix = (
        extraire_prix(
            html_source,
            json_ld,
        )
    )


    description, source_description = (
        extraire_description(
            html_source,
            json_ld,
        )
    )


    (
        localisation,
        code_postal,
        source_localisation,
    ) = extraire_localisation(
        reponse.url,
        json_ld,
    )


    print()
    print(
        "🆔 Identifiant :",
        identifiant,
    )


    print()
    print(
        "📝 Titre :",
        titre,
    )

    print(
        "   Source :",
        source_titre,
    )


    print()
    print(
        "💶 Prix :",
        prix,
    )

    print(
        "   Source :",
        source_prix,
    )


    print()
    print(
        "📍 Localisation :",
        localisation,
    )

    print(
        "📮 Code postal :",
        code_postal,
    )

    print(
        "   Source :",
        source_localisation,
    )


    print()
    print(
        "📄 Description :"
    )


    if description:

        print(
            description[:500]
        )

    else:

        print(
            "❌ Non détectée"
        )


    print(
        "   Source :",
        source_description,
    )


    print()
    print(
        "🧩 JSON-LD valides :",
        len(
            json_ld
        ),
    )

    print(
        "🧩 Types JSON-LD :",
        types_json,
    )


    complet = all(
        (
            identifiant,
            titre,
            prix is not None,
            localisation,
            description,
        )
    )


    print()
    print(
        "🎯 DONNEES MINIMALES HUNTER :",
        (
            "✅ COMPLETES"
            if complet
            else
            "⚠️ INCOMPLETES"
        ),
    )


    return {

        "plateforme": (
            "Vivastreet"
        ),

        "identifiant": (
            identifiant
        ),

        "titre": titre,

        "prix": prix,

        "description": (
            description
        ),

        "localisation": (
            localisation
        ),

        "code_postal": (
            code_postal
        ),

        "url": (
            reponse.url
        ),

        "statut_http": (
            reponse.status_code
        ),

        "sources_extraction": {

            "titre": (
                source_titre
            ),

            "prix": (
                source_prix
            ),

            "description": (
                source_description
            ),

            "localisation": (
                source_localisation
            ),

        },

        "json_ld_types": (
            types_json
        ),

        "complet": complet,

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("#" * 70)
    print(
        "🧪 PC HUNTER — PROBE DETAIL VIVASTREET"
    )
    print("#" * 70)

    print()
    print(
        "3 annonces testées : "
        "composant, portable gaming et PC complet."
    )

    print(
        "Aucune donnée vendeur n'est collectée."
    )

    print(
        "Aucun compte, cookie privé, proxy "
        "ou contournement."
    )


    session = requests.Session()


    session.headers.update(
        {

            "User-Agent": (
                "PC-Hunter-Prototype/0.1 "
                "(marketplace compatibility research)"
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "fr-FR,fr;q=0.9"
            ),

        }
    )


    resultats = []


    for position, url in enumerate(
        URLS_TEST,
        start=1,
    ):

        resultat = analyser_annonce(
            session,
            url,
        )


        resultats.append(
            resultat
        )


        if position < len(
            URLS_TEST
        ):

            time.sleep(
                PAUSE
            )


    # ========================================================
    # SAUVEGARDE
    # ========================================================

    FICHIER_RESULTATS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    donnees = {

        "date_probe": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),

        "nombre_tests": len(
            resultats
        ),

        "resultats": (
            resultats
        ),

    }


    fichier_temporaire = (
        FICHIER_RESULTATS
        .with_suffix(
            ".tmp"
        )
    )


    with fichier_temporaire.open(
        "w",
        encoding="utf-8",
    ) as fichier:

        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2,
        )


    fichier_temporaire.replace(
        FICHIER_RESULTATS
    )


    print()
    print()
    print("#" * 70)
    print("🏁 RESULTAT FINAL")
    print("#" * 70)
    print()


    complets = sum(
        1
        for resultat in resultats
        if resultat.get(
            "complet"
        )
    )


    print(
        "Annonces complètes :",
        f"{complets}/{len(resultats)}",
    )


    print(
        "💾 Rapport :",
        FICHIER_RESULTATS,
    )


    if complets == len(
        resultats
    ):

        print()
        print(
            "🟢 VIVASTREET EST PRET "
            "POUR UN VRAI PROVIDER."
        )

    else:

        print()
        print(
            "🟡 Certaines données doivent encore "
            "être extraites autrement."
        )


if __name__ == "__main__":

    main()