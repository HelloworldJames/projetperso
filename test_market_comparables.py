import sqlite3
import unittest

from unittest.mock import patch

from collector.models import Annonce
from database import market


def creer_annonce(
    identifiant,
    titre,
    description,
    prix=500,
    plateforme="ParuVendu",
):
    return Annonce(
        identifiant=identifiant,
        titre=titre,
        prix=prix,
        description=description,
        plateforme=plateforme,
    )


def estimation_pour_mode(mode):
    return {
        "mode_valorisation": mode,
    }


class MarketComparablesTests(unittest.TestCase):

    def setUp(self):
        self.connexions_ouvertes = []

        self.uri_db = (
            f"file:market_comparables_{id(self)}"
            "?mode=memory&cache=shared"
        )

        self.connexion_gardienne = (
            self.ouvrir_connexion()
        )

        self.patch_connexion = patch.object(
            market,
            "connexion_db",
            side_effect=self.ouvrir_connexion,
        )

        self.patch_connexion_lecture = patch.object(
            market,
            "connexion_db_lecture_seule",
            side_effect=self.ouvrir_connexion,
        )

        self.patch_connexion.start()
        self.patch_connexion_lecture.start()

        market.initialiser_market()

        with self.ouvrir_connexion() as connexion:
            connexion.execute(
                """
                CREATE TABLE annonces (
                    identifiant TEXT UNIQUE,
                    plateforme TEXT,
                    prix_actuel REAL
                )
                """
            )

    def tearDown(self):
        self.patch_connexion_lecture.stop()
        self.patch_connexion.stop()

        for connexion in reversed(
            self.connexions_ouvertes
        ):
            connexion.close()

    def ouvrir_connexion(self):
        connexion = sqlite3.connect(
            self.uri_db,
            uri=True,
        )

        connexion.row_factory = sqlite3.Row

        self.connexions_ouvertes.append(
            connexion
        )

        return connexion

    def ajouter_observation_courante(
        self,
        annonce,
    ):
        market.enregistrer_observation(
            annonce
        )

        with self.ouvrir_connexion() as connexion:
            connexion.execute(
                """
                INSERT INTO annonces (
                    identifiant,
                    plateforme,
                    prix_actuel
                )
                VALUES (?, ?, ?)

                ON CONFLICT (identifiant)
                DO UPDATE SET
                    plateforme = excluded.plateforme,
                    prix_actuel = excluded.prix_actuel
                """,
                (
                    annonce.identifiant,
                    annonce.plateforme,
                    annonce.prix,
                ),
            )

    def creer_desktop(
        self,
        identifiant,
        prix=500,
        plateforme="ParuVendu",
        cpu="Ryzen 5 5600",
    ):
        return creer_annonce(
            identifiant=identifiant,
            titre=(
                f"PC gamer {cpu} RTX 3060"
            ),
            description=(
                "16 Go DDR4 SSD 512 Go"
            ),
            prix=prix,
            plateforme=plateforme,
        )

    def creer_portable(
        self,
        identifiant,
        prix=500,
        plateforme="ParuVendu",
    ):
        return creer_annonce(
            identifiant=identifiant,
            titre=(
                "PC portable Lenovo Legion 5 "
                "15.6 pouces"
            ),
            description=(
                "Ryzen 7 5800H RTX 3060 "
                "16 Go DDR4 SSD 512 Go"
            ),
            prix=prix,
            plateforme=plateforme,
        )

    def creer_apple(
        self,
        identifiant,
        prix=500,
        plateforme="ParuVendu",
    ):
        return creer_annonce(
            identifiant=identifiant,
            titre=(
                "MacBook Air M1 13 pouces"
            ),
            description=(
                "16 Go RAM SSD 512 Go"
            ),
            prix=prix,
            plateforme=plateforme,
        )

    def test_auto_comparaison_exclue(self):
        annonce = self.creer_desktop(
            "PV-CIBLE",
            prix=150,
        )

        comparable = self.creer_desktop(
            "VV-AUTRE",
            prix=250,
            plateforme="Vivastreet",
        )

        self.ajouter_observation_courante(
            annonce
        )

        self.ajouter_observation_courante(
            comparable
        )

        resultat = (
            market.calculer_comparables_marche(
                annonce,
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat["nombre_comparables"],
            1,
        )

        self.assertEqual(
            resultat["prix_median"],
            250.0,
        )

    def test_cpu_generique_refuse(self):
        cible = self.creer_desktop(
            "CIBLE-PRECISE"
        )

        generique = self.creer_desktop(
            "CPU-GENERIQUE",
            prix=200,
            cpu="Intel Core i5",
        )

        self.ajouter_observation_courante(
            generique
        )

        resultat = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat["nombre_comparables"],
            0,
        )

    def test_apple_ne_compare_pas_windows(self):
        cible = self.creer_apple(
            "APPLE-CIBLE"
        )

        windows = self.creer_portable(
            "WINDOWS-AUTRE",
            prix=300,
        )

        self.ajouter_observation_courante(
            windows
        )

        resultat = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "machine_complete_apple"
                ),
            )
        )

        self.assertEqual(
            resultat["nombre_comparables"],
            0,
        )

    def test_portable_ne_compare_pas_desktop(self):
        cible = self.creer_portable(
            "PORTABLE-CIBLE"
        )

        desktop = creer_annonce(
            identifiant="DESKTOP-AUTRE",
            titre=(
                "PC gamer Ryzen 7 5800H "
                "RTX 3060"
            ),
            description=(
                "16 Go DDR4 SSD 512 Go"
            ),
            prix=350,
        )

        self.ajouter_observation_courante(
            desktop
        )

        resultat = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "machine_complete_portable_windows"
                ),
            )
        )

        self.assertEqual(
            resultat["nombre_comparables"],
            0,
        )

    def test_medianes_nombre_impair_et_pair(self):
        cible = self.creer_desktop(
            "MEDIANE-CIBLE"
        )

        for numero, prix in enumerate(
            (
                100,
                200,
                300,
            ),
            start=1,
        ):
            self.ajouter_observation_courante(
                self.creer_desktop(
                    f"IMPAIR-{numero}",
                    prix=prix,
                )
            )

        resultat_impair = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat_impair,
            {
                "nombre_comparables": 3,
                "prix_minimum": 100.0,
                "prix_median": 200.0,
                "prix_maximum": 300.0,
            },
        )

        self.ajouter_observation_courante(
            self.creer_desktop(
                "PAIR-4",
                prix=400,
            )
        )

        resultat_pair = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat_pair[
                "nombre_comparables"
            ],
            4,
        )

        self.assertEqual(
            resultat_pair[
                "prix_median"
            ],
            250.0,
        )

    def test_zero_comparable_renvoie_none(self):
        resultat = (
            market.calculer_comparables_marche(
                self.creer_desktop(
                    "SANS-COMPARABLE"
                ),
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat,
            {
                "nombre_comparables": 0,
                "prix_minimum": None,
                "prix_median": None,
                "prix_maximum": None,
            },
        )

    def test_easy_cash_est_exclu(self):
        cible = self.creer_desktop(
            "CIBLE-MARKETPLACE"
        )

        easy_cash = self.creer_desktop(
            "EASY-CASH-MEME-CONFIG",
            prix=250,
            plateforme="Easy Cash",
        )

        self.ajouter_observation_courante(
            easy_cash
        )

        resultat = (
            market.calculer_comparables_marche(
                cible,
                estimation_pour_mode(
                    "composants_desktop"
                ),
            )
        )

        self.assertEqual(
            resultat["nombre_comparables"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
