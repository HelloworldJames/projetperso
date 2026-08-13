# Diagnostic Playwright des URL Hunter

Ouvre une URL dans Chromium visible, attend explicitement apres
`DOMContentLoaded`, puis enregistre uniquement des signaux techniques : statut
HTTP, redirection, titre, compteurs DOM et echecs de ressources. L'outil ne
conserve ni HTML, ni cookie, ni donnee vendeur.

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\url_playwright_diagnostic\run.ps1 `
  -Url "URL_A_DIAGNOSTIQUER" -WaitSeconds 12
```

Lancer une commande separee pour chaque URL evite qu'une erreur ou une page de
controle sur une plateforme influence le diagnostic de la suivante.

Les rapports JSON sont places dans `results/`, dossier ignore par Git.
