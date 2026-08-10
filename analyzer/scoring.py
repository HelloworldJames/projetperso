def analyser_annonce(annonce):
    """
    Analyse une annonce et retourne un score basé sur les critères définis.
    """

    score = 0
    raisons = []

    texte = (annonce.titre + " " + annonce.description).lower()

    # Carte graphique

    if "gtx 1660 super" in texte:
        score += 25
        raisons.append("GTX 1660 Super détectée")

    elif "gtx 1660" in texte:
        score += 20
        raisons.append("GTX 1660 détectée")

    if "rx 5700" in texte:
        score += 25
        raisons.append("RX 5700 détectée")

    if "rx 6700" in texte:
        score += 30
        raisons.append("RX 6700 détectée")

    if "rtx 3060" in texte or "rtx3060" in texte:
        score += 30
        raisons.append("RTX 3060 détectée")

    if "rx 6600" in texte:
        score += 30
        raisons.append("RX 6600 détectée")

    if "rtx 2060" in texte:
        score += 25
        raisons.append("RTX 2060 détectée")


    # Processeur

    if "ryzen 5 5600" in texte:
        score += 25
        raisons.append("Ryzen 5 5600 détecté")

    elif "ryzen 5 3600" in texte:
        score += 20
        raisons.append("Ryzen 5 3600 détecté")

    elif "ryzen 5" in texte:
        score += 15
        raisons.append("Ryzen 5 détecté")

    if "ryzen 7" in texte:
        score += 20
        raisons.append("Ryzen 7 détecté")

    if "i5 10400" in texte:
        score += 20
        raisons.append("Intel i5 10400 détecté")
    elif "i5" in texte:
        score += 15
        raisons.append("Intel i5 détecté")    

    if "i5 11400" in texte:
        score += 20
        raisons.append("Intel i5 11400 détecté")


    # RAM

    if "16 go" in texte or "16gb" in texte or "16 gb" in texte:
        score += 10
        raisons.append("16 Go RAM détectés")

    if "32 go" in texte or "32gb" in texte or "32 gb" in texte:
        score += 15
        raisons.append("32 Go RAM détectés")

    if "64 go" in texte or "64gb" in texte or "64 gb" in texte:
        score += 20
        raisons.append("64 Go RAM détectés")


    # Stockage

    if "ssd nvme" in texte:
        score += 15
        raisons.append("SSD NVMe détecté")

    elif "ssd" in texte:
        score += 10
        raisons.append("SSD détecté")

    if "hdd" in texte:
        score += 5
        raisons.append("HDD détecté")


    # Problèmes

    mots_risque = [
        "problème",
        "defaut",
        "panne",
        "ne fonctionne pas",
        "ne marche pas",
        "ne démarre pas",
        "ne s'allume pas",
        "hs"
    ]

    for mot in mots_risque:
        if mot in texte:
            score -= 20
            raisons.append("Problème détecté : " + mot)


    return score, raisons