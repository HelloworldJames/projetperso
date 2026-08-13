import os
import ssl
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


os.environ.setdefault(
    "DISCORD_BOT_TOKEN",
    "test-token",
)
os.environ.setdefault(
    "DISCORD_GUILD_ID",
    "1",
)

import bot_discord


class BotDiscordPathsTests(unittest.TestCase):
    def test_base_et_top_sont_independants_du_dossier_courant(self):
        racine = Path(bot_discord.__file__).resolve().parent

        self.assertTrue(bot_discord.DB_PATH.is_absolute())
        self.assertEqual(
            bot_discord.DB_PATH,
            racine / "database" / "pc_hunter.db",
        )
        self.assertEqual(
            bot_discord.TOP_PATH,
            racine / "data" / "top_actuel.json",
        )


class BotDiscordTLSTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_utilise_le_contexte_tls_windows_verifie(self):
        client = bot_discord.PCHunterBot()

        with patch.object(
            bot_discord.discord.Client,
            "login",
            new=AsyncMock(),
        ) as login_parent:
            await client.login("test-token")

        contexte = client.http.connector._ssl

        self.assertIsInstance(contexte, ssl.SSLContext)
        self.assertTrue(contexte.check_hostname)
        self.assertEqual(
            contexte.verify_mode,
            ssl.CERT_REQUIRED,
        )

        if hasattr(ssl, "VERIFY_X509_STRICT"):
            self.assertFalse(
                contexte.verify_flags
                & ssl.VERIFY_X509_STRICT
            )

        login_parent.assert_awaited_once_with(
            "test-token"
        )
        await client.http.connector.close()


if __name__ == "__main__":
    unittest.main()
