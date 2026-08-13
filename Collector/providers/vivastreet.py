import re
import time
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from collector.http import creer_session_http

from collector.models import Annonce


BASE_URL = "https://www.vivastreet.com"

PAGE_URL = (
    BASE_URL
    + "/achat-vente-informatique/fr"
)

HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


# Sécurité / politesse : on ne parcourt jamais un nombre
# illimité de pages, même si Vivastreet change sa navigation.
MAX_PAGES = 10
PAUSE_ENTRE_PAGES = 1.0


def nettoyer(texte):
    if texte is None:
        return ""

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .replace("\u202f", " ")
        .split()
    )


def est_url_annonce(url):
    if not url:
        return False

    return bool(
        re.search(
            r"^/achat-vente-informatique/"
            r"[^/]+/[^/]+/\d+/?$",
            urlparse(url).path,
            flags=re.IGNORECASE,
        )
    )


def normaliser_url(lien):
    return urljoin(
        BASE_URL,
        lien,
    ).split("#")[0]


def extraire_identifiant(url):
    match = re.search(
        r"/(\d+)$",
        urlparse(url).path.rstrip("/"),
    )

    if not match:
        return None

    return (
        "VIVASTREET-"
        + match.group(1)
    )


def extraire_titre_url(url):
    morceaux = [
        morceau
        for morceau in urlparse(url).path.split("/")
        if morceau
    ]

    if len(morceaux) < 3:
        return ""

    return nettoyer(
        unquote(
            morceaux[-2]
        ).replace("-", " ")
    )


def departement_depuis_code_postal(code_postal):
    if not code_postal:
        return None

    code = str(code_postal).strip()

    if not re.fullmatch(r"\d{5}", code):
        return None

    if code.startswith(("97", "98")):
        return code[:3]

    # Les codes postaux 20xxx ne suffisent pas
    # à distinguer automatiquement 2A et 2B.
    if code.startswith("20"):
        return None

    return code[:2]


def extraire_localisation_url(url):
    morceaux = [
        morceau
        for morceau in urlparse(url).path.split("/")
        if morceau
    ]

    if len(morceaux) < 4:
        return "Inconnue"

    localisation_slug = unquote(
        morceaux[1]
    )

    match = re.match(
        r"^(.+)-(\d{5})$",
        localisation_slug,
    )

    if match:
        ville_slug = match.group(1)
        code_postal = match.group(2)
    else:
        ville_slug = localisation_slug
        code_postal = None

    ville = (
        ville_slug
        .replace("-", " ")
        .strip()
        .title()
    )

    if not ville:
        return "Inconnue"

    departement = (
        departement_depuis_code_postal(
            code_postal
        )
    )

    if departement:
        return f"{ville} ({departement})"

    return ville


def convertir_prix(texte):
    """
    Exemples :
    420 -> 420
    1 250 -> 1250
    1.250 -> 1250
    1,250 -> 1250
    1250,50 -> 1250.50
    1.250,50 -> 1250.50
    """
    if texte is None:
        return None

    valeur = (
        str(texte)
        .replace("\xa0", " ")
        .replace("\u202f", " ")
        .strip()
    )

    valeur = re.sub(
        r"[^\d., ]",
        "",
        valeur,
    )

    valeur = valeur.replace(
        " ",
        "",
    )

    if not valeur:
        return None

    if "." in valeur and "," in valeur:
        dernier_point = valeur.rfind(".")
        derniere_virgule = valeur.rfind(",")

        if derniere_virgule > dernier_point:
            decimal = ","
            milliers = "."
        else:
            decimal = "."
            milliers = ","

        apres_decimal = valeur.split(decimal)[-1]

        if len(apres_decimal) in {1, 2}:
            valeur = valeur.replace(
                milliers,
                "",
            )
            valeur = valeur.replace(
                decimal,
                ".",
            )
        else:
            valeur = (
                valeur
                .replace(".", "")
                .replace(",", "")
            )

    elif "." in valeur or "," in valeur:
        separateur = (
            "."
            if "." in valeur
            else ","
        )

        morceaux = valeur.split(
            separateur
        )

        # 1.250 / 1,250
        if (
            len(morceaux) == 2
            and len(morceaux[1]) == 3
        ):
            valeur = "".join(
                morceaux
            )

        # 1.250.000
        elif (
            len(morceaux) > 2
            and all(
                len(morceau) == 3
                for morceau in morceaux[1:]
            )
        ):
            valeur = "".join(
                morceaux
            )

        # 1250,50 / 1250.50
        elif (
            len(morceaux) == 2
            and len(morceaux[1]) in {1, 2}
        ):
            valeur = (
                morceaux[0]
                + "."
                + morceaux[1]
            )

        else:
            return None

    try:
        prix = float(valeur)

    except ValueError:
        return None

    if prix <= 0 or prix > 100_000:
        return None

    if prix.is_integer():
        return int(prix)

    return round(prix, 2)


def extraire_prix_texte(texte):
    texte = nettoyer(texte)

    nombre = (
        r"("
        r"\d{1,3}(?:[ .\u00a0\u202f]\d{3})+"
        r"(?:,\d{1,2})?"
        r"|"
        r"\d+(?:[.,]\d{1,3})?"
        r")"
    )

    motifs = [
        rf"Prix\s*(?:€|EUR)\s*{nombre}",
        rf"Prix\s*{nombre}\s*(?:€|EUR)",
        rf"{nombre}\s*(?:€|EUR)",
        rf"(?:€|EUR)\s*{nombre}",
    ]

    for motif in motifs:
        match = re.search(
            motif,
            texte,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        prix = convertir_prix(
            match.group(1)
        )

        if prix is not None:
            return prix

    return None


def trouver_bloc_annonce(lien):
    element = lien

    for _ in range(8):
        element = element.parent

        if element is None:
            break

        texte = nettoyer(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if len(texte) > 6000:
            break

        if extraire_prix_texte(texte) is None:
            continue

        nombre_annonces = 0

        for autre_lien in element.find_all(
            "a",
            href=True,
        ):
            url_autre = normaliser_url(
                autre_lien.get("href")
            )

            if est_url_annonce(url_autre):
                nombre_annonces += 1

        if nombre_annonces <= 2:
            return element

    return None


def extraire_description(
    bloc,
    titre,
    localisation,
):
    candidats = []

    titre_min = nettoyer(titre).lower()
    localisation_min = nettoyer(
        localisation
    ).lower()

    for chaine in bloc.stripped_strings:
        texte = nettoyer(chaine)

        if len(texte) < 15:
            continue

        texte_min = texte.lower()

        if texte_min == titre_min:
            continue

        if texte_min == localisation_min:
            continue

        if texte_min in {
            "particulier",
            "professionnel",
            "voir l'annonce",
            "informatique",
        }:
            continue

        if re.fullmatch(r"\d+", texte):
            continue

        if (
            extraire_prix_texte(texte)
            is not None
            and len(texte) < 40
        ):
            continue

        if re.fullmatch(
            r".+\s*-\s*\d{5}",
            texte,
        ):
            continue

        if (
            "ordinateur occasion" in texte_min
            and len(texte) < 100
        ):
            continue

        if (
            texte_min.startswith("informatique ")
            and len(texte) < 100
        ):
            continue

        candidats.append(texte)

    if not candidats:
        return ""

    candidats.sort(
        key=len,
        reverse=True,
    )

    return candidats[0][:2000]


def parser_annonce(lien):
    href = lien.get("href")

    if not href:
        return None

    url = normaliser_url(href)

    if not est_url_annonce(url):
        return None

    identifiant = extraire_identifiant(url)

    if not identifiant:
        return None

    titre = nettoyer(
        lien.get_text(
            " ",
            strip=True,
        )
    )

    if titre.lower() in {
        "",
        "vivastreet",
        "vivastreet fr",
        "voir l'annonce",
    }:
        titre = extraire_titre_url(url)

    if not titre:
        return None

    bloc = trouver_bloc_annonce(lien)

    if bloc is None:
        return None

    texte_bloc = nettoyer(
        bloc.get_text(
            " ",
            strip=True,
        )
    )

    prix = extraire_prix_texte(
        texte_bloc
    )

    if prix is None:
        return None

    localisation = extraire_localisation_url(
        url
    )

    description = extraire_description(
        bloc=bloc,
        titre=titre,
        localisation=localisation,
    )

    if not description:
        description = titre

    return Annonce(
        identifiant=identifiant,
        titre=titre,
        prix=prix,
        description=description,
        localisation=localisation,
        plateforme="Vivastreet",
        url=url,
        date_publication=None,
    )


def recuperer_page(
    session,
    url,
):
    try:
        response = session.get(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:
        print(
            "⚠️ Vivastreet erreur réseau :",
            erreur,
        )
        return None

    print(
        "🌐 Vivastreet HTTP :",
        response.status_code,
    )

    if response.status_code in {
        401,
        403,
        429,
    }:
        print(
            "⛔ Vivastreet refuse ou limite "
            "la collecte."
        )
        print(
            "➡️ Arrêt propre, aucun contournement."
        )
        return None

    if response.status_code != 200:
        print(
            "⚠️ Vivastreet HTTP inattendu :",
            response.status_code,
        )
        return None

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


# ============================================================
# PAGINATION
# ============================================================

def extraire_pages_pagination(
    soup,
):
    """
    Extrait uniquement les vraies pages de la rubrique :
    /achat-vente-informatique/fr/t+2
    /achat-vente-informatique/fr/t+3
    etc.

    Le numéro après t+ est utilisé uniquement pour ordonner
    les pages. Aucune URL n'est inventée.
    """
    pages = {}

    for lien in soup.find_all(
        "a",
        href=True,
    ):
        url = normaliser_url(
            lien.get("href")
        )

        chemin = unquote(
            urlparse(url).path
        )

        match = re.fullmatch(
            r"/achat-vente-informatique/"
            r"fr/t\+(\d+)/?",
            chemin,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        numero = int(
            match.group(1)
        )

        # La page principale représente déjà la page 1.
        if numero <= 1:
            continue

        pages[
            numero
        ] = url

    return dict(
        sorted(
            pages.items()
        )
    )


def extraire_liens_annonces_uniques(
    soup,
    ids_vus,
):
    """
    Retourne les liens d'annonces de cette page qui n'ont
    encore jamais été vus pendant le scan Vivastreet.
    """
    candidats = []

    for lien in soup.find_all(
        "a",
        href=True,
    ):
        url = normaliser_url(
            lien.get("href")
        )

        if not est_url_annonce(
            url
        ):
            continue

        identifiant = extraire_identifiant(
            url
        )

        if not identifiant:
            continue

        if identifiant in ids_vus:
            continue

        ids_vus.add(
            identifiant
        )

        candidats.append(
            lien
        )

    return candidats


# ============================================================
# RECHERCHE
# ============================================================

def rechercher(
    limite=None,
):
    annonces = []
    ids_vus = set()

    with creer_session_http() as session:

        # ----------------------------------------------------
        # PAGE PRINCIPALE
        # ----------------------------------------------------

        premiere_page = recuperer_page(
            session,
            PAGE_URL,
        )

        if premiere_page is None:
            return []

        print()
        print(
            "📡 Vivastreet France"
        )

        # File d'attente :
        # on démarre avec la page principale.
        pages_a_lire = [
            (
                1,
                PAGE_URL,
                premiere_page,
            )
        ]

        urls_pages_vues = {
            PAGE_URL
        }

        index_page = 0

        # ----------------------------------------------------
        # PARCOURS DES PAGES REELLEMENT EXPOSEES
        # ----------------------------------------------------

        while (
            index_page
            <
            len(pages_a_lire)
            and
            index_page
            <
            MAX_PAGES
        ):
            (
                numero_page,
                url_page,
                soup,
            ) = pages_a_lire[
                index_page
            ]

            index_page += 1

            if soup is None:
                if index_page > 1:
                    time.sleep(
                        PAUSE_ENTRE_PAGES
                    )

                soup = recuperer_page(
                    session,
                    url_page,
                )

                if soup is None:
                    # Si Vivastreet refuse/limite une page,
                    # on arrête ce provider proprement.
                    break

            # Découvre les pages présentes dans le HTML.
            # On n'invente pas t+3, t+4, etc.
            nouvelles_pages = (
                extraire_pages_pagination(
                    soup
                )
            )

            for (
                numero,
                url,
            ) in nouvelles_pages.items():
                if (
                    url
                    in urls_pages_vues
                ):
                    continue

                if (
                    len(
                        pages_a_lire
                    )
                    >= MAX_PAGES
                ):
                    break

                urls_pages_vues.add(
                    url
                )

                pages_a_lire.append(
                    (
                        numero,
                        url,
                        None,
                    )
                )

            # Garde un ordre logique même si Vivastreet
            # affiche ses liens de pagination dans un autre ordre.
            if (
                index_page
                <
                len(pages_a_lire)
            ):
                deja_lues = (
                    pages_a_lire[
                        :index_page
                    ]
                )

                a_lire = sorted(
                    pages_a_lire[
                        index_page:
                    ],
                    key=lambda item: (
                        item[0]
                    ),
                )

                pages_a_lire = (
                    deja_lues
                    +
                    a_lire
                )

            candidats = (
                extraire_liens_annonces_uniques(
                    soup,
                    ids_vus,
                )
            )

            print(
                f"📄 Vivastreet page "
                f"{numero_page} : "
                f"{len(candidats)} "
                f"nouvelles annonces"
            )

            for lien in candidats:
                try:
                    annonce = (
                        parser_annonce(
                            lien
                        )
                    )

                except Exception as erreur:
                    print(
                        "⚠️ Annonce Vivastreet ignorée :",
                        erreur,
                    )
                    continue

                if annonce is None:
                    continue

                annonces.append(
                    annonce
                )

                if (
                    limite is not None
                    and
                    len(annonces)
                    >= limite
                ):
                    print(
                        "✅ Vivastreet :",
                        len(annonces),
                        "annonces normalisées",
                    )
                    return annonces

        print(
            "📚 IDs uniques Vivastreet vus :",
            len(ids_vus),
        )

    print(
        "✅ Vivastreet :",
        len(annonces),
        "annonces normalisées",
    )

    return annonces

def main():
    print()
    print("=" * 55)
    print("🟢 PC HUNTER - VIVASTREET")
    print("=" * 55)

    annonces = rechercher()

    print()
    print(
        "💻 Annonces récupérées :",
        len(annonces),
    )

    for position, annonce in enumerate(
        annonces[:15],
        start=1,
    ):
        print()
        print("-" * 55)
        print(f"#{position}")
        print("🆔", annonce.identifiant)
        print("🖥️", annonce.titre)
        print("💰", annonce.prix, "€")
        print("📍", annonce.localisation)
        print(
            "📄",
            annonce.description[:250],
        )
        print("🔗", annonce.url)


if __name__ == "__main__":
    main()
