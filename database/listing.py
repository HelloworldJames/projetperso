import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pc_hunter.db"


def connexion_db():

    connexion = sqlite3.connect(DB_PATH)

    connexion.row_factory = sqlite3.Row

    return connexion


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


def enregistrer_annonce(annonce):

    maintenant = datetime.now().isoformat(
        timespec="seconds"
    )

    connexion = connexion_db()
    curseur = connexion.cursor()

    curseur.execute(
        """
        SELECT *
        FROM annonces
        WHERE identifiant = ?
        """,
        (annonce.identifiant,)
    )

    ancienne_annonce = curseur.fetchone()


    # -------------------------------
    # NOUVELLE ANNONCE
    # -------------------------------

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
            "ancien_prix": None,
            "nouveau_prix": annonce.prix
        }


    # -------------------------------
    # ANNONCE DÉJÀ CONNUE
    # -------------------------------

    ancien_prix = ancienne_annonce["prix_actuel"]

    curseur.execute(
        """
        UPDATE annonces
        SET
            prix_actuel = ?,
            derniere_detection = ?,
            titre = ?,
            description = ?,
            localisation = ?
        WHERE identifiant = ?
        """,
        (
            annonce.prix,
            maintenant,
            annonce.titre,
            annonce.description,
            annonce.localisation,
            annonce.identifiant
        )
    )


    # -------------------------------
    # CHANGEMENT DE PRIX
    # -------------------------------

    if annonce.prix != ancien_prix:

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


    if annonce.prix < ancien_prix:

        return {
            "statut": "baisse",
            "ancien_prix": ancien_prix,
            "nouveau_prix": annonce.prix
        }

    elif annonce.prix > ancien_prix:

        return {
            "statut": "hausse",
            "ancien_prix": ancien_prix,
            "nouveau_prix": annonce.prix
        }

    return {
        "statut": "connue",
        "ancien_prix": ancien_prix,
        "nouveau_prix": annonce.prix
    }
def obtenir_historique_prix(identifiant):

    connexion = connexion_db()
    curseur = connexion.cursor()

    curseur.execute(
        """
        SELECT prix, date_detection
        FROM historique_prix
        WHERE identifiant_annonce = ?
        ORDER BY date_detection ASC
        """,
        (identifiant,)
    )

    lignes = curseur.fetchall()

    connexion.close()

    return [
        {
            "prix": ligne["prix"],
            "date": ligne["date_detection"]
        }
        for ligne in lignes
    ]