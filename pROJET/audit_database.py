import sqlite3

DB_PATH = "database/pc_hunter.db"

connexion = sqlite3.connect(DB_PATH)
curseur = connexion.cursor()

print()
print("===== OBSERVATIONS MARCHE =====")
print()

resultats = curseur.execute(
    """
    SELECT
        plateforme,
        titre,
        prix,
        localisation,
        date_observation
    FROM observations_marche
    ORDER BY date_observation DESC
    LIMIT 20
    """
).fetchall()

for ligne in resultats:

    plateforme, titre, prix, localisation, date = ligne

    print(f"[{plateforme}] {titre}")
    print(f"Prix : {prix} €")
    print(f"Lieu : {localisation}")
    print(f"Date : {date}")
    print("-" * 50)

connexion.close()