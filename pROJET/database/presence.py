import sqlite3
from contextlib import contextmanager
from datetime import datetime

from database.listing import DB_PATH


# ============================================================
# OUTILS
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


@contextmanager
def connexion_db_fermee():

    connexion = connexion_db()

    try:

        with connexion:
            yield connexion

    finally:

        connexion.close()


# ============================================================
# INITIALISATION TABLE DE PRÉSENCE
# ============================================================

def initialiser_presence():

    with connexion_db_fermee() as connexion:

        connexion.execute(
            """
            CREATE TABLE IF NOT EXISTS presence_annonces (
                plateforme TEXT NOT NULL,
                identifiant TEXT NOT NULL,

                titre TEXT,
                prix REAL,
                localisation TEXT,
                url TEXT,

                premiere_vue TEXT NOT NULL,
                derniere_vue TEXT NOT NULL,

                active INTEGER NOT NULL DEFAULT 1,
                date_disparition TEXT,
                absences_consecutives INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (
                    plateforme,
                    identifiant
                )
            )
            """
        )

        colonnes = {
            ligne["name"]
            for ligne in connexion.execute(
                "PRAGMA table_info(presence_annonces)"
            ).fetchall()
        }

        if "absences_consecutives" not in colonnes:

            connexion.execute(
                """
                ALTER TABLE presence_annonces
                ADD COLUMN absences_consecutives INTEGER
                NOT NULL DEFAULT 0
                """
            )


# ============================================================
# MISE À JOUR DE LA PRÉSENCE
# ============================================================

def mettre_a_jour_presence(
    annonces,
    plateformes_valides=None,
    seuil_absences=2,
):

    initialiser_presence()

    maintenant = maintenant_iso()

    evenements = {
        "disparues": [],
        "reapparues": [],
    }


    # ========================================================
    # SÉCURITÉ
    #
    # Si la source renvoie zéro annonce à cause :
    # - d'une erreur JSON
    # - d'une erreur API
    # - d'un problème réseau
    #
    # on ne marque PAS toutes les annonces comme disparues.
    # ========================================================

    if not annonces:

        return evenements


    cles_actuelles = set()

    plateformes_observees = {
        str(annonce.plateforme)
        for annonce in annonces
    }

    if plateformes_valides is None:

        plateformes_valides = (
            plateformes_observees
        )

    else:

        plateformes_valides = {
            str(plateforme)
            for plateforme in plateformes_valides
        }

    seuil_absences = max(
        1,
        int(seuil_absences),
    )


    with connexion_db_fermee() as connexion:

        # ====================================================
        # ANNONCES PRÉSENTES DANS LE SCAN ACTUEL
        # ====================================================

        for annonce in annonces:

            plateforme = str(
                annonce.plateforme
            )

            identifiant = str(
                annonce.identifiant
            )


            cle = (
                plateforme,
                identifiant,
            )


            cles_actuelles.add(
                cle
            )


            ancienne = connexion.execute(
                """
                SELECT *
                FROM presence_annonces

                WHERE plateforme = ?
                AND identifiant = ?
                """,
                cle,
            ).fetchone()


            # =================================================
            # PREMIÈRE APPARITION DANS LE MODULE PRÉSENCE
            # =================================================

            if ancienne is None:

                connexion.execute(
                    """
                    INSERT INTO presence_annonces (
                        plateforme,
                        identifiant,

                        titre,
                        prix,
                        localisation,
                        url,

                        premiere_vue,
                        derniere_vue,

                        active,
                        date_disparition,
                        absences_consecutives
                    )

                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, 0
                    )
                    """,
                    (
                        plateforme,
                        identifiant,

                        annonce.titre,
                        annonce.prix,
                        annonce.localisation,
                        annonce.url,

                        maintenant,
                        maintenant,
                    ),
                )

                continue


            # =================================================
            # ANNONCE QUI ÉTAIT DISPARUE ET QUI REVIENT
            # =================================================

            if ancienne["active"] == 0:

                evenements[
                    "reapparues"
                ].append(
                    {
                        "plateforme":
                            plateforme,

                        "identifiant":
                            identifiant,

                        "titre":
                            annonce.titre,

                        "prix":
                            annonce.prix,

                        "localisation":
                            annonce.localisation,

                        "url":
                            annonce.url,

                        "date_disparition":
                            ancienne[
                                "date_disparition"
                            ],
                    }
                )


            # =================================================
            # ANNONCE TOUJOURS PRÉSENTE / RÉAPPARUE
            # =================================================

            connexion.execute(
                """
                UPDATE presence_annonces

                SET
                    titre = ?,
                    prix = ?,
                    localisation = ?,
                    url = ?,

                    derniere_vue = ?,

                    active = 1,
                    date_disparition = NULL,
                    absences_consecutives = 0

                WHERE plateforme = ?
                AND identifiant = ?
                """,
                (
                    annonce.titre,
                    annonce.prix,
                    annonce.localisation,
                    annonce.url,

                    maintenant,

                    plateforme,
                    identifiant,
                ),
            )


        # ====================================================
        # RECHERCHE DES ANNONCES QUI ÉTAIENT ACTIVES
        # MAIS QUI NE SONT PLUS DANS LE SCAN ACTUEL
        # ====================================================

        annonces_actives = connexion.execute(
            """
            SELECT *
            FROM presence_annonces

            WHERE active = 1
            """
        ).fetchall()


        for ancienne in annonces_actives:

            cle = (
                ancienne[
                    "plateforme"
                ],

                ancienne[
                    "identifiant"
                ],
            )


            # Elle existe encore
            if cle in cles_actuelles:

                continue


            # Une source totalement absente du scan est considérée
            # indisponible, pas vide. Elle ne peut donc pas faire
            # disparaître toutes ses annonces à la suite d'un 403,
            # d'une erreur réseau ou d'un cache inaccessible.
            if (
                ancienne["plateforme"]
                not in plateformes_valides
            ):

                continue


            absences_consecutives = (
                int(
                    ancienne[
                        "absences_consecutives"
                    ]
                    or 0
                )
                + 1
            )

            connexion.execute(
                """
                UPDATE presence_annonces

                SET absences_consecutives = ?

                WHERE plateforme = ?
                AND identifiant = ?
                """,
                (
                    absences_consecutives,
                    ancienne["plateforme"],
                    ancienne["identifiant"],
                ),
            )

            # Un seul scan incomplet ne suffit plus à déclarer
            # qu'une annonce a disparu.
            if absences_consecutives < seuil_absences:

                continue


            # =================================================
            # DISPARITION
            # =================================================

            connexion.execute(
                """
                UPDATE presence_annonces

                SET
                    active = 0,
                    date_disparition = ?,
                    absences_consecutives = ?

                WHERE plateforme = ?
                AND identifiant = ?
                """,
                (
                    maintenant,

                    absences_consecutives,

                    ancienne[
                        "plateforme"
                    ],

                    ancienne[
                        "identifiant"
                    ],
                ),
            )


            # =================================================
            # ÉVÉNEMENT DISPARITION
            # =================================================

            evenements[
                "disparues"
            ].append(
                {
                    "plateforme":
                        ancienne[
                            "plateforme"
                        ],

                    "identifiant":
                        ancienne[
                            "identifiant"
                        ],

                    "titre":
                        ancienne[
                            "titre"
                        ],

                    "prix":
                        ancienne[
                            "prix"
                        ],

                    "localisation":
                        ancienne[
                            "localisation"
                        ],

                    "url":
                        ancienne[
                            "url"
                        ],
                    "premiere_vue":
                        ancienne[  
                            "premiere_vue"
                        ],
                    "derniere_vue":
                        ancienne[
                            "derniere_vue"
                        ],

                    "date_disparition":
                        maintenant,
                }
            )


    return evenements

from datetime import datetime


def calculer_duree_vie(
    premiere_vue,
    derniere_vue
):

    try:

        debut = datetime.fromisoformat(
            premiere_vue
        )

        fin = datetime.fromisoformat(
            derniere_vue
        )

        secondes = max(
            0,
            int(
                (
                    fin - debut
                ).total_seconds()
            )
        )

        minutes = secondes // 60


        if minutes < 60:

            return (
                f"{minutes} min"
            )


        heures = (
            minutes // 60
        )

        minutes_restantes = (
            minutes % 60
        )


        if heures < 24:

            if minutes_restantes == 0:

                return (
                    f"{heures} h"
                )

            return (
                f"{heures} h "
                f"{minutes_restantes} min"
            )


        jours = (
            heures // 24
        )

        heures_restantes = (
            heures % 24
        )


        if heures_restantes == 0:

            return (
                f"{jours} jour(s)"
            )


        return (
            f"{jours} jour(s) "
            f"{heures_restantes} h"
        )


    except (
        ValueError,
        TypeError
    ):

        return "inconnue"
# ============================================================
# AFFICHAGE DES ÉVÉNEMENTS
# ============================================================

def afficher_evenements_presence(
    evenements
):

    disparues = evenements.get(
        "disparues",
        []
    )

    reapparues = evenements.get(
        "reapparues",
        []
    )


    # ========================================================
    # ANNONCES DISPARUES
    # ========================================================

    for annonce in disparues:

        print()
        print(
            "========================================"
        )

        print(
            "❌ ANNONCE DISPARUE DU SCAN"
        )

        print(
            "========================================"
        )


        print(
            "📝",
            annonce.get(
                "titre",
                "Titre inconnu"
            )
        )


        print(
            "🌐",
            annonce.get(
                "plateforme",
                "Plateforme inconnue"
            )
        )


        print(
            "💵 Dernier prix :",
            annonce.get(
                "prix",
                "?"
            ),
            "€"
        )


        localisation = annonce.get(
            "localisation"
        )

        if localisation:

            print(
                "📍",
                localisation
            )

        
        derniere_vue = annonce.get(
            "derniere_vue"
        )

        if derniere_vue:

            print(
                "🕒 Dernière vue :",
                derniere_vue
            )

            duree_vie = calculer_duree_vie(
            annonce.get(
                "premiere_vue"
            ),
            annonce.get(
                "derniere_vue"
            )
        )

        print(
    "⏳ Durée observée :",
    duree_vie
)
        print(
            "⚠️ Statut : disparition du scan, "
            "vente non confirmée"
        )


        print(
            "========================================"
        )


    # ========================================================
    # ANNONCES RÉAPPARUES
    # ========================================================

    for annonce in reapparues:

        print()
        print(
            "========================================"
        )

        print(
            "♻️ ANNONCE RÉAPPARUE"
        )

        print(
            "========================================"
        )


        print(
            "📝",
            annonce.get(
                "titre",
                "Titre inconnu"
            )
        )


        print(
            "🌐",
            annonce.get(
                "plateforme",
                "Plateforme inconnue"
            )
        )


        print(
            "💵 Prix actuel :",
            annonce.get(
                "prix",
                "?"
            ),
            "€"
        )


        localisation = annonce.get(
            "localisation"
        )

        if localisation:

            print(
                "📍",
                localisation
            )


        date_disparition = annonce.get(
            "date_disparition"
        )

        if date_disparition:

            print(
                "🕒 Était absente depuis :",
                date_disparition
            )


        print(
            "========================================"
        )
