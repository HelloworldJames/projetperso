import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

FICHIER_SOURCE = (
    BASE_DIR
    / "data"
    / "easycash_real.json"
)


HEADERS = {
    "User-Agent": (
        "PC-Hunter/0.1 "
        "(personal second-hand market monitor)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


# ============================================================
# MOTIFS GPU
# ============================================================

GPU_PATTERNS = [
    r"\bRTX\s*\d{4}(?:\s*Ti|\s*SUPER)?\b",
    r"\bGTX\s*\d{3,4}(?:\s*Ti|\s*SUPER)?\b",
    r"\bRX\s*\d{4}(?:\s*XT|\s*XTX)?\b",
    r"\bARC\s*[AB]\d{3}\b",
]


# ============================================================
# MOTIFS CPU
# ============================================================

CPU_PATTERNS = [

    # AMD Ryzen
    r"\bRyzen\s*[3579]\s*\d{4,5}[A-Z0-9]*\b",

    # Intel Core classiques
    r"\bi[3579][-\s]?\d{4,5}[A-Z]{0,3}\b",

    # Intel Core Ultra
    r"\bCore\s+Ultra\s+[3579]\s+\d{3}[A-Z]?\b",
]


def nettoyer_texte(texte):

    return " ".join(
        str(texte)
        .replace("\xa0", " ")
        .split()
    )


def trouver_premier_pattern(
    texte,
    patterns
):

    for pattern in patterns:

        resultat = re.search(
            pattern,
            texte,
            flags=re.IGNORECASE
        )

        if resultat:

            return nettoyer_texte(
                resultat.group(0)
            )

    return None


def extraire_json_ld(
    soup
):

    donnees = []

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        contenu = script.string

        if not contenu:
            continue

        try:

            objet = json.loads(
                contenu
            )

            donnees.append(
                objet
            )

        except json.JSONDecodeError:
            continue

    return donnees


def extraire_lignes_interessantes(
    texte
):

    mots_cles = [
        "nvidia",
        "geforce",
        "radeon",
        "rtx",
        "gtx",
        "rx ",
        "carte graphique",
        "processeur",
        "mémoire",
        "memoire",
        "ram",
        "ssd",
        "stockage",
        "magasin",
        "retrait",
        "disponible",
    ]

    lignes = []

    for ligne in texte.splitlines():

        ligne_propre = nettoyer_texte(
            ligne
        )

        if len(ligne_propre) < 3:
            continue

        ligne_min = ligne_propre.lower()

        if any(
            mot in ligne_min
            for mot in mots_cles
        ):

            if ligne_propre not in lignes:

                lignes.append(
                    ligne_propre
                )

    return lignes


def analyser_fiche(
    session,
    annonce
):

    url = annonce.get(
        "url"
    )

    if not url:

        return None


    try:

        reponse = session.get(
            url,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as erreur:

        print(
            "❌ Erreur fiche :",
            erreur
        )

        return None


    print(
        "📡 HTTP fiche :",
        reponse.status_code
    )


    if reponse.status_code != 200:

        return None


    soup = BeautifulSoup(
        reponse.text,
        "html.parser"
    )


    # Texte visible complet
    texte_page = soup.get_text(
        "\n",
        strip=True
    )

    texte_normalise = nettoyer_texte(
        texte_page
    )


    gpu = trouver_premier_pattern(
        texte_normalise,
        GPU_PATTERNS
    )

    cpu = trouver_premier_pattern(
        texte_normalise,
        CPU_PATTERNS
    )


    json_ld = extraire_json_ld(
        soup
    )


    lignes_interessantes = (
        extraire_lignes_interessantes(
            texte_page
        )
    )


    return {
        "titre":
            annonce.get(
                "titre"
            ),

        "prix":
            annonce.get(
                "prix"
            ),

        "url":
            url,

        "gpu_detecte":
            gpu,

        "cpu_detecte":
            cpu,

        "json_ld":
            json_ld,

        "lignes_interessantes":
            lignes_interessantes[:40],
    }


def main():

    print()
    print(
        "========================================"
    )

    print(
        "🔬 PC HUNTER - PROBE FICHES EASY CASH"
    )

    print(
        "========================================"
    )

    print()


    if not FICHIER_SOURCE.exists():

        print(
            "❌ easycash_real.json introuvable"
        )

        return


    annonces = json.loads(
        FICHIER_SOURCE.read_text(
            encoding="utf-8"
        )
    )


    # Seulement 5 fiches pour le test.
    annonces_test = annonces[:5]


    print(
        "📦 Fiches à tester :",
        len(annonces_test)
    )

    print()


    resultats = []


    with requests.Session() as session:

        for numero, annonce in enumerate(
            annonces_test,
            start=1
        ):

            print(
                "========================================"
            )

            print(
                f"🔎 FICHE {numero}/{len(annonces_test)}"
            )

            print(
                "========================================"
            )

            print(
                "📝",
                annonce.get(
                    "titre"
                )
            )

            print(
                "💵",
                annonce.get(
                    "prix"
                ),
                "€"
            )


            resultat = analyser_fiche(
                session,
                annonce
            )


            if resultat is None:

                print(
                    "❌ Impossible d'analyser cette fiche"
                )

                continue


            resultats.append(
                resultat
            )


            print(
                "🎮 GPU détecté :",
                resultat[
                    "gpu_detecte"
                ]
                or
                "NON TROUVÉ"
            )

            print(
                "🧠 CPU détecté :",
                resultat[
                    "cpu_detecte"
                ]
                or
                "NON TROUVÉ"
            )


            print()
            print(
                "📋 Informations intéressantes :"
            )


            for ligne in resultat[
                "lignes_interessantes"
            ][:15]:

                print(
                    "-",
                    ligne
                )


            print()


            # Petite pause volontaire entre les fiches.
            time.sleep(
                1.0
            )


    fichier_resultat = (
        BASE_DIR
        / "data"
        / "easycash_details_probe.json"
    )


    fichier_resultat.write_text(
        json.dumps(
            resultats,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "========================================"
    )

    print(
        "✅ TEST TERMINÉ"
    )

    print(
        "========================================"
    )

    print(
        "📦 Fiches analysées :",
        len(resultats)
    )

    print(
        "💾 Résultat :",
        fichier_resultat
    )

    print()
    print(
        "🔒 Aucune information vendeur collectée."
    )


if __name__ == "__main__":

    main()
    