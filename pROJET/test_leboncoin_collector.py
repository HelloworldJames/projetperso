import json
import tempfile
import unittest

from pathlib import Path

from collector.models import Annonce
from collector.providers.leboncoin_collector import (
    collecter_depuis_etat_observateur,
    collecter_observations_leboncoin,
    comparer_couverture_leboncoin,
    normaliser_observation_leboncoin,
)


def observation(numero, **complements):
    valeur = {
        "list_id": 3247812200 + numero,
        "subject": f"MacBook test {numero}",
        "price": 400 + numero,
        "body": "MacBook 256 Go / 8 Go en bon état",
        "location": {
            "city": "Saint-Jean-d'Angély",
            "zipcode": "17400",
        },
        "url": (
            "https://www.leboncoin.fr/ad/ordinateurs/"
            f"{3247812200 + numero}"
        ),
    }
    valeur.update(complements)
    return valeur


class LeboncoinCollectorTests(unittest.TestCase):
    def test_cas_reel_macbook_neo_est_normalise_sans_vendeur(self):
        annonce = normaliser_observation_leboncoin(
            {
                "list_id": 3247812256,
                "subject": "MacBook Neo",
                "price": "495 €",
                "body": (
                    "256 Go / 8 Go, année 2026, très bon état, "
                    "garantie jusqu’à 05/2027"
                ),
                "location": {
                    "city": "Saint-Jean-d'Angély",
                    "zipcode": "17400",
                },
                "url": (
                    "https://www.leboncoin.fr/ad/ordinateurs/"
                    "3247812256"
                ),
                "owner": {
                    "name": "ne doit pas être conservé",
                    "phone": "0000000000",
                },
            },
            date_detection="2026-08-10T16:00:00+02:00",
        )

        self.assertEqual(annonce.identifiant, "LEBONCOIN-3247812256")
        self.assertEqual(annonce.source, "Leboncoin")
        self.assertEqual(annonce.prix, 495)
        self.assertEqual(annonce.localisation, "Saint-Jean-d'Angély (17)")
        self.assertEqual(annonce.marque, "Apple")
        self.assertEqual(annonce.annee, 2026)
        self.assertEqual(annonce.ram_go, 8)
        self.assertEqual(annonce.stockage_go, 256)
        self.assertEqual(annonce.etat.casefold(), "très bon état")
        self.assertEqual(annonce.garantie_jusqu_au, "05/2027")
        self.assertFalse(hasattr(annonce, "owner"))
        self.assertFalse(hasattr(annonce, "phone"))

        fiche = annonce.vers_annonce()
        self.assertIsInstance(fiche, Annonce)
        self.assertEqual(fiche.identifiant, "LEBONCOIN-3247812256")
        self.assertEqual(fiche.date_detection, "2026-08-10T16:00:00+02:00")
        self.assertFalse(hasattr(fiche, "owner"))

    def test_doublon_est_fusionne_et_identifiant_connu_n_est_pas_nouveau(self):
        incomplete = observation(
            1,
            subject="Voir l’annonce",
            body="",
        )
        complete = observation(
            1,
            subject="MacBook Air M2",
            body="MacBook Air M2, RAM 8 Go, stockage 256 Go",
        )

        with self.assertLogs(
            "collector.providers.leboncoin_collector",
            level="INFO",
        ) as journaux:
            rapport = collecter_observations_leboncoin(
                [incomplete, complete],
                identifiants_connus=["3247812201"],
            )

        self.assertEqual(rapport.nombre_annonces, 1)
        self.assertEqual(rapport.nombre_nouvelles, 0)
        self.assertEqual(rapport.nombre_doublons, 1)
        self.assertEqual(rapport.annonces[0].titre, "MacBook Air M2")
        self.assertIn("doublons=1", journaux.output[0])

    def test_titre_generique_reste_detecte_mais_fiche_incomplete(self):
        rapport = collecter_observations_leboncoin(
            [observation(2, subject="Voir l’annonce", body="")]
        )

        self.assertEqual(rapport.nombre_annonces, 1)
        self.assertEqual(rapport.nombre_incompletes, 1)
        self.assertIsNone(rapport.annonces[0].titre)
        self.assertFalse(rapport.annonces[0].prete_pour_hunter)

    def test_dix_visibles_dix_detectees_donne_cent_pour_cent(self):
        attendues = [observation(numero) for numero in range(1, 11)]
        collecte = collecter_observations_leboncoin(attendues)

        couverture = comparer_couverture_leboncoin(
            attendues,
            collecte.annonces,
        )

        self.assertEqual(couverture.nombre_attendues, 10)
        self.assertEqual(couverture.nombre_detectees, 10)
        self.assertEqual(couverture.nombre_correspondances, 10)
        self.assertEqual(couverture.couverture_pourcentage, 100.0)
        self.assertTrue(couverture.succes)

    def test_annonce_manquante_est_visible_dans_le_rapport(self):
        attendues = [observation(numero) for numero in range(1, 11)]
        collecte = collecter_observations_leboncoin(attendues[:-1])

        couverture = comparer_couverture_leboncoin(
            attendues,
            collecte.annonces,
        )

        self.assertEqual(couverture.nombre_correspondances, 9)
        self.assertEqual(couverture.couverture_pourcentage, 90.0)
        self.assertEqual(len(couverture.manquantes), 1)
        self.assertFalse(couverture.succes)

    def test_reference_sans_id_peut_retrouver_macbook_neo(self):
        collecte = collecter_observations_leboncoin(
            [
                observation(
                    56,
                    list_id=3247812256,
                    subject="MacBook Neo",
                    price=495,
                )
            ]
        )
        couverture = comparer_couverture_leboncoin(
            [
                {
                    "titre": "MacBook Neo",
                    "prix": 495,
                    "ville": "Saint-Jean-d'Angély",
                }
            ],
            collecte.annonces,
        )
        self.assertTrue(couverture.succes)

    def test_statut_403_ignore_le_snapshot_ancien(self):
        with tempfile.TemporaryDirectory() as dossier_temporaire:
            dossier = Path(dossier_temporaire)
            (dossier / "status.json").write_text(
                json.dumps(
                    {
                        "statut": "intervention_manuelle_requise",
                        "date_observation": "2026-08-10T13:21:48+02:00",
                        "raison": "Leboncoin a répondu HTTP 403.",
                        "http_status": 403,
                    }
                ),
                encoding="utf-8",
            )
            (dossier / "listings.json").write_text(
                json.dumps({"annonces": [observation(1)]}),
                encoding="utf-8",
            )

            rapport = collecter_depuis_etat_observateur(dossier)

        self.assertEqual(rapport.statut, "BLOCKED")
        self.assertEqual(rapport.nombre_annonces, 0)
        self.assertIn("HTTP 403", rapport.erreurs[0])


if __name__ == "__main__":
    unittest.main()

