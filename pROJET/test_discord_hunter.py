import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from analyzer.instant import analyser_annonce_immediate
from collector.models import Annonce
from database.watchlist import ajouter_watchlist
from discord_hunter import (
    construire_message_analyse,
    construire_message_disparues,
    construire_message_pepites,
    construire_message_sources,
    construire_message_veille,
)


class DiscordHunterV15Tests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporaire.name) / "discord_v15.db"

    def tearDown(self):
        self.temporaire.cleanup()

    @patch("analyzer.instant.calculer_comparables_marche")
    def test_messages_analyse_pepites_et_veille(self, comparables):
        comparables.return_value = {
            "nombre_comparables": 4,
            "prix_minimum": 500,
            "prix_median": 600,
            "prix_maximum": 700,
        }
        annonce = Annonce(
            identifiant="DISCORD-V15",
            titre="PC gamer Ryzen 5 5600 RTX 3060",
            prix=200,
            description="16 Go DDR4 SSD NVMe 1 To",
            localisation="Rochefort 17300",
            plateforme="Test",
            url="https://example.test/discord-v15",
        )
        analyser_annonce_immediate(
            annonce,
            db_path=self.db_path,
            inclure_ia=False,
        )
        ajouter_watchlist(
            annonce.url,
            titre=annonce.titre,
            prix_connu=annonce.prix,
            db_path=self.db_path,
        )

        self.assertIn("ANALYSE HUNTER V1.5", construire_message_analyse("DISCORD-V15", self.db_path))
        self.assertIn("TOP 3", construire_message_pepites(db_path=self.db_path))
        self.assertIn("VEILLE HUNTER", construire_message_veille(db_path=self.db_path))
        self.assertIn("SOURCES HUNTER V1.5", construire_message_sources())

    def test_disparition_explique_qu_elle_n_est_pas_une_vente(self):
        with closing(sqlite3.connect(self.db_path)) as connexion:
            with connexion:
                connexion.execute(
                    """
                    CREATE TABLE presence_annonces (
                        titre TEXT, prix REAL, plateforme TEXT, url TEXT,
                        date_disparition TEXT, active INTEGER
                    )
                    """
                )
                connexion.execute(
                    "INSERT INTO presence_annonces VALUES (?, ?, ?, ?, ?, 0)",
                    ("PC disparu", 250, "Test", "https://example.test/x", "2026-08-10T10:00:00"),
                )
        message = construire_message_disparues(db_path=self.db_path)
        self.assertIn("plus vue", message)
        self.assertIn("vente, retrait, expiration", message)


if __name__ == "__main__":
    unittest.main()
