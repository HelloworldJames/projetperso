import argparse
import sqlite3
import sys

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from database.watchlist import (  # noqa: E402
    ajouter_watchlist,
    desactiver_watchlist,
    lister_watchlist,
    marquer_notification_detection_envoyee,
    mettre_a_jour_prix,
)
from notifications.discord import (  # noqa: E402
    envoyer_nouvelles_annonces_discord,
)


def construire_parser():
    parser = argparse.ArgumentParser(
        description="Administration locale de la watchlist PC Hunter.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Base SQLite alternative (utile pour les tests).",
    )

    commandes = parser.add_subparsers(
        dest="commande",
        required=True,
    )

    ajouter = commandes.add_parser(
        "ajouter",
        help="Ajouter ou réactiver une URL.",
    )
    ajouter.add_argument("url")
    ajouter.add_argument("--plateforme")
    ajouter.add_argument("--identifiant")
    ajouter.add_argument("--titre")
    ajouter.add_argument("--description")
    ajouter.add_argument("--localisation")
    ajouter.add_argument("--date-publication")
    ajouter.add_argument("--prix")
    ajouter.add_argument(
        "--sans-discord",
        action="store_true",
        help="Enregistrer sans tenter la notification de détection.",
    )

    lister = commandes.add_parser(
        "lister",
        help="Lister les annonces suivies.",
    )
    lister.add_argument(
        "--toutes",
        action="store_true",
        help="Inclure les annonces désactivées.",
    )

    desactiver = commandes.add_parser(
        "desactiver",
        help="Désactiver par ID de watchlist, URL ou identifiant plateforme.",
    )
    desactiver.add_argument("reference")

    prix = commandes.add_parser(
        "prix",
        help="Mettre à jour le dernier prix connu.",
    )
    prix.add_argument("reference")
    prix.add_argument("nouveau_prix")

    commandes.add_parser(
        "notifier",
        help="Envoyer un résumé Discord des détections encore non notifiées.",
    )

    return parser


def _arguments_db(args):
    if args.db is None:
        return {}

    return {
        "db_path": args.db,
    }


def _afficher_annonce(annonce):
    etat = "active" if annonce["actif"] else "inactive"
    prix = annonce["dernier_prix_connu"]
    prix_texte = f"{prix} €" if prix is not None else "prix inconnu"

    print(
        f"#{annonce['id']} | {etat} | {annonce['plateforme']} | "
        f"{prix_texte}"
    )
    print(
        "  Titre :",
        annonce["titre"] or "non renseigné",
    )
    print(
        "  Identifiant :",
        annonce["identifiant"] or "non détecté",
    )
    print(
        "  URL :",
        annonce["url"],
    )


def main(argv=None):
    parser = construire_parser()
    args = parser.parse_args(argv)
    arguments_db = _arguments_db(args)

    try:
        if args.commande == "ajouter":
            annonce = ajouter_watchlist(
                url=args.url,
                plateforme=args.plateforme,
                identifiant=args.identifiant,
                titre=args.titre,
                description=args.description,
                localisation=args.localisation,
                date_publication=args.date_publication,
                prix_connu=args.prix,
                **arguments_db,
            )

            action = "ajoutée" if annonce["cree"] else "réactivée/mise à jour"
            print(f"Annonce {action} dans la watchlist.")
            _afficher_annonce(annonce)

            if (
                not args.sans_discord
                and
                not annonce["notification_detection_envoyee"]
            ):
                notification_envoyee = (
                    envoyer_nouvelles_annonces_discord(
                        [annonce]
                    )
                )

                if notification_envoyee:
                    marquer_notification_detection_envoyee(
                        [annonce["id"]],
                        **arguments_db,
                    )

            return 0

        if args.commande == "lister":
            annonces = lister_watchlist(
                actif=None if args.toutes else True,
                **arguments_db,
            )

            if not annonces:
                print("Aucune annonce dans la watchlist demandée.")
                return 0

            for index, annonce in enumerate(annonces):
                if index:
                    print()

                _afficher_annonce(annonce)

            return 0

        if args.commande == "desactiver":
            trouvee = desactiver_watchlist(
                args.reference,
                **arguments_db,
            )

            if not trouvee:
                print("Annonce introuvable dans la watchlist.")
                return 2

            print("Annonce désactivée. Aucune donnée n'a été supprimée.")
            return 0

        if args.commande == "prix":
            resultat = mettre_a_jour_prix(
                args.reference,
                args.nouveau_prix,
                **arguments_db,
            )
            print(
                "Prix enregistré :",
                resultat["ancien_prix"],
                "->",
                resultat["nouveau_prix"],
            )
            print(
                "Changement réel :",
                "oui" if resultat["prix_change"] else "non",
            )
            return 0

        if args.commande == "notifier":
            annonces = lister_watchlist(
                actif=True,
                **arguments_db,
            )
            en_attente = [
                annonce
                for annonce in annonces
                if not annonce["notification_detection_envoyee"]
            ]

            if not en_attente:
                print("Aucune nouvelle détection Discord en attente.")
                return 0

            notification_envoyee = (
                envoyer_nouvelles_annonces_discord(
                    en_attente
                )
            )

            if not notification_envoyee:
                print("Le résumé Discord n'a pas pu être envoyé.")
                return 3

            marquees = marquer_notification_detection_envoyee(
                [
                    annonce["id"]
                    for annonce in en_attente
                ],
                **arguments_db,
            )
            print(
                marquees,
                "annonce(s) marquée(s) comme notifiée(s).",
            )
            return 0

    except (ValueError, sqlite3.Error) as error:
        parser.error(str(error))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
