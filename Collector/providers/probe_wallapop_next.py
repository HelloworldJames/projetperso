import json
import re

import requests


URL = (
    "https://fr.wallapop.com/search"
    "?keywords=pc"
    "&order_by=most_relevance"
)


def chercher_cles(objet, chemin="root", resultats=None):

    if resultats is None:
        resultats = []

    mots_interessants = (
        "item",
        "product",
        "listing",
        "search",
        "price",
        "title",
        "location",
        "keyword",
    )

    if isinstance(objet, dict):

        for cle, valeur in objet.items():

            nouveau_chemin = (
                f"{chemin}.{cle}"
            )

            cle_min = str(
                cle
            ).lower()

            if any(
                mot in cle_min
                for mot in mots_interessants
            ):

                resultats.append(
                    nouveau_chemin
                )

            chercher_cles(
                valeur,
                nouveau_chemin,
                resultats,
            )

    elif isinstance(objet, list):

        for index, valeur in enumerate(
            objet[:100]
        ):

            chercher_cles(
                valeur,
                f"{chemin}[{index}]",
                resultats,
            )

    return resultats


def compter_signaux(objet):

    texte = json.dumps(
        objet,
        ensure_ascii=False,
    ).lower()

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
        "item": texte.count(
            "/item/"
        ),
        "price": texte.count(
            '"price"'
        ),
        "title": texte.count(
            '"title"'
        ),
        "location": texte.count(
            '"location"'
        ),
        "rtx": texte.count(
            "rtx"
        ),
        "ryzen": texte.count(
            "ryzen"
        ),
    }


def main():

    print()
    print("=" * 60)
    print("🔬 WALLAPOP — ANALYSE __NEXT_DATA__")
    print("=" * 60)
    print()

    try:

        reponse = requests.get(
            URL,
            timeout=20,
            headers={
                "User-Agent": (
                    "PC-Hunter-Prototype/0.1 "
                    "(marketplace compatibility research)"
                ),
                "Accept-Language": "fr-FR,fr;q=0.9",
            },
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur réseau :",
            erreur,
        )

        return


    print(
        "HTTP :",
        reponse.status_code,
    )

    print(
        "Taille HTML :",
        len(reponse.content),
        "octets",
    )


    if reponse.status_code != 200:

        print(
            "⛔ Réponse non exploitable."
        )

        return


    html = reponse.text


    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>'
        r'(.*?)'
        r'</script>',
        html,
        flags=(
            re.IGNORECASE
            |
            re.DOTALL
        ),
    )


    if not match:

        print(
            "❌ __NEXT_DATA__ introuvable."
        )

        return


    contenu = match.group(
        1
    ).strip()


    print(
        "📦 Taille __NEXT_DATA__ :",
        len(
            contenu
        ),
        "caractères",
    )


    try:

        donnees = json.loads(
            contenu
        )

    except json.JSONDecodeError as erreur:

        print(
            "❌ JSON invalide :",
            erreur,
        )

        return


    print()
    print(
        "✅ JSON valide"
    )


    # ========================================================
    # INFORMATIONS NEXT.JS
    # ========================================================

    print()
    print("🧩 INFORMATIONS NEXT.JS")
    print()


    print(
        "Page :",
        donnees.get(
            "page"
        ),
    )

    print(
        "Build ID présent :",
        "✅"
        if donnees.get(
            "buildId"
        )
        else "❌",
    )

    print(
        "Query :",
        donnees.get(
            "query"
        ),
    )


    # ========================================================
    # CLES INTERESSANTES
    # ========================================================

    chemins = chercher_cles(
        donnees
    )


    chemins_uniques = []

    deja_vus = set()


    for chemin in chemins:

        if chemin in deja_vus:
            continue

        deja_vus.add(
            chemin
        )

        chemins_uniques.append(
            chemin
        )


    print()
    print("🔑 CLÉS INTÉRESSANTES")
    print()


    if not chemins_uniques:

        print(
            "Aucune clé intéressante."
        )

    else:

        for chemin in chemins_uniques[
            :50
        ]:

            print(
                "•",
                chemin,
            )


    # ========================================================
    # SIGNAUX DANS LE JSON
    # ========================================================

    signaux = compter_signaux(
        donnees
    )


    print()
    print("🧠 SIGNAUX DANS __NEXT_DATA__")
    print()


    for nom, valeur in signaux.items():

        print(
            f"{nom:<12} : {valeur}"
        )


    # ========================================================
    # VERDICT
    # ========================================================

    signal_annonces = (
        signaux["item"]
        +
        signaux["price"]
        +
        signaux["title"]
        +
        signaux["rtx"]
        +
        signaux["ryzen"]
    )


    print()
    print("=" * 60)


    if signal_annonces > 10:

        print(
            "🟢 Des données d'annonces semblent "
            "présentes dans __NEXT_DATA__."
        )

        print(
            "➡️ Wallapop mérite une extraction plus poussée."
        )

    else:

        print(
            "🟡 __NEXT_DATA__ semble surtout contenir "
            "la configuration de l'application."
        )

        print(
            "➡️ Les résultats sont probablement "
            "chargés ensuite côté navigateur."
        )


    print("=" * 60)


if __name__ == "__main__":

    main()