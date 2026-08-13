import json
import re
import time

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests


# ============================================================
# CONFIGURATION
# ============================================================

USER_AGENT = (
    "PC-Hunter-Prototype/0.1 "
    "(marketplace compatibility research)"
)

TIMEOUT = 20

PAUSE_ENTRE_SITES = 1.0

FICHIER_RESULTATS = Path(
    "data/probe_sources_resultats.json"
)


# ============================================================
# MODELE SOURCE
# ============================================================

@dataclass
class SourceProbe:

    nom: str
    url: str
    type_source: str


# ============================================================
# SOURCES A TESTER
# ============================================================

SOURCES = [

    SourceProbe(
        nom="ParuVendu",
        url=(
            "https://www.paruvendu.fr/"
            "annonces/ordinateur-portable/"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="Vivastreet",
        url=(
            "https://www.vivastreet.com/"
            "achat-vente-informatique/fr"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="TopAnnonces",
        url=(
            "https://www.topannonces.fr/"
            "vente-occasion-informatique/"
            "annonces/837406/"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="Marche.fr",
        url=(
            "https://www.marche.fr/"
            "informatique-hardware/"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="AnnoncesEnFrance",
        url=(
            "https://annoncesenfrance.fr/"
            "annonces/electronique/"
            "ordinateurs-portables"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="Locanto",
        url=(
            "https://www.locanto.fr/"
            "g/Ordinateurs-logiciels/403/"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="Wallapop",
        url=(
            "https://fr.wallapop.com/"
        ),
        type_source="marketplace",
    ),

    SourceProbe(
        nom="Vinted",
        url=(
            "https://www.vinted.fr/"
            "catalog/3564-computers-and-accessories"
        ),
        type_source="marketplace",
    ),

    SourceProbe(
        nom="Rakuten",
        url=(
            "https://fr.shopping.rakuten.com/"
            "nav/Informatique_Ordinateur-portable"
        ),
        type_source="marketplace",
    ),

    SourceProbe(
        nom="eBay",
        url=(
            "https://www.ebay.fr/b/"
            "Ordinateurs-portables-et-netbooks/"
            "177/bn_16550152"
        ),
        type_source="marketplace",
    ),

    SourceProbe(
        nom="Leboncoin",
        url=(
            "https://www.leboncoin.fr/"
            "ck/ordinateurs/pc-gamer"
        ),
        type_source="petites_annonces",
    ),

    SourceProbe(
        nom="Facebook Marketplace",
        url=(
            "https://www.facebook.com/"
            "marketplace/category/computers/"
        ),
        type_source="marketplace",
    ),

    SourceProbe(
        nom="Amazon Seconde main",
        url=(
            "https://www.amazon.fr/"
            "Seconde-main/b/?node=3581943031"
        ),
        type_source="marketplace",
    ),

]


# ============================================================
# OUTILS
# ============================================================

def extraire_titre(html):

    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )

    if not match:
        return None

    titre = re.sub(
        r"\s+",
        " ",
        match.group(1),
    )

    return titre.strip()


def compter_liens(html):

    liens = re.findall(
        r"""href\s*=\s*["']([^"']+)["']""",
        html,
        flags=re.IGNORECASE,
    )

    return len(
        set(liens)
    )


def detecter_indices(html):

    texte = html.lower()

    indices = {

        "ordinateur": (
            "ordinateur" in texte
        ),

        "pc": (
            re.search(
                r"\bpc\b",
                texte,
            )
            is not None
        ),

        "prix": (
            "prix" in texte
            or
            "€" in html
        ),

        "occasion": (
            "occasion" in texte
        ),

        "livraison": (
            "livraison" in texte
        ),

        "rtx": (
            "rtx" in texte
        ),

        "ryzen": (
            "ryzen" in texte
        ),

        "ssd": (
            "ssd" in texte
        ),

        "localisation": any(
            mot in texte
            for mot in (
                "localisation",
                "située à",
                "situee a",
                "ville",
                "location",
            )
        ),

    }

    return indices


def detecter_structure(html):

    texte = html.lower()

    return {

        "json_ld": (
            "application/ld+json"
            in texte
        ),

        "next_data": (
            "__next_data__"
            in texte
        ),

        "nuxt": (
            "__nuxt__"
            in texte
        ),

        "json_api": any(
            indice in texte
            for indice in (
                '"price"',
                '"title"',
                '"location"',
                '"items"',
                '"products"',
            )
        ),

    }


def detecter_protection(html):

    texte = html.lower()

    marqueurs = [

        "access denied",

        "forbidden",

        "captcha",

        "verify you are human",

        "are you a human",

        "unusual traffic",

        "automated requests",

        "bot detection",

        "cloudflare",

        "challenge-platform",

    ]

    trouves = []

    for marqueur in marqueurs:

        if marqueur in texte:

            trouves.append(
                marqueur
            )

    return trouves


def calculer_score(
    statut,
    taille,
    indices,
    structures,
    nombre_liens,
    protections,
):

    if statut in {
        401,
        403,
        429,
    }:

        return 0


    score = 0


    if statut == 200:

        score += 35


    if taille >= 10_000:

        score += 10


    if taille >= 50_000:

        score += 5


    if indices.get(
        "ordinateur"
    ):

        score += 5


    if indices.get(
        "pc"
    ):

        score += 5


    if indices.get(
        "prix"
    ):

        score += 10


    if indices.get(
        "occasion"
    ):

        score += 5


    if indices.get(
        "localisation"
    ):

        score += 5


    if indices.get(
        "livraison"
    ):

        score += 5


    if any(
        structures.values()
    ):

        score += 10


    if nombre_liens >= 20:

        score += 5


    if protections:

        score -= 30


    return max(
        0,
        min(
            score,
            100,
        ),
    )


def determiner_statut(
    statut_http,
    taille,
    score,
    protections,
):

    if statut_http in {
        401,
        403,
        429,
    }:

        return "🔒 BLOQUE"


    if statut_http != 200:

        return "⚠️ A_REVOIR"


    if protections:

        return "🛡️ PROTEGE"


    if taille < 5_000:

        return "🟡 PAGE_MINCE_JS"


    if score >= 65:

        return "🟢 CANDIDAT_DIRECT"


    if score >= 45:

        return "🟠 A_ETUDIER"


    return "🔴 FAIBLE"


# ============================================================
# PROBE D'UNE SOURCE
# ============================================================

def tester_source(
    session,
    source,
):

    print()
    print("=" * 65)
    print(
        f"🔎 {source.nom}"
    )
    print("=" * 65)

    print(
        "🌐",
        source.url,
    )


    try:

        reponse = session.get(
            source.url,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return {

            "nom": source.nom,

            "url": source.url,

            "type_source": (
                source.type_source
            ),

            "statut_http": None,

            "statut_probe": (
                "❌ ERREUR_RESEAU"
            ),

            "erreur": str(
                erreur
            ),

        }


    statut = reponse.status_code

    taille = len(
        reponse.content
    )

    content_type = (
        reponse.headers.get(
            "Content-Type",
            "",
        )
    )


    print(
        "HTTP :",
        statut,
    )

    print(
        "URL finale :",
        reponse.url,
    )

    print(
        "Taille :",
        taille,
        "octets",
    )

    print(
        "Content-Type :",
        content_type,
    )


    # --------------------------------------------------------
    # REFUS / RATE LIMIT
    # --------------------------------------------------------

    if statut in {
        401,
        403,
        429,
    }:

        print()
        print(
            "⛔ Accès automatisé refusé "
            "ou limité."
        )

        print(
            "➡️ Aucun retry ni contournement."
        )

        return {

            "nom": source.nom,

            "url": source.url,

            "url_finale": (
                reponse.url
            ),

            "type_source": (
                source.type_source
            ),

            "statut_http": statut,

            "taille": taille,

            "content_type": (
                content_type
            ),

            "score": 0,

            "statut_probe": (
                "🔒 BLOQUE"
            ),

        }


    html = reponse.text


    titre = extraire_titre(
        html
    )


    liens = compter_liens(
        html
    )


    indices = detecter_indices(
        html
    )


    structures = detecter_structure(
        html
    )


    protections = detecter_protection(
        html
    )


    score = calculer_score(
        statut=statut,
        taille=taille,
        indices=indices,
        structures=structures,
        nombre_liens=liens,
        protections=protections,
    )


    statut_probe = determiner_statut(
        statut_http=statut,
        taille=taille,
        score=score,
        protections=protections,
    )


    print()

    if titre:

        print(
            "📝",
            titre[:120],
        )


    print(
        "🔗 Liens HTML :",
        liens,
    )


    print()

    print(
        "Ordinateur :",
        "✅"
        if indices["ordinateur"]
        else "❌",
    )

    print(
        "PC         :",
        "✅"
        if indices["pc"]
        else "❌",
    )

    print(
        "Prix       :",
        "✅"
        if indices["prix"]
        else "❌",
    )

    print(
        "Occasion   :",
        "✅"
        if indices["occasion"]
        else "❌",
    )

    print(
        "Localité   :",
        "✅"
        if indices["localisation"]
        else "❌",
    )

    print(
        "Livraison  :",
        "✅"
        if indices["livraison"]
        else "❌",
    )


    print()

    print(
        "JSON-LD    :",
        "✅"
        if structures["json_ld"]
        else "❌",
    )

    print(
        "NEXT_DATA  :",
        "✅"
        if structures["next_data"]
        else "❌",
    )

    print(
        "NUXT       :",
        "✅"
        if structures["nuxt"]
        else "❌",
    )

    print(
        "JSON potentiel :",
        "✅"
        if structures["json_api"]
        else "❌",
    )


    if protections:

        print()

        print(
            "🛡️ Marqueurs protection :",
            ", ".join(
                protections
            ),
        )


    print()

    print(
        "📊 Score probe :",
        f"{score}/100",
    )

    print(
        "🎯 Verdict :",
        statut_probe,
    )


    return {

        "nom": source.nom,

        "url": source.url,

        "url_finale": (
            reponse.url
        ),

        "type_source": (
            source.type_source
        ),

        "statut_http": statut,

        "taille": taille,

        "content_type": (
            content_type
        ),

        "titre": titre,

        "nombre_liens": liens,

        "indices": indices,

        "structures": structures,

        "protections": protections,

        "score": score,

        "statut_probe": (
            statut_probe
        ),

    }


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print()
    print("#" * 65)
    print("🌍 PC HUNTER — PROBE GEANT DES MARKETPLACES")
    print("#" * 65)

    print()

    print(
        "Sources testées :",
        len(SOURCES),
    )

    print(
        "Une seule requête normale "
        "par source."
    )

    print(
        "Aucun proxy, aucun compte, "
        "aucun cookie privé."
    )

    print()


    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,

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


    for position, source in enumerate(
        SOURCES,
        start=1,
    ):

        print()
        print(
            f"[{position}/{len(SOURCES)}]"
        )


        resultat = tester_source(
            session=session,
            source=source,
        )


        resultats.append(
            resultat
        )


        if position < len(
            SOURCES
        ):

            time.sleep(
                PAUSE_ENTRE_SITES
            )


    # ========================================================
    # CLASSEMENT
    # ========================================================

    classement = sorted(
        resultats,
        key=lambda element: (
            element.get(
                "score",
                0,
            )
        ),
        reverse=True,
    )


    print()
    print()
    print("#" * 65)
    print("🏆 CLASSEMENT DES SOURCES")
    print("#" * 65)
    print()


    for position, resultat in enumerate(
        classement,
        start=1,
    ):

        print(
            f"{position:02d}. "
            f"{resultat['nom']:<22} "
            f"{resultat.get('score', 0):>3}/100 "
            f"{resultat.get('statut_probe', '?')}"
        )


    # ========================================================
    # SAUVEGARDE JSON
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

        "nombre_sources": (
            len(resultats)
        ),

        "resultats": classement,

    }


    with FICHIER_RESULTATS.open(
        "w",
        encoding="utf-8",
    ) as fichier:

        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2,
        )


    print()

    print(
        "💾 Résultats enregistrés :",
        FICHIER_RESULTATS,
    )

    print()

    print(
        "✅ Probe géant terminé."
    )


if __name__ == "__main__":

    main()