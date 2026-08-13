import unittest

from analyzer.classifier import classer_annonce
from analyzer.components import detecter_cpu
from analyzer.value import estimer_valeur
from collector.models import Annonce


def creer_annonce(titre, description):
    return Annonce(
        identifiant=titre,
        titre=titre,
        prix=500,
        description=description,
    )


class MachineValuationTests(unittest.TestCase):

    def test_familles_portables_ne_passent_pas_en_desktop(self):
        for titre in (
            "Dell G15",
            "ASUS TUF A15",
            "Acer Predator Helios",
            "Alienware m15",
        ):
            with self.subTest(titre=titre):
                annonce = creer_annonce(
                    titre,
                    (
                        "i5-10400, RTX 3060, "
                        "16 Go DDR4, SSD 512 Go"
                    ),
                )

                classification = classer_annonce(
                    annonce
                )

                _, _, estimation = estimer_valeur(
                    annonce
                )

                self.assertEqual(
                    classification["categorie"],
                    "PORTABLE_GAMING",
                )

                self.assertEqual(
                    estimation["mode_valorisation"],
                    "machine_complete_portable_windows",
                )

    def test_gamme_gaming_sans_gpu_est_bloquee(self):
        annonce = creer_annonce(
            "PC portable Lenovo Legion 5",
            "Ryzen 7 5800H, 16 Go DDR4, SSD 512 Go",
        )

        _, _, estimation = estimer_valeur(
            annonce
        )

        self.assertFalse(
            estimation["analyse_autorisee"]
        )

        self.assertTrue(
            any(
                "GPU" in raison
                for raison in estimation[
                    "raisons_blocage"
                ]
            )
        )

    def test_annees_apple_contradictoires_bloquent(self):
        annonce = creer_annonce(
            "MacBook Pro 2015",
            (
                "Achete en 2019, i5-5257U, "
                "16 Go RAM, SSD 512 Go"
            ),
        )

        _, _, estimation = estimer_valeur(
            annonce
        )

        self.assertFalse(
            estimation["analyse_autorisee"]
        )

        self.assertIsNone(
            estimation["machine"]["annee"]
        )

    def test_vieil_imac_hdd_sans_bonus_stockage(self):
        annonce = creer_annonce(
            "iMac 2010 27 pouces",
            "Disque dur 1 To",
        )

        _, _, estimation = estimer_valeur(
            annonce
        )

        self.assertTrue(
            estimation["analyse_autorisee"]
        )

        self.assertEqual(
            estimation["base_machine"],
            110,
        )

        self.assertEqual(
            estimation["ajustements_configuration"],
            70,
        )

    def test_suffixe_cpu_ne_consomme_pas_rtx(self):
        self.assertEqual(
            detecter_cpu(
                "i5 10400 RTX 3060"
            ),
            ["i5-10400"],
        )

        self.assertEqual(
            detecter_cpu(
                "i7 6700 HQ"
            ),
            ["i7-6700HQ"],
        )

        self.assertEqual(
            detecter_cpu(
                "Ryzen 7 5800 HS"
            ),
            ["Ryzen 7 5800HS"],
        )


if __name__ == "__main__":
    unittest.main()
