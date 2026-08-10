class Annonce:

    def __init__(
        self,
        titre,
        prix,
        description,
        localisation,
        plateforme="Test",
        url=None,
        identifiant=None,
        date_publication=None
    ):
        self.titre = titre
        self.prix = prix
        self.description = description
        self.localisation = localisation

        # Informations utiles pour les futures vraies annonces
        self.plateforme = plateforme
        self.url = url
        self.identifiant = identifiant
        self.date_publication = date_publication


    def afficher(self):

        print("================================")
        print("Titre :", self.titre)
        print("Prix :", self.prix)
        print("Description :", self.description)
        print("Localisation :", self.localisation)
        print("Plateforme :", self.plateforme)

        if self.url:
            print("URL :", self.url)

        if self.date_publication:
            print("Date :", self.date_publication)

        print("================================")


def rechercher_annonces():

    annonces = []


    # --------------------------------
    # ANNONCES DE TEST
    # --------------------------------

    annonce1 = Annonce(
        titre="PC Gamer Ryzen 5 5600 RTX 3060",
        prix=350,
        description="16 go RAM, SSD 512go tres bon etat",
        localisation="Rochefort",
        plateforme="Test",
        identifiant="TEST-001"
    )


    annonce2 = Annonce(
        titre="PC Gamer RTX 3060 Ryzen 5 5600",
        prix=150,
        description="SSD 500go ne demarre plus vendu en l'etat",
        localisation="Saintes",
        plateforme="Test",
        identifiant="TEST-002"
    )


    annonce3 = Annonce(
        titre="PC Gamer i5 10400 GTX 1660 Super",
        prix=350,
        description="16 go RAM, SSD 512go tres bon etat",
        localisation="La Rochelle",
        plateforme="Test",
        identifiant="TEST-003"
    )


    annonces.append(annonce1)
    annonces.append(annonce2)
    annonces.append(annonce3)


    return annonces