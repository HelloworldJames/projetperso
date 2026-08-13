from database.watchlist import (
    annonces_watchlist_pour_analyse,
)


def rechercher(limite=None):
    """Source locale : aucune requête vers la plateforme d'origine."""
    annonces = annonces_watchlist_pour_analyse(
        limite=limite,
    )

    print(
        "[Watchlist]",
        len(annonces),
        "annonce(s) complète(s) envoyée(s) à l'analyse",
    )

    return annonces


if __name__ == "__main__":
    for annonce in rechercher():
        print(annonce)
