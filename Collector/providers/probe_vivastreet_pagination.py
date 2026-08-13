import re
import time

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.vivastreet.com"

URL_NATIONALE = (
    BASE_URL
    + "/achat-vente-informatique/fr"
)

URL_LOCALE = (
    BASE_URL
    + "/achat-vente-informatique/charente-maritime"
)

TIMEOUT = 20
PAUSE = 1.5


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": (
        "text/html,"
        "application/xhtml+xml"
    ),
    "Accept-Language": (
        "fr-FR,fr;q=0.9"
    ),
}


# ============================================================
# ANNONCES
# ============================================================

def est_url_annonce(url):

    chemin = urlparse(
        url
    ).path

    return bool(
        re.search(
            r"^/achat-vente-informatique/"
            r"[^/]+/"
            r"[^/]+/"
            r"\d+/?$",
            chemin,
            flags=re.IGNORECASE,
        )
    )


def extraire_id(url):

    match = re.search(
        r"/(\d+)/?$",
        urlparse(
            url
        ).path,
    )

    if not match:
        return None

    return match.group(1)


def extraire_annonces(
    soup,
    base_url,
):

    annonces = {}

    for lien in soup.find_all(
        "a",
        href=True,
    ):

        url = urljoin(
            base_url,
            lien.get("href"),
        )

        if not est_url_annonce(
            url
        ):
            continue

        identifiant = extraire_id(
            url
        )

        if not identifiant:
            continue

        annonces[
            identifiant
        ] = url

    return annonces


# ============================================================
# PAGINATION
# ============================================================

def extraire_liens_pagination(
    soup,
    base_url,
):

    resultats = {}

    for lien in soup.find_all(
        "a",
        href=True,
    ):

        href = lien.get(
            "href",
            "",
        )

        url = urljoin(
            base_url,
            href,
        )

        chemin = urlparse(
            url
        ).path

        match = re.search(
            r"/achat-vente-informatique/"
            r"fr/"
            r"t(?:%2B|\+)(\d+)",
            chemin,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        numero = int(
            match.group(1)
        )

        resultats[
            numero
        ] = url

    return dict(
        sorted(
            resultats.items()
        )
    )


# ============================================================
# TOTAL RESULTATS
# ============================================================

def extraire_total(
    soup,
):

    texte = " ".join(
        soup.stripped_strings
    )

    motifs = (
        r"(\d+)\s+r[ée]sultats?",
        r"(\d+)\s+annonces?",
    )

    for motif in motifs:

        match = re.search(
            motif,
            texte,
            flags=re.IGNORECASE,
        )

        if match:

            try:
                return int(
                    match.group(1)
                )

            except ValueError:
                pass

    return None


# ============================================================
# HTTP
# ============================================================

def recuperer(
    session,
    url,
):

    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return None


    print(
        "HTTP :",
        response.status_code,
    )

    print(
        "Taille :",
        len(response.content),
        "octets",
    )


    if response.status_code in {
        401,
        403,
        429,
    }:

        print(
            "⛔ Accès refusé ou limité."
        )

        print(
            "➡️ Aucun contournement."
        )

        return None


    if response.status_code != 200:

        print(
            "⚠️ HTTP inattendu."
        )

        return None


    return BeautifulSoup(
        response.text,
        "html.parser",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("#" * 70)
    print(
        "🧪 PC HUNTER — VIVASTREET PAGINATION"
    )
    print("#" * 70)


    with requests.Session() as session:

        # ====================================================
        # PAGE NATIONALE
        # ====================================================

        print()
        print("=" * 70)
        print("🇫🇷 PAGE NATIONALE")
        print("=" * 70)

        print(
            URL_NATIONALE
        )


        soup = recuperer(
            session,
            URL_NATIONALE,
        )


        if soup is None:
            return


        annonces_page_1 = (
            extraire_annonces(
                soup,
                URL_NATIONALE,
            )
        )


        total = extraire_total(
            soup
        )


        pagination = (
            extraire_liens_pagination(
                soup,
                URL_NATIONALE,
            )
        )


        print()
        print(
            "📊 Total annoncé :",
            total,
        )

        print(
            "📦 Annonces page principale :",
            len(
                annonces_page_1
            ),
        )

        print(
            "📄 Liens pagination détectés :",
            len(
                pagination
            ),
        )


        if pagination:

            print()
            print(
                "🔗 PAGINATION"
            )

            for numero, url in list(
                pagination.items()
            )[:20]:

                print(
                    f"t+{numero} → {url}"
                )


        # ====================================================
        # TEST DES 2 PREMIERES PAGES DE PAGINATION
        # ====================================================

        ids_globaux = set(
            annonces_page_1.keys()
        )


        for numero, url in list(
            pagination.items()
        )[:2]:

            time.sleep(
                PAUSE
            )

            print()
            print("=" * 70)
            print(
                f"📄 TEST t+{numero}"
            )
            print("=" * 70)

            print(
                url
            )


            soup_page = recuperer(
                session,
                url,
            )


            if soup_page is None:
                break


            annonces_page = (
                extraire_annonces(
                    soup_page,
                    url,
                )
            )


            ids_page = set(
                annonces_page.keys()
            )


            nouveaux = (
                ids_page
                -
                ids_globaux
            )


            communs = (
                ids_page
                &
                ids_globaux
            )


            print()
            print(
                "📦 Annonces :",
                len(
                    ids_page
                ),
            )

            print(
                "🆕 Nouveaux IDs :",
                len(
                    nouveaux
                ),
            )

            print(
                "♻️ IDs déjà vus :",
                len(
                    communs
                ),
            )


            ids_globaux.update(
                ids_page
            )


        # ====================================================
        # PAGE CHARENTE-MARITIME
        # ====================================================

        time.sleep(
            PAUSE
        )


        print()
        print("=" * 70)
        print("📍 CHARENTE-MARITIME")
        print("=" * 70)

        print(
            URL_LOCALE
        )


        soup_locale = recuperer(
            session,
            URL_LOCALE,
        )


        if soup_locale is not None:

            annonces_locales = (
                extraire_annonces(
                    soup_locale,
                    URL_LOCALE,
                )
            )


            total_local = (
                extraire_total(
                    soup_locale
                )
            )


            print()
            print(
                "📊 Total annoncé :",
                total_local,
            )

            print(
                "📦 URLs d'annonces trouvées :",
                len(
                    annonces_locales
                ),
            )


            for url in list(
                annonces_locales.values()
            )[:10]:

                print(
                    "•",
                    url,
                )


        # ====================================================
        # VERDICT
        # ====================================================

        print()
        print("#" * 70)
        print("🏁 RESULTAT")
        print("#" * 70)

        print()
        print(
            "IDs uniques vus national + pagination :",
            len(
                ids_globaux
            ),
        )


        if pagination:

            print(
                "🟢 Une pagination Vivastreet "
                "a été détectée."
            )

        else:

            print(
                "🟡 Aucun lien de pagination "
                "détecté dans le HTML actuel."
            )


if __name__ == "__main__":
    main()