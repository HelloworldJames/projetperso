import unicodedata


def normaliser_texte(texte):
    texte = texte.lower()

    # Supprime les accents pour faciliter les détections
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(caractere) != "Mn"
    )

    return texte


def diagnostiquer_reparation(annonce):

    texte = normaliser_texte(
        annonce.titre + " " + annonce.description
    )

    diagnostics = []
    cout_min = 0
    cout_max = 0

    # PC ne démarre pas
    if (
        "ne demarre pas" in texte
        or "ne demarre plus" in texte
        or "ne s'allume pas" in texte
        or "ne s'allume plus" in texte
        or "aucun demarrage" in texte
    ):
        diagnostics.append(
            "Alimentation, RAM ou carte mère à diagnostiquer"
        )

        cout_min += 50
        cout_max += 150

    # Écran noir
    if (
        "ecran noir" in texte
        or "pas d'image" in texte
        or "aucune image" in texte
        or "pas d'affichage" in texte
    ):
        diagnostics.append(
            "RAM, GPU ou connexion écran à vérifier"
        )

        cout_min += 20
        cout_max += 100

    # Surchauffe
    if (
        "chauffe" in texte
        or "surchauffe" in texte
        or "bruyant" in texte
    ):
        diagnostics.append(
            "Nettoyage et changement de pâte thermique possible"
        )

        cout_min += 10
        cout_max += 40

    # Carte graphique
    if (
        "artefact" in texte
        or "artefacts" in texte
        or "gpu hs" in texte
        or "carte graphique hs" in texte
    ):
        diagnostics.append(
            "Carte graphique potentiellement défectueuse"
        )

        cout_min += 100
        cout_max += 300

    # Aucun problème détecté
    if not diagnostics:
        diagnostics.append(
            "Aucune panne identifiée"
        )

    return {
        "diagnostics": diagnostics,
        "cout_min": cout_min,
        "cout_max": cout_max
    }