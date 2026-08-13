from types import SimpleNamespace

from notifications.discord import (
    envoyer_nouveau_pc_discord,
)


annonce_test = SimpleNamespace(
    titre="TEST PC HUNTER - RTX 4060",
    prix=320,
    localisation="Rochefort",
    plateforme="TEST",
    distance_km=8.5,
    url="https://example.com/test-pc-hunter",
)


print()
print("===== TEST NOTIFICATION NOUVEAU PC =====")
print()

resultat = envoyer_nouveau_pc_discord(
    annonce=annonce_test,
    categorie="PC_GAMING",
    est_nouvelle=False,
)

print()
print("Résultat :", resultat)
print()