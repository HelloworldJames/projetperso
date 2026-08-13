PRIX_COMPOSANTS = {

    # ========================================================
    # GPU - RÉFÉRENCES ACTUELLEMENT VALORISÉES
    # ========================================================

    "rtx 3070": {
        "prix": 260,
        "categorie": "gpu",
        "score": 35,
        "label": "RTX 3070",
        "valorisation_fiable": True,
        "aliases": [
            "rtx 3070",
            "rtx3070",
            "geforce rtx 3070",
        ]
    },

    "rtx 3060": {
        "prix": 230,
        "categorie": "gpu",
        "score": 30,
        "label": "RTX 3060",
        "valorisation_fiable": True,
        "aliases": [
            "rtx 3060",
            "rtx3060",
            "geforce rtx 3060",
        ]
    },

    "rx 6700": {
        "prix": 230,
        "categorie": "gpu",
        "score": 30,
        "label": "RX 6700",
        "valorisation_fiable": True,
        "aliases": [
            "rx 6700",
            "rx6700",
        ]
    },

    "rx 6600": {
        "prix": 180,
        "categorie": "gpu",
        "score": 30,
        "label": "RX 6600",
        "valorisation_fiable": True,
        "aliases": [
            "rx 6600",
            "rx6600",
        ]
    },

    "rtx 2060": {
        "prix": 160,
        "categorie": "gpu",
        "score": 25,
        "label": "RTX 2060",
        "valorisation_fiable": True,
        "aliases": [
            "rtx 2060",
            "rtx2060",
            "geforce rtx 2060",
        ]
    },

    "gtx 1660 super": {
        "prix": 130,
        "categorie": "gpu",
        "score": 25,
        "label": "GTX 1660 Super",
        "valorisation_fiable": True,
        "aliases": [
            "gtx 1660 super",
            "gtx1660 super",
            "gtx1660super",
            "geforce gtx 1660 super",
        ]
    },

"rtx 4060": {
    "prix": 230,
    "categorie": "gpu",
    "score": 30,
    "label": "RTX 4060",
    "valorisation_fiable": True,
    "aliases": [
        "rtx 4060",
        "rtx4060",
        "geforce rtx 4060",
        "nvidia geforce rtx 4060",
    ]
},
    # ========================================================
    # GPU DÉTECTABLES MAIS PAS ENCORE VALORISÉS
    #
    # IMPORTANT :
    # PC Hunter sait qu'ils existent mais ne leur attribue
    # volontairement aucun prix pour l'instant.
    # ========================================================

    "rtx 3050": {
        "prix": None,
        "categorie": "gpu",
        "score": 0,
        "label": "RTX 3050",
        "valorisation_fiable": False,
        "aliases": [
            "rtx 3050",
            "rtx3050",
            "geforce rtx 3050",
        ]
    },

    "apple m4 gpu": {
        "prix": None,
        "categorie": "gpu",
        "score": 0,
        "label": "Apple M4 GPU",
        "valorisation_fiable": False,
        "aliases": [
            "gpu: apple m4",
        ]
    },


    # ========================================================
    # CPU - MODÈLES PRÉCIS
    # ========================================================

    "ryzen 5 5600": {
        "prix": 100,
        "categorie": "cpu",
        "score": 25,
        "label": "Ryzen 5 5600",
        "valorisation_fiable": True,
        "aliases": [
            "ryzen 5 5600",
            "ryzen5 5600",
            "r5 5600",
        ]
    },

    "i5 11400": {
        "prix": 100,
        "categorie": "cpu",
        "score": 20,
        "label": "Intel i5 11400",
        "valorisation_fiable": True,
        "aliases": [
            "i5 11400",
            "i5-11400",
            "i511400",
            "intel core i5 11400",
            "intel core i5-11400",
        ]
    },

    "i5 10400": {
        "prix": 80,
        "categorie": "cpu",
        "score": 20,
        "label": "Intel i5 10400",
        "valorisation_fiable": True,
        "aliases": [
            "i5 10400",
            "i5-10400",
            "i510400",
            "intel core i5 10400",
            "intel core i5-10400",
        ]
    },

    "ryzen 5 3600": {
        "prix": 60,
        "categorie": "cpu",
        "score": 20,
        "label": "Ryzen 5 3600",
        "valorisation_fiable": True,
        "aliases": [
            "ryzen 5 3600",
            "ryzen5 3600",
            "r5 3600",
        ]
    },
"i5 13400f": {
    "prix": 110,
    "categorie": "cpu",
    "score": 25,
    "label": "Intel Core i5-13400F",
    "valorisation_fiable": True,
    "aliases": [
        "i5 13400f",
        "i5-13400f",
        "i513400f",
        "intel i5 13400f",
        "intel i5-13400f",
        "intel core i5 13400f",
        "intel core i5-13400f",
    ]
},

    # ========================================================
    # CPU - FAMILLES / MODÈLES INCOMPLETS
    # ========================================================

    "ryzen 7": {
        "prix": 140,
        "categorie": "cpu",
        "score": 20,
        "label": "Ryzen 7 - modèle inconnu",
        "valorisation_fiable": False,
        "aliases": [
            "cpu: amd ryzen 7",
            "ryzen 7",
            "ryzen7",
        ]
    },

    "ryzen 5 generique": {
        "prix": None,
        "categorie": "cpu",
        "score": 0,
        "label": "Ryzen 5 - modèle inconnu",
        "valorisation_fiable": False,
        "aliases": [
            "cpu: amd ryzen 5",
            "cpu: ryzen 5",
        ]
    },

    "intel core i5 generique": {
        "prix": None,
        "categorie": "cpu",
        "score": 0,
        "label": "Intel Core i5 - génération inconnue",
        "valorisation_fiable": False,
        "aliases": [
            "cpu: intel core i5",
        ]
    },

    "apple m4 cpu": {
        "prix": None,
        "categorie": "cpu",
        "score": 0,
        "label": "Apple M4",
        "valorisation_fiable": False,
        "aliases": [
            "cpu: apple m4",
        ]
    },


    # ========================================================
    # RAM
    # ========================================================

    "32 go": {
        "prix": 70,
        "categorie": "ram",
        "score": 15,
        "label": "32 Go RAM",
        "valorisation_fiable": True,
        "aliases": [
            "32 go",
            "32go",
            "32 gb",
            "32gb",
        ]
    },

    "16 go": {
        "prix": 40,
        "categorie": "ram",
        "score": 10,
        "label": "16 Go RAM",
        "valorisation_fiable": True,
        "aliases": [
            "16 go",
            "16go",
            "16 gb",
            "16gb",
        ]
    },


    # ========================================================
    # STOCKAGE
    # ========================================================

    "ssd nvme": {
        "prix": 50,
        "categorie": "stockage",
        "score": 15,
        "label": "SSD NVMe",
        "valorisation_fiable": True,
        "aliases": [
            "ssd nvme",
            "nvme",
        ]
    },

    "ssd": {
        "prix": 40,
        "categorie": "stockage",
        "score": 10,
        "label": "SSD",
        "valorisation_fiable": True,
        "aliases": [
            "ssd",
        ]
    },
}