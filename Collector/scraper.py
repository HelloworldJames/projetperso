from collector.providers.json_provider import (
    JsonProvider,
)

from collector.providers.paruvendu import (
    rechercher as rechercher_paruvendu,
)

from collector.providers.vivastreet import (
    rechercher as rechercher_vivastreet,
)

from collector.providers.watchlist import (
    rechercher as rechercher_watchlist,
)

from collector.geo import (
    filtrer_par_distance,
)

from collector.dedup import (
    dedupliquer_annonces,
)

from config import (
    ACTIVER_JSON,
    ACTIVER_PARUVENDU,
    ACTIVER_VIVASTREET,
    ACTIVER_EBAY,
    ACTIVER_FILTRE_GEO,
    VILLE_ORIGINE,
    RAYON_KM,
)


# ============================================================
# CHARGEMENT GENERIQUE D'UNE SOURCE
# ============================================================

def charger_provider(
    provider,
    nom,
):

    try:

        print()
        print(
            f"📡 Chargement source : {nom}"
        )

        # ----------------------------------------------------
        # Provider sous forme d'objet :
        #
        # JsonProvider().rechercher()
        # ----------------------------------------------------

        if hasattr(
            provider,
            "rechercher",
        ):

            annonces = (
                provider.rechercher()
            )

        # ----------------------------------------------------
        # Provider sous forme de fonction :
        #
        # rechercher_paruvendu()
        # rechercher_vivastreet()
        # ----------------------------------------------------

        elif callable(
            provider
        ):

            annonces = (
                provider()
            )

        else:

            print(
                f"⚠️ Provider {nom} non reconnu."
            )

            return []


        if annonces is None:

            annonces = []


        print(
            f"✅ {nom} : "
            f"{len(annonces)} annonces récupérées"
        )


        return annonces


    except Exception as erreur:

        print()
        print(
            f"⚠️ Erreur provider {nom} :",
            erreur,
        )

        print(
            f"➡️ PC Hunter continue sans {nom}."
        )

        return []


# ============================================================
# JSON
# ============================================================

def charger_json():

    try:

        provider = (
            JsonProvider()
        )

    except Exception as erreur:

        print()
        print(
            "⚠️ Impossible d'initialiser JSON :",
            erreur,
        )

        return []


    return charger_provider(
        provider,
        "JSON",
    )


# ============================================================
# PARUVENDU
# ============================================================

def charger_paruvendu():

    return charger_provider(
        rechercher_paruvendu,
        "ParuVendu",
    )


# ============================================================
# VIVASTREET
# ============================================================

def charger_vivastreet():

    return charger_provider(
        rechercher_vivastreet,
        "Vivastreet",
    )


# ============================================================
# WATCHLIST LOCALE
# ============================================================

def charger_watchlist():

    return charger_provider(
        rechercher_watchlist,
        "Watchlist locale",
    )


# ============================================================
# EBAY
# ============================================================

def charger_ebay():

    try:

        from collector.providers.ebay import (
            EbayProvider,
        )

    except ImportError as erreur:

        print()
        print(
            "⚠️ Provider eBay indisponible :",
            erreur,
        )

        return []


    try:

        provider = (
            EbayProvider()
        )

    except Exception as erreur:

        print()
        print(
            "⚠️ eBay n'est pas encore configuré :",
            erreur,
        )

        print(
            "➡️ PC Hunter continue sans eBay."
        )

        return []


    return charger_provider(
        provider,
        "eBay",
    )


# ============================================================
# RECHERCHE GENERALE
# ============================================================

def rechercher_annonces():

    annonces = []


    print()
    print(
        "========================================"
    )

    print(
        "🔎 PC HUNTER - COLLECTE"
    )

    print(
        "========================================"
    )


    # ========================================================
    # JSON
    # ========================================================

    if ACTIVER_JSON:

        annonces_json = (
            charger_json()
        )

        annonces.extend(
            annonces_json
        )


    # ========================================================
    # PARUVENDU
    # ========================================================

    if ACTIVER_PARUVENDU:

        annonces_paruvendu = (
            charger_paruvendu()
        )

        annonces.extend(
            annonces_paruvendu
        )


    # ========================================================
    # VIVASTREET
    # ========================================================

    if ACTIVER_VIVASTREET:

        annonces_vivastreet = (
            charger_vivastreet()
        )

        annonces.extend(
            annonces_vivastreet
        )


    # ========================================================
    # EBAY
    # ========================================================

    if ACTIVER_EBAY:

        annonces_ebay = (
            charger_ebay()
        )

        annonces.extend(
            annonces_ebay
        )


    # ========================================================
    # WATCHLIST LOCALE
    #
    # Toujours disponible : elle ne contacte aucune plateforme.
    # Les fiches incomplètes restent en attente dans SQLite.
    # ========================================================

    annonces_watchlist = (
        charger_watchlist()
    )

    annonces.extend(
        annonces_watchlist
    )


    # ========================================================
    # TOTAL BRUT
    # ========================================================

    print()

    print(
        "📦",
        len(annonces),
        "annonces récupérées "
        "avant déduplication",
    )


    # ========================================================
    # AUCUNE ANNONCE
    # ========================================================

    if not annonces:

        print()
        print(
            "⚠️ Aucune annonce récupérée."
        )

        return []


    # ========================================================
    # DEDUPLICATION
    # ========================================================

    try:

        avant_dedup = (
            len(annonces)
        )


        annonces = (
            dedupliquer_annonces(
                annonces
            )
        )


        print()
        print(
            "🧹 Déduplication :",
            avant_dedup,
            "→",
            len(annonces),
        )


    except Exception as erreur:

        print()
        print(
            "⚠️ Déduplication impossible :",
            erreur,
        )

        print(
            "➡️ Les annonces sont conservées "
            "sans déduplication."
        )


    # ========================================================
    # FILTRE GEOGRAPHIQUE
    #
    # Important :
    #
    # Vivastreet est actuellement lu au niveau national.
    # Le filtre PC Hunter garde ensuite uniquement
    # les annonces comprises dans notre rayon.
    #
    # Cela permet de conserver le même système géographique
    # pour toutes les plateformes.
    # ========================================================

    if (
        ACTIVER_FILTRE_GEO
        and
        annonces
    ):

        try:

            avant_geo = (
                len(annonces)
            )


            annonces = (
                filtrer_par_distance(
                    annonces,
                    VILLE_ORIGINE,
                    RAYON_KM,
                )
            )


            print()
            print(
                f"📍 Filtre géographique : "
                f"{VILLE_ORIGINE} + "
                f"{RAYON_KM} km"
            )

            print(
                "📦",
                avant_geo,
                "→",
                len(annonces),
                "annonces",
            )


        except Exception as erreur:

            print()
            print(
                "⚠️ Filtre géographique impossible :",
                erreur,
            )

            print(
                "➡️ Les annonces restent disponibles "
                "sans filtrage géographique."
            )


    # ========================================================
    # RESULTAT FINAL
    # ========================================================

    print()
    print(
        "========================================"
    )

    print(
        "✅ COLLECTE TERMINEE"
    )

    print(
        "📦",
        len(annonces),
        "annonces retenues",
    )

    print(
        "========================================"
    )


    return annonces
