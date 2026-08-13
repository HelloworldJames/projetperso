import ssl
import unittest

from collector.http import creer_contexte_tls_windows


class ContexteTLSWindowsTests(unittest.TestCase):
    def test_verification_tls_reste_active(self):
        contexte = creer_contexte_tls_windows()

        self.assertEqual(
            contexte.verify_mode,
            ssl.CERT_REQUIRED,
        )
        self.assertTrue(
            contexte.check_hostname
        )

        if hasattr(ssl, "VERIFY_X509_STRICT"):
            self.assertEqual(
                contexte.verify_flags & ssl.VERIFY_X509_STRICT,
                0,
            )


if __name__ == "__main__":
    unittest.main()
