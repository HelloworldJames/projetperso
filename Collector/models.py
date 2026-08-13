class Annonce:

    def __init__(
        self,
        identifiant,
        titre,
        prix,
        description,
        localisation="Inconnue",
        plateforme="Inconnue",
        url=None,
        date_publication=None
    ):

        self.identifiant = str(identifiant)

        self.titre = titre.strip()

        prix = float(prix)

        if prix.is_integer():
            self.prix = int(prix)
        else:
            self.prix = prix

        self.description = description.strip()

        self.localisation = localisation

        self.plateforme = plateforme

        self.url = url

        self.date_publication = date_publication

        # Cette valeur sera remplie ensuite par geo.py
        self.distance_km = None


    def __repr__(self):

        return (
            f"Annonce("
            f"{self.plateforme} | "
            f"{self.identifiant} | "
            f"{self.titre} | "
            f"{self.prix} €"
            f")"
        )