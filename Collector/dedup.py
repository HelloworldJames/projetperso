import hashlib
import re
import unicodedata


def normaliser_texte(texte):

    if texte is None:
        return ""

    texte = str(texte).lower()

    texte = unicodedata.normalize(
        "NFD",
        texte
    )

    texte = "".join(
        caractere
        for caractere in texte
        if unicodedata.category(caractere) != "Mn"
    )

    texte = re.sub(
        r"[^a-z0-9]+",
        " ",
        texte
    )

    return " ".join(
        texte.split()
    )


def cle_unique_annonce(annonce):

    """
    Première clé :
    plateforme + identifiant officiel.
    """

    plateforme = normaliser_texte(
        annonce.plateforme
    )

    identifiant = normaliser_texte(
        annonce.identifiant
    )

    if identifiant:

        return (
            "ID|"
            + plateforme
            + "|"
            + identifiant
        )


    # Fallback si une source ne fournit pas d'identifiant

    contenu = "|".join([
        normaliser_texte(annonce.titre),
        str(annonce.prix),
        normaliser_texte(annonce.localisation),
        normaliser_texte(annonce.url)
    ])

    empreinte = hashlib.sha1(
        contenu.encode("utf-8")
    ).hexdigest()

    return "HASH|" + empreinte


def signature_annonce(annonce):

    """
    Signature plus large permettant de repérer
    une annonce éventuellement présente sur plusieurs sources.
    """

    contenu = "|".join([
        normaliser_texte(annonce.titre),
        normaliser_texte(annonce.description),
        str(annonce.prix),
        normaliser_texte(annonce.localisation)
    ])

    return hashlib.sha1(
        contenu.encode("utf-8")
    ).hexdigest()


def dedupliquer_annonces(annonces):

    annonces_uniques = []

    cles_connues = set()
    signatures_connues = set()

    doublons_exact = 0
    doublons_probables = 0


    for annonce in annonces:

        cle = cle_unique_annonce(
            annonce
        )

        signature = signature_annonce(
            annonce
        )


        # Même annonce / même plateforme
        if cle in cles_connues:

            doublons_exact += 1

            print(
                "♻️ Doublon exact ignoré :",
                annonce.titre
            )

            continue


        # Même contenu provenant éventuellement
        # de plusieurs providers
        if signature in signatures_connues:

            doublons_probables += 1

            print(
                "🔁 Doublon probable ignoré :",
                annonce.titre
            )

            continue


        cles_connues.add(
            cle
        )

        signatures_connues.add(
            signature
        )

        annonces_uniques.append(
            annonce
        )


    print(
        f"🧹 Déduplication : "
        f"{len(annonces)} → "
        f"{len(annonces_uniques)} annonces"
    )

    if doublons_exact > 0:

        print(
            "   ♻️ Doublons exacts :",
            doublons_exact
        )

    if doublons_probables > 0:

        print(
            "   🔁 Doublons probables :",
            doublons_probables
        )


    return annonces_uniques