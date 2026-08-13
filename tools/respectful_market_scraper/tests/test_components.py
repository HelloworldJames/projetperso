import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from scraper.parser import AnnonceExtraite, extraire_annonces
from scraper.rate_limiter import calculer_delai
from scraper.robots_checker import construire_url_robots, verifier_robots
from scraper.storage import sauvegarder_annonces
from scraper.vpn_manager import StatutVpn, VpnManuelRequis, _analyser_ipconfig
from scraper import vpn_manager


class RobotsTests(unittest.TestCase):
    def test_construire_url_robots(self):
        self.assertEqual(
            construire_url_robots("https://www.vinted.fr/catalog/3581-x"),
            "https://www.vinted.fr/robots.txt",
        )

    @patch("scraper.robots_checker._telecharger_robots")
    def test_refuse_interdiction_explicite(self, telecharger):
        telecharger.return_value = (
            200,
            "# Access is only permitted with special permission from the site.\nUser-agent: *\nAllow: /",
        )
        decision = verifier_robots("https://example.org/ad/1")
        self.assertFalse(decision.autorise)
        self.assertIn("autorisation speciale", decision.raison)

    @patch("scraper.robots_checker._telecharger_robots")
    def test_applique_regles_et_crawl_delay(self, telecharger):
        telecharger.return_value = (
            200,
            "User-agent: *\nDisallow: /private\nAllow: /catalog\nCrawl-delay: 12",
        )
        autorise = verifier_robots("https://example.org/catalog/1")
        interdit = verifier_robots("https://example.org/private/1")
        self.assertTrue(autorise.autorise)
        self.assertEqual(autorise.delai_exploration, 12)
        self.assertFalse(interdit.autorise)

    @patch("scraper.robots_checker._telecharger_robots")
    def test_refuse_si_robots_inaccessible_avec_cause(self, telecharger):
        telecharger.side_effect = urllib.error.URLError("DNS indisponible")
        decision = verifier_robots("https://example.org/catalog/1")
        self.assertFalse(decision.autorise)
        self.assertIn("DNS indisponible", decision.raison)

    @patch("scraper.robots_checker._telecharger_robots")
    def test_refuse_si_robots_repond_403(self, telecharger):
        telecharger.side_effect = urllib.error.HTTPError(
            "https://example.org/robots.txt", 403, "Forbidden", {}, None
        )
        decision = verifier_robots("https://example.org/catalog/1")
        self.assertFalse(decision.autorise)
        self.assertIn("HTTP 403", decision.raison)


class RateLimiterTests(unittest.TestCase):
    def test_respecte_delai_robots_superieur(self):
        delai = calculer_delai(3, 8, 15, generateur=lambda _a, _b: 5)
        self.assertEqual(delai, 15)


class ParserTests(unittest.TestCase):
    def test_extrait_carte_vinted_et_deduplique(self):
        html = """
        <a href="/items/123-pc-gaming">
          <img alt="Image: PC gaming, marque: Asus, etat: Bon etat, 250,00 €">
          <span>250,00 €</span>
        </a>
        <a href="/items/123-pc-gaming"><span>250,00 €</span></a>
        """
        annonces = extraire_annonces(html, "https://www.vinted.fr/catalog/1")
        self.assertEqual(len(annonces), 1)
        self.assertEqual(annonces[0].identifiant, "123")
        self.assertEqual(annonces[0].titre, "PC gaming")
        self.assertEqual(annonces[0].prix, 250)

    def test_extrait_json_ld(self):
        html = """
        <script type="application/ld+json">
          {"@type":"Product","name":"Portable","productID":"42",
           "url":"/items/42-portable","offers":{"price":"199.90"}}
        </script>
        """
        annonces = extraire_annonces(html, "https://example.org/catalog")
        self.assertEqual(annonces[0].prix, 199.9)
        self.assertEqual(annonces[0].titre, "Portable")


class StorageTests(unittest.TestCase):
    def test_sauvegarde_sans_doublon(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "annonces.json"
            annonce = AnnonceExtraite("1", "PC", 200, "https://example.org/items/1")
            premier = sauvegarder_annonces((annonce,), chemin)
            second = sauvegarder_annonces((annonce,), chemin)
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
            self.assertEqual(premier["nouvelles"], 1)
            self.assertEqual(second["nouvelles"], 0)
            self.assertEqual(len(contenu["annonces"]), 1)


class VpnManagerTests(unittest.TestCase):
    def test_detecte_tunnel_nordlynx_actif(self):
        statut = _analyser_ipconfig(
            "Carte inconnue NordLynx :\n"
            "Description : NordLynx Tunnel\n"
            "Adresse IPv4 : 10.5.0.2\n"
        )
        self.assertTrue(statut.connecte)

    def test_detecte_adaptateur_nordvpn_inactif(self):
        statut = _analyser_ipconfig(
            "Unknown adapter NordVPN:\nMedia State: Media disconnected\n"
        )
        self.assertFalse(statut.connecte)

    @patch("scraper.vpn_manager.lire_statut_vpn")
    def test_exige_connexion_manuelle(self, lire):
        lire.return_value = StatutVpn(True, False, "NordVPN", "Inactif")
        with self.assertRaises(VpnManuelRequis):
            vpn_manager.exiger_vpn_manuel()

    @patch("scraper.vpn_manager.lire_statut_vpn")
    def test_accepte_vpn_deja_connecte(self, lire):
        attendu = StatutVpn(True, True, "NordVPN", "Actif")
        lire.return_value = attendu
        self.assertEqual(vpn_manager.exiger_vpn_manuel(), attendu)


if __name__ == "__main__":
    unittest.main()
