import json
import re
import time

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


# ============================================================
# CONFIGURATION
# ============================================================

TIMEOUT = 20

PAUSE_ENTRE_SOURCES = 1.5

USER_AGENT = (
    "PC-Hunter-Prototype/0.1 "
    "(marketplace compatibility research)"
)

FICHIER_RESULTATS = Path(
    "data/probe_vague_2_resultats.json"
)


# ============================================================
# MODELE
# ============================================================

@dataclass
class Source:
    nom: str
    url: str
    motifs_annonces: tuple


# ============================================================
# SOURCES
# ============================================================

SOURCES = [

    Source(
        nom="Vinted",
        url=(
            "https://www.vinted.fr/"
            "catalog/3564-computers-and-accessories"
        ),
        motifs_annonces=(
            r"/items/\d+",
        ),
    ),

    Source(
        nom="Vivastreet",
        url=(
            "https://www.vivastreet.com/"
            "achat-vente-informatique/fr"
        ),
        motifs_annonces=(
            r"/.+/\d+",
            r"/.+-\d+",
        ),
    ),

    Source(
        nom="AnnoncesEnFrance",
        url=(
            "https://annoncesenfrance.fr/"
            "annonces/electronique/"
            "ordinateurs-portables"
        ),
        motifs_annonces=(
            r"/annonce/",
            r"/ordinateurs/",
        ),
    ),

    Source(
        nom="Rakuten",
        url=(
            "https://fr.shopping.rakuten.com/"
            "nav/Informatique_Ordinateur-portable"
        ),
        motifs_annonces=(
            r"/offer/buy/",
            r"/mfp/",
            r"/product/",
        ),
    ),

    Source(
        nom="Facebook Marketplace",
        url=(
            "https://www.facebook.com/"
            "marketplace/category/computers/"
        ),
        motifs_annonces=(
            r"/marketplace/item/\d+",
        ),
    ),

]


# ============================================================
# PARSEUR HTML
# ============================================================

class ParseurHTML(HTMLParser):

    def __init__(self):

        super().__init__()

        self.liens = []

        self.scripts = []

        self.script_actif = False

        self.buffer_script = []


    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        attributs = dict(
            attrs
        )


        if tag == "a":

            href = attributs.get(
                "href"
            )

            if href:

                self.liens.append(
                    href
                )


        if tag == "script":

            self.script_actif = True

            self.buffer_script = []


    def handle_data(
        self,
        data,
    ):

        if self.script_actif:

            self.buffer_script.append(
                data
            )


    def handle_endtag(
        self,
        tag,
    ):

        if (
            tag == "script"
            and
            self.script_actif
        ):

            contenu = "".join(
                self.buffer_script
            ).strip()

            if contenu:

                self.scripts.append(
                    contenu
                )

            self.script_actif = False

            self.buffer_script = []


# ============================================================
# OUTILS
# ============================================================

def extraire_titre(
    html
):

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


def normaliser_domaine(
    url
):

    try:

        domaine = (
            urlparse(
                url
            )
            .netloc
            .lower()
        )

        return domaine.replace(
            "www.",
            ""
        )

    except Exception:

        return ""


def meme_domaine(
    url_a,
    url_b,
):

    domaine_a = normaliser_domaine(
        url_a
    )

    domaine_b = normaliser_domaine(
        url_b
    )

    if not domaine_a or not domaine_b:

        return False


    return (
        domaine_a == domaine_b
        or
        domaine_a.endswith(
            "." + domaine_b
        )
        or
        domaine_b.endswith(
            "." + domaine_a
        )
    )


def nettoyer_url(
    base,
    lien
):

    if not lien:

        return None


    if lien.startswith(
        (
            "#",
            "javascript:",
            "mailto:",
            "tel:",
        )
    ):

        return None


    url = urljoin(
        base,
        lien,
    )


    url = (
        url
        .replace(
            "\\u002F",
            "/"
        )
        .replace(
            "\\/",
            "/"
        )
    )


    return url.split(
        "#"
    )[0]


def extraire_urls_annonces(
    source,
    liens,
):

    resultats = []

    deja_vus = set()


    for lien in liens:

        url = nettoyer_url(
            source.url,
            lien,
        )


        if not url:

            continue


        if not meme_domaine(
            source.url,
            url,
        ):

            continue


        chemin = (
            urlparse(
                url
            )
            .path
        )


        correspond = False


        for motif in source.motifs_annonces:

            if re.search(
                motif,
                chemin,
                flags=re.IGNORECASE,
            ):

                correspond = True
                break


        if not correspond:

            continue


        if url in deja_vus:

            continue


        deja_vus.add(
            url
        )

        resultats.append(
            url
        )


    return resultats


def extraire_prix(
    html
):

    motifs = [

        r"(\d{1,5}(?:[.,]\d{1,2})?)\s*€",

        r"€\s*(\d{1,5}(?:[.,]\d{1,2})?)",

    ]


    valeurs = []

    deja_vus = set()


    for motif in motifs:

        matches = re.findall(
            motif,
            html,
            flags=re.IGNORECASE,
        )


        for valeur in matches:

            valeur = valeur.replace(
                ",",
                "."
            )


            try:

                prix = float(
                    valeur
                )

            except ValueError:

                continue


            if (
                prix <= 0
                or
                prix > 100_000
            ):

                continue


            if prix in deja_vus:

                continue


            deja_vus.add(
                prix
            )

            valeurs.append(
                prix
            )


    return valeurs


def extraire_codes_postaux(
    html
):

    matches = re.findall(
        r"\b(?:0[1-9]|[1-8]\d|9[0-5])\d{3}\b",
        html,
    )


    resultats = []

    deja_vus = set()


    for code in matches:

        if code in deja_vus:

            continue


        deja_vus.add(
            code
        )

        resultats.append(
            code
        )


    return resultats


def compter_signaux(
    html
):

    texte = html.lower()


    return {

        "pc": len(
            re.findall(
                r"\bpc\b",
                texte,
            )
        ),

        "ordinateur": texte.count(
            "ordinateur"
        ),

        "portable": texte.count(
            "portable"
        ),

        "gaming": texte.count(
            "gaming"
        ),

        "rtx": texte.count(
            "rtx"
        ),

        "gtx": texte.count(
            "gtx"
        ),

        "ryzen": texte.count(
            "ryzen"
        ),

        "intel": texte.count(
            "intel"
        ),

        "ssd": texte.count(
            "ssd"
        ),

        "livraison": texte.count(
            "livraison"
        ),

        "occasion": texte.count(
            "occasion"
        ),

    }


def detecter_structures(
    html
):

    texte = html.lower()


    return {

        "next_data": (
            "__next_data__"
            in texte
        ),

        "nuxt": (
            "__nuxt__"
            in texte
        ),

        "json_ld": (
            "application/ld+json"
            in texte
        ),

        "price_json": (
            '"price"'
            in texte
        ),

        "title_json": (
            '"title"'
            in texte
        ),

        "location_json": (
            '"location"'
            in texte
        ),

        "items_json": (
            '"items"'
            in texte
        ),

        "products_json": (
            '"products"'
            in texte
        ),

        "search_results": any(
            marqueur in texte
            for marqueur in (
                "searchresults",
                "search_results",
                "search-results",
            )
        ),

    }


def detecter_protections(
    html
):

    texte = html.lower()


    marqueurs = (

        "access denied",

        "forbidden",

        "captcha",

        "verify you are human",

        "are you human",

        "unusual traffic",

        "automated requests",

        "challenge-platform",

        "cloudflare",

        "bot detection",

    )


    trouves = []


    for marqueur in marqueurs:

        if marqueur in texte:

            trouves.append(
                marqueur
            )


    return trouves


def compter_json_probable(
    scripts
):

    nombre_json = 0

    tailles = []


    for script in scripts:

        script = script.strip()


        if not script:

            continue


        if not (
            script.startswith(
                "{"
            )
            or
            script.startswith(
                "["
            )
        ):

            continue


        try:

            json.loads(
                script
            )

        except json.JSONDecodeError:

            continue


        nombre_json += 1

        tailles.append(
            len(
                script
            )
        )


    return {
        "nombre": nombre_json,
        "tailles": tailles[:20],
    }


# ============================================================
# SCORE
# ============================================================

def calculer_score(
    statut,
    taille,
    urls,
    prix,
    codes_postaux,
    signaux,
    structures,
    protections,
):

    if statut in {
        401,
        403,
        429,
    }:

        return 0


    if statut != 200:

        return 0


    score = 20


    if taille >= 20_000:

        score += 5


    if len(
        urls
    ) >= 20:

        score += 25

    elif len(
        urls
    ) >= 5:

        score += 18

    elif urls:

        score += 8


    if len(
        prix
    ) >= 5:

        score += 15

    elif prix:

        score += 7


    if codes_postaux:

        score += 8


    signal_materiel = (

        signaux["pc"]
        +
        signaux["ordinateur"]
        +
        signaux["gaming"]
        +
        signaux["rtx"]
        +
        signaux["gtx"]
        +
        signaux["ryzen"]

    )


    if signal_materiel >= 20:

        score += 10

    elif signal_materiel:

        score += 5


    if (
        structures["price_json"]
        and
        structures["title_json"]
    ):

        score += 10


    elif any(
        structures.values()
    ):

        score += 5


    if signaux[
        "occasion"
    ]:

        score += 5


    if signaux[
        "livraison"
    ]:

        score += 2


    if protections:

        score -= 25


    return max(
        0,
        min(
            score,
            100,
        ),
    )


def determiner_verdict(
    statut,
    urls,
    structures,
    protections,
    score,
):

    if statut in {
        401,
        403,
        429,
    }:

        return (
            "🔒 BLOQUE"
        )


    if statut != 200:

        return (
            "⚠️ HTTP_INATTENDU"
        )


    if protections:

        return (
            "🛡️ PROTEGE"
        )


    if len(
        urls
    ) >= 5:

        return (
            "🟢 ANNONCES_DANS_HTML"
        )


    if (
        structures["price_json"]
        or
        structures["items_json"]
        or
        structures["products_json"]
    ):

        return (
            "🟡 DONNEES_JSON_POSSIBLES"
        )


    if (
        structures["next_data"]
        or
        structures["nuxt"]
    ):

        return (
            "🟠 APPLICATION_DYNAMIQUE"
        )


    if score >= 50:

        return (
            "🟠 A_ETUDIER"
        )


    return (
        "🔴 PAUVRE"
    )


# ============================================================
# TEST SOURCE
# ============================================================

def tester_source(
    session,
    source,
):

    print()
    print("=" * 70)
    print(
        f"🔎 {source.nom}"
    )
    print("=" * 70)

    print()

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

        print()

        print(
            "❌ Erreur réseau :",
            erreur,
        )


        return {

            "source": source.nom,

            "statut_http": None,

            "score": 0,

            "verdict": (
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


    print(
        "HTTP :",
        statut,
    )

    print(
        "Taille :",
        taille,
        "octets",
    )

    print(
        "URL finale :",
        reponse.url,
    )


    if statut in {
        401,
        403,
        429,
    }:

        print()

        print(
            "⛔ Accès refusé ou limité."
        )

        print(
            "➡️ Aucun contournement."
        )


        return {

            "source": source.nom,

            "url": source.url,

            "url_finale": reponse.url,

            "statut_http": statut,

            "taille": taille,

            "score": 0,

            "verdict": "🔒 BLOQUE",

        }


    if statut != 200:

        return {

            "source": source.nom,

            "url": source.url,

            "url_finale": reponse.url,

            "statut_http": statut,

            "taille": taille,

            "score": 0,

            "verdict": (
                "⚠️ HTTP_INATTENDU"
            ),

        }


    html = reponse.text


    parseur = ParseurHTML()


    try:

        parseur.feed(
            html
        )

    except Exception:

        pass


    titre = extraire_titre(
        html
    )


    urls_annonces = (
        extraire_urls_annonces(
            source,
            parseur.liens,
        )
    )


    prix = extraire_prix(
        html
    )


    codes_postaux = (
        extraire_codes_postaux(
            html
        )
    )


    signaux = compter_signaux(
        html
    )


    structures = detecter_structures(
        html
    )


    protections = detecter_protections(
        html
    )


    json_probable = (
        compter_json_probable(
            parseur.scripts
        )
    )


    score = calculer_score(
        statut=statut,
        taille=taille,
        urls=urls_annonces,
        prix=prix,
        codes_postaux=codes_postaux,
        signaux=signaux,
        structures=structures,
        protections=protections,
    )


    verdict = determiner_verdict(
        statut=statut,
        urls=urls_annonces,
        structures=structures,
        protections=protections,
        score=score,
    )


    print()

    print(
        "📝 Titre :",
        titre,
    )


    print()

    print(
        "🔗 Liens HTML :",
        len(
            parseur.liens
        ),
    )

    print(
        "📦 Annonces candidates :",
        len(
            urls_annonces
        ),
    )

    print(
        "💶 Prix détectés :",
        len(
            prix
        ),
    )

    print(
        "📍 Codes postaux :",
        len(
            codes_postaux
        ),
    )

    print(
        "🧩 Scripts JSON valides :",
        json_probable[
            "nombre"
        ],
    )


    print()

    print(
        "🧠 SIGNAUX"
    )


    for nom, valeur in signaux.items():

        print(
            f"   {nom:<12} : {valeur}"
        )


    print()

    print(
        "🧩 STRUCTURES"
    )


    for nom, valeur in structures.items():

        print(
            f"   {nom:<16} :",
            (
                "✅"
                if valeur
                else
                "❌"
            ),
        )


    if protections:

        print()

        print(
            "🛡️ Protections détectées :",
            ", ".join(
                protections
            ),
        )


    if urls_annonces:

        print()

        print(
            "🔎 EXEMPLES D'ANNONCES"
        )


        for position, url in enumerate(
            urls_annonces[:8],
            start=1,
        ):

            print(
                f"{position:02d}.",
                url,
            )


    print()

    print(
        "📊 Score :",
        f"{score}/100",
    )

    print(
        "🎯 Verdict :",
        verdict,
    )


    return {

        "source": source.nom,

        "url": source.url,

        "url_finale": reponse.url,

        "statut_http": statut,

        "taille": taille,

        "titre": titre,

        "liens_html": len(
            parseur.liens
        ),

        "annonces_candidates": len(
            urls_annonces
        ),

        "exemples_annonces": (
            urls_annonces[:15]
        ),

        "prix_detectes": (
            prix[:30]
        ),

        "codes_postaux": (
            codes_postaux[:30]
        ),

        "signaux": signaux,

        "structures": structures,

        "scripts_json": json_probable,

        "protections": protections,

        "score": score,

        "verdict": verdict,

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("#" * 70)
    print("🌊 PC HUNTER — PROBE VAGUE 2")
    print("#" * 70)

    print()

    print(
        "Sources :",
        len(
            SOURCES
        ),
    )

    print()

    print(
        "Vinted"
    )

    print(
        "Vivastreet"
    )

    print(
        "AnnoncesEnFrance"
    )

    print(
        "Rakuten"
    )

    print(
        "Facebook Marketplace"
    )

    print()

    print(
        "Une seule requête normale "
        "par plateforme."
    )

    print(
        "Aucun compte, cookie privé, "
        "proxy ou contournement."
    )


    session = requests.Session()


    session.headers.update(
        {

            "User-Agent": (
                USER_AGENT
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
                PAUSE_ENTRE_SOURCES
            )


    # ========================================================
    # CLASSEMENT
    # ========================================================

    classement = sorted(
        resultats,
        key=lambda resultat: (
            resultat.get(
                "score",
                0,
            )
        ),
        reverse=True,
    )


    print()
    print()
    print("#" * 70)
    print("🏆 CLASSEMENT VAGUE 2")
    print("#" * 70)
    print()


    for position, resultat in enumerate(
        classement,
        start=1,
    ):

        print(
            f"{position}. "
            f"{resultat['source']:<22} "
            f"{resultat.get('score', 0):>3}/100 "
            f"{resultat.get('verdict', '?')}"
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

        "nombre_sources": len(
            classement
        ),

        "resultats": classement,

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

    print(
        "💾 Rapport :",
        FICHIER_RESULTATS,
    )

    print()

    print(
        "✅ Vague 2 terminée."
    )


if __name__ == "__main__":

    main()