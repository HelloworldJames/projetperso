import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


PAGE_URL = (
    "https://www.paruvendu.fr/"
    "annonces/informatique/"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand opportunity monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


CODE_INSEE = "17449"
CODE_POSTAL = "17430"
RAYON_KM = "50"


def nettoyer(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def extraire_localisation(bloc):

    for chaine in bloc.stripped_strings:

        texte = nettoyer(
            chaine
        )

        match = re.fullmatch(
            r"(.+?)\s+\((\d{2,3})\)",
            texte,
        )

        if not match:
            continue

        ville = nettoyer(
            match.group(1)
        )

        departement = (
            match.group(2)
        )

        if len(ville) <= 80:

            return (
                ville,
                departement,
            )

    return (
        "Inconnue",
        None,
    )


def extraire_titre(bloc):

    for lien in bloc.find_all(
        "a",
        href=True,
    ):

        href = lien.get(
            "href",
            "",
        )

        if (
            "/annonces/high-tech/"
            not in href
        ):
            continue

        titre = nettoyer(
            lien.get(
                "title",
                "",
            )
        )

        if titre:

            return titre

    return "Annonce"


def main():

    print()
    print(
        "========================================"
    )

    print(
        "📍 PC HUNTER - PARUVENDU LOCAL"
    )

    print(
        "========================================"
    )


    with requests.Session() as session:

        # ----------------------------------------------------
        # 1. Ouvre d'abord normalement la catégorie
        # ----------------------------------------------------

        try:

            page = session.get(
                PAGE_URL,
                headers=HEADERS,
                timeout=20,
            )

        except requests.RequestException as erreur:

            print(
                "❌ Erreur page :",
                erreur,
            )

            return


        print()
        print(
            "📡 Page initiale :",
            page.status_code,
        )


        if page.status_code != 200:

            return


        soup = BeautifulSoup(
            page.text,
            "html.parser",
        )


        form = soup.find(
            "form",
            id="rechercher",
        )


        if form is None:

            print(
                "❌ Formulaire introuvable."
            )

            return


        action = form.get(
            "action"
        )


        if not action:

            print(
                "❌ Action formulaire introuvable."
            )

            return


        search_url = urljoin(
            PAGE_URL,
            action,
        )


        # ----------------------------------------------------
        # 2. Récupère les paramètres catégorie du site
        # ----------------------------------------------------

        params = {}


        for nom in [
            "codPro",
            "filtre",
            "tri",
            "idtag",
        ]:

            champ = form.find(
                attrs={
                    "name": nom
                }
            )

            if champ is not None:

                params[nom] = (
                    champ.get(
                        "value",
                        "",
                    )
                )


        # Rubrique sélectionnée si elle existe.
        rubrique = form.find(
            "select",
            attrs={
                "name": "r"
            },
        )


        if rubrique is not None:

            option = rubrique.find(
                "option",
                selected=True,
            )


            if option is not None:

                params["r"] = (
                    option.get(
                        "value",
                        "",
                    )
                )


        # ----------------------------------------------------
        # 3. Localisation officielle retournée par ParuVendu
        # ----------------------------------------------------

        # Le JS ParuVendu utilise des listes séparées
        # par des virgules dans le mode multi-localisation.
        params["codeinsee"] = (
            CODE_INSEE + ","
        )

        params["lo"] = (
            CODE_POSTAL + ","
        )

        params["pa"] = ""

        params["ray"] = RAYON_KM

        params["elargrayon"] = "1"

        # uniquement les annonces de vente
        params["zmd[]"] = "VENTE"


        print()
        print(
            "🎯 Recherche :"
        )

        print(
            "   Ville : Tonnay-Charente"
        )

        print(
            "   INSEE :",
            CODE_INSEE,
        )

        print(
            "   CP :",
            CODE_POSTAL,
        )

        print(
            "   Rayon :",
            RAYON_KM,
            "km",
        )


        # ----------------------------------------------------
        # 4. Soumission normale du formulaire public
        # ----------------------------------------------------

        try:

            response = session.get(
                search_url,
                params=params,
                headers={
                    **HEADERS,
                    "Referer": PAGE_URL,
                },
                timeout=20,
            )

        except requests.RequestException as erreur:

            print(
                "❌ Recherche :",
                erreur,
            )

            return


        print()
        print(
            "🌐 URL finale :"
        )

        print(
            response.url
        )

        print()
        print(
            "📡 HTTP :",
            response.status_code,
        )

        print(
            "📦 Taille :",
            len(response.content),
        )


        if response.status_code in {
            403,
            429,
        }:

            print()
            print(
                "⛔ Accès refusé / limité."
            )

            print(
                "➡️ Aucun contournement."
            )

            return


        if response.status_code != 200:

            return


        # ----------------------------------------------------
        # 5. Analyse des résultats
        # ----------------------------------------------------

        resultat = BeautifulSoup(
            response.text,
            "html.parser",
        )


        titre_page = (
            resultat.title.get_text(
                " ",
                strip=True,
            )
            if resultat.title
            else "Inconnu"
        )


        print()
        print(
            "📑 Titre page :",
            titre_page,
        )


        blocs = resultat.select(
            "div.debarras-annonce[data-id]"
        )


        print()
        print(
            "📦 Annonces détectées :",
            len(blocs),
        )


        texte_page = nettoyer(
            resultat.get_text(
                " ",
                strip=True,
            )
        )


        match_total = re.search(
            r"([\d\s]+)\s+annonces?",
            texte_page,
            flags=re.IGNORECASE,
        )


        if match_total:

            print(
                "📊 Total affiché par ParuVendu :",
                nettoyer(
                    match_total.group(1)
                ),
            )


        villes = {}


        print()
        print(
            "========================================"
        )

        print(
            "🗺️ PREMIERS RÉSULTATS"
        )

        print(
            "========================================"
        )


        for numero, bloc in enumerate(
            blocs[:20],
            start=1,
        ):

            identifiant = bloc.get(
                "data-id"
            )


            ville, departement = (
                extraire_localisation(
                    bloc
                )
            )


            titre = extraire_titre(
                bloc
            )


            cle = (
                ville,
                departement,
            )


            villes[cle] = (
                villes.get(
                    cle,
                    0,
                )
                + 1
            )


            print()
            print(
                f"#{numero}"
            )

            print(
                "🆔",
                identifiant,
            )

            print(
                "📍",
                ville,
                f"({departement})"
                if departement
                else "",
            )

            print(
                "🖥️",
                titre[:150],
            )


        print()
        print(
            "========================================"
        )

        print(
            "📍 VILLES TROUVÉES"
        )

        print(
            "========================================"
        )


        for (
            ville,
            departement,
        ), nombre in villes.items():

            print(
                f"- {ville} "
                f"({departement}) : "
                f"{nombre}"
            )


        print()
        print(
            "========================================"
        )

        print(
            "✅ TEST LOCAL TERMINÉ"
        )

        print(
            "========================================"
        )


if __name__ == "__main__":
    main()