import re
import sqlite3

from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from database.listing import DB_PATH


TRACKING_QUERY_PREFIXES = (
    "at_",
    "utm_",
)


def maintenant_iso():
    return (
        datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


def _chemin_db(db_path):
    if db_path is None:
        return DB_PATH

    return Path(db_path)


def _connexion(db_path):
    connexion = sqlite3.connect(
        _chemin_db(db_path)
    )
    connexion.row_factory = sqlite3.Row
    return connexion


def initialiser_watchlist(db_path=DB_PATH):
    """Crée uniquement la table indépendante de watchlist si nécessaire."""
    with closing(_connexion(db_path)) as connexion:
        with connexion:
            connexion.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist_annonces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    plateforme TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    identifiant TEXT,

                    titre TEXT,
                    description TEXT,
                    localisation TEXT,
                    date_publication TEXT,
                    mode_acquisition TEXT NOT NULL DEFAULT 'ajout_manuel',
                    prix_connu REAL,

                    date_ajout TEXT NOT NULL,
                    dernier_prix_connu REAL,
                    derniere_observation TEXT,

                    actif INTEGER NOT NULL DEFAULT 1
                        CHECK (actif IN (0, 1)),

                    notification_detection_envoyee INTEGER NOT NULL DEFAULT 0
                        CHECK (notification_detection_envoyee IN (0, 1)),
                    date_notification_detection TEXT
                )
                """
            )

            colonnes = {
                ligne["name"]
                for ligne in connexion.execute(
                    "PRAGMA table_info(watchlist_annonces)"
                ).fetchall()
            }

            migrations = {
                "description": "TEXT",
                "localisation": "TEXT",
                "date_publication": "TEXT",
                "mode_acquisition": (
                    "TEXT NOT NULL DEFAULT 'ajout_manuel'"
                ),
                "notification_detection_envoyee": (
                    "INTEGER NOT NULL DEFAULT 0"
                ),
                "date_notification_detection": "TEXT",
            }

            for nom, definition in migrations.items():
                if nom in colonnes:
                    continue

                connexion.execute(
                    f"ALTER TABLE watchlist_annonces "
                    f"ADD COLUMN {nom} {definition}"
                )

            connexion.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_watchlist_plateforme_identifiant
                ON watchlist_annonces (
                    plateforme,
                    identifiant
                )
                WHERE identifiant IS NOT NULL
                """
            )


def normaliser_url(url):
    """Valide l'URL et retire les marqueurs de suivi non nécessaires."""
    valeur = str(url or "").strip()
    parties = urlsplit(valeur)

    if (
        parties.scheme.lower() not in {"http", "https"}
        or not parties.hostname
    ):
        raise ValueError("L'URL doit être une adresse HTTP(S) complète.")

    parametres = []

    for nom, contenu in parse_qsl(
        parties.query,
        keep_blank_values=True,
    ):
        nom_minuscule = nom.lower()

        if any(
            nom_minuscule.startswith(prefixe)
            for prefixe in TRACKING_QUERY_PREFIXES
        ):
            continue

        parametres.append(
            (nom, contenu)
        )

    chemin = parties.path or "/"

    if chemin != "/":
        chemin = chemin.rstrip("/")

    return urlunsplit(
        (
            parties.scheme.lower(),
            parties.netloc.lower(),
            chemin,
            urlencode(parametres, doseq=True),
            "",
        )
    )


def detecter_plateforme(url):
    hote = (
        urlsplit(url).hostname
        or ""
    ).lower()

    if hote == "leboncoin.fr" or hote.endswith(".leboncoin.fr"):
        return "Leboncoin"

    if hote == "paruvendu.fr" or hote.endswith(".paruvendu.fr"):
        return "ParuVendu"

    if "vivastreet." in hote:
        return "Vivastreet"

    if hote == "facebook.com" or hote.endswith(".facebook.com"):
        return "Facebook Marketplace"

    if hote == "vinted.fr" or hote.endswith(".vinted.fr"):
        return "Vinted"

    return hote or "Inconnue"


def extraire_identifiant(url, plateforme=None):
    """Extrait seulement les identifiants visibles dans l'URL publique."""
    chemin = urlsplit(url).path
    plateforme = (
        plateforme
        or detecter_plateforme(url)
    ).lower()

    if plateforme == "leboncoin":
        motifs = (
            r"/vi/(\d+)(?:\.htm)?$",
            r"/ad/[^/]+/(\d+)$",
        )

        for motif in motifs:
            correspondance = re.search(
                motif,
                chemin,
                flags=re.IGNORECASE,
            )

            if correspondance:
                return correspondance.group(1)

    if plateforme in {
        "facebook marketplace",
        "facebook.com",
        "www.facebook.com",
    }:
        correspondance = re.search(
            r"/marketplace/item/(\d+)",
            chemin,
            flags=re.IGNORECASE,
        )
        if correspondance:
            return correspondance.group(1)

    if plateforme == "vinted":
        correspondance = re.search(
            r"/items/(\d+)",
            chemin,
            flags=re.IGNORECASE,
        )
        if correspondance:
            return correspondance.group(1)

    return None


def _normaliser_texte_optionnel(valeur):
    if valeur is None:
        return None

    texte = str(valeur).strip()
    return texte or None


def _normaliser_prix(prix):
    if prix is None:
        return None

    if isinstance(prix, bool):
        raise ValueError("Le prix doit être un nombre positif ou nul.")

    if isinstance(prix, str):
        prix = (
            prix.strip()
            .replace("€", "")
            .replace(" ", "")
            .replace(",", ".")
        )

    try:
        valeur = float(prix)
    except (TypeError, ValueError) as error:
        raise ValueError("Le prix doit être un nombre positif ou nul.") from error

    if valeur < 0:
        raise ValueError("Le prix doit être un nombre positif ou nul.")

    return valeur


def _prix_lisible(prix):
    if prix is None:
        return None

    valeur = float(prix)

    if valeur.is_integer():
        return int(valeur)

    return valeur


def _ligne_vers_dict(ligne):
    if ligne is None:
        return None

    resultat = dict(ligne)
    resultat["actif"] = bool(resultat["actif"])
    resultat["notification_detection_envoyee"] = bool(
        resultat["notification_detection_envoyee"]
    )
    resultat["prix_connu"] = _prix_lisible(resultat["prix_connu"])
    resultat["dernier_prix_connu"] = _prix_lisible(
        resultat["dernier_prix_connu"]
    )
    return resultat


def ajouter_watchlist(
    url,
    plateforme=None,
    identifiant=None,
    titre=None,
    description=None,
    localisation=None,
    date_publication=None,
    prix_connu=None,
    db_path=DB_PATH,
    mode_acquisition=None,
):
    """Ajoute ou réactive une URL sans enregistrer de donnée vendeur."""
    url_normalisee = normaliser_url(url)
    plateforme = (
        _normaliser_texte_optionnel(plateforme)
        or detecter_plateforme(url_normalisee)
    )
    identifiant = (
        _normaliser_texte_optionnel(identifiant)
        or extraire_identifiant(url_normalisee, plateforme)
    )
    titre = _normaliser_texte_optionnel(titre)
    description = _normaliser_texte_optionnel(description)
    localisation = _normaliser_texte_optionnel(localisation)
    date_publication = _normaliser_texte_optionnel(date_publication)
    mode_acquisition = _normaliser_texte_optionnel(mode_acquisition)
    if mode_acquisition is not None:
        mode_acquisition = mode_acquisition[:50]
    prix = _normaliser_prix(prix_connu)
    maintenant = maintenant_iso()

    initialiser_watchlist(db_path)

    with closing(_connexion(db_path)) as connexion:
        existante = connexion.execute(
            """
            SELECT *
            FROM watchlist_annonces
            WHERE url = ?
               OR (
                    identifiant IS NOT NULL
                    AND plateforme = ?
                    AND identifiant = ?
               )
            LIMIT 1
            """,
            (
                url_normalisee,
                plateforme,
                identifiant,
            ),
        ).fetchone()

        with connexion:
            if existante is None:
                curseur = connexion.execute(
                    """
                    INSERT INTO watchlist_annonces (
                        plateforme,
                        url,
                        identifiant,
                        titre,
                        description,
                        localisation,
                        date_publication,
                        mode_acquisition,
                        prix_connu,
                        date_ajout,
                        dernier_prix_connu,
                        derniere_observation,
                        actif
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        plateforme,
                        url_normalisee,
                        identifiant,
                        titre,
                        description,
                        localisation,
                        date_publication,
                        mode_acquisition or "ajout_manuel",
                        prix,
                        maintenant,
                        prix,
                        maintenant,
                    ),
                )
                watchlist_id = curseur.lastrowid
                cree = True

            else:
                watchlist_id = existante["id"]

                connexion.execute(
                    """
                    UPDATE watchlist_annonces
                    SET plateforme = ?,
                        url = ?,
                        identifiant = COALESCE(?, identifiant),
                        titre = COALESCE(?, titre),
                        description = COALESCE(?, description),
                        localisation = COALESCE(?, localisation),
                        date_publication = COALESCE(?, date_publication),
                        mode_acquisition = COALESCE(?, mode_acquisition),
                        prix_connu = COALESCE(prix_connu, ?),
                        dernier_prix_connu = COALESCE(?, dernier_prix_connu),
                        derniere_observation = ?,
                        actif = 1
                    WHERE id = ?
                    """,
                    (
                        plateforme,
                        url_normalisee,
                        identifiant,
                        titre,
                        description,
                        localisation,
                        date_publication,
                        mode_acquisition,
                        prix,
                        prix,
                        maintenant,
                        watchlist_id,
                    ),
                )
                cree = False

        ligne = connexion.execute(
            """
            SELECT *
            FROM watchlist_annonces
            WHERE id = ?
            """,
            (watchlist_id,),
        ).fetchone()

    resultat = _ligne_vers_dict(ligne)
    resultat["cree"] = cree
    return resultat


def lister_watchlist(actif=None, db_path=DB_PATH):
    initialiser_watchlist(db_path)

    requete = "SELECT * FROM watchlist_annonces"
    parametres = ()

    if actif is not None:
        requete += " WHERE actif = ?"
        parametres = (1 if actif else 0,)

    requete += " ORDER BY date_ajout DESC, id DESC"

    with closing(_connexion(db_path)) as connexion:
        lignes = connexion.execute(
            requete,
            parametres,
        ).fetchall()

    return [
        _ligne_vers_dict(ligne)
        for ligne in lignes
    ]


def _trouver_par_reference(connexion, reference):
    if isinstance(reference, int) or str(reference).strip().isdigit():
        return connexion.execute(
            "SELECT * FROM watchlist_annonces WHERE id = ?",
            (int(reference),),
        ).fetchone()

    texte = str(reference).strip()

    if texte.lower().startswith(("http://", "https://")):
        texte = normaliser_url(texte)
        return connexion.execute(
            "SELECT * FROM watchlist_annonces WHERE url = ?",
            (texte,),
        ).fetchone()

    return connexion.execute(
        """
        SELECT *
        FROM watchlist_annonces
        WHERE identifiant = ?
        ORDER BY actif DESC, id DESC
        LIMIT 1
        """,
        (texte,),
    ).fetchone()


def desactiver_watchlist(reference, db_path=DB_PATH):
    initialiser_watchlist(db_path)

    with closing(_connexion(db_path)) as connexion:
        ligne = _trouver_par_reference(
            connexion,
            reference,
        )

        if ligne is None:
            return False

        with connexion:
            connexion.execute(
                """
                UPDATE watchlist_annonces
                SET actif = 0
                WHERE id = ?
                """,
                (ligne["id"],),
            )

    return True


def supprimer_watchlist(reference, db_path=DB_PATH):
    """Suppression logique : l'historique futur restera récupérable."""
    return desactiver_watchlist(
        reference,
        db_path=db_path,
    )


def mettre_a_jour_prix(
    reference,
    nouveau_prix,
    date_observation=None,
    db_path=DB_PATH,
):
    initialiser_watchlist(db_path)
    nouveau_prix = _normaliser_prix(nouveau_prix)

    if nouveau_prix is None:
        raise ValueError("Le nouveau prix doit être renseigné.")

    observation = date_observation or maintenant_iso()

    with closing(_connexion(db_path)) as connexion:
        ligne = _trouver_par_reference(
            connexion,
            reference,
        )

        if ligne is None:
            raise ValueError("Annonce absente de la watchlist.")

        ancien_prix = _prix_lisible(
            ligne["dernier_prix_connu"]
        )

        with connexion:
            connexion.execute(
                """
                UPDATE watchlist_annonces
                SET prix_connu = COALESCE(prix_connu, ?),
                    dernier_prix_connu = ?,
                    derniere_observation = ?
                WHERE id = ?
                """,
                (
                    nouveau_prix,
                    nouveau_prix,
                    observation,
                    ligne["id"],
                ),
            )

    nouveau_prix = _prix_lisible(nouveau_prix)

    return {
        "watchlist_id": ligne["id"],
        "ancien_prix": ancien_prix,
        "nouveau_prix": nouveau_prix,
        "prix_change": (
            ancien_prix is not None
            and nouveau_prix != ancien_prix
        ),
        "premier_prix_connu": ancien_prix is None,
        "date_observation": observation,
    }


def marquer_notification_detection_envoyee(
    references,
    date_notification=None,
    db_path=DB_PATH,
):
    references = [
        str(reference).strip()
        for reference in references
        if str(reference).strip()
    ]

    if not references:
        return 0

    initialiser_watchlist(db_path)
    date_notification = date_notification or maintenant_iso()
    marquees = 0

    with closing(_connexion(db_path)) as connexion:
        with connexion:
            for reference in references:
                ligne = _trouver_par_reference(
                    connexion,
                    reference,
                )

                if ligne is None:
                    continue

                connexion.execute(
                    """
                    UPDATE watchlist_annonces
                    SET notification_detection_envoyee = 1,
                        date_notification_detection = ?
                    WHERE id = ?
                    """,
                    (
                        date_notification,
                        ligne["id"],
                    ),
                )
                marquees += 1

    return marquees


def annonces_watchlist_pour_analyse(
    limite=None,
    db_path=DB_PATH,
):
    """Convertit les fiches ayant au moins un titre et un prix.

    Le moteur V1.5 répond prudemment lorsque la description ou la
    localisation manque, sans inventer les informations absentes.
    """
    from collector.models import Annonce

    initialiser_watchlist(db_path)

    requete = """
        SELECT *
        FROM watchlist_annonces
        WHERE actif = 1
          AND titre IS NOT NULL
          AND dernier_prix_connu IS NOT NULL
        ORDER BY date_ajout DESC, id DESC
    """
    parametres = ()

    if limite is not None:
        requete += " LIMIT ?"
        parametres = (max(0, int(limite)),)

    with closing(_connexion(db_path)) as connexion:
        lignes = connexion.execute(
            requete,
            parametres,
        ).fetchall()

    annonces = []

    for ligne in lignes:
        annonce = Annonce(
            identifiant=ligne["identifiant"] or f"watchlist-{ligne['id']}",
            titre=ligne["titre"],
            prix=ligne["dernier_prix_connu"],
            description=ligne["description"] or ligne["titre"],
            localisation=ligne["localisation"] or "Inconnue",
            plateforme=ligne["plateforme"],
            url=ligne["url"],
            date_publication=ligne["date_publication"],
        )
        annonce.origine_watchlist = True
        annonce.mode_acquisition = ligne["mode_acquisition"]
        annonce.notification_detection_deja_envoyee = bool(
            ligne["notification_detection_envoyee"]
        )
        annonces.append(annonce)

    return annonces
