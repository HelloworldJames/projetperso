"""Registre explicite des moyens d'accès autorisés de Hunter."""

import os

from config import ACTIVER_EBAY, ACTIVER_PARUVENDU, ACTIVER_VIVASTREET


def lister_sources_hunter():
    ebay_configure = bool(
        os.getenv("EBAY_CLIENT_ID")
        and os.getenv("EBAY_CLIENT_SECRET")
    )
    brave_configure = bool(os.getenv("BRAVE_SEARCH_API_KEY"))

    return [
        {
            "nom": "ParuVendu",
            "mode": "collecte publique ordinaire",
            "statut": "actif" if ACTIVER_PARUVENDU else "inactif",
        },
        {
            "nom": "Vivastreet",
            "mode": "collecte publique ordinaire",
            "statut": "actif" if ACTIVER_VIVASTREET else "inactif",
        },
        {
            "nom": "eBay",
            "mode": "API Browse officielle",
            "statut": "actif" if ACTIVER_EBAY else "identifiants à valider"
            if ebay_configure else "à configurer",
        },
        {
            "nom": "Leboncoin",
            "mode": "Compagnon privé + partenariat futur",
            "statut": "assisté",
        },
        {
            "nom": "Facebook Marketplace",
            "mode": "Compagnon dans le navigateur de l'utilisateur",
            "statut": "assisté",
        },
        {
            "nom": "Vinted",
            "mode": "Compagnon dans le navigateur de l'utilisateur",
            "statut": "assisté",
        },
        {
            "nom": "Index Web Brave",
            "mode": "découverte de liens, sans lecture des pages",
            "statut": "clé disponible" if brave_configure else "optionnel",
        },
    ]

