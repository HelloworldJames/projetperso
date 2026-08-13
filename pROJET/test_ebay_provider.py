import unittest

from unittest.mock import Mock

from collector.providers.ebay import EbayProvider


class EbayProviderTests(unittest.TestCase):
    def test_api_officielle_normalise_sans_donnee_vendeur(self):
        session = Mock()
        jeton = Mock()
        jeton.json.return_value = {"access_token": "token-test", "expires_in": 7200}
        jeton.raise_for_status.return_value = None
        recherche = Mock()
        recherche.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "v1|123|0",
                    "title": "PC gamer Ryzen 5 RTX 3060",
                    "price": {"value": "450", "currency": "EUR"},
                    "shortDescription": "16 Go RAM SSD 1 To",
                    "condition": "Occasion",
                    "itemLocation": {"city": "Rochefort", "postalCode": "17300"},
                    "itemWebUrl": "https://www.ebay.fr/itm/123",
                    "itemCreationDate": "2026-08-10T10:00:00Z",
                    "seller": {"username": "ne-doit-pas-sortir"},
                }
            ]
        }
        recherche.raise_for_status.return_value = None
        session.post.return_value = jeton
        session.get.return_value = recherche

        provider = EbayProvider(
            session=session,
            client_id="client",
            client_secret="secret",
        )
        annonces = provider.rechercher("pc gamer", limite_par_recherche=10)

        self.assertEqual(len(annonces), 1)
        self.assertEqual(annonces[0].plateforme, "eBay")
        self.assertEqual(annonces[0].prix, 450)
        self.assertEqual(annonces[0].localisation, "Rochefort 17300")
        self.assertNotIn("ne-doit-pas-sortir", annonces[0].description)
        self.assertEqual(session.post.call_count, 1)
        self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
