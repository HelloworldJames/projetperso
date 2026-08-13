import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path

from database.watchlist import (
    ajouter_watchlist,
    annonces_watchlist_pour_analyse,
    desactiver_watchlist,
    initialiser_watchlist,
    lister_watchlist,
    marquer_notification_detection_envoyee,
    mettre_a_jour_prix,
    normaliser_url,
)


class WatchlistTests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporaire.name) / "watchlist_test.db"

    def tearDown(self):
        self.temporaire.cleanup()

    def test_ajout_leboncoin_detecte_plateforme_et_identifiant(self):
        annonce = ajouter_watchlist(
            "https://www.leboncoin.fr/vi/3247579720.htm"
            "#at_medium=email&utm_source=test",
            titre="PC Ryzen 5",
            description="Ryzen 5, 16 Go RAM, SSD 512 Go.",
            localisation="Rochefort 17300",
            prix_connu="300 €",
            db_path=self.db_path,
        )

        self.assertTrue(annonce["cree"])
        self.assertEqual(annonce["plateforme"], "Leboncoin")
        self.assertEqual(annonce["identifiant"], "3247579720")
        self.assertEqual(annonce["prix_connu"], 300)
        self.assertEqual(annonce["dernier_prix_connu"], 300)
        self.assertNotIn("at_medium", annonce["url"])
        self.assertNotIn("utm_source", annonce["url"])
        self.assertEqual(annonce["localisation"], "Rochefort 17300")
        self.assertFalse(annonce["notification_detection_envoyee"])

    def test_doublon_reactive_sans_creer_deux_lignes(self):
        premiere = ajouter_watchlist(
            "https://www.leboncoin.fr/ad/ordinateurs/1234567890",
            prix_connu=300,
            db_path=self.db_path,
        )
        self.assertTrue(
            desactiver_watchlist(
                premiere["id"],
                db_path=self.db_path,
            )
        )

        seconde = ajouter_watchlist(
            "https://www.leboncoin.fr/ad/ordinateurs/1234567890/",
            titre="PC complété manuellement",
            prix_connu=280,
            db_path=self.db_path,
        )

        annonces = lister_watchlist(
            actif=None,
            db_path=self.db_path,
        )
        self.assertFalse(seconde["cree"])
        self.assertTrue(seconde["actif"])
        self.assertEqual(seconde["prix_connu"], 300)
        self.assertEqual(seconde["dernier_prix_connu"], 280)
        self.assertEqual(len(annonces), 1)

    def test_mise_a_jour_prix_distingue_premier_prix_et_changement(self):
        annonce = ajouter_watchlist(
            "https://www.leboncoin.fr/vi/1111111111.htm",
            db_path=self.db_path,
        )

        premier = mettre_a_jour_prix(
            annonce["id"],
            300,
            db_path=self.db_path,
        )
        identique = mettre_a_jour_prix(
            annonce["id"],
            300,
            db_path=self.db_path,
        )
        changement = mettre_a_jour_prix(
            annonce["id"],
            260,
            db_path=self.db_path,
        )

        self.assertTrue(premier["premier_prix_connu"])
        self.assertFalse(premier["prix_change"])
        self.assertFalse(identique["prix_change"])
        self.assertTrue(changement["prix_change"])
        self.assertEqual(changement["ancien_prix"], 300)
        self.assertEqual(changement["nouveau_prix"], 260)

        with self.assertRaises(ValueError):
            mettre_a_jour_prix(
                annonce["id"],
                None,
                db_path=self.db_path,
            )

    def test_url_invalide_est_refusee(self):
        with self.assertRaises(ValueError):
            normaliser_url("pas-un-lien")

    def test_ajout_marketplace_detecte_plateforme_et_identifiant(self):
        annonce = ajouter_watchlist(
            "https://www.facebook.com/marketplace/item/1773289397189564/"
            "?ref=search&utm_source=test",
            titre="Appareil photo Canon",
            description="Annonce détectée depuis la catégorie électronique.",
            localisation="Lille",
            prix_connu=350,
            db_path=self.db_path,
        )

        self.assertEqual(annonce["plateforme"], "Facebook Marketplace")
        self.assertEqual(annonce["identifiant"], "1773289397189564")
        self.assertNotIn("utm_source", annonce["url"])

    def test_reinjection_accepte_fiche_minimale_et_conserve_origine(self):
        incomplete = ajouter_watchlist(
            "https://www.leboncoin.fr/vi/2222222222.htm",
            titre="PC incomplet",
            prix_connu=100,
            db_path=self.db_path,
        )
        complete = ajouter_watchlist(
            "https://www.leboncoin.fr/vi/3333333333.htm",
            titre="PC portable complet",
            description="Intel i5-11400, 16 Go RAM, SSD 512 Go.",
            localisation="Rochefort 17300",
            prix_connu=250,
            db_path=self.db_path,
        )

        self.assertEqual(
            marquer_notification_detection_envoyee(
                [complete["id"]],
                db_path=self.db_path,
            ),
            1,
        )

        annonces = annonces_watchlist_pour_analyse(
            db_path=self.db_path,
        )

        self.assertEqual(len(annonces), 2)
        par_identifiant = {
            annonce.identifiant: annonce
            for annonce in annonces
        }
        self.assertEqual(
            par_identifiant["2222222222"].localisation,
            "Inconnue",
        )
        self.assertEqual(
            par_identifiant["2222222222"].description,
            "PC incomplet",
        )
        self.assertTrue(par_identifiant["3333333333"].origine_watchlist)
        self.assertTrue(
            par_identifiant["3333333333"].notification_detection_deja_envoyee
        )
        self.assertNotEqual(incomplete["id"], complete["id"])

    def test_migration_ajoute_les_champs_aux_anciennes_watchlists(self):
        with closing(sqlite3.connect(self.db_path)) as connexion:
            with connexion:
                connexion.execute(
                    """
                    CREATE TABLE watchlist_annonces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plateforme TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        identifiant TEXT,
                        titre TEXT,
                        prix_connu REAL,
                        date_ajout TEXT NOT NULL,
                        dernier_prix_connu REAL,
                        derniere_observation TEXT,
                        actif INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )

        initialiser_watchlist(
            self.db_path
        )

        with closing(sqlite3.connect(self.db_path)) as connexion:
            colonnes = {
                ligne[1]
                for ligne in connexion.execute(
                    "PRAGMA table_info(watchlist_annonces)"
                ).fetchall()
            }

        self.assertTrue(
            {
                "description",
                "localisation",
                "date_publication",
                "notification_detection_envoyee",
                "date_notification_detection",
            }.issubset(colonnes)
        )


if __name__ == "__main__":
    unittest.main()
