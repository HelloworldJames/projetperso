import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from collector.models import Annonce
from database import presence


def annonce(plateforme, identifiant):
    return Annonce(
        identifiant=identifiant,
        titre=f"PC {identifiant}",
        prix=250,
        description="PC de test",
        localisation="Tonnay-Charente",
        plateforme=plateforme,
        url=f"https://example.test/{identifiant}",
        date_publication=None,
    )


class PresenceResilienceTests(unittest.TestCase):

    def setUp(self):
        fichier = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False,
        )
        self.db_path = fichier.name
        fichier.close()
        self.patch_db = patch.object(
            presence,
            "DB_PATH",
            self.db_path,
        )
        self.patch_db.start()

    def tearDown(self):
        self.patch_db.stop()
        os.unlink(self.db_path)

    def lire(self, plateforme, identifiant):
        with closing(sqlite3.connect(self.db_path)) as connexion:
            connexion.row_factory = sqlite3.Row
            return connexion.execute(
                """
                SELECT * FROM presence_annonces
                WHERE plateforme = ? AND identifiant = ?
                """,
                (plateforme, identifiant),
            ).fetchone()

    def test_source_absente_ne_desactive_pas_ses_annonces(self):
        pv = annonce("ParuVendu", "pv-1")
        viva = annonce("Vivastreet", "viva-1")
        presence.mettre_a_jour_presence([pv, viva])

        evenements = presence.mettre_a_jour_presence([viva])

        self.assertEqual(evenements["disparues"], [])
        self.assertEqual(self.lire("ParuVendu", "pv-1")["active"], 1)
        self.assertEqual(
            self.lire("ParuVendu", "pv-1")["absences_consecutives"],
            0,
        )

    def test_disparition_exige_deux_scans_valides(self):
        pv_1 = annonce("ParuVendu", "pv-1")
        pv_2 = annonce("ParuVendu", "pv-2")
        presence.mettre_a_jour_presence([pv_1, pv_2])

        premier = presence.mettre_a_jour_presence([pv_1])
        second = presence.mettre_a_jour_presence([pv_1])

        self.assertEqual(premier["disparues"], [])
        self.assertEqual(len(second["disparues"]), 1)
        self.assertEqual(second["disparues"][0]["identifiant"], "pv-2")
        self.assertEqual(self.lire("ParuVendu", "pv-2")["active"], 0)

    def test_reapparition_reinitialise_les_absences(self):
        pv_1 = annonce("ParuVendu", "pv-1")
        pv_2 = annonce("ParuVendu", "pv-2")
        presence.mettre_a_jour_presence([pv_1, pv_2])
        presence.mettre_a_jour_presence([pv_1])
        presence.mettre_a_jour_presence([pv_1])

        evenements = presence.mettre_a_jour_presence([pv_1, pv_2])

        self.assertEqual(len(evenements["reapparues"]), 1)
        ligne = self.lire("ParuVendu", "pv-2")
        self.assertEqual(ligne["active"], 1)
        self.assertEqual(ligne["absences_consecutives"], 0)


if __name__ == "__main__":
    unittest.main()
