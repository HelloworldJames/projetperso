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
    "data/probe_profond_resultats.json"
)


# ============================================================
# MODELE
# ============================================================

@dataclass
class Source:
    nom: str
    url: str
    motif_annonce: str


SOURCES = [

    Source(
        nom="ParuVendu",
        url=(
            "https://www.paruvendu.fr/"
            "annonces/ordinateur-portable/"
        ),
        motif_annonce=(
            r"/annonces/"
            r"(?:high-tech|informatique)/.*"
        ),
    ),

    Source(
        nom="TopAnnonces",
        url=(
            "https://www.topannonces.fr/"
            "vente-occasion-informatique/"
            "nord-pas-de-calais/837534/"
        ),
        motif_annonce=(
            r"/vente-occasion/"
            r".*/\d+/?$"
        ),
    ),

    Source(
    nom="Marche.fr",
    url=(
        "https://www.marche.fr/"
        "ordinateurs-pc/"
    ),
    motif_annonce=(
        r"/Petite-annonce-a-vendre-"
        r".+\.html\?a=\d+_?"
    ),
        ),

    Source(
        nom="Wallapop",
        url=(
            "https://fr.wallapop.com/"
        ),
        motif_annonce=(
            r"/item/"
            r".+-\d+"
        ),
    ),

]


# ============================================================
# PARSEUR HTML
# ============================================================

class AnalyseurHTML(
    HTMLParser
):

    def __init__(
        self
    ):

        super().__init__()

        self.liens = []

        self.scripts_json_ld = []

        self.dans_json_ld = False

        self.buffer_json_ld = []


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

            type_script = (
                attributs.get(
                    "type",
                    ""
                )
                .lower()
            )

            if (
                "ld+json"
                in type_script
            ):

                self.dans_json_ld = True

                self.buffer_json_ld = []


    def handle_data(
        self,
        data,
    ):

        if self.dans_json_ld:

            self.buffer_json_ld.append(
                data
            )


    def handle_endtag(
        self,
        tag,
    ):

        if (
            tag == "script"
            and
            self.dans_json_ld
        ):

            contenu = "".join(
                self.buffer_json_ld
            ).strip()

            if contenu:

                self.scripts_json_ld.append(
                    contenu
                )

            self.dans_json_ld = False

            self.buffer_json_ld = []


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

    return urljoin(
        base,
        lien,
    )


def meme_domaine(
    url_source,
    url_cible,
):

    try:

        domaine_source = (
            urlparse(
                url_source
            )
            .netloc
            .lower()
            .replace(
                "www.",
                ""
            )
        )

        domaine_cible = (
            urlparse(
                url_cible
            )
            .netloc
            .lower()
            .replace(
                "www.",
                ""
            )
        )

        return (
            domaine_source
            ==
            domaine_cible
        )

    except Exception:

        return False


def extraire_liens_annonces(
    source,
    liens,
):

    annonces = []

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


        if not re.search(
            source.motif_annonce,
            url,
            flags=re.IGNORECASE,
        ):

            continue


        url_propre = (
            url.split("#")[0]
        )


        if url_propre in deja_vus:
            continue


        deja_vus.add(
            url_propre
        )

        annonces.append(
            url_propre
        )


    return annonces


def extraire_prix(
    html
):

    motifs = [

        r"(\d{1,4}(?:[.,]\d{1,2})?)\s*€",

        r"€\s*(\d{1,4}(?:[.,]\d{1,2})?)",

    ]


    valeurs = []


    for motif in motifs:

        matches = re.findall(
            motif,
            html,
            flags=re.IGNORECASE,
        )

        for valeur in matches:

            valeur = (
                valeur
                .replace(
                    ",",
                    "."
                )
            )

            try:

                nombre = float(
                    valeur
                )

            except ValueError:

                continue


            if (
                nombre <= 0
                or
                nombre > 100_000
            ):

                continue


            if nombre not in valeurs:

                valeurs.append(
                    nombre
                )


    return valeurs


def extraire_codes_postaux(
    html
):

    codes = re.findall(
        r"\b(?:0[1-9]|[1-8]\d|9[0-5])\d{3}\b",
        html,
    )

    uniques = []

    deja_vus = set()


    for code in codes:

        if code in deja_vus:
            continue

        deja_vus.add(
            code
        )

        uniques.append(
            code
        )


    return uniques


def analyser_json_ld(
    scripts
):

    types = []

    produits = 0

    listes = 0

    offres = 0


    def parcourir(
        objet
    ):

        nonlocal produits
        nonlocal listes
        nonlocal offres


        if isinstance(
            objet,
            dict,
        ):

            type_objet = objet.get(
                "@type"
            )


            if type_objet:

                if isinstance(
                    type_objet,
                    list,
                ):

                    types.extend(
                        str(element)
                        for element
                        in type_objet
                    )

                else:

                    types.append(
                        str(type_objet)
                    )


                texte_type = str(
                    type_objet
                ).lower()


                if "product" in texte_type:

                    produits += 1


                if (
                    "itemlist"
                    in texte_type
                ):

                    listes += 1


                if "offer" in texte_type:

                    offres += 1


            for valeur in objet.values():

                parcourir(
                    valeur
                )


        elif isinstance(
            objet,
            list,
        ):

            for element in objet:

                parcourir(
                    element
                )


    scripts_valides = 0


    for script in scripts:

        try:

            donnees = json.loads(
                script
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            continue


        scripts_valides += 1

        parcourir(
            donnees
        )


    return {

        "scripts_valides": (
            scripts_valides
        ),

        "types": sorted(
            set(types)
        ),

        "products": produits,

        "item_lists": listes,

        "offers": offres,

    }


def detecter_pagination(
    liens
):

    pagination = []


    motifs = (

        r"[?&]page=\d+",

        r"[?&]p=\d+",

        r"/page/\d+",

        r"/page-\d+",

    )


    for lien in liens:

        texte = lien.lower()

        if any(
            re.search(
                motif,
                texte,
            )
            for motif
            in motifs
        ):

            if lien not in pagination:

                pagination.append(
                    lien
                )


    return pagination


def compter_mots(
    html
):

    texte = html.lower()


    mots = {

        "pc": (
            len(
                re.findall(
                    r"\bpc\b",
                    texte,
                )
            )
        ),

        "ordinateur": (
            texte.count(
                "ordinateur"
            )
        ),

        "portable": (
            texte.count(
                "portable"
            )
        ),

        "gaming": (
            texte.count(
                "gaming"
            )
        ),

        "rtx": (
            texte.count(
                "rtx"
            )
        ),

        "gtx": (
            texte.count(
                "gtx"
            )
        ),

        "ryzen": (
            texte.count(
                "ryzen"
            )
        ),

        "intel": (
            texte.count(
                "intel"
            )
        ),

        "ssd": (
            texte.count(
                "ssd"
            )
        ),

    }


    return mots


def detecter_identifiants(
    source,
    urls_annonces,
    html,
):

    identifiants = []


    if source.nom == "Wallapop":

        for url in urls_annonces:

            match = re.search(
                r"-(\d+)(?:[/?#]|$)",
                url,
            )

            if match:

                identifiants.append(
                    match.group(1)
                )


    elif source.nom == "TopAnnonces":

        for url in urls_annonces:

            match = re.search(
                r"/(\d+)/?$",
                url,
            )

            if match:

                identifiants.append(
                    match.group(1)
                )


    elif source.nom == "ParuVendu":

        motifs = [

            r"/(\d{8,})A1",

            r"/(\d{8,})/",

        ]


        for url in urls_annonces:

            for motif in motifs:

                match = re.search(
                    motif,
                    url,
                )

                if match:

                    identifiants.append(
                        match.group(1)
                    )

                    break


    elif source.nom == "Marche.fr":

        for url in urls_annonces:

            match = re.search(
                r"[?&]a=(\d+)_?",
                url,
                flags=re.IGNORECASE,
            )

            if match:

                identifiants.append(
                    match.group(1)
                )

        motifs = [

            r"[?&]id=(\d+)",

            r"/(\d{6,})",

        ]


        for motif in motifs:

            matches = re.findall(
                motif,
                html,
            )

            identifiants.extend(
                matches
            )


    return sorted(
        set(
            identifiants
        )
    )


def calculer_score(
    statut_http,
    annonces,
    prix,
    codes_postaux,
    json_ld,
    pagination,
    identifiants,
    mots,
):

    if statut_http != 200:

        return 0


    score = 20


    # Vraies URLs d'annonces
    if len(
        annonces
    ) >= 5:

        score += 20

    elif annonces:

        score += 10


    # Prix
    if len(
        prix
    ) >= 5:

        score += 15

    elif prix:

        score += 7


    # Localisation
    if codes_postaux:

        score += 10


    # Identifiants stables probables
    if len(
        identifiants
    ) >= 5:

        score += 15

    elif identifiants:

        score += 7


    # Données structurées
    if (
        json_ld["products"]
        or
        json_ld["item_lists"]
        or
        json_ld["offers"]
    ):

        score += 10


    # Pagination
    if pagination:

        score += 5


    # Contenu réellement informatique
    signal_pc = (
        mots["pc"]
        +
        mots["ordinateur"]
        +
        mots["gaming"]
        +
        mots["rtx"]
        +
        mots["gtx"]
        +
        mots["ryzen"]
    )


    if signal_pc >= 10:

        score += 5


    return min(
        score,
        100,
    )


def verdict(
    score
):

    if score >= 80:

        return (
            "🟢 PROVIDER PRIORITAIRE"
        )


    if score >= 60:

        return (
            "🟢 PROVIDER POSSIBLE"
        )


    if score >= 40:

        return (
            "🟠 ANALYSE SUPPLEMENTAIRE"
        )


    return (
        "🔴 PEU EXPLOITABLE"
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
        f"🔬 ANALYSE PROFONDE — {source.nom}"
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
                "❌ ERREUR RESEAU"
            ),

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

    print(
        "URL finale :",
        reponse.url,
    )


    if reponse.status_code in {
        401,
        403,
        429,
    }:

        print()
        print(
            "⛔ Accès refusé ou limité."
        )

        print(
            "Aucun contournement."
        )

        return {

            "source": source.nom,

            "statut_http": (
                reponse.status_code
            ),

            "score": 0,

            "verdict": "🔒 BLOQUE",

        }


    if reponse.status_code != 200:

        return {

            "source": source.nom,

            "statut_http": (
                reponse.status_code
            ),

            "score": 0,

            "verdict": (
                "⚠️ HTTP INATTENDU"
            ),

        }


    html = reponse.text


    parseur = AnalyseurHTML()

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
        extraire_liens_annonces(
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


    json_ld = analyser_json_ld(
        parseur.scripts_json_ld
    )


    pagination = (
        detecter_pagination(
            parseur.liens
        )
    )


    mots = compter_mots(
        html
    )


    identifiants = (
        detecter_identifiants(
            source,
            urls_annonces,
            html,
        )
    )


    score = calculer_score(
        statut_http=(
            reponse.status_code
        ),
        annonces=urls_annonces,
        prix=prix,
        codes_postaux=codes_postaux,
        json_ld=json_ld,
        pagination=pagination,
        identifiants=identifiants,
        mots=mots,
    )


    resultat_verdict = verdict(
        score
    )


    # ========================================================
    # SIGNAL SPECIAL TOPANNONCES / PARUVENDU
    # ========================================================

    mentions_paruvendu = (
        html.lower()
        .count(
            "paruvendu"
        )
    )


    print()

    print(
        "📝 Titre :",
        titre,
    )

    print()

    print(
        "🔗 Liens HTML totaux :",
        len(
            parseur.liens
        ),
    )

    print(
        "📦 URLs d'annonces candidates :",
        len(
            urls_annonces
        ),
    )

    print(
        "🆔 Identifiants candidats :",
        len(
            identifiants
        ),
    )

    print(
        "💶 Valeurs de prix détectées :",
        len(
            prix
        ),
    )

    print(
        "📍 Codes postaux détectés :",
        len(
            codes_postaux
        ),
    )

    print(
        "📄 Liens pagination :",
        len(
            pagination
        ),
    )

    print()

    print(
        "🧩 JSON-LD valides :",
        json_ld[
            "scripts_valides"
        ],
    )

    print(
        "📦 Product :",
        json_ld[
            "products"
        ],
    )

    print(
        "📋 ItemList :",
        json_ld[
            "item_lists"
        ],
    )

    print(
        "💵 Offer :",
        json_ld[
            "offers"
        ],
    )


    if source.nom == "TopAnnonces":

        print()

        print(
            "🔁 Mentions ParuVendu :",
            mentions_paruvendu,
        )


    print()
    print(
        "🧠 Signaux PC :",
        mots,
    )


    print()
    print(
        "📊 SCORE PROFOND :",
        f"{score}/100",
    )

    print(
        "🎯 VERDICT :",
        resultat_verdict,
    )


    if urls_annonces:

        print()
        print(
            "🔎 EXEMPLES D'URLS"
        )


        for position, url in enumerate(
            urls_annonces[:5],
            start=1,
        ):

            print(
                f"{position}. {url}"
            )


    return {

        "source": source.nom,

        "url": source.url,

        "url_finale": reponse.url,

        "statut_http": (
            reponse.status_code
        ),

        "taille_octets": len(
            reponse.content
        ),

        "titre": titre,

        "liens_html": len(
            parseur.liens
        ),

        "annonces_candidates": len(
            urls_annonces
        ),

        "exemples_annonces": (
            urls_annonces[:10]
        ),

        "prix_detectes": (
            prix[:30]
        ),

        "codes_postaux": (
            codes_postaux[:30]
        ),

        "identifiants_detectes": (
            identifiants[:30]
        ),

        "pagination": (
            pagination[:20]
        ),

        "json_ld": json_ld,

        "mots": mots,

        "mentions_paruvendu": (
            mentions_paruvendu
        ),

        "score": score,

        "verdict": (
            resultat_verdict
        ),

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("#" * 70)
    print("🔬 PC HUNTER — PROBE PROFOND DES SOURCES")
    print("#" * 70)
    print()

    print(
        "Objectif : identifier la meilleure "
        "source réelle n°2."
    )

    print()

    print(
        "Aucune donnée vendeur n'est extraite."
    )

    print(
        "Aucun proxy, cookie privé, compte "
        "ou contournement n'est utilisé."
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
    print("🏆 CLASSEMENT PROFOND")
    print("#" * 70)
    print()


    for position, resultat in enumerate(
        classement,
        start=1,
    ):

        print(
            f"{position}. "
            f"{resultat['source']:<15} "
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
        "✅ Probe profond terminé."
    )


if __name__ == "__main__":

    main()