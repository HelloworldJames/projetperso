import json
import tempfile
import threading
import unittest

from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from database.watchlist import lister_watchlist
from tools.hunter_link_scanner.importer import (
    importer_capture_navigateur,
    lister_resultats_companion,
)
from tools.hunter_link_scanner.server import (
    creer_serveur,
    origine_extension_autorisee,
)


class HunterLinkScannerTests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporaire.name) / "hunter_link_test.db"

    def tearDown(self):
        self.temporaire.cleanup()

    def payload_complet(self, prix=300):
        return {
            "url": "https://www.leboncoin.fr/ad/ordinateurs/1234567890",
            "titre": "PC Ryzen 5 RTX 3060",
            "prix": prix,
            "description": "Ryzen 5, RTX 3060, 16 Go RAM, SSD 1 To.",
            "localisation": "Rochefort 17300",
            "date_publication": "2026-08-10",
            "vendeur": "ce champ doit etre ignore",
        }

    def test_import_complet_est_pret_et_ignore_vendeur(self):
        resultat = importer_capture_navigateur(
            self.payload_complet(),
            db_path=self.db_path,
        )

        self.assertTrue(resultat["ok"])
        self.assertTrue(resultat["cree"])
        self.assertEqual(resultat["statut"], "analyse_disponible")
        self.assertIn("analyse", resultat)
        self.assertIn("decision", resultat["analyse"])
        self.assertEqual(resultat["plateforme"], "Leboncoin")
        self.assertEqual(resultat["identifiant"], "1234567890")

        annonces = lister_watchlist(
            actif=None,
            db_path=self.db_path,
        )
        self.assertEqual(len(annonces), 1)
        self.assertNotIn("vendeur", annonces[0])
        self.assertEqual(annonces[0]["mode_acquisition"], "companion_local")

        captures = lister_resultats_companion(
            db_path=self.db_path,
        )
        self.assertEqual(len(captures), 1)
        self.assertEqual(captures[0]["titre"], "PC Ryzen 5 RTX 3060")
        self.assertEqual(captures[0]["statut"], "analyse_disponible")
        self.assertNotIn("vendeur", captures[0])

    def test_nouveau_scan_met_a_jour_prix_sans_doublon(self):
        importer_capture_navigateur(
            self.payload_complet(prix=300),
            db_path=self.db_path,
        )
        resultat = importer_capture_navigateur(
            self.payload_complet(prix=260),
            db_path=self.db_path,
        )

        self.assertFalse(resultat["cree"])
        self.assertTrue(resultat["prix_change"])
        self.assertEqual(resultat["ancien_prix"], 300)
        self.assertEqual(resultat["nouveau_prix"], 260)
        self.assertEqual(
            len(lister_watchlist(actif=None, db_path=self.db_path)),
            1,
        )

    def test_identifiant_capture_est_stable_puis_change_avec_le_prix(self):
        importer_capture_navigateur(
            self.payload_complet(prix=300),
            db_path=self.db_path,
        )
        premiere = lister_resultats_companion(db_path=self.db_path)[0]

        importer_capture_navigateur(
            self.payload_complet(prix=300),
            db_path=self.db_path,
        )
        doublon = lister_resultats_companion(db_path=self.db_path)[0]
        self.assertEqual(premiere["capture_id"], doublon["capture_id"])

        importer_capture_navigateur(
            self.payload_complet(prix=260),
            db_path=self.db_path,
        )
        baisse = lister_resultats_companion(db_path=self.db_path)[0]
        self.assertNotEqual(premiere["capture_id"], baisse["capture_id"])
        self.assertEqual(baisse["prix"], 260)
        self.assertFalse(baisse["notification_detection_envoyee"])

    def test_capture_incomplete_reste_en_etude(self):
        resultat = importer_capture_navigateur(
            {"url": "https://example.test/annonce/42"},
            db_path=self.db_path,
        )

        self.assertEqual(resultat["statut"], "en_etude")
        self.assertEqual(
            resultat["champs_manquants"],
            ["titre", "prix", "description", "localisation"],
        )

    def test_capture_catalogue_marketplace_est_prete_et_dedoublonnee(self):
        payload = {
            "url": "https://www.facebook.com/marketplace/item/1773289397189564",
            "titre": "Canon Powershot 360",
            "prix": 350,
            "description": "Annonce détectée dans la veille Marketplace.",
            "localisation": "Lille",
            "source_catalogue": "https://www.facebook.com/marketplace/category/search/",
        }

        premiere = importer_capture_navigateur(payload, db_path=self.db_path)
        seconde = importer_capture_navigateur(payload, db_path=self.db_path)

        self.assertEqual(premiere["statut"], "analyse_disponible")
        self.assertEqual(premiere["plateforme"], "Facebook Marketplace")
        self.assertEqual(premiere["identifiant"], "1773289397189564")
        self.assertFalse(seconde["cree"])
        self.assertEqual(len(lister_watchlist(actif=None, db_path=self.db_path)), 1)

    def test_capture_vinted_reconnait_plateforme_et_identifiant(self):
        payload = {
            "url": "https://www.vinted.fr/items/1234567890-pc-portable",
            "titre": "PC portable Lenovo",
            "prix": 220,
            "description": "Lenovo, 16 Go RAM et SSD 512 Go.",
            "localisation": "La Rochelle",
        }
        resultat = importer_capture_navigateur(payload, db_path=self.db_path)
        self.assertEqual(resultat["statut"], "analyse_disponible")
        self.assertEqual(resultat["plateforme"], "Vinted")
        self.assertEqual(resultat["identifiant"], "1234567890")

    def test_capture_generique_publique_utilise_le_meme_moteur(self):
        payload = {
            "url": "https://occasion.example/annonces/pc-ryzen-42",
            "plateforme": "occasion.example",
            "identifiant": "pc-ryzen-42",
            "titre": "PC Ryzen 7 RTX 3070",
            "prix": 480,
            "description": "Ryzen 7, RTX 3070, 32 Go RAM et SSD 1 To.",
            "localisation": "Rochefort",
            "vendeur": "champ interdit",
        }
        resultat = importer_capture_navigateur(payload, db_path=self.db_path)
        self.assertEqual(resultat["statut"], "analyse_disponible")
        self.assertEqual(resultat["plateforme"], "occasion.example")
        self.assertEqual(resultat["identifiant"], "pc-ryzen-42")
        annonce = lister_watchlist(actif=None, db_path=self.db_path)[0]
        self.assertNotIn("vendeur", annonce)
        self.assertEqual(annonce["mode_acquisition"], "companion_local")

    def test_endpoint_local_accepte_extension(self):
        serveur = creer_serveur(
            host="127.0.0.1",
            port=0,
            db_path=self.db_path,
        )
        thread = threading.Thread(
            target=serveur.serve_forever,
            daemon=True,
        )
        thread.start()

        try:
            port = serveur.server_address[1]
            donnees = json.dumps(self.payload_complet()).encode("utf-8")
            requete = Request(
                f"http://127.0.0.1:{port}/import",
                data=donnees,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "chrome-extension://hunter-test",
                },
                method="POST",
            )

            with urlopen(requete, timeout=3) as reponse:
                resultat = json.loads(reponse.read().decode("utf-8"))

            self.assertTrue(resultat["ok"])
        finally:
            serveur.shutdown()
            serveur.server_close()
            thread.join(timeout=3)

    def test_endpoint_recent_expose_boite_locale_sans_vendeur(self):
        importer_capture_navigateur(
            self.payload_complet(),
            db_path=self.db_path,
        )
        serveur = creer_serveur(
            host="127.0.0.1",
            port=0,
            db_path=self.db_path,
        )
        thread = threading.Thread(target=serveur.serve_forever, daemon=True)
        thread.start()

        try:
            port = serveur.server_address[1]
            requete = Request(
                f"http://127.0.0.1:{port}/recent?limit=10",
                headers={"Origin": "chrome-extension://hunter-test"},
            )
            with urlopen(requete, timeout=3) as reponse:
                resultat = json.loads(reponse.read().decode("utf-8"))

            self.assertTrue(resultat["ok"])
            self.assertEqual(resultat["source"], "watchlist_locale")
            self.assertEqual(resultat["total"], 1)
            self.assertNotIn("vendeur", resultat["captures"][0])

            origine_web = Request(
                f"http://127.0.0.1:{port}/recent",
                headers={"Origin": "https://site-inconnu.example"},
            )
            with self.assertRaises(HTTPError) as erreur:
                urlopen(origine_web, timeout=3)
            self.assertEqual(erreur.exception.code, 403)
            erreur.exception.close()
        finally:
            serveur.shutdown()
            serveur.server_close()
            thread.join(timeout=3)

    def test_origine_site_web_est_refusee(self):
        self.assertTrue(
            origine_extension_autorisee(
                "chrome-extension://hunter-test"
            )
        )
        self.assertFalse(
            origine_extension_autorisee(
                "https://site-inconnu.example"
            )
        )


if __name__ == "__main__":
    unittest.main()
