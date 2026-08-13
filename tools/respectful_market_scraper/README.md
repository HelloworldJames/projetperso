# Collecteur respectueux des regles publiques

Outil isole de PC Hunter. Il ne modifie ni `main.py`, ni le radar, ni Discord,
ni les providers existants.

Avant chaque page, il telecharge `robots.txt` avec l'identite explicite
`PC-Hunter-Bot/1.0`. Une interdiction, une exigence d'autorisation speciale ou
une erreur de lecture du fichier provoque un arret prudent. Aucune session
utilisateur n'est chargee et aucun en-tete de navigateur n'est falsifie.

Le delai avant la page est aleatoire entre 3 et 8 secondes, ou plus long si
`Crawl-delay` l'exige. Le script ne reessaie jamais apres HTTP 401, 403 ou 429.
Seuls l'identifiant public, le titre, le prix et l'URL sont sauvegardes.

## Verifier seulement robots.txt

```powershell
.\tools\leboncoin_playwright_observer\.venv\Scripts\python.exe `
  .\tools\respectful_market_scraper\main.py "URL" --robots-only
```

## Effectuer un passage

Le mode sans fenetre est utilise par defaut. Ajouter `--visible` pour afficher
Chromium.

```powershell
.\tools\leboncoin_playwright_observer\.venv\Scripts\python.exe `
  .\tools\respectful_market_scraper\main.py "URL" --visible
```

Ce prototype n'est pas branche automatiquement a Hunter. Une source ne doit
etre integree qu'apres validation de son autorisation et de sa stabilite.

## VPN manuel facultatif

Le module `vpn_manager.py` est strictement en lecture seule. Il ne connecte,
ne deconnecte et ne change jamais de serveur NordVPN. Sous Windows, il lit la
sortie locale non privilegiee de `ipconfig /all` et cherche un tunnel
NordVPN/NordLynx possedant une adresse IPv4.

Afficher l'etat detecte sans contacter une plateforme :

```powershell
.\tools\leboncoin_playwright_observer\.venv\Scripts\python.exe `
  .\tools\respectful_market_scraper\main.py "https://example.org" --vpn-status
```

Exiger une connexion NordVPN effectuee manuellement avant une session :

```powershell
.\tools\leboncoin_playwright_observer\.venv\Scripts\python.exe `
  .\tools\respectful_market_scraper\main.py "URL" --require-manual-vpn
```

Un VPN ne modifie jamais la decision de `robots.txt` et ne provoque aucune
nouvelle tentative apres un refus HTTP.
