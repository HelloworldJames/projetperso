import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from analyzer.instant import (
    analyser_annonce_immediate,
    calibrer_estimation_marche,
)
from collector.models import Annonce
from database.analysis import lister_analyses_recentes


class HunterV15Tests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporaire.name) / "hunter_v15.db"

    def tearDown(self):
        self.temporaire.cleanup()

    def annonce_complete(self, prix=300):
        return Annonce(
            identifiant="V15-PC-1",
            titre="PC gamer Ryzen 5 5600 RTX 3060",
            prix=prix,
            description="16 Go DDR4, SSD NVMe 1 To, fonctionne parfaitement.",
            localisation="Rochefort 17300",
            plateforme="Test",
            url="https://example.test/v15-pc-1",
        )

    @patch("analyzer.instant.calculer_comparables_marche")
    def test_analyse_immediate_retourne_decision_prix_max_et_marge(self, comparables):
        comparables.return_value = {
            "nombre_comparables": 4,
            "prix_minimum": 500,
            "prix_median": 600,
            "prix_maximum": 700,
        }
        resultat = analyser_annonce_immediate(
            self.annonce_complete(),
            db_path=self.db_path,
            inclure_ia=False,
        )

        self.assertTrue(resultat["estimation"]["analyse_autorisee"])
        self.assertIn(
            resultat["decision"],
            {"PEPITE", "BONNE_AFFAIRE", "INTERESSANTE", "A_NEGOCIER", "A_ECARTER"},
        )
        self.assertIsInstance(resultat["score_affaire"], int)
        self.assertIsNotNone(resultat["prix_achat_max"])
        self.assertIsNotNone(resultat["marge_nette_prudente"])
        self.assertEqual(len(lister_analyses_recentes(db_path=self.db_path)), 1)

    @patch("analyzer.instant.calculer_comparables_marche")
    def test_doublon_identique_ne_cree_pas_deux_analyses(self, comparables):
        comparables.return_value = {
            "nombre_comparables": 0,
            "prix_minimum": None,
            "prix_median": None,
            "prix_maximum": None,
        }
        annonce = self.annonce_complete()
        analyser_annonce_immediate(annonce, db_path=self.db_path, inclure_ia=False)
        analyser_annonce_immediate(annonce, db_path=self.db_path, inclure_ia=False)
        self.assertEqual(len(lister_analyses_recentes(db_path=self.db_path)), 1)

    def test_information_insuffisante_n_invente_pas_de_valeur(self):
        annonce = Annonce(
            identifiant="V15-INCOMPLET",
            titre="Ordinateur à vendre",
            prix=250,
            description="Bon état.",
            plateforme="Test",
        )
        resultat = analyser_annonce_immediate(
            annonce,
            db_path=self.db_path,
            inclure_ia=False,
        )
        self.assertIn(
            resultat["decision"],
            {"INFORMATIONS_INSUFFISANTES", "HORS_CIBLE"},
        )
        self.assertFalse(resultat["estimation"]["analyse_autorisee"])

    def test_calibration_marche_est_bornee(self):
        estimation = {
            "valeur_probable": 500,
            "valeur_basse": 450,
            "valeur_haute": 550,
            "confiance_score": 70,
        }
        comparables = {
            "nombre_comparables": 10,
            "prix_minimum": 1000,
            "prix_median": 1200,
            "prix_maximum": 1400,
        }
        resultat = calibrer_estimation_marche(estimation, comparables)
        self.assertTrue(resultat["calibration_marche"])
        self.assertLessEqual(resultat["valeur_probable"], 600)
        self.assertEqual(estimation["valeur_probable"], 500)


if __name__ == "__main__":
    unittest.main()

