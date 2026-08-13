import sys
import time
import traceback

from datetime import (
    datetime,
    timedelta,
)

from pathlib import Path

from main import main

from config import (
    INTERVALLE_SCAN_MINUTES,
)


# ============================================================
# PARAMÈTRES RADAR
# ============================================================

# Protection contre une mauvaise valeur dans config.py
# qui provoquerait des scans en boucle ultra-rapide.
INTERVALLE_MINIMUM_MINUTES = 5

# Le fichier est créé à la racine du projet.
FICHIER_LOG = (
    Path(__file__).resolve().parent
    / "radar.log"
)


# ============================================================
# SORTIE CONSOLE + FICHIER
# ============================================================

class SortieDouble:
    """
    Envoie chaque print à la fois :
    - vers la console PowerShell ;
    - vers radar.log en UTF-8.

    Ainsi, tout ce que main.py affiche déjà
    (sources, déduplication, géographie, TOP, erreurs...)
    est automatiquement conservé dans le journal.
    """

    def __init__(
        self,
        sortie_console,
        fichier_log,
    ):
        self.sortie_console = (
            sortie_console
        )

        self.fichier_log = (
            fichier_log
        )

    def write(
        self,
        texte,
    ):
        self.sortie_console.write(
            texte
        )

        self.fichier_log.write(
            texte
        )

        return len(
            texte
        )

    def flush(
        self,
    ):
        self.sortie_console.flush()
        self.fichier_log.flush()

    def isatty(
        self,
    ):
        return self.sortie_console.isatty()

    @property
    def encoding(
        self,
    ):
        return getattr(
            self.sortie_console,
            "encoding",
            "utf-8",
        )


# ============================================================
# INTERVALLE
# ============================================================

def obtenir_intervalle_effectif():
    try:
        intervalle = float(
            INTERVALLE_SCAN_MINUTES
        )

    except (
        TypeError,
        ValueError,
    ):
        intervalle = (
            INTERVALLE_MINIMUM_MINUTES
        )

    if (
        intervalle
        <
        INTERVALLE_MINIMUM_MINUTES
    ):
        intervalle = (
            INTERVALLE_MINIMUM_MINUTES
        )

    return intervalle


# ============================================================
# AFFICHAGE
# ============================================================

def afficher_entete_radar():
    intervalle = (
        obtenir_intervalle_effectif()
    )

    print()
    print(
        "========================================"
    )
    print(
        "📡 PC HUNTER - MODE RADAR"
    )
    print(
        "========================================"
    )
    print(
        f"⏱️ Intervalle : "
        f"{intervalle:g} minute(s)"
    )
    print(
        "📲 Alertes Discord : actives"
    )
    print(
        "💾 Historique annonces : actif"
    )
    print(
        "🗺️ Filtre géographique : actif"
    )
    print(
        "🛡️ Garde financière : active"
    )
    print(
        "📝 Journal : radar.log"
    )
    print(
        "🛑 Pour arrêter : CTRL + C"
    )
    print(
        "========================================"
    )
    print()


# ============================================================
# UN SCAN
# ============================================================

def executer_scan(
    numero_scan,
):
    debut_scan = (
        datetime.now()
    )

    print()
    print()
    print(
        "========================================"
    )
    print(
        f"🔄 SCAN RADAR #{numero_scan}"
    )
    print(
        "🕒",
        debut_scan.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )
    print(
        "========================================"
    )
    print()

    try:
        main()

        fin_scan = (
            datetime.now()
        )

        duree = (
            fin_scan
            -
            debut_scan
        )

        secondes = round(
            duree.total_seconds(),
            1,
        )

        print()
        print(
            f"✅ Scan #{numero_scan} terminé"
        )
        print(
            f"⏱️ Durée : {secondes} seconde(s)"
        )
        print(
            "📊 Statut du scan : OK"
        )

        return True

    except Exception as erreur:
        fin_scan = (
            datetime.now()
        )

        secondes = round(
            (
                fin_scan
                -
                debut_scan
            ).total_seconds(),
            1,
        )

        print()
        print(
            "⚠️ ERREUR PENDANT LE SCAN"
        )
        print(
            type(erreur).__name__,
            ":",
            erreur,
        )
        print()
        print(
            "📚 Trace complète :"
        )

        traceback.print_exc()

        print()
        print(
            f"⏱️ Durée avant erreur : "
            f"{secondes} seconde(s)"
        )
        print(
            "📊 Statut du scan : ERREUR"
        )
        print()
        print(
            "🔄 Le radar n'est pas arrêté."
        )
        print(
            "➡️ Un nouveau scan sera tenté "
            "après l'intervalle normal."
        )

        return False


# ============================================================
# ATTENTE
# ============================================================

def attendre_prochain_scan():
    intervalle = (
        obtenir_intervalle_effectif()
    )

    secondes_attente = int(
        intervalle
        *
        60
    )

    prochain_scan = (
        datetime.now()
        +
        timedelta(
            seconds=secondes_attente
        )
    )

    print()
    print(
        "💤 Radar en attente..."
    )
    print(
        "⏰ Prochain scan :",
        prochain_scan.strftime(
            "%H:%M:%S"
        ),
    )
    print(
        f"⏱️ Dans {intervalle:g} minute(s)"
    )
    print()

    time.sleep(
        secondes_attente
    )


# ============================================================
# RADAR
# ============================================================

def lancer_radar():
    # Append : on conserve les anciens scans.
    # buffering=1 : écrit progressivement dans le fichier.
    with open(
        FICHIER_LOG,
        "a",
        encoding="utf-8",
        buffering=1,
    ) as fichier_log:

        sortie_console = (
            sys.stdout
        )

        erreur_console = (
            sys.stderr
        )

        sortie_double = (
            SortieDouble(
                sortie_console,
                fichier_log,
            )
        )

        erreur_double = (
            SortieDouble(
                erreur_console,
                fichier_log,
            )
        )

        sys.stdout = (
            sortie_double
        )

        sys.stderr = (
            erreur_double
        )

        try:
            print()
            print(
                "########################################"
            )
            print(
                "📝 OUVERTURE SESSION RADAR"
            )
            print(
                "🕒",
                datetime.now().strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
            )
            print(
                "📁 Log :",
                FICHIER_LOG,
            )
            print(
                "########################################"
            )

            afficher_entete_radar()

            numero_scan = 0

            try:
                while True:
                    numero_scan += 1

                    executer_scan(
                        numero_scan
                    )

                    attendre_prochain_scan()

            except KeyboardInterrupt:
                print()
                print()
                print(
                    "========================================"
                )
                print(
                    "🛑 PC HUNTER RADAR ARRÊTÉ"
                )
                print(
                    "========================================"
                )
                print()
                print(
                    "💾 Les annonces et l'historique "
                    "déjà enregistrés sont conservés."
                )
                print(
                    "📝 Le journal radar.log "
                    "est également conservé."
                )
                print()

        finally:
            sys.stdout = (
                sortie_console
            )

            sys.stderr = (
                erreur_console
            )


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    lancer_radar()