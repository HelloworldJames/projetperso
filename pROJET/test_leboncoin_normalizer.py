import unittest
from types import SimpleNamespace

from collector.models import Annonce
from collector.providers.leboncoin_normalizer import (
    LeboncoinResult,
    normaliser_leboncoin,
    normaliser_resultats_leboncoin,
    resultat_leboncoin_depuis_source,
)


class LeboncoinNormalizerTests(unittest.TestCase):
    def test_format_dictionnaire_observe_dans_le_projet_typescript(self):
        source = {
            "list_id": 3247000001,
            "subject": "PC Ryzen 5 RTX 3060",
            "body": "Ryzen 5 5600, 16 Go, SSD 1 To",
            "price_cents": 25000,
            "url": "https://www.leboncoin.fr/ad/ordinateurs/3247000001",
            "first_publication_date": "2026-08-10T08:00:00+02:00",
            "location": {
                "city": "Rochefort",
                "zipcode": "17300",
            },
            "owner": {
                "user_id": "ne-doit-pas-etre-conserve",
                "name": "vendeur",
            },
            "has_phone": True,
        }

        annonce = normaliser_leboncoin(source)

        self.assertIsInstance(annonce, Annonce)
        self.assertEqual(annonce.identifiant, "3247000001")
        self.assertEqual(annonce.titre, "PC Ryzen 5 RTX 3060")
        self.assertEqual(annonce.prix, 250)
        self.assertEqual(annonce.localisation, "Rochefort (17)")
        self.assertEqual(annonce.plateforme, "Leboncoin")
        self.assertEqual(
            annonce.date_publication,
            "2026-08-10T08:00:00+02:00",
        )
        self.assertFalse(hasattr(annonce, "owner"))
        self.assertFalse(hasattr(annonce, "has_phone"))

    def test_format_objet_observe_dans_le_projet_python(self):
        source = SimpleNamespace(
            id=3247000002,
            subject="Portable HP 845 G8",
            body="Ryzen 5 Pro, 16 Go, SSD 500 Go",
            price=320.0,
            url="https://www.leboncoin.fr/ad/ordinateurs/3247000002",
            first_publication_date="2026-08-10T07:00:00+02:00",
            location=SimpleNamespace(
                city="Saintes",
                department_id="17",
                zipcode="17100",
            ),
            user=SimpleNamespace(name="vendeur"),
        )

        resultat = resultat_leboncoin_depuis_source(source)
        annonce = normaliser_leboncoin(resultat)

        self.assertEqual(resultat.id, "3247000002")
        self.assertEqual(resultat.localisation, "Saintes (17)")
        self.assertEqual(annonce.prix, 320)
        self.assertFalse(hasattr(annonce, "user"))

    def test_prix_tableau_et_url_canonique_de_secours(self):
        annonce = normaliser_leboncoin(
            {
                "list_id": 3247000003,
                "subject": "Ordinateur Dell",
                "body": "Configuration à confirmer",
                "price": [70],
                "location": {
                    "city_label": "La Rochelle",
                    "department_id": "17",
                },
            }
        )

        self.assertEqual(annonce.prix, 70)
        self.assertEqual(
            annonce.url,
            "https://www.leboncoin.fr/ad/ordinateurs/3247000003",
        )

    def test_resultat_canonique_et_liste(self):
        resultats = [
            LeboncoinResult(
                id="3247000004",
                titre="Mini PC",
                prix=99.99,
                description="Mini PC bureautique",
                localisation="Saujon (17)",
            )
        ]

        annonces = normaliser_resultats_leboncoin(resultats)

        self.assertEqual(len(annonces), 1)
        self.assertEqual(annonces[0].prix, 99.99)
        self.assertEqual(annonces[0].plateforme, "Leboncoin")

    def test_champs_obligatoires_et_url_sont_valides(self):
        cas_invalides = [
            {"subject": "Sans ID", "price": 100},
            {"list_id": 1, "price": 100},
            {"list_id": 1, "subject": "Sans prix"},
            {"list_id": 1, "subject": "Prix nul", "price": 0},
            {
                "list_id": 1,
                "subject": "Mauvais domaine",
                "price": 100,
                "url": "https://example.com/annonce/1",
            },
        ]

        for source in cas_invalides:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    normaliser_leboncoin(source)


if __name__ == "__main__":
    unittest.main()

