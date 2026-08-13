import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import observer


class TestObserverVinted(unittest.TestCase):
    def test_valider_url_vinted(self):
        url = "https://www.vinted.fr/catalog/3581-"
        self.assertEqual(observer.valider_url_vinted(url), url)
        with self.assertRaises(ValueError):
            observer.valider_url_vinted("https://example.org/catalog/3581-")
        with self.assertRaises(ValueError):
            observer.valider_url_vinted("http://www.vinted.fr/catalog/3581-")

    def test_detecter_intervention_http_et_captcha(self):
        self.assertIn("403", observer.detecter_intervention_manuelle(403, "", "", "") or "")
        self.assertIsNotNone(
            observer.detecter_intervention_manuelle(200, "Security check", "", "")
        )
        self.assertIsNone(observer.detecter_intervention_manuelle(200, "Vinted", "Articles", ""))

    def test_normaliser_et_dedupliquer(self):
        annonces = observer.normaliser_annonces(
            [
                {
                    "identifiant": "123",
                    "titre": "  PC   gaming  ",
                    "prix": 250.0,
                    "url": "https://www.vinted.fr/items/123-pc-gaming",
                },
                {
                    "identifiant": "123",
                    "titre": "PC gaming actualise",
                    "prix": 240.5,
                    "url": "https://www.vinted.fr/items/123-pc-gaming",
                },
                {"identifiant": "invalide"},
            ]
        )
        self.assertEqual(len(annonces), 1)
        self.assertEqual(annonces[0].titre, "PC gaming actualise")
        self.assertEqual(annonces[0].prix, 240.5)

    def test_comparer_nouvelles(self):
        ancienne = observer.AnnonceObservee("1", "Ancienne", 100, "https://vinted.fr/items/1-x")
        actuelle = observer.AnnonceObservee("2", "Nouvelle", 90, "https://vinted.fr/items/2-x")
        self.assertEqual(observer.comparer_nouvelles((ancienne,), (ancienne, actuelle)), (actuelle,))

    def test_enregistrer_resultat(self):
        annonce = observer.AnnonceObservee("1", "PC", 100, "https://vinted.fr/items/1-pc")
        resultat = observer.ResultatPassage(
            "ok", "2026-08-10T13:30:00+02:00", "https://vinted.fr/catalog/3581-", (annonce,), ()
        )
        with tempfile.TemporaryDirectory() as dossier:
            etat = Path(dossier)
            with patch.object(observer, "FICHIER_STATUT", etat / "status.json"), patch.object(
                observer, "FICHIER_ANNONCES", etat / "listings.json"
            ):
                observer.enregistrer_resultat(resultat)
                self.assertTrue((etat / "status.json").exists())
                self.assertTrue((etat / "listings.json").exists())


if __name__ == "__main__":
    unittest.main()
