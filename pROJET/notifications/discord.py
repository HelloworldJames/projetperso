import json
import os
import ssl

from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()


DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL"
)


# ============================================================
# OUTILS
# ============================================================

def formater_nombre(
    valeur
):

    try:

        nombre = float(
            valeur
        )

        if nombre.is_integer():

            return str(
                int(nombre)
            )

        return str(
            round(
                nombre,
                2
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return str(
            valeur
        )


def envoyer_message_discord(
    message,
    label="Notification Discord",
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "⚠️ Discord : "
            "DISCORD_WEBHOOK_URL absent du .env"
        )

        return False


    donnees = json.dumps(
        {
            "content": message,
        }
    ).encode("utf-8")

    requete = Request(
        DISCORD_WEBHOOK_URL,
        data=donnees,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PC-Hunter/1.0",
        },
        method="POST",
    )

    contexte_tls = ssl.create_default_context()

    # Python récent active X509_STRICT. Certains antivirus Windows
    # installent un certificat local valide mais ancien qui ne respecte pas
    # cette extension à la lettre. On garde CERT_REQUIRED et la vérification
    # du nom d'hôte, en retirant seulement ce drapeau strict.
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        contexte_tls.verify_flags &= ~ssl.VERIFY_X509_STRICT

    try:

        with urlopen(
            requete,
            context=contexte_tls,
            timeout=10,
        ) as reponse:
            statut = reponse.status

        if statut in (
            200,
            204,
        ):

            print(
                f"📲 {label} envoyée"
            )

            return True


        print(
            "⚠️ Discord : erreur HTTP",
            statut,
        )

        return False


    except HTTPError as erreur:

        print(
            "⚠️ Discord : erreur HTTP",
            erreur.code,
        )

        return False


    except (
        URLError,
        TimeoutError,
        OSError,
    ) as erreur:

        print(
            "⚠️ Discord inaccessible :",
            type(erreur).__name__,
        )

        return False


def _lire_champ_annonce(
    annonce,
    nom,
    *alternatives,
    defaut=None,
):
    noms = (
        nom,
        *alternatives,
    )

    for champ in noms:
        if isinstance(annonce, dict):
            valeur = annonce.get(champ)
        else:
            valeur = getattr(
                annonce,
                champ,
                None,
            )

        if valeur is not None:
            return valeur

    return defaut


def _nettoyer_texte_discord(
    valeur,
    limite,
):
    texte = " ".join(
        str(valeur or "")
        .replace("@", "@\u200b")
        .split()
    )

    if len(texte) <= limite:
        return texte

    return (
        texte[: limite - 1]
        .rstrip()
        + "…"
    )


def construire_messages_nouvelles_annonces(
    annonces,
):
    """Construit un résumé Discord indépendant du canal de détection."""
    annonces = list(
        annonces
        or []
    )

    if not annonces:
        return []

    plateformes = []

    for annonce in annonces:
        plateformes.append(
            str(
                _lire_champ_annonce(
                    annonce,
                    "plateforme",
                    defaut="Source inconnue",
                )
            )
        )

    compte_plateformes = Counter(
        plateformes
    )

    provenance = " · ".join(
        f"{plateforme} × {nombre}"
        for plateforme, nombre
        in sorted(
            compte_plateformes.items()
        )
    )

    total = len(annonces)
    pluriel = "S" if total > 1 else ""

    entete = "\n".join(
        [
            (
                f"🆕 **{total} NOUVELLE{pluriel} "
                f"ANNONCE{pluriel} DÉTECTÉE{pluriel}**"
            ),
            f"🌐 Provenance : **{provenance}**",
            "📚 Statut : **en étude par PC Hunter**",
            (
                "ℹ️ Détection enregistrée ; une alerte séparée sera "
                "envoyée seulement si l’analyse valide une opportunité."
            ),
        ]
    )

    blocs = []

    for numero, annonce in enumerate(
        annonces,
        start=1,
    ):
        titre = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "titre",
                defaut="Annonce sans titre",
            ),
            120,
        )

        plateforme = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "plateforme",
                defaut="Source inconnue",
            ),
            40,
        )

        prix = _lire_champ_annonce(
            annonce,
            "prix",
            "dernier_prix_connu",
            defaut=None,
        )

        localisation = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "localisation",
                defaut="Localisation à confirmer",
            ),
            70,
        )

        categorie = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "categorie",
                defaut="EN ÉTUDE",
            ),
            40,
        )

        description = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "description",
                defaut="Description non disponible",
            ),
            240,
        )

        url = _nettoyer_texte_discord(
            _lire_champ_annonce(
                annonce,
                "url",
                defaut="",
            ),
            300,
        )

        lignes = [
            f"**{numero}. {titre}**",
            (
                f"💵 {formater_nombre(prix)} €"
                if prix is not None
                else "💵 Prix à confirmer"
            ),
            f"🌐 {plateforme} · 📍 {localisation}",
            f"🏷️ {categorie}",
            f"📝 {description}",
        ]

        if url:
            lignes.append(
                f"🔗 {url}"
            )

        blocs.append(
            "\n".join(lignes)
        )

    limite_discord = 1900
    messages = []
    courant = entete

    for bloc in blocs:
        candidat = (
            courant
            + "\n\n"
            + bloc
        )

        if len(candidat) <= limite_discord:
            courant = candidat
            continue

        messages.append(courant)
        courant = (
            f"🆕 **SUITE — {total} NOUVELLES ANNONCES DÉTECTÉES**"
            + "\n\n"
            + bloc
        )

    messages.append(courant)
    return messages


def envoyer_nouvelles_annonces_discord(
    annonces,
):
    messages = construire_messages_nouvelles_annonces(
        annonces
    )

    if not messages:
        return False

    resultats = []

    for numero, message in enumerate(
        messages,
        start=1,
    ):
        label = "Nouvelles annonces Discord"

        if len(messages) > 1:
            label += (
                f" ({numero}/{len(messages)})"
            )

        resultats.append(
            envoyer_message_discord(
                message,
                label=label,
            )
        )

    return all(resultats)


# ============================================================
# NOUVEAU PC DÉTECTÉ
# ============================================================

def envoyer_nouveau_pc_discord(
    annonce,
    categorie,
    est_nouvelle,
):

    # --------------------------------------------------------
    # Seulement première détection
    # --------------------------------------------------------

    if not est_nouvelle:

        return False


    # --------------------------------------------------------
    # Seulement les vraies catégories PC
    # --------------------------------------------------------

    categories_autorisees = {
        "PC_GAMING",
        "PC_COMPLET",
        "PORTABLE",
        "PORTABLE_GAMING",
    }


    if categorie not in categories_autorisees:

        return False


    titre = getattr(
        annonce,
        "titre",
        "Annonce PC",
    )


    prix = getattr(
        annonce,
        "prix",
        "?",
    )


    localisation = getattr(
        annonce,
        "localisation",
        "Localisation inconnue",
    )


    plateforme = getattr(
        annonce,
        "plateforme",
        "Plateforme inconnue",
    )


    distance = getattr(
        annonce,
        "distance_km",
        None,
    )


    url = getattr(
        annonce,
        "url",
        None,
    )


    lignes = [

        "🆕 **NOUVEAU PC DÉTECTÉ**",

        "",

        f"🖥️ **{titre}**",

        "",

        (
            f"💵 Prix : "
            f"**{formater_nombre(prix)} €**"
        ),

        (
            f"📍 Localisation : "
            f"**{localisation}**"
        ),

        (
            f"🌐 Plateforme : "
            f"**{plateforme}**"
        ),

        (
            f"🏷️ Type : "
            f"**{categorie}**"
        ),
    ]


    if distance is not None:

        lignes.append(
            (
                f"🚗 Distance : "
                f"**{distance} km**"
            )
        )


    lignes.extend(
        [
            "",
            "🔎 Analyse PC Hunter en cours...",
        ]
    )


    if url:

        lignes.extend(
            [
                "",
                f"🔗 {url}",
            ]
        )


    message = "\n".join(
        lignes
    )


    return envoyer_message_discord(
        message,
        label="Nouveau PC Discord",
    )


# ============================================================
# ALERTE OPPORTUNITÉ
# ============================================================

def construire_message_discord(
    alerte
):

    titre = alerte[
        "titre"
    ]

    prix = alerte[
        "prix"
    ]


    valeur_probable = alerte[
        "valeur_probable"
    ]


    benefice_min = alerte[
        "benefice_min"
    ]

    benefice_max = alerte[
        "benefice_max"
    ]


    distance = alerte.get(
        "distance_km"
    )


    score_opportunite = alerte[
        "score_opportunite"
    ]


    score_classement = alerte[
        "score_classement"
    ]


    fraicheur = alerte[
        "fraicheur"
    ]


    url = alerte.get(
        "url"
    )


    # ========================================================
    # TYPE D'ALERTE
    # ========================================================

    if (
        alerte["niveau"]
        ==
        "PEPITE"
    ):

        entete = (
            "🚨💎 **PÉPITE PC HUNTER**"
        )

    else:

        entete = (
            "🚨 **OPPORTUNITÉ PRIORITAIRE**"
        )


    # ========================================================
    # MARGE
    # ========================================================

    if (
        benefice_min
        ==
        benefice_max
    ):

        marge = (
            f"+{formater_nombre(benefice_min)} €"
        )

    else:

        marge = (
            f"+{formater_nombre(benefice_min)} "
            f"à "
            f"+{formater_nombre(benefice_max)} €"
        )


    # ========================================================
    # MESSAGE
    # ========================================================

    lignes = [

        entete,

        "",

        f"🖥️ **{titre}**",

        "",

        (
            f"💵 Achat : "
            f"**{formater_nombre(prix)} €**"
        ),

        (
            f"🎯 Valeur probable : "
            f"**{formater_nombre(valeur_probable)} €**"
        ),

        (
            f"💰 Marge estimée : "
            f"**{marge}**"
        ),
    ]


    if distance is not None:

        lignes.append(
            (
                f"📍 Distance : "
                f"**{distance} km**"
            )
        )


    lignes.extend(
        [
            (
                f"💎 Opportunité : "
                f"**{score_opportunite}/100**"
            ),

            (
                f"🎯 Score profil : "
                f"**{score_classement}/100**"
            ),

            (
                f"⏱️ {fraicheur['label']}"
            ),
        ]
    )


    if (
        fraicheur[
            "age_secondes"
        ]
        is not None
    ):

        lignes.append(
            (
                f"🕒 Publiée il y a : "
                f"**{fraicheur['age_texte']}**"
            )
        )


    lignes.extend(
        [
            "",
            "⚡ **À VÉRIFIER RAPIDEMENT**",
        ]
    )


    if url:

        lignes.extend(
            [
                "",
                f"🔗 {url}",
            ]
        )


    return "\n".join(
        lignes
    )


def envoyer_alerte_discord(
    alerte
):

    if not alerte.get(
        "declencher",
        False,
    ):

        return False


    message = (
        construire_message_discord(
            alerte
        )
    )


    return envoyer_message_discord(
        message,
        label="Alerte PC Hunter Discord",
    )


# ============================================================
# NOTIFICATION BAISSE DE PRIX
# ============================================================

def envoyer_baisse_prix_discord(
    alerte
):

    if not alerte.get(
        "declencher",
        False,
    ):

        return False


    ancien_prix = alerte[
        "ancien_prix"
    ]

    nouveau_prix = alerte[
        "nouveau_prix"
    ]

    baisse_euros = alerte[
        "baisse_euros"
    ]

    baisse_pourcentage = alerte[
        "baisse_pourcentage"
    ]


    if (
        alerte["niveau"]
        ==
        "BAISSE_IMPORTANTE"
    ):

        entete = (
            "🚨📉 **FORTE BAISSE DE PRIX PC HUNTER**"
        )

    else:

        entete = (
            "📉 **BAISSE DE PRIX PC HUNTER**"
        )


    lignes = [

        entete,

        "",

        (
            f"🖥️ **"
            f"{alerte['titre']}"
            f"**"
        ),

        "",

        (
            f"💵 Ancien prix : "
            f"**{formater_nombre(ancien_prix)} €**"
        ),

        (
            f"💵 Nouveau prix : "
            f"**{formater_nombre(nouveau_prix)} €**"
        ),

        (
            f"📉 Baisse : "
            f"**{formater_nombre(baisse_euros)} € "
            f"({formater_nombre(baisse_pourcentage)} %) **"
        ),
    ]


    distance = alerte.get(
        "distance_km"
    )


    if distance is not None:

        lignes.append(
            (
                f"📍 Distance : "
                f"**{distance} km**"
            )
        )


    lignes.extend(
        [
            "",
            "⚡ **Le nouveau prix mérite une nouvelle vérification.**",
        ]
    )


    url = alerte.get(
        "url"
    )


    if url:

        lignes.extend(
            [
                "",
                f"🔗 {url}",
            ]
        )


    message = "\n".join(
        lignes
    )


    return envoyer_message_discord(
        message,
        label="Alerte baisse de prix Discord",
    )
