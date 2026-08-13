import os
import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault(
    "DISCORD_BOT_TOKEN",
    "test-token",
)
os.environ.setdefault(
    "DISCORD_GUILD_ID",
    "1",
)

import bot_discord


class BotDiscordWatchlistTests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporaire.name) / "watchlist.db"

    def tearDown(self):
        self.temporaire.cleanup()

    def test_url_seule_reste_en_etude(self):
        annonce = bot_discord.ajouter_url_watchlist_discord(
            "https://www.leboncoin.fr/ad/ordinateurs/1234567890",
            db_path=self.db_path,
        )
        message = bot_discord.construire_message_ajout_watchlist(
            annonce
        )

        self.assertTrue(annonce["cree"])
        self.assertEqual(annonce["plateforme"], "Leboncoin")
        self.assertIn("en etude", message)
        self.assertIn("titre, prix, description, localisation", message)

    def test_meme_url_complete_la_fiche_pour_le_prochain_scan(self):
        url = "https://www.leboncoin.fr/ad/ordinateurs/1234567890"
        bot_discord.ajouter_url_watchlist_discord(
            url,
            db_path=self.db_path,
        )
        annonce = bot_discord.ajouter_url_watchlist_discord(
            url,
            titre="PC Ryzen 5",
            prix=300,
            description="Ryzen 5, 16 Go RAM, SSD 512 Go.",
            localisation="Rochefort 17300",
            db_path=self.db_path,
        )
        message = bot_discord.construire_message_ajout_watchlist(
            annonce
        )

        self.assertFalse(annonce["cree"])
        self.assertEqual(annonce["dernier_prix_connu"], 300)
        self.assertEqual(
            bot_discord.champs_manquants_watchlist(annonce),
            [],
        )
        self.assertIn("prete pour analyse", message)
        self.assertIn("5 minutes maximum", message)

    def test_permission_administrateur_est_verifiee(self):
        admin = SimpleNamespace(
            permissions=SimpleNamespace(administrator=True)
        )
        membre = SimpleNamespace(
            permissions=SimpleNamespace(administrator=False)
        )

        self.assertTrue(
            bot_discord.interaction_est_administrateur(admin)
        )
        self.assertFalse(
            bot_discord.interaction_est_administrateur(membre)
        )


if __name__ == "__main__":
    unittest.main()
