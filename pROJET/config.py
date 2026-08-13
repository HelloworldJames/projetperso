# ============================================================
# CONFIGURATION PC HUNTER
# ============================================================


# ============================================================
# PROFIL D'ACHAT
# ============================================================

PROFIL = "equilibre"

# Profils disponibles :
#
# "prudent"
# "equilibre"
# "reparation"

TOP_N = 20

BUDGET_MAX = 600

MARGE_MIN = 50

ACCEPTER_REPARATIONS = True


# ============================================================
# SOURCES
# ============================================================

# Fichier JSON de test
ACTIVER_JSON = False


# ParuVendu réel
ACTIVER_PARUVENDU = True


# Vivastreet réel
ACTIVER_VIVASTREET = True


# eBay officiel
# On laisse désactivé tant que l'accès API
# n'est pas prêt.
ACTIVER_EBAY = False

# Requêtes PC généralistes pour l'API Browse officielle eBay.
EBAY_RECHERCHES = (
    "pc gamer occasion",
    "ordinateur portable gamer occasion",
    "macbook occasion",
)


# ============================================================
# FILTRE GEOGRAPHIQUE PC HUNTER
# ============================================================

ACTIVER_FILTRE_GEO = True

VILLE_ORIGINE = "Tonnay-Charente"

RAYON_KM = 50


# ============================================================
# RADAR AUTOMATIQUE
# ============================================================

INTERVALLE_SCAN_MINUTES = 5
