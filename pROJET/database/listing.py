import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pc_hunter.db"


# ============================================================
# CONNEXION
# ============================================================

def connexion_db():

    connexion = sqlite3.connect(
        DB_PATH
    )

    connexion.row_factory = sqlite3.Row

    return connexion


# ============================================================
# INITIALISATION
# ============================================================

def initialiser_database():

    connexion = connexion_db()
    curseur = connexion.cursor()

    curseur.execute(
        """
        CREATE TABLE IF NOT EXISTS annonces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            identifiant TEXT UNIQUE,
            plateforme TEXT,

            titre TEXT,
            description TEXT,
            localisation TEXT,
            url TEXT,

            prix_initial REAL,
            prix_actuel REAL,

            premiere_detection TEXT,
            derniere_detection TEXT
        )
        """
    )

    curseur.execute(
        """
        CREATE TABLE IF NOT EXISTS historique_prix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            identifiant_annonce TEXT,
            prix REAL,
            date_detection TEXT
        )
        """
    )

    connexion.commit()
    connexion.close()


# ============================================================
# DATE ACTUELLE
# ============================================================

def maintenant_iso():

    return (
        datetime
        .now()
        .astimezone()
        .isoformat(
            timespec="seconds"
        )
    )


# ============================================================
# ENREGISTRER / METTRE À JOUR UNE ANNONCE
# ============================================================

def enregistrer_annonce(annonce):

    maintenant = maintenant_iso()

    connexion = connexion_db()
    curseur = connexion.cursor()


    # --------------------------------------------------------
    # RECHERCHE
    # --------------------------------------------------------

    curseur.execute(
        """
        SELECT *
        FROM annonces
        WHERE identifiant = ?
        """,
        (
            annonce.identifiant,
        )
    )

    ancienne_annonce = (
        curseur.fetchone()
    )


    # ========================================================
    # NOUVELLE ANNONCE
    # ========================================================

    if ancienne_annonce is None:

        curseur.execute(
            """
            INSERT INTO annonces (
                identifiant,
                plateforme,
                titre,
                description,
                localisation,
                url,
                prix_initial,
                prix_actuel,
                premiere_detection,
                derniere_detection
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annonce.identifiant,
                annonce.plateforme,
                annonce.titre,
                annonce.description,
                annonce.localisation,
                annonce.url,
                annonce.prix,
                annonce.prix,
                maintenant,
                maintenant
            )
        )


        # Premier prix connu
        curseur.execute(
            """
            INSERT INTO historique_prix (
                identifiant_annonce,
                prix,
                date_detection
            )
            VALUES (?, ?, ?)
            """,
            (
                annonce.identifiant,
                annonce.prix,
                maintenant
            )
        )

        connexion.commit()
        connexion.close()


        return {
            "statut": "nouvelle",

            "est_nouvelle": True,

            "ancien_prix": None,
            "nouveau_prix": annonce.prix,

            "premiere_detection":
                maintenant,

            "derniere_detection":
                maintenant
        }


    # ========================================================
    # ANNONCE DÉJÀ CONNUE
    # ========================================================

    ancien_prix = float(
        ancienne_annonce[
            "prix_actuel"
        ]
    )

    premiere_detection = (
        ancienne_annonce[
            "premiere_detection"
        ]
    )


    # Mise à jour des informations
    curseur.execute(
        """
        UPDATE annonces
        SET
            plateforme = ?,
            titre = ?,
            description = ?,
            localisation = ?,
            url = ?,
            prix_actuel = ?,
            derniere_detection = ?
        WHERE identifiant = ?
        """,
        (
            annonce.plateforme,
            annonce.titre,
            annonce.description,
            annonce.localisation,
            annonce.url,
            annonce.prix,
            maintenant,
            annonce.identifiant
        )
    )


    # ========================================================
    # CHANGEMENT DE PRIX
    # ========================================================

    if float(annonce.prix) != ancien_prix:

        curseur.execute(
            """
            INSERT INTO historique_prix (
                identifiant_annonce,
                prix,
                date_detection
            )
            VALUES (?, ?, ?)
            """,
            (
                annonce.identifiant,
                annonce.prix,
                maintenant
            )
        )


    connexion.commit()
    connexion.close()


    # ========================================================
    # BAISSE
    # ========================================================

    if float(annonce.prix) < ancien_prix:

        return {
            "statut": "baisse",

            "est_nouvelle": False,

            "ancien_prix":
                ancien_prix,

            "nouveau_prix":
                annonce.prix,

            "premiere_detection":
                premiere_detection,

            "derniere_detection":
                maintenant
        }


    # ========================================================
    # HAUSSE
    # ========================================================

    if float(annonce.prix) > ancien_prix:

        return {
            "statut": "hausse",

            "est_nouvelle": False,

            "ancien_prix":
                ancien_prix,

            "nouveau_prix":
                annonce.prix,

            "premiere_detection":
                premiere_detection,

            "derniere_detection":
                maintenant
        }


    # ========================================================
    # CONNUE, SANS CHANGEMENT
    # ========================================================

    return {
        "statut": "connue",

        "est_nouvelle": False,

        "ancien_prix":
            ancien_prix,

        "nouveau_prix":
            annonce.prix,

        "premiere_detection":
            premiere_detection,

        "derniere_detection":
            maintenant
    }


# ============================================================
# HISTORIQUE DES PRIX
# ============================================================

def obtenir_historique_prix(
    identifiant
):

    connexion = connexion_db()
    curseur = connexion.cursor()

    curseur.execute(
        """
        SELECT
            prix,
            date_detection

        FROM historique_prix

        WHERE identifiant_annonce = ?

        ORDER BY date_detection ASC
        """,
        (
            identifiant,
        )
    )

    lignes = curseur.fetchall()

    connexion.close()


    return [
        {
            "prix":
                ligne["prix"],

            "date":
                ligne[
                    "date_detection"
                ]
        }

        for ligne in lignes
    ]


# ============================================================
# INFORMATIONS DE DÉTECTION
# ============================================================

def obtenir_infos_detection(
    identifiant
):

    connexion = connexion_db()
    curseur = connexion.cursor()

    curseur.execute(
        """
        SELECT
            premiere_detection,
            derniere_detection

        FROM annonces

        WHERE identifiant = ?
        """,
        (
            identifiant,
        )
    )

    ligne = curseur.fetchone()

    connexion.close()


    if ligne is None:

        return None


    return {
        "premiere_detection":
            ligne[
                "premiere_detection"
            ],

        "derniere_detection":
            ligne[
                "derniere_detection"
            ]
    }