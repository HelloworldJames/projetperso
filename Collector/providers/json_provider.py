import json
import hashlib
from pathlib import Path
from json import JSONDecodeError
from collector.models import Annonce


class JsonProvider:

    nom = "JSON"

    def __init__(self, chemin=None):

        if chemin is None:

            racine_projet = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

            chemin = (
                racine_projet
                / "data"
                / "annonces.json"
            )

        self.chemin = Path(chemin)


    def generer_identifiant(
        self,
        donnees
    ):

        if donnees.get("identifiant"):
            return str(
                donnees["identifiant"]
            )

        if donnees.get("url"):
            return donnees["url"]

        texte = (
            str(donnees.get("plateforme", "JSON"))
            + "|"
            + str(donnees.get("titre", ""))
            + "|"
            + str(donnees.get("localisation", ""))
        )

        empreinte = hashlib.sha1(
            texte.encode("utf-8")
        ).hexdigest()[:16]

        return f"JSON-{empreinte}"


    def rechercher(self):

        if not self.chemin.exists():

            print(
                "⚠️ Fichier JSON introuvable :",
                self.chemin
            )

            return []


        try:

            with open(
                self.chemin,
                "r",
                encoding="utf-8"
            ) as fichier:

                donnees = json.load(fichier)


        except JSONDecodeError as erreur:

            print(
                "⚠️ Erreur de décodage JSON :",
                erreur
            )
            print("detail :", erreur)

            return []


        if not isinstance(donnees, list):

            raise ValueError(
                "annonces.json doit contenir une liste d'annonces."
            )


        annonces = []


        for numero, item in enumerate(
            donnees,
            start=1
        ):

            try:

                annonce = Annonce(

                    identifiant=self.generer_identifiant(
                        item
                    ),

                    titre=item["titre"],

                    prix=item["prix"],

                    description=item.get(
                        "description",
                        ""
                    ),

                    localisation=item.get(
                        "localisation",
                        "Inconnue"
                    ),

                    plateforme=item.get(
                        "plateforme",
                        "JSON"
                    ),

                    url=item.get(
                        "url"
                    ),

                    date_publication=item.get(
                        "date_publication"
                    )
                )

                annonces.append(
                    annonce
                )

            except (
                KeyError,
                ValueError,
                TypeError
            ) as erreur:

                print(
                    f"⚠️ Annonce JSON #{numero} ignorée :",
                    erreur
                )


        print(
            f"📥 {len(annonces)} annonces chargées depuis JSON"
        )

        return annonces