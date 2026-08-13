import json
import re

import requests
from bs4 import BeautifulSoup


URL = (
    "https://bons-plans.easycash.fr/pc/"
    "cooler-master-i5-16-go-ram-2-to-hdd-500-go-ssd-005567364"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


MOTS_CLES = (
    "magasin",
    "store",
    "shop",
    "retrait",
    "pickup",
    "stock",
    "disponib",
    "availability",
    "livraison",
    "city",
    "ville",
    "adresse",
    "address",
)


MOTS_INTERDITS = (
    "email",
    "e-mail",
    "telephone",
    "téléphone",
    "phone",
    "contact",
    "vendeur",
    "seller",
    "customer",
    "client",
    "user",
)


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def contient_mot_cle(texte):

    texte = str(
        texte
    ).lower()

    return any(
        mot in texte
        for mot in MOTS_CLES
    )


def contient_mot_interdit(texte):

    texte = str(
        texte
    ).lower()

    return any(
        mot in texte
        for mot in MOTS_INTERDITS
    )


# ============================================================
# JSON-LD
# ============================================================

def afficher_json_ld(soup):

    print()
    print("========================================")
    print("🧩 JSON-LD")
    print("========================================")


    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )


    print(
        "📦 Blocs JSON-LD :",
        len(scripts)
    )


    for numero, script in enumerate(
        scripts,
        start=1
    ):

        contenu = script.string

        if not contenu:
            continue


        try:

            objet = json.loads(
                contenu
            )

        except json.JSONDecodeError:
            continue


        print()
        print(
            f"--- JSON-LD {numero} ---"
        )


        if isinstance(
            objet,
            dict
        ):

            print(
                "@type :",
                objet.get(
                    "@type"
                )
            )


            offers = objet.get(
                "offers"
            )


            if offers:

                print(
                    "offers :"
                )

                print(
                    json.dumps(
                        offers,
                        ensure_ascii=False,
                        indent=2
                    )[:3000]
                )


# ============================================================
# TEXTE VISIBLE
# ============================================================

def afficher_lignes_visibles(soup):

    print()
    print("========================================")
    print("👁️ TEXTE VISIBLE LIÉ AUX OFFRES")
    print("========================================")


    texte = soup.get_text(
        "\n",
        strip=True
    )


    lignes_trouvees = []


    for ligne in texte.splitlines():

        propre = nettoyer(
            ligne
        )


        if len(propre) < 2:
            continue


        if contient_mot_interdit(
            propre
        ):
            continue


        if contient_mot_cle(
            propre
        ):

            if propre not in lignes_trouvees:

                lignes_trouvees.append(
                    propre
                )


    for ligne in lignes_trouvees[
        :60
    ]:

        print(
            "-",
            ligne
        )


# ============================================================
# BALISES / ATTRIBUTS HTML
# ============================================================

def afficher_elements_html(soup):

    print()
    print("========================================")
    print("🏪 ÉLÉMENTS HTML POTENTIELS")
    print("========================================")


    compteur = 0


    for element in soup.find_all(
        True
    ):

        attributs = element.attrs


        representation = (
            str(
                attributs
            )
        )


        if not contient_mot_cle(
            representation
        ):
            continue


        if contient_mot_interdit(
            representation
        ):
            continue


        texte = nettoyer(
            element.get_text(
                " ",
                strip=True
            )
        )


        # Évite d'imprimer des énormes
        # sections HTML.
        if len(texte) > 500:
            texte = (
                texte[:500]
                + "..."
            )


        print()
        print(
            "TAG :",
            element.name
        )

        print(
            "ATTR :",
            representation[:700]
        )

        if texte:

            print(
                "TEXTE :",
                texte
            )


        compteur += 1


        if compteur >= 30:
            break


# ============================================================
# LIENS
# ============================================================

def afficher_liens(soup):

    print()
    print("========================================")
    print("🔗 LIENS MAGASIN / STOCK / RETRAIT")
    print("========================================")


    deja_vus = set()


    for lien in soup.find_all(
        "a",
        href=True
    ):

        href = lien.get(
            "href",
            ""
        )

        texte = nettoyer(
            lien.get_text(
                " ",
                strip=True
            )
        )


        ensemble = (
            texte
            + " "
            + href
        )


        if not contient_mot_cle(
            ensemble
        ):
            continue


        if contient_mot_interdit(
            ensemble
        ):
            continue


        cle = (
            texte,
            href
        )


        if cle in deja_vus:
            continue


        deja_vus.add(
            cle
        )


        print()
        print(
            "📝",
            texte
        )

        print(
            "🔗",
            href
        )


# ============================================================
# SCRIPTS HYDRATÉS
# ============================================================

def afficher_scripts_interessants(soup):

    print()
    print("========================================")
    print("🧠 DONNÉES EMBARQUÉES POTENTIELLES")
    print("========================================")


    compteur = 0


    for script in soup.find_all(
        "script"
    ):

        contenu = (
            script.string
            or script.get_text()
            or ""
        )


        if not contenu:
            continue


        contenu_min = (
            contenu.lower()
        )


        if not any(
            mot in contenu_min
            for mot in (
                "store",
                "magasin",
                "stock",
                "availability",
                "pickup",
            )
        ):

            continue


        # Ne jamais afficher des blocs
        # contenant potentiellement des infos
        # de contact/vendeur.
        if contient_mot_interdit(
            contenu_min
        ):
            continue


        extrait = nettoyer(
            contenu
        )


        print()
        print(
            f"--- SCRIPT {compteur + 1} ---"
        )

        print(
            extrait[:2000]
        )


        compteur += 1


        if compteur >= 8:
            break


# ============================================================
# PROGRAMME
# ============================================================

def main():

    print()
    print("========================================")
    print("🏪 PC HUNTER - PROBE OFFRES EASY CASH")
    print("========================================")
    print()


    try:

        reponse = requests.get(
            URL,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur :",
            erreur
        )

        return


    print(
        "📡 HTTP :",
        reponse.status_code
    )

    print(
        "📦 Taille :",
        len(
            reponse.content
        ),
        "octets"
    )


    if reponse.status_code != 200:

        print(
            "❌ Arrêt du probe."
        )

        return


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    afficher_json_ld(
        soup
    )

    afficher_lignes_visibles(
        soup
    )

    afficher_liens(
        soup
    )

    afficher_elements_html(
        soup
    )

    afficher_scripts_interessants(
        soup
    )


    print()
    print("========================================")
    print("✅ PROBE TERMINÉ")
    print("========================================")

    print(
        "🔒 Aucune information personnelle "
        "vendeur recherchée."
    )


if __name__ == "__main__":

    main()