import unittest
from unittest.mock import patch

from collector.providers import paruvendu_detail


class ParuVenduCacheResilienceTests(unittest.TestCase):

    def test_erreur_cache_ne_fait_pas_echouer_la_collecte(self):
        with patch(
            "collector.providers.paruvendu_detail.os.makedirs",
            side_effect=PermissionError("accès refusé"),
        ):
            resultat = paruvendu_detail.sauvegarder_cache({"pv-1": {}})

        self.assertFalse(resultat)


if __name__ == "__main__":
    unittest.main()
