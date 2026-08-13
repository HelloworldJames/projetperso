import unittest

from observer import (
    AnnonceObservee,
    comparer_nouvelles,
    detecter_intervention_manuelle,
    normaliser_annonces,
    valider_url_leboncoin,
)


class ObserverTests(unittest.TestCase):
    def test_url_externe_est_refusee(self):
        with self.assertRaises(ValueError):
            valider_url_leboncoin("https://example.test/recherche")

    def test_verification_et_statuts_sont_detectes(self):
        self.assertIn(
            "HTTP 403",
            detecter_intervention_manuelle(403, "Leboncoin", "", "https://www.leboncoin.fr"),
        )
        self.assertIn(
            "vérification",
            detecter_intervention_manuelle(
                200,
                "Vérifiez que vous êtes humain",
                "Captcha",
                "https://www.leboncoin.fr/recherche",
            ),
        )

    def test_normalisation_dedoublonne_et_ignore_capture_invalide(self):
        valeurs = [
            {
                "identifiant": "123",
                "titre": " PC Ryzen 5 ",
                "prix": 300,
                "url": "https://www.leboncoin.fr/ad/ordinateurs/123",
            },
            {
                "identifiant": "123",
                "titre": "PC Ryzen 5 mis à jour",
                "prix": 280,
                "url": "https://www.leboncoin.fr/ad/ordinateurs/123",
            },
            {"titre": "invalide"},
        ]
        annonces = normaliser_annonces(valeurs)
        self.assertEqual(len(annonces), 1)
        self.assertEqual(annonces[0].prix, 280)

    def test_comparaison_ne_retient_que_nouvel_identifiant(self):
        connue = AnnonceObservee(
            identifiant="123",
            titre="PC connu",
            prix=300,
            url="https://www.leboncoin.fr/ad/ordinateurs/123",
        )
        nouvelle = AnnonceObservee(
            identifiant="456",
            titre="PC nouveau",
            prix=250,
            url="https://www.leboncoin.fr/ad/ordinateurs/456",
        )
        self.assertEqual(comparer_nouvelles((connue,), (connue, nouvelle)), (nouvelle,))

    def test_titre_generique_n_est_pas_conserve_comme_titre(self):
        annonces = normaliser_annonces(
            [
                {
                    "identifiant": "789",
                    "titre": "Voir l’annonce",
                    "prix": 495,
                    "url": "https://www.leboncoin.fr/ad/ordinateurs/789",
                }
            ]
        )
        self.assertEqual(len(annonces), 1)
        self.assertIsNone(annonces[0].titre)


if __name__ == "__main__":
    unittest.main()
