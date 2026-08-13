import unittest

import diagnose_urls


class DiagnosticUrlsTests(unittest.TestCase):
    def test_valider_url(self):
        url = "https://www.leboncoin.fr/ad/ordinateurs/1234567890"
        self.assertEqual(diagnose_urls.valider_url(url), url)
        with self.assertRaises(ValueError):
            diagnose_urls.valider_url("javascript:alert(1)")
        with self.assertRaises(ValueError):
            diagnose_urls.valider_url("https://login:secret@example.org/item")

    def test_url_sans_requete(self):
        self.assertEqual(
            diagnose_urls.url_sans_requete("https://example.org/item?a=1#x"),
            "https://example.org/item",
        )
        self.assertEqual(
            diagnose_urls.url_sans_requete(
                "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/x/token"
            ),
            "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/[MASQUE]",
        )

    def test_detecter_controle(self):
        self.assertEqual(
            diagnose_urls.detecter_controle("Security check", "", ""),
            "security check",
        )
        self.assertIsNone(diagnose_urls.detecter_controle("Annonce", "PC 300 EUR", ""))

    def test_classer_comportement(self):
        self.assertEqual(
            diagnose_urls.classer_comportement(403, None, None, 0, 0),
            "acces_refuse",
        )
        self.assertEqual(
            diagnose_urls.classer_comportement(200, None, None, 1, 1),
            "contenu_annonce_visible",
        )
        self.assertEqual(
            diagnose_urls.classer_comportement(200, None, None, 0, 0),
            "lecture_incomplete",
        )


if __name__ == "__main__":
    unittest.main()
