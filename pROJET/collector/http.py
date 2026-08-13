import ssl

import requests
from requests.adapters import HTTPAdapter


def creer_contexte_tls_windows():
    """Conserve la validation TLS tout en tolérant certains CA antivirus."""
    contexte = ssl.create_default_context()

    if hasattr(ssl, "VERIFY_X509_STRICT"):
        contexte.verify_flags &= ~ssl.VERIFY_X509_STRICT

    return contexte


class AdaptateurTLSWindows(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = creer_contexte_tls_windows()
        return super().init_poolmanager(*args, **kwargs)


def creer_session_http():
    session = requests.Session()
    session.mount(
        "https://",
        AdaptateurTLSWindows(),
    )
    return session
