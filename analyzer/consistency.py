import re


def verifier_coherence(annonce, composants):

    texte = (
        f"{getattr(annonce, 'titre', '')} "
        f"{getattr(annonce, 'description', '')}"
    ).lower()

    problemes = []


    cpu = " ".join(
        composants.get(
            "cpu",
            []
        )
    ).lower()


    ram = " ".join(
        composants.get(
            "ram",
            []
        )
    ).lower()


    # ========================================================
    # RYZEN AM4 + DDR5
    #
    # Ryzen 1000 / 2000 / 3000 / 4000 / 5000
    # utilisent ici de la DDR4, pas de DDR5.
    # ========================================================

    match_ryzen = re.search(
        r"ryzen\s+[3579]\s+(\d{4})",
        cpu
    )

    if match_ryzen:

        modele = int(
            match_ryzen.group(1)
        )

        if (
            1000 <= modele <= 5999
            and
            "ddr5" in ram
        ):

            problemes.append(
                "CPU Ryzen AM4 détecté avec DDR5 déclarée"
            )


    # ========================================================
    # CHIPSETS AM4 + DDR5
    # ========================================================

    chipset_am4 = re.search(
        r"\b(?:a320|a520|b350|b450|b550|x370|x470|x570)",
        texte
    )

    if (
        chipset_am4
        and
        "ddr5" in ram
    ):

        problemes.append(
            "Carte mère AM4 déclarée avec DDR5"
        )


    # ========================================================
    # RÉSULTAT
    # ========================================================

    return {

        "coherent":
            len(problemes) == 0,

        "problemes":
            problemes,
    }