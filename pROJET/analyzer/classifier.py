import re
import unicodedata

from analyzer.components import detecter_composants


CATEGORIES_PC = {
    "PC_COMPLET",
    "PC_GAMING",
    "PORTABLE",
    "PORTABLE_GAMING",
}


def normaliser_texte(texte):

    texte = str(
        texte or ""
    )

    texte = unicodedata.normalize(
        "NFKD",
        texte
    )

    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(
            caractere
        )
    )

    texte = texte.lower()

    texte = re.sub(
        r"[^a-z0-9]+",
        " ",
        texte
    )

    texte = re.sub(
        r"\s+",
        " ",
        texte
    )

    return texte.strip()


def contient_un(
    texte,
    mots
):

    return any(
        mot in texte
        for mot in mots
    )


def classer_annonce(
    annonce
):

    titre = normaliser_texte(
        getattr(
            annonce,
            "titre",
            ""
        )
    )

    description = normaliser_texte(
        getattr(
            annonce,
            "description",
            ""
        )
    )

    texte = (
        titre
        +
        " "
        +
        description
    )


    # ========================================================
    # COMPOSANTS DÉTECTÉS
    # ========================================================

    detection = (
        detecter_composants(
            annonce
        )
    )

    gpu = detection.get(
        "gpu",
        []
    )

    cpu = detection.get(
        "cpu",
        []
    )

    ram = detection.get(
        "ram",
        []
    )

    stockage = detection.get(
        "stockage",
        []
    )


    nombre_categories_materiel = sum(
        [
            bool(gpu),
            bool(cpu),
            bool(ram),
            bool(stockage),
        ]
    )


    # ========================================================
    # MARQUEURS
    # ========================================================

    marqueurs_portable = (
        "pc portable",
        "ordinateur portable",
        "portable gamer",
        "portable gaming",
        "laptop",
        "notebook",
        "macbook",
        "asus rog",
        "rog strix",
        "msi katana",
        "msi pulse",
    )


    marqueurs_gaming = (
        "gaming",
        "gamer",
        "pc gamer",
        "pc gaming",
        "setup gaming",
        "setup gamer",
        "rog",
        "rtx ",
        "gtx ",
        "radeon rx",
    )


    marqueurs_pc = (
        "pc ",
        "ordinateur",
        "ordinateur fixe",
        "ordinateur bureau",
        "pc fixe",
        "pc bureau",
        "tour gaming",
        "tour gamer",
        "tour pc",
        "setup gaming",
        "setup gamer",
        "optiplex",
        "imac",
        "tout en un",
        "all in one",
    )


    marqueurs_composants = (
        "carte graphique",
        "gpu ",
        "processeur",
        "cpu ",
        "carte mere",
        "memoire ram",
        "barrette ram",
        "disque dur",
        "disques dur",
        "ssd ",
        "nvme",
        "alimentation pc",
        "ventirad",
        "boitier pc",
    )


    marqueurs_accessoires = (
        "clavier",
        "souris",
        "tapis de souris",
        "webcam",
        "camera pc",
        "casque",
        "ecran",
        "moniteur",
        "cable",
        "adaptateur",
        "chargeur",
        "station accueil",
        "dock",
    )


    est_portable = (
        bool(
            detection.get(
                "machine_portable_windows"
            )
        )
        or
        contient_un(
            texte,
            marqueurs_portable
        )
    )


    est_gaming = (
        contient_un(
            texte,
            marqueurs_gaming
        )
        or
        bool(gpu)
    )


    semble_pc = (
        contient_un(
            texte,
            marqueurs_pc
        )
    )


    semble_composant = (
        contient_un(
            titre,
            marqueurs_composants
        )
    )


    semble_accessoire = (
        contient_un(
            titre,
            marqueurs_accessoires
        )
    )

    # ========================================================
    # PRIORITÉ : COMPOSANT CLAIREMENT VENDU SEUL
    #
    # Exemples :
    # "2 disques dur de pc portable"
    # "carte graphique pour pc"
    # "processeur Ryzen 5"
    # ========================================================

    titre_composant_fort = bool(
        re.search(
            r"\b(?:"
            r"\d+\s+)?"
            r"(?:"
            r"disques?\s+durs?|"
            r"ssd|"
            r"nvme|"
            r"carte\s+graphique|"
            r"processeur|"
            r"cpu|"
            r"gpu|"
            r"barrettes?\s+(?:de\s+)?ram|"
            r"memoire\s+ram|"
            r"carte\s+mere|"
            r"alimentation|"
            r"ventirad"
            r")\b",
            titre,
        )
    )

    composant_pour_pc = bool(
        re.search(
            r"\b(?:de|pour)\s+"
            r"(?:pc|ordinateur)"
            r"(?:\s+portable)?\b",
            titre,
        )
    )

    if (
        titre_composant_fort
        and
        (
            composant_pour_pc
            or
            not semble_pc
        )
    ):

        return {
            "categorie":
                "COMPOSANT",

            "analyse_pc":
                False,

            "raison":
                "Composant informatique vendu seul détecté",

            "detection":
                detection,
        }
    # ========================================================
    # 1. PORTABLE GAMING
    # ========================================================

    if (
        est_portable
        and
        est_gaming
    ):

        return {
            "categorie":
                "PORTABLE_GAMING",

            "analyse_pc":
                True,

            "raison":
                "Ordinateur portable gaming détecté",

            "detection":
                detection,
        }


    # ========================================================
    # 2. PORTABLE CLASSIQUE
    # ========================================================

    if est_portable:

        return {
            "categorie":
                "PORTABLE",

            "analyse_pc":
                True,

            "raison":
                "Ordinateur portable détecté",

            "detection":
                detection,
        }


    # ========================================================
    # 3. PC GAMING
    #
    # Important :
    # une annonce "setup gaming" reste un PC gaming
    # si elle contient suffisamment de matériel PC.
    # ========================================================

    if (
        est_gaming
        and
        (
            semble_pc
            or
            nombre_categories_materiel >= 2
        )
    ):

        return {
            "categorie":
                "PC_GAMING",

            "analyse_pc":
                True,

            "raison":
                "PC gaming détecté",

            "detection":
                detection,
        }


    # ========================================================
    # 4. ACCESSOIRE
    #
    # On le fait avant PC_COMPLET pour éviter qu'un titre
    # comme "clavier pour ordinateur" soit pris pour un PC.
    # ========================================================

    if (
        semble_accessoire
        and
        nombre_categories_materiel < 2
    ):

        return {
            "categorie":
                "ACCESSOIRE",

            "analyse_pc":
                False,

            "raison":
                "Accessoire informatique détecté",

            "detection":
                detection,
        }


    # ========================================================
    # 5. COMPOSANT
    # ========================================================

    if (
        semble_composant
        and
        not semble_pc
    ):

        return {
            "categorie":
                "COMPOSANT",

            "analyse_pc":
                False,

            "raison":
                "Composant informatique seul détecté",

            "detection":
                detection,
        }


    # Cas particulier :
    #
    # titre très orienté composant +
    # aucune combinaison CPU/GPU/RAM suffisante.
    if (
        semble_composant
        and
        nombre_categories_materiel <= 1
    ):

        return {
            "categorie":
                "COMPOSANT",

            "analyse_pc":
                False,

            "raison":
                "Annonce orientée composant seul",

            "detection":
                detection,
        }


    # ========================================================
    # 6. PC COMPLET
    # ========================================================

    if semble_pc:

        return {
            "categorie":
                "PC_COMPLET",

            "analyse_pc":
                True,

            "raison":
                "Ordinateur complet probable",

            "detection":
                detection,
        }


    # ========================================================
    # 7. CONFIGURATION MATÉRIELLE SUFFISANTE
    #
    # Même si le vendeur écrit un titre bizarre,
    # CPU + GPU + RAM est un signal fort de PC complet.
    # ========================================================

    if (
        bool(cpu)
        and
        bool(gpu)
        and
        nombre_categories_materiel >= 3
    ):

        return {
            "categorie":
                "PC_COMPLET",

            "analyse_pc":
                True,

            "raison":
                "Configuration PC complète détectée par les composants",

            "detection":
                detection,
        }


    # ========================================================
    # INCONNU
    # ========================================================

    return {
        "categorie":
            "INCONNU",

        "analyse_pc":
            False,

        "raison":
            "Impossible de confirmer qu'il s'agit d'un PC complet",

        "detection":
            detection,
    }


def est_un_pc(
    annonce
):

    resultat = classer_annonce(
        annonce
    )

    return bool(
        resultat.get(
            "analyse_pc",
            False
        )
    )
