import sqlite3
import re

from contextlib import closing
from datetime import datetime
from statistics import median
from types import SimpleNamespace

from analyzer.classifier import (
    classer_annonce,
)

from analyzer.components import (
    detecter_composants,
    normaliser_texte,
)

from database.listing import (
    DB_PATH,
)


PLATEFORMES_COMPARABLES = (
    "ParuVendu",
    "Vivastreet",
)

PRIX_MINIMUM_COMPARABLE = 20.0
PRIX_MAXIMUM_COMPARABLE = 10_000.0

GAMMES_PORTABLES_GPU_REQUIS = {
    "ROG Zephyrus",
    "ROG Strix",
    "ROG",
    "TUF",
    "Legion",
    "IdeaPad Gaming",
    "Omen",
    "Victus",
    "Pavilion Gaming",
    "Predator",
    "Nitro",
    "Katana",
    "Pulse",
    "GF",
    "GL",
    "GS",
    "G15",
    "G5",
    "Alienware",
    "Blade",
    "AORUS",
}


# ============================================================
# TEMPS / CONNEXION
# ============================================================

def maintenant_iso():
    return (
        datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


def connexion_db():
    connexion = sqlite3.connect(
        DB_PATH
    )

    connexion.row_factory = (
        sqlite3.Row
    )

    return connexion


def connexion_db_lecture_seule():
    chemin_db = DB_PATH.resolve()

    uri_db = (
        "file:"
        + chemin_db.as_posix()
        + "?mode=ro"
    )

    connexion = sqlite3.connect(
        uri_db,
        uri=True,
    )

    connexion.row_factory = (
        sqlite3.Row
    )

    return connexion


# ============================================================
# INITIALISATION
# ============================================================

def initialiser_market():
    with connexion_db() as connexion:
        connexion.execute(
            """
            CREATE TABLE IF NOT EXISTS observations_marche (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                plateforme TEXT NOT NULL,
                identifiant TEXT NOT NULL,

                titre TEXT,
                prix REAL NOT NULL,

                description TEXT,
                localisation TEXT,
                url TEXT,

                gpu TEXT,
                cpu TEXT,
                ram TEXT,
                stockage TEXT,

                date_observation TEXT NOT NULL,

                UNIQUE (
                    plateforme,
                    identifiant,
                    prix
                )
            )
            """
        )


# ============================================================
# OUTILS
# ============================================================

def valeur_propre(
    valeur,
):
    if valeur is None:
        return None

    texte = str(
        valeur
    ).strip()

    if texte.lower() in {
        "",
        "-",
        "--",
        "n.c.",
        "n.c",
        "nc",
        "inconnu",
        "inconnue",
        "none",
    }:
        return None

    return texte


def premiere_valeur(
    valeur,
):
    """
    Les détecteurs de components.py renvoient souvent
    des listes. Pour le marché, on garde ici la première
    valeur utile lorsqu'un seul champ est disponible en BDD.
    """
    if isinstance(
        valeur,
        (
            list,
            tuple,
            set,
        ),
    ):
        for element in valeur:
            propre = valeur_propre(
                element
            )

            if propre:
                return propre

        return None

    return valeur_propre(
        valeur
    )


def joindre_valeurs(
    valeur,
):
    """
    Le stockage peut contenir plusieurs éléments,
    par exemple SSD + HDD.
    """
    if isinstance(
        valeur,
        (
            list,
            tuple,
            set,
        ),
    ):
        propres = []

        for element in valeur:
            propre = valeur_propre(
                element
            )

            if (
                propre
                and
                propre not in propres
            ):
                propres.append(
                    propre
                )

        if propres:
            return " + ".join(
                propres
            )

        return None

    return valeur_propre(
        valeur
    )


# ============================================================
# EXTRACTION LEGACY
# ============================================================

def extraire_valeur_description(
    description,
    champ,
):
    """
    Compatibilité avec les anciennes descriptions
    normalisées du type :

    GPU: RTX 3060 | CPU: Ryzen 5 5600 | RAM: 16 Go
    """
    if not description:
        return None

    parties = description.split(
        "|"
    )

    prefixe = (
        champ.lower()
        + ":"
    )

    for partie in parties:
        propre = partie.strip()

        if propre.lower().startswith(
            prefixe
        ):
            valeur = propre.split(
                ":",
                1,
            )[1].strip()

            return valeur_propre(
                valeur
            )

    return None


# ============================================================
# EXTRACTION REELLE PC HUNTER
# ============================================================

def extraire_composants_marche(
    annonce,
):
    """
    Utilise maintenant le même moteur d'extraction que
    l'analyse principale de PC Hunter.

    Important :
    les annonces réelles ParuVendu/Vivastreet sont du texte
    libre. L'ancien market.py cherchait surtout des champs
    déjà écrits sous la forme "GPU: ... | CPU: ...", ce qui
    laissait beaucoup de colonnes vides.
    """
    detection = detecter_composants(
        annonce
    )

    gpu = premiere_valeur(
        detection.get(
            "gpu"
        )
    )

    cpu = premiere_valeur(
        detection.get(
            "cpu"
        )
    )

    ram = premiere_valeur(
        detection.get(
            "ram"
        )
    )

    stockage = joindre_valeurs(
        detection.get(
            "stockage"
        )
    )

    # Une machine complète peut contenir une information
    # plus précise que la détection générale.
    machine_portable = detection.get(
        "machine_portable_windows"
    )

    if machine_portable:
        gpu = (
            gpu
            or
            valeur_propre(
                machine_portable.get(
                    "gpu"
                )
            )
        )

        cpu = (
            cpu
            or
            valeur_propre(
                machine_portable.get(
                    "cpu"
                )
            )
        )

        ram = (
            ram
            or
            valeur_propre(
                machine_portable.get(
                    "ram"
                )
            )
        )

        stockage = (
            stockage
            or
            valeur_propre(
                machine_portable.get(
                    "stockage"
                )
            )
        )

    machine_apple = detection.get(
        "machine_apple"
    )

    if machine_apple:
        cpu = (
            cpu
            or
            valeur_propre(
                machine_apple.get(
                    "cpu"
                )
            )
            or
            valeur_propre(
                machine_apple.get(
                    "puce"
                )
            )
        )

        ram = (
            ram
            or
            valeur_propre(
                machine_apple.get(
                    "ram"
                )
            )
        )

        stockage = (
            stockage
            or
            valeur_propre(
                machine_apple.get(
                    "stockage"
                )
            )
        )

    # Fallback pour les anciennes données déjà structurées.
    description = (
        getattr(
            annonce,
            "description",
            "",
        )
        or ""
    )

    gpu = (
        gpu
        or
        extraire_valeur_description(
            description,
            "GPU",
        )
    )

    cpu = (
        cpu
        or
        extraire_valeur_description(
            description,
            "CPU",
        )
    )

    ram = (
        ram
        or
        extraire_valeur_description(
            description,
            "RAM",
        )
    )

    if not stockage:
        ssd = extraire_valeur_description(
            description,
            "SSD",
        )

        hdd = extraire_valeur_description(
            description,
            "HDD",
        )

        stockage_parts = []

        if ssd:
            stockage_parts.append(
                f"SSD {ssd}"
            )

        if hdd:
            stockage_parts.append(
                f"HDD {hdd}"
            )

        if stockage_parts:
            stockage = " + ".join(
                stockage_parts
            )

    return {
        "gpu": gpu,
        "cpu": cpu,
        "ram": ram,
        "stockage": stockage,
    }


# ============================================================
# COMPARABLES DE MARCHE - SIGNATURE STRICTE V1
# ============================================================

def resultat_comparables_vide():
    return {
        "nombre_comparables": 0,
        "prix_minimum": None,
        "prix_median": None,
        "prix_maximum": None,
    }


def normaliser_reference_marche(
    valeur,
):
    if valeur is None:
        return None

    normalisee = re.sub(
        r"[^a-z0-9]+",
        "",
        normaliser_texte(
            valeur
        ),
    )

    return normalisee or None


def extraire_capacite_go_marche(
    valeur,
):
    if not valeur:
        return None

    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*"
        r"(to|tb|go|gb)\b",
        normaliser_texte(
            valeur
        ),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    try:
        capacite = float(
            match.group(1)
            .replace(
                ",",
                ".",
            )
        )

    except ValueError:
        return None

    if match.group(2).lower() in {
        "to",
        "tb",
    }:
        capacite *= 1024

    return round(
        capacite
    )


def tranche_stockage_marche(
    capacite_go,
):
    if capacite_go is None:
        return None

    if capacite_go <= 256:
        return "LE_256"

    if capacite_go <= 512:
        return "257_512"

    if capacite_go <= 1024:
        return "513_1024"

    return "GT_1024"


def normaliser_stockage_marche(
    valeurs,
    technologie_defaut=None,
):
    if not valeurs:
        return None

    if not isinstance(
        valeurs,
        (
            list,
            tuple,
            set,
        ),
    ):
        valeurs = [
            valeurs
        ]

    stockages = []

    for valeur in valeurs:
        texte = normaliser_texte(
            valeur
        )

        if "nvme" in texte:
            technologie = "NVME"

        elif "ssd" in texte:
            technologie = "SSD"

        elif (
            "hdd" in texte
            or
            "disque dur" in texte
        ):
            technologie = "HDD"

        else:
            technologie = (
                technologie_defaut
            )

        tranche = tranche_stockage_marche(
            extraire_capacite_go_marche(
                valeur
            )
        )

        if (
            technologie is None
            or
            tranche is None
        ):
            return None

        signature_stockage = (
            technologie,
            tranche,
        )

        if signature_stockage not in stockages:
            stockages.append(
                signature_stockage
            )

    return tuple(
        sorted(
            stockages
        )
    )


def normaliser_ecran_marche(
    valeur,
):
    if not valeur:
        return None

    match = re.search(
        r"(\d+(?:[.,]\d+)?)",
        str(
            valeur
        ),
    )

    if not match:
        return None

    try:
        taille = float(
            match.group(1)
            .replace(
                ",",
                ".",
            )
        )

    except ValueError:
        return None

    return round(
        taille,
        1,
    )


def cpu_marche_est_precis(
    valeur,
):
    if not valeur:
        return False

    return bool(
        re.search(
            r"\d{4,5}",
            str(
                valeur
            ),
        )
    )


def construire_signature_marche(
    annonce,
):
    classification = classer_annonce(
        annonce
    )

    if not isinstance(
        classification,
        dict,
    ):
        return None

    detection = classification.get(
        "detection"
    )

    # Le contrat actuel du classifieur fournit la detection.
    # Ce garde-fou conserve cependant l'independance du moteur
    # marche si ce contrat evolue plus tard.
    if not isinstance(
        detection,
        dict,
    ):
        detection = detecter_composants(
            annonce
        )

    machine_apple = detection.get(
        "machine_apple"
    )

    machine_portable = detection.get(
        "machine_portable_windows"
    )

    if (
        not classification.get(
            "analyse_pc",
            False,
        )
        and
        not machine_apple
    ):
        return None

    ram = premiere_valeur(
        detection.get(
            "ram"
        )
    )

    ram_go = extraire_capacite_go_marche(
        ram
    )

    if ram_go is None:
        return None

    # --------------------------------------------------------
    # APPLE
    # --------------------------------------------------------

    if machine_apple:
        modele = machine_apple.get(
            "modele"
        )

        puce = machine_apple.get(
            "puce"
        )

        stockage = normaliser_stockage_marche(
            detection.get(
                "stockage"
            )
            or
            machine_apple.get(
                "stockage"
            ),
            technologie_defaut=(
                "SSD"
                if puce
                else None
            ),
        )

        if (
            not modele
            or
            stockage is None
        ):
            return None

        ecran = normaliser_ecran_marche(
            machine_apple.get(
                "ecran"
            )
        )

        if modele in {
            "MacBook Air",
            "MacBook Pro",
            "iMac",
        } and ecran is None:
            return None

        if puce:
            return (
                "APPLE_SILICON",
                modele,
                normaliser_reference_marche(
                    puce
                ),
                ram_go,
                stockage,
                ecran,
            )

        annee = machine_apple.get(
            "annee"
        )

        cpu = machine_apple.get(
            "cpu"
        ) or premiere_valeur(
            detection.get(
                "cpu"
            )
        )

        if (
            annee is None
            or
            not cpu_marche_est_precis(
                cpu
            )
        ):
            return None

        return (
            "APPLE_INTEL",
            modele,
            int(
                annee
            ),
            normaliser_reference_marche(
                cpu
            ),
            ram_go,
            stockage,
            ecran,
        )

    # --------------------------------------------------------
    # PORTABLE WINDOWS
    # --------------------------------------------------------

    if machine_portable:
        cpu = machine_portable.get(
            "cpu"
        )

        if not cpu_marche_est_precis(
            cpu
        ):
            return None

        marque = machine_portable.get(
            "marque"
        )

        gamme = machine_portable.get(
            "gamme"
        )

        ecran = normaliser_ecran_marche(
            machine_portable.get(
                "ecran"
            )
        )

        stockage = normaliser_stockage_marche(
            detection.get(
                "stockage"
            )
            or
            machine_portable.get(
                "stockage"
            )
        )

        if (
            not marque
            or
            ecran is None
            or
            stockage is None
        ):
            return None

        gpu = machine_portable.get(
            "gpu"
        )

        gpu_requis = (
            classification.get(
                "categorie"
            )
            == "PORTABLE_GAMING"
            or
            gamme
            in GAMMES_PORTABLES_GPU_REQUIS
        )

        if (
            gpu_requis
            and
            not gpu
        ):
            return None

        return (
            "PORTABLE_WINDOWS",
            normaliser_reference_marche(
                marque
            ),
            normaliser_reference_marche(
                gamme
            ),
            normaliser_reference_marche(
                cpu
            ),
            normaliser_reference_marche(
                gpu
            ),
            ram_go,
            stockage,
            ecran,
        )

    # --------------------------------------------------------
    # DESKTOP
    # --------------------------------------------------------

    categorie = classification.get(
        "categorie"
    )

    if categorie not in {
        "PC_COMPLET",
        "PC_GAMING",
    }:
        return None

    texte = normaliser_texte(
        " ".join(
            (
                str(
                    getattr(
                        annonce,
                        "titre",
                        "",
                    )
                    or ""
                ),
                str(
                    getattr(
                        annonce,
                        "description",
                        "",
                    )
                    or ""
                ),
            )
        )
    )

    if any(
        marqueur in texte
        for marqueur in (
            "tout en un",
            "all in one",
            "all-in-one",
        )
    ):
        return None

    cpu = premiere_valeur(
        detection.get(
            "cpu"
        )
    )

    if not cpu_marche_est_precis(
        cpu
    ):
        return None

    gpu = premiere_valeur(
        detection.get(
            "gpu"
        )
    )

    if (
        categorie == "PC_GAMING"
        and
        not gpu
    ):
        return None

    stockage = normaliser_stockage_marche(
        detection.get(
            "stockage"
        )
    )

    if stockage is None:
        return None

    return (
        "DESKTOP",
        normaliser_reference_marche(
            cpu
        ),
        normaliser_reference_marche(
            gpu
        ),
        ram_go,
        stockage,
    )


def signature_compatible_avec_estimation(
    signature,
    estimation,
):
    if (
        not signature
        or
        not isinstance(
            estimation,
            dict,
        )
    ):
        return False

    mode = estimation.get(
        "mode_valorisation"
    )

    type_signature = signature[0]

    if mode == "machine_complete_apple":
        return type_signature in {
            "APPLE_SILICON",
            "APPLE_INTEL",
        }

    if mode == "machine_complete_portable_windows":
        return (
            type_signature
            == "PORTABLE_WINDOWS"
        )

    if mode == "composants_desktop":
        return (
            type_signature
            == "DESKTOP"
        )

    return False


def calculer_comparables_marche(
    annonce,
    estimation,
):
    resultat_vide = resultat_comparables_vide()

    signature_annonce = construire_signature_marche(
        annonce
    )

    if not signature_compatible_avec_estimation(
        signature_annonce,
        estimation,
    ):
        return resultat_vide

    with closing(
        connexion_db_lecture_seule()
    ) as connexion:
        lignes = connexion.execute(
            """
            SELECT
                observation.plateforme,
                observation.identifiant,
                observation.titre,
                observation.prix,
                observation.description,
                observation.localisation,
                observation.url

            FROM observations_marche AS observation

            INNER JOIN annonces AS annonce_courante
                ON annonce_courante.plateforme =
                   observation.plateforme
               AND annonce_courante.identifiant =
                   observation.identifiant
               AND annonce_courante.prix_actuel =
                   observation.prix

            WHERE observation.plateforme IN (?, ?)

              AND NOT (
                  observation.plateforme = ?
                  AND observation.identifiant = ?
              )

              AND observation.id = (
                  SELECT MAX(observation_version.id)

                  FROM observations_marche
                       AS observation_version

                  WHERE observation_version.plateforme =
                        observation.plateforme
                    AND observation_version.identifiant =
                        observation.identifiant
                    AND observation_version.prix =
                        annonce_courante.prix_actuel
              )

            ORDER BY observation.id
            """,
            (
                *PLATEFORMES_COMPARABLES,
                str(
                    getattr(
                        annonce,
                        "plateforme",
                        "",
                    )
                ),
                str(
                    getattr(
                        annonce,
                        "identifiant",
                        "",
                    )
                ),
            ),
        ).fetchall()

    prix_comparables = []

    for ligne in lignes:
        prix = float(
            ligne["prix"]
        )

        if not (
            PRIX_MINIMUM_COMPARABLE
            <= prix
            <= PRIX_MAXIMUM_COMPARABLE
        ):
            continue

        comparable = SimpleNamespace(
            plateforme=ligne[
                "plateforme"
            ],
            identifiant=ligne[
                "identifiant"
            ],
            titre=ligne[
                "titre"
            ]
            or "",
            prix=prix,
            description=ligne[
                "description"
            ]
            or "",
            localisation=ligne[
                "localisation"
            ]
            or "Inconnue",
            url=ligne[
                "url"
            ],
        )

        signature_comparable = (
            construire_signature_marche(
                comparable
            )
        )

        if (
            signature_comparable
            != signature_annonce
        ):
            continue

        prix_comparables.append(
            prix
        )

    if not prix_comparables:
        return resultat_vide

    prix_ordonnes = sorted(
        prix_comparables
    )

    return {
        "nombre_comparables":
            len(
                prix_ordonnes
            ),

        "prix_minimum":
            round(
                prix_ordonnes[0],
                2,
            ),

        "prix_median":
            round(
                float(
                    median(
                        prix_ordonnes
                    )
                ),
                2,
            ),

        "prix_maximum":
            round(
                prix_ordonnes[-1],
                2,
            ),
    }


# ============================================================
# ENREGISTREMENT
# ============================================================

def enregistrer_observation(
    annonce,
):
    initialiser_market()

    description = (
        annonce.description
        or ""
    )

    composants = (
        extraire_composants_marche(
            annonce
        )
    )

    plateforme = str(
        annonce.plateforme
    )

    identifiant = str(
        annonce.identifiant
    )

    prix = float(
        annonce.prix
    )

    with connexion_db() as connexion:
        existait = (
            connexion.execute(
                """
                SELECT 1
                FROM observations_marche
                WHERE plateforme = ?
                  AND identifiant = ?
                  AND prix = ?
                LIMIT 1
                """,
                (
                    plateforme,
                    identifiant,
                    prix,
                ),
            ).fetchone()
            is not None
        )

        connexion.execute(
            """
            INSERT INTO observations_marche (
                plateforme,
                identifiant,

                titre,
                prix,

                description,
                localisation,
                url,

                gpu,
                cpu,
                ram,
                stockage,

                date_observation
            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )

            ON CONFLICT (
                plateforme,
                identifiant,
                prix
            )

            DO UPDATE SET
                titre = excluded.titre,
                description = excluded.description,
                localisation = excluded.localisation,
                url = excluded.url,

                gpu = COALESCE(
                    excluded.gpu,
                    observations_marche.gpu
                ),

                cpu = COALESCE(
                    excluded.cpu,
                    observations_marche.cpu
                ),

                ram = COALESCE(
                    excluded.ram,
                    observations_marche.ram
                ),

                stockage = COALESCE(
                    excluded.stockage,
                    observations_marche.stockage
                )
            """,
            (
                plateforme,
                identifiant,

                annonce.titre,
                prix,

                description,
                annonce.localisation,
                annonce.url,

                composants["gpu"],
                composants["cpu"],
                composants["ram"],
                composants["stockage"],

                maintenant_iso(),
            ),
        )

    # Même si une ancienne ligne est enrichie,
    # on ne la compte pas comme une nouvelle observation.
    return not existait


# ============================================================
# ENREGISTREMENT D'UN SCAN COMPLET
# ============================================================

def enregistrer_observations(
    annonces,
):
    nouvelles = 0

    for annonce in annonces:
        if enregistrer_observation(
            annonce
        ):
            nouvelles += 1

    return nouvelles


# ============================================================
# ENRICHISSEMENT DES ANCIENNES OBSERVATIONS
# ============================================================

def enrichir_observations_existantes():
    """
    Relit les lignes déjà présentes dans observations_marche
    et tente de remplir GPU/CPU/RAM/stockage avec le moteur
    actuel de components.py.

    Aucun historique n'est supprimé.
    Aucun prix n'est modifié.
    """
    initialiser_market()

    with connexion_db() as connexion:
        lignes = connexion.execute(
            """
            SELECT
                id,
                plateforme,
                identifiant,
                titre,
                prix,
                description,
                localisation,
                url,
                gpu,
                cpu,
                ram,
                stockage

            FROM observations_marche

            ORDER BY id
            """
        ).fetchall()

        mises_a_jour = 0

        for ligne in lignes:
            annonce = SimpleNamespace(
                plateforme=ligne[
                    "plateforme"
                ],
                identifiant=ligne[
                    "identifiant"
                ],
                titre=ligne[
                    "titre"
                ]
                or "",
                prix=ligne[
                    "prix"
                ],
                description=ligne[
                    "description"
                ]
                or "",
                localisation=ligne[
                    "localisation"
                ]
                or "Inconnue",
                url=ligne[
                    "url"
                ],
            )

            composants = (
                extraire_composants_marche(
                    annonce
                )
            )

            nouveau_gpu = (
                composants["gpu"]
                or
                ligne["gpu"]
            )

            nouveau_cpu = (
                composants["cpu"]
                or
                ligne["cpu"]
            )

            nouvelle_ram = (
                composants["ram"]
                or
                ligne["ram"]
            )

            nouveau_stockage = (
                composants["stockage"]
                or
                ligne["stockage"]
            )

            avant = (
                ligne["gpu"],
                ligne["cpu"],
                ligne["ram"],
                ligne["stockage"],
            )

            apres = (
                nouveau_gpu,
                nouveau_cpu,
                nouvelle_ram,
                nouveau_stockage,
            )

            if apres == avant:
                continue

            connexion.execute(
                """
                UPDATE observations_marche
                SET
                    gpu = ?,
                    cpu = ?,
                    ram = ?,
                    stockage = ?
                WHERE id = ?
                """,
                (
                    nouveau_gpu,
                    nouveau_cpu,
                    nouvelle_ram,
                    nouveau_stockage,
                    ligne["id"],
                ),
            )

            mises_a_jour += 1

    return mises_a_jour


# ============================================================
# STATISTIQUES
# ============================================================

def statistiques_market():
    initialiser_market()

    with connexion_db() as connexion:
        total = connexion.execute(
            """
            SELECT COUNT(*)
            FROM observations_marche
            """
        ).fetchone()[0]

        sources = connexion.execute(
            """
            SELECT
                plateforme,
                COUNT(*) AS nombre

            FROM observations_marche

            GROUP BY plateforme

            ORDER BY nombre DESC
            """
        ).fetchall()

        qualite = connexion.execute(
            """
            SELECT
                SUM(
                    CASE
                        WHEN gpu IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS avec_gpu,

                SUM(
                    CASE
                        WHEN cpu IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS avec_cpu,

                SUM(
                    CASE
                        WHEN ram IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS avec_ram,

                SUM(
                    CASE
                        WHEN stockage IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS avec_stockage

            FROM observations_marche
            """
        ).fetchone()

    return {
        "total":
            total,

        "sources":
            [
                dict(
                    ligne
                )
                for ligne
                in sources
            ],

        "qualite": {
            "avec_gpu":
                int(
                    qualite["avec_gpu"]
                    or 0
                ),

            "avec_cpu":
                int(
                    qualite["avec_cpu"]
                    or 0
                ),

            "avec_ram":
                int(
                    qualite["avec_ram"]
                    or 0
                ),

            "avec_stockage":
                int(
                    qualite["avec_stockage"]
                    or 0
                ),
        },
    }


# ============================================================
# TEST MANUEL
# ============================================================

if __name__ == "__main__":
    mises_a_jour = (
        enrichir_observations_existantes()
    )

    stats = (
        statistiques_market()
    )

    print()
    print(
        "========================================"
    )
    print(
        "📊 PC HUNTER - MARKET"
    )
    print(
        "========================================"
    )
    print(
        "🧠 Anciennes observations enrichies :",
        mises_a_jour,
    )
    print(
        "📦 Observations totales :",
        stats["total"],
    )

    print()
    print(
        "Sources :"
    )

    for source in stats[
        "sources"
    ]:
        print(
            f"- {source['plateforme']} : "
            f"{source['nombre']}"
        )

    print()
    print(
        "Qualité des données :"
    )
    print(
        "- GPU renseigné :",
        stats["qualite"][
            "avec_gpu"
        ],
    )
    print(
        "- CPU renseigné :",
        stats["qualite"][
            "avec_cpu"
        ],
    )
    print(
        "- RAM renseignée :",
        stats["qualite"][
            "avec_ram"
        ],
    )
    print(
        "- Stockage renseigné :",
        stats["qualite"][
            "avec_stockage"
        ],
    )
