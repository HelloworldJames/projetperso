from collector.providers.easycash import rechercher
from database.market import (
    enregistrer_observations,
    statistiques_market,
)


def main():

    print()
    print("========================================")
    print("🧠 PC HUNTER - COLLECTE MARCHÉ EASY CASH")
    print("========================================")
    print()

    # Pas de limite :
    # on récupère tout le catalogue PC Gaming trouvé.
    annonces = rechercher()

    print()
    print(
        "📦 Produits récupérés :",
        len(annonces)
    )

    nouvelles = enregistrer_observations(
        annonces
    )

    stats = statistiques_market()

    print()
    print("========================================")
    print("📊 MÉMOIRE MARCHÉ")
    print("========================================")

    print(
        "🧠 Observations totales :",
        stats["total"]
    )

    print(
        "➕ Nouvelles observations :",
        nouvelles
    )

    print()

    for source in stats["sources"]:

        print(
            "🌐",
            source["plateforme"],
            ":",
            source["nombre"]
        )

    print()
    print("✅ Collecte terminée.")


if __name__ == "__main__":
    main()