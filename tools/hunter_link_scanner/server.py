"""Petit recepteur HTTP local pour l'extension Hunter Link Scanner."""

import argparse
import json

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from database.listing import DB_PATH
from tools.hunter_link_scanner.importer import (
    importer_capture_navigateur,
    lister_resultats_companion,
)


TAILLE_MAX_REQUETE = 256 * 1024


def origine_extension_autorisee(origine):
    if not origine:
        return True

    return origine.startswith((
        "chrome-extension://",
        "moz-extension://",
    ))


def creer_handler(db_path):
    class HunterLinkHandler(BaseHTTPRequestHandler):
        server_version = "HunterLinkScanner/0.2"

        def log_message(self, format_message, *arguments):
            print(
                "[Hunter Link]",
                format_message % arguments,
            )

        def _envoyer_json(self, statut, contenu):
            donnees = json.dumps(
                contenu,
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(statut)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(donnees)),
            )

            origine = self.headers.get("Origin")
            if origine_extension_autorisee(origine) and origine:
                self.send_header(
                    "Access-Control-Allow-Origin",
                    origine,
                )

            self.send_header("Vary", "Origin")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(donnees)
            self.close_connection = True

        def _origine_valide(self):
            return origine_extension_autorisee(
                self.headers.get("Origin")
            )

        def do_OPTIONS(self):
            if not self._origine_valide():
                self._envoyer_json(
                    403,
                    {"ok": False, "erreur": "Origine refusee."},
                )
                return

            self.send_response(204)
            origine = self.headers.get("Origin")
            if origine:
                self.send_header(
                    "Access-Control-Allow-Origin",
                    origine,
                )
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type",
            )
            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, POST, OPTIONS",
            )
            self.end_headers()

        def do_GET(self):
            route = urlsplit(self.path)

            if route.path == "/health":
                self._envoyer_json(
                    200,
                    {"ok": True, "service": "hunter-link-scanner"},
                )
                return

            if route.path == "/recent":
                if not self._origine_valide():
                    self._envoyer_json(
                        403,
                        {"ok": False, "erreur": "Origine refusee."},
                    )
                    return

                try:
                    limite = int(
                        parse_qs(route.query).get("limit", ["50"])[0]
                    )
                    captures = lister_resultats_companion(
                        limite=limite,
                        db_path=db_path,
                    )
                except ValueError as erreur:
                    self._envoyer_json(
                        400,
                        {"ok": False, "erreur": str(erreur)},
                    )
                    return

                self._envoyer_json(
                    200,
                    {
                        "ok": True,
                        "captures": captures,
                        "total": len(captures),
                        "source": "watchlist_locale",
                    },
                )
                return

            self._envoyer_json(
                404,
                {"ok": False, "erreur": "Route inconnue."},
            )

        def do_POST(self):
            if self.path != "/import":
                self._envoyer_json(
                    404,
                    {"ok": False, "erreur": "Route inconnue."},
                )
                return

            if not self._origine_valide():
                self._envoyer_json(
                    403,
                    {"ok": False, "erreur": "Origine refusee."},
                )
                return

            try:
                taille = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                taille = 0

            if taille <= 0 or taille > TAILLE_MAX_REQUETE:
                self._envoyer_json(
                    413,
                    {"ok": False, "erreur": "Requete trop volumineuse."},
                )
                return

            try:
                payload = json.loads(
                    self.rfile.read(taille).decode("utf-8")
                )
                resultat = importer_capture_navigateur(
                    payload,
                    db_path=db_path,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as erreur:
                self._envoyer_json(
                    400,
                    {"ok": False, "erreur": str(erreur)},
                )
                return

            self._envoyer_json(200, resultat)

    return HunterLinkHandler


def creer_serveur(host="127.0.0.1", port=8765, db_path=DB_PATH):
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            "Le scanner V1 doit rester local a cet ordinateur."
        )

    return ThreadingHTTPServer(
        (host, port),
        creer_handler(Path(db_path)),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Recepteur local Hunter Link Scanner",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(DB_PATH))
    arguments = parser.parse_args()

    serveur = creer_serveur(
        host=arguments.host,
        port=arguments.port,
        db_path=arguments.db,
    )

    print("Hunter Link Scanner actif sur http://127.0.0.1:8765")
    print("Ouvre une annonce : Companion l'analyse et la conserve localement.")
    print("La webapp Hunter synchronise ensuite cette boite locale.")

    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArret du scanner.")
    finally:
        serveur.server_close()


if __name__ == "__main__":
    main()
