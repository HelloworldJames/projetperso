import unittest

from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from urllib.error import URLError
from unittest.mock import patch

from notifications.discord import (
    construire_messages_nouvelles_annonces,
    envoyer_message_discord,
    envoyer_nouvelles_annonces_discord,
)


class NouvellesAnnoncesDiscordTests(unittest.TestCase):
    def test_resume_contient_nombre_sources_description_et_statut(self):
        annonces = [
            SimpleNamespace(
                titre="PC portable Dell",
                prix=70,
                plateforme="Leboncoin",
                localisation="La Rochelle",
                description="Caractéristiques à confirmer.",
                url="https://example.com/1",
            ),
            {
                "titre": "PC Ryzen 5",
                "dernier_prix_connu": 250,
                "plateforme": "ParuVendu",
                "localisation": "Rochefort",
                "description": "Ryzen 5, 16 Go, SSD 512 Go.",
                "url": "https://example.com/2",
                "categorie": "PC_COMPLET",
            },
        ]

        messages = construire_messages_nouvelles_annonces(
            annonces
        )
        contenu = "\n".join(messages)

        self.assertIn("2 NOUVELLES ANNONCES DÉTECTÉES", contenu)
        self.assertIn("Leboncoin × 1", contenu)
        self.assertIn("ParuVendu × 1", contenu)
        self.assertIn("en étude par PC Hunter", contenu)
        self.assertIn("Caractéristiques à confirmer", contenu)
        self.assertIn("Ryzen 5, 16 Go, SSD 512 Go", contenu)

    def test_longue_liste_est_decoupee_sous_la_limite_discord(self):
        annonces = [
            {
                "titre": f"Annonce {numero}",
                "prix": 100 + numero,
                "plateforme": "Vivastreet",
                "localisation": "Rochefort",
                "description": "Description " + ("longue " * 80),
                "url": f"https://example.com/{numero}",
            }
            for numero in range(20)
        ]

        messages = construire_messages_nouvelles_annonces(
            annonces
        )

        self.assertGreater(len(messages), 1)
        self.assertTrue(
            all(len(message) <= 1900 for message in messages)
        )

    @patch("notifications.discord.envoyer_message_discord")
    def test_envoi_vide_ne_contacte_pas_discord(self, envoyer):
        self.assertFalse(
            envoyer_nouvelles_annonces_discord([])
        )
        envoyer.assert_not_called()

    @patch(
        "notifications.discord.DISCORD_WEBHOOK_URL",
        "https://discord.com/api/webhooks/secret-ne-pas-afficher",
    )
    @patch(
        "notifications.discord.urlopen",
        side_effect=URLError("erreur sur URL secrète"),
    )
    def test_erreur_reseau_ne_revele_jamais_le_webhook(self, _urlopen):
        sortie = StringIO()

        with redirect_stdout(sortie):
            resultat = envoyer_message_discord(
                "test"
            )

        self.assertFalse(resultat)
        self.assertNotIn("secret-ne-pas-afficher", sortie.getvalue())
        self.assertNotIn("erreur sur URL secrète", sortie.getvalue())


if __name__ == "__main__":
    unittest.main()
