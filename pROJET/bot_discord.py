import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from collector.http import creer_contexte_tls_windows
from database.listing import DB_PATH
from database.watchlist import ajouter_watchlist
from discord_hunter import (
    construire_message_analyse,
    construire_message_disparues,
    construire_message_pepites,
    construire_message_sources,
    construire_message_veille,
)
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env"
)

TOKEN = os.getenv(
    "DISCORD_BOT_TOKEN"
)

GUILD_ID = os.getenv(
    "DISCORD_GUILD_ID"
)

TOP_PATH = (
    BASE_DIR
    / "data"
    / "top_actuel.json"
)


# ============================================================
# VERIFICATIONS
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_BOT_TOKEN absent du fichier .env"
    )


if not GUILD_ID:

    raise RuntimeError(
        "DISCORD_GUILD_ID absent du fichier .env"
    )


try:

    GUILD_ID = int(
        GUILD_ID
    )

except ValueError:

    raise RuntimeError(
        "DISCORD_GUILD_ID doit être un nombre"
    )


SERVEUR_PC_HUNTER = discord.Object(
    id=GUILD_ID
)


# ============================================================
# OUTILS
# ============================================================

def formater_prix(
    valeur
):

    if valeur is None:
        return "?"

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


def charger_top():

    if not TOP_PATH.exists():

        return None

    try:

        with TOP_PATH.open(
            "r",
            encoding="utf-8",
        ) as fichier:

            return json.load(
                fichier
            )

    except (
        OSError,
        json.JSONDecodeError,
    ):

        return None


def interaction_est_administrateur(interaction):
    permissions = getattr(
        interaction,
        "permissions",
        None,
    )

    return bool(
        permissions
        and getattr(
            permissions,
            "administrator",
            False,
        )
    )


def ajouter_url_watchlist_discord(
    url,
    titre=None,
    prix=None,
    description=None,
    localisation=None,
    db_path=DB_PATH,
):
    """Point d'entree testable partage par la commande Discord."""
    return ajouter_watchlist(
        url=url,
        titre=titre,
        prix_connu=prix,
        description=description,
        localisation=localisation,
        db_path=db_path,
    )


def champs_manquants_watchlist(annonce):
    correspondances = (
        ("titre", "titre"),
        ("dernier_prix_connu", "prix"),
        ("description", "description"),
        ("localisation", "localisation"),
    )

    return [
        libelle
        for champ, libelle in correspondances
        if annonce.get(champ) in (None, "")
    ]


def construire_message_ajout_watchlist(annonce):
    action = (
        "ajoutee"
        if annonce.get("cree")
        else "mise a jour/reactivee"
    )
    manquants = champs_manquants_watchlist(
        annonce
    )

    lignes = [
        "📥 **ANNONCE AJOUTEE PAR UN ADMIN**",
        "",
        f"Plateforme : **{annonce['plateforme']}**",
        f"URL : {annonce['url']}",
        f"Etat : **{action}**",
    ]

    if annonce.get("titre"):
        lignes.append(
            f"Titre : **{annonce['titre']}**"
        )

    if annonce.get("dernier_prix_connu") is not None:
        lignes.append(
            "Prix : **"
            f"{formater_prix(annonce['dernier_prix_connu'])} €**"
        )

    lignes.append("")

    if manquants:
        lignes.extend(
            [
                "🟡 Statut : **en etude**",
                "Informations manquantes : "
                + ", ".join(manquants)
                + ".",
                (
                    "Pour une analyse automatique, ouvrez l'URL dans votre "
                    "navigateur puis utilisez le Compagnon Hunter. Hunter "
                    "lira les informations visibles dans votre session sans "
                    "contourner le site."
                ),
            ]
        )
    else:
        lignes.extend(
            [
                "🟢 Statut : **prete pour analyse**",
                (
                    "Hunter l'integrera automatiquement au prochain "
                    "scan du radar (5 minutes maximum)."
                ),
            ]
        )

    return "\n".join(lignes)


# ============================================================
# BOT
# ============================================================

class PCHunterBot(
    discord.Client
):

    def __init__(
        self
    ):

        intents = discord.Intents.default()

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )


    async def login(
        self,
        token,
    ):
        # Le connecteur doit être créé dans la boucle asyncio.
        # La vérification TLS reste active ; seul le mode X509_STRICT,
        # incompatible avec certains certificats d'antivirus Windows,
        # est retiré par creer_contexte_tls_windows().
        self.http.connector = aiohttp.TCPConnector(
            ssl=creer_contexte_tls_windows()
        )

        await super().login(
            token
        )


    async def setup_hook(
        self
    ):

        self.tree.copy_global_to(
            guild=SERVEUR_PC_HUNTER
        )

        commandes = await self.tree.sync(
            guild=SERVEUR_PC_HUNTER
        )

        print(
            f"✅ {len(commandes)} commande(s) "
            "Discord synchronisée(s) sur le serveur"
        )


bot = PCHunterBot()


# ============================================================
# BOT CONNECTE
# ============================================================

@bot.event
async def on_ready():

    print()
    print("=" * 40)
    print("🤖 HUNTER IA BOT")
    print("=" * 40)

    print(
        f"Connecté comme : {bot.user}"
    )

    print(
        f"Serveur ID : {GUILD_ID}"
    )

    print("=" * 40)
    print()


# ============================================================
# COMMANDE /AJOUTER (ADMIN)
# ============================================================

@bot.tree.command(
    name="ajouter",
    description="Ajouter une URL d'annonce a etudier (admin)",
)
@app_commands.describe(
    url="URL complete de l'annonce",
    titre="Titre connu de l'annonce",
    prix="Prix connu en euros",
    description="Caracteristiques ou description connues",
    localisation="Ville ou code postal connu",
)
@app_commands.default_permissions(
    administrator=True
)
@app_commands.guild_only()
async def ajouter(
    interaction: discord.Interaction,
    url: str,
    titre: Optional[str] = None,
    prix: Optional[float] = None,
    description: Optional[str] = None,
    localisation: Optional[str] = None,
):
    if not interaction_est_administrateur(
        interaction
    ):
        await interaction.response.send_message(
            "⛔ Cette commande est reservee aux administrateurs.",
            ephemeral=True,
        )
        return

    try:
        annonce = ajouter_url_watchlist_discord(
            url=url,
            titre=titre,
            prix=prix,
            description=description,
            localisation=localisation,
        )

    except (ValueError, sqlite3.Error) as erreur:
        await interaction.response.send_message(
            f"⚠️ Ajout impossible : {erreur}",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        construire_message_ajout_watchlist(
            annonce
        )
    )


# ============================================================
# COMMANDE /STATUS
# ============================================================

@bot.tree.command(
    name="status",
    description="Afficher l'état de PC Hunter",
)
async def status(
    interaction: discord.Interaction
):

    try:

        connexion = sqlite3.connect(
            DB_PATH
        )

        curseur = connexion.cursor()

        annonces = curseur.execute(
            """
            SELECT COUNT(*)
            FROM annonces
            """
        ).fetchone()[0]

        actives = curseur.execute(
            """
            SELECT COUNT(*)
            FROM presence_annonces
            WHERE active = 1
            """
        ).fetchone()[0]

        connexion.close()

    except sqlite3.Error:

        await interaction.response.send_message(
            "⚠️ Impossible de lire la base PC Hunter."
        )

        return


    donnees_top = charger_top()

    nombre_top = 0

    if donnees_top:

        nombre_top = donnees_top.get(
            "nombre_resultats",
            0,
        )


    message = (
        "🟢 **PC HUNTER ONLINE**\n\n"
        f"🗃️ Annonces mémorisées : **{annonces}**\n"
        f"👁️ Annonces actives : **{actives}**\n"
        f"🏆 Opportunités dans le Top : **{nombre_top}**\n"
        "📍 Rayon : **50 km**\n"
        "⏱️ Scan : **toutes les 5 minutes**"
    )


    await interaction.response.send_message(
        message
    )


# ============================================================
# COMMANDE /TOP
# ============================================================

@bot.tree.command(
    name="top",
    description="Afficher les meilleures opportunités PC Hunter",
)
async def top(
    interaction: discord.Interaction
):

    donnees = charger_top()


    if donnees is None:

        await interaction.response.send_message(
            "⚠️ Aucun snapshot PC Hunter disponible pour le moment."
        )

        return


    resultats = donnees.get(
        "top",
        [],
    )


    profil = donnees.get(
        "profil",
        "inconnu",
    )


    budget_max = donnees.get(
        "budget_max",
        "?",
    )


    marge_min = donnees.get(
        "marge_min",
        "?",
    )


    date_generation = donnees.get(
        "date_generation",
        "?",
    )


    # --------------------------------------------------------
    # TOP VIDE
    # --------------------------------------------------------

    if not resultats:

        message = (
            "🏆 **PC HUNTER — TOP ACTUEL**\n\n"
            "😴 **Aucune opportunité rentable actuellement.**\n\n"
            f"🎯 Profil : **{str(profil).upper()}**\n"
            f"💳 Budget max : **{formater_prix(budget_max)} €**\n"
            f"💰 Marge minimum : **{formater_prix(marge_min)} €**\n\n"
            "🟢 Le radar continue sa surveillance."
        )


        await interaction.response.send_message(
            message
        )

        return


    # --------------------------------------------------------
    # TOP AVEC RESULTATS
    # --------------------------------------------------------

    lignes = [

        "🏆 **PC HUNTER — TOP ACTUEL**",

        "",

        (
            f"🎯 Profil : "
            f"**{str(profil).upper()}**"
        ),

        (
            f"💳 Budget max : "
            f"**{formater_prix(budget_max)} €**"
        ),

        (
            f"💰 Marge minimum : "
            f"**{formater_prix(marge_min)} €**"
        ),

        "",
    ]


    medailles = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }


    for resultat in resultats:

        position = resultat.get(
            "position",
            "?",
        )


        medaille = medailles.get(
            position,
            "🏅",
        )


        titre = resultat.get(
            "titre",
            "Annonce inconnue",
        )


        prix = resultat.get(
            "prix"
        )


        localisation = resultat.get(
            "localisation"
        )


        plateforme = resultat.get(
            "plateforme"
        )


        distance = resultat.get(
            "distance_km"
        )


        benefice_min = resultat.get(
            "benefice_min"
        )


        benefice_max = resultat.get(
            "benefice_max"
        )


        score = resultat.get(
            "score_classement"
        )


        url = resultat.get(
            "url"
        )


        lignes.append(
            f"{medaille} **#{position} — {titre}**"
        )


        lignes.append(
            f"💵 Prix : **{formater_prix(prix)} €**"
        )


        if (
            benefice_min is not None
            and
            benefice_max is not None
        ):

            if benefice_min == benefice_max:

                lignes.append(
                    "💰 Marge prudente : "
                    f"**+{formater_prix(benefice_min)} €**"
                )

            else:

                lignes.append(
                    "💰 Marge estimée : "
                    f"**+{formater_prix(benefice_min)} "
                    f"à +{formater_prix(benefice_max)} €**"
                )


        if score is not None:

            lignes.append(
                f"💎 Score : **{score}/100**"
            )


        if localisation:

            texte_lieu = (
                f"📍 {localisation}"
            )

            if distance is not None:

                texte_lieu += (
                    f" — {distance} km"
                )

            lignes.append(
                texte_lieu
            )


        if plateforme:

            lignes.append(
                f"🌐 {plateforme}"
            )


        if url:

            lignes.append(
                f"🔗 {url}"
            )


        lignes.append(
            ""
        )


    message = "\n".join(
        lignes
    )


    # Sécurité Discord :
    # un message classique ne peut pas être énorme.

    if len(message) > 1900:

        message = (
            message[:1850]
            +
            "\n\n⚠️ Top tronqué : trop de données à afficher."
        )


    await interaction.response.send_message(
        message
    )
# ============================================================
# COMMANDE /LAST
# ============================================================

@bot.tree.command(
    name="last",
    description="Afficher les dernières annonces détectées",
)
async def last(
    interaction: discord.Interaction
):

    try:

        connexion = sqlite3.connect(
            DB_PATH
        )

        curseur = connexion.cursor()

        annonces = curseur.execute(
            """
            SELECT
                a.titre,
                a.prix_actuel,
                a.localisation,
                a.plateforme,
                a.url,
                a.premiere_detection
            FROM annonces AS a
            INNER JOIN presence_annonces AS p
                ON p.plateforme = a.plateforme
                AND p.identifiant = a.identifiant
            WHERE p.active = 1
            ORDER BY a.premiere_detection DESC
            LIMIT 5
            """
        ).fetchall()

        connexion.close()

    except sqlite3.Error as erreur:

        print(
            "⚠️ Erreur /last :",
            erreur,
        )

        await interaction.response.send_message(
            "⚠️ Impossible de lire les annonces PC Hunter."
        )

        return


    if not annonces:

        await interaction.response.send_message(
            "📭 **Aucune annonce active enregistrée actuellement.**"
        )

        return


    lignes = [

        "🆕 **PC HUNTER — DERNIÈRES ANNONCES**",

        "",
    ]


    for position, annonce in enumerate(
        annonces,
        start=1,
    ):

        (
            titre,
            prix,
            localisation,
            plateforme,
            url,
            premiere_detection,
        ) = annonce


        lignes.append(
            f"**#{position} — {titre}**"
        )

        lignes.append(
            f"💵 Prix : **{formater_prix(prix)} €**"
        )

        if localisation:

            lignes.append(
                f"📍 {localisation}"
            )

        if plateforme:

            lignes.append(
                f"🌐 {plateforme}"
            )

        if premiere_detection:

            date_affichee = (
                premiere_detection
                .replace("T", " ")
                [:16]
            )

            lignes.append(
                f"🕒 Première détection : {date_affichee}"
            )

        if url:

            lignes.append(
                f"🔗 {url}"
            )

        lignes.append(
            ""
        )


    message = "\n".join(
        lignes
    )


    if len(message) > 1900:

        message = (
            message[:1850]
            +
            "\n\n⚠️ Liste tronquée."
        )


    await interaction.response.send_message(
        message
    )


# ============================================================
# COMMANDES HUNTER V1.5
# ============================================================

@bot.tree.command(
    name="analyse",
    description="Afficher le dernier verdict Hunter d'une annonce",
)
@app_commands.describe(
    reference="Identifiant public ou URL complète de l'annonce",
)
async def analyse(
    interaction: discord.Interaction,
    reference: str,
):
    try:
        message = construire_message_analyse(reference)
    except sqlite3.Error:
        message = "⚠️ La base d'analyses Hunter est indisponible."
    await interaction.response.send_message(message)


@bot.tree.command(
    name="pepites",
    description="Afficher les trois meilleures affaires validées",
)
async def pepites(interaction: discord.Interaction):
    try:
        message = construire_message_pepites()
    except sqlite3.Error:
        message = "⚠️ Le classement des pépites est indisponible."
    await interaction.response.send_message(message)


@bot.tree.command(
    name="veille",
    description="Afficher les annonces suivies et leur état",
)
async def veille(interaction: discord.Interaction):
    try:
        message = construire_message_veille()
    except sqlite3.Error:
        message = "⚠️ La watchlist Hunter est indisponible."
    await interaction.response.send_message(message)


@bot.tree.command(
    name="disparues",
    description="Afficher les dernières annonces absentes du radar",
)
async def disparues(interaction: discord.Interaction):
    try:
        message = construire_message_disparues()
    except sqlite3.Error:
        message = "⚠️ Aucun historique de présence n'est encore disponible."
    await interaction.response.send_message(message)


@bot.tree.command(
    name="sources",
    description="Afficher les sources et leurs modes d'accès",
)
async def sources(interaction: discord.Interaction):
    await interaction.response.send_message(
        construire_message_sources()
    )

    # ============================================================
# COMMANDE /STATS
# ============================================================

@bot.tree.command(
    name="stats",
    description="Afficher les statistiques de PC Hunter",
)
async def stats(
    interaction: discord.Interaction
):

    try:

        connexion = sqlite3.connect(
            DB_PATH
        )

        curseur = connexion.cursor()


        # ----------------------------------------------------
        # ANNONCES MEMORISEES
        # ----------------------------------------------------

        annonces_total = curseur.execute(
            """
            SELECT COUNT(*)
            FROM annonces
            """
        ).fetchone()[0]


        # ----------------------------------------------------
        # ANNONCES ACTIVES
        # ----------------------------------------------------

        annonces_actives = curseur.execute(
            """
            SELECT COUNT(*)
            FROM presence_annonces
            WHERE active = 1
            """
        ).fetchone()[0]


        # ----------------------------------------------------
        # ANNONCES DISPARUES
        # ----------------------------------------------------

        annonces_disparues = curseur.execute(
            """
            SELECT COUNT(*)
            FROM presence_annonces
            WHERE active = 0
            """
        ).fetchone()[0]


        # ----------------------------------------------------
        # HISTORIQUE DES PRIX
        # ----------------------------------------------------

        historique_prix = curseur.execute(
            """
            SELECT
                identifiant_annonce,
                prix,
                date_detection
            FROM historique_prix
            ORDER BY
                identifiant_annonce,
                date_detection,
                id
            """
        ).fetchall()


        # ----------------------------------------------------
        # PLATEFORMES
        # ----------------------------------------------------

        plateformes = curseur.execute(
            """
            SELECT
                plateforme,
                COUNT(*)
            FROM annonces
            GROUP BY plateforme
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()


        connexion.close()


    except sqlite3.Error as erreur:

        print(
            "⚠️ Erreur /stats :",
            erreur,
        )

        await interaction.response.send_message(
            "⚠️ Impossible de lire les statistiques PC Hunter."
        )

        return


    # ========================================================
    # CALCUL DES BAISSES DE PRIX
    # ========================================================

    baisses_prix = 0

    dernier_prix = {}


    for (
        identifiant,
        prix,
        date_detection,
    ) in historique_prix:

        if prix is None:
            continue


        if identifiant in dernier_prix:

            ancien_prix = dernier_prix[
                identifiant
            ]

            if (
                ancien_prix is not None
                and
                prix < ancien_prix
            ):

                baisses_prix += 1


        dernier_prix[
            identifiant
        ] = prix


    # ========================================================
    # TOP ACTUEL
    # ========================================================

    donnees_top = charger_top()

    nombre_top = 0
    date_top = None


    if donnees_top:

        nombre_top = donnees_top.get(
            "nombre_resultats",
            0,
        )

        date_top = donnees_top.get(
            "date_generation"
        )


    # ========================================================
    # PLATEFORMES EN TEXTE
    # ========================================================

    if plateformes:

        lignes_plateformes = []

        for (
            plateforme,
            nombre,
        ) in plateformes:

            lignes_plateformes.append(
                f"• {plateforme} : **{nombre}**"
            )

        texte_plateformes = "\n".join(
            lignes_plateformes
        )

    else:

        texte_plateformes = (
            "• Aucune plateforme enregistrée"
        )


    # ========================================================
    # MESSAGE
    # ========================================================

    lignes = [

        "📊 **PC HUNTER — STATISTIQUES**",

        "",

        f"🗃️ Annonces mémorisées : **{annonces_total}**",

        f"👁️ Annonces actives : **{annonces_actives}**",

        f"👻 Annonces disparues : **{annonces_disparues}**",

        f"📉 Baisses de prix détectées : **{baisses_prix}**",

        f"🏆 Opportunités dans le Top : **{nombre_top}**",

        "",

        "🌐 **Plateformes en mémoire**",

        texte_plateformes,
    ]


    if date_top:

        date_affichee = (
            str(date_top)
            .replace("T", " ")
            [:19]
        )

        lignes.extend(
            [
                "",
                f"🕒 Dernier Top calculé : **{date_affichee}**",
            ]
        )


    message = "\n".join(
        lignes
    )


    await interaction.response.send_message(
        message
    )

# ============================================================
# DEMARRAGE
# ============================================================

if __name__ == "__main__":
    bot.run(
        TOKEN
    )
