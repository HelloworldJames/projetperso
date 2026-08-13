# Observateur Vinted Playwright

Prototype isole pour verifier qu'une categorie publique Vinted peut etre lue
dans un Chromium visible. Il extrait uniquement l'identifiant, le titre, le
prix et l'URL des annonces. Aucune donnee vendeur n'est conservee.

Le navigateur utilise un profil local persistant. Le script ne modifie pas le
user-agent, n'utilise pas de mode stealth et ne tente pas de franchir une page
de verification. En cas de HTTP 401/403/429 ou de verification detectee, il le
signale et ferme le navigateur.

## Passage unique

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\vinted_playwright_observer\run.ps1 `
  -Url "https://www.vinted.fr/catalog/3581-"
```

Le premier passage constitue la base de comparaison. Les passages suivants
indiquent uniquement les identifiants absents de la sauvegarde precedente.
L'outil n'est pas encore branche au radar, a la base principale ou a Discord.

## Tests

```powershell
.\tools\leboncoin_playwright_observer\.venv\Scripts\python.exe `
  -m unittest discover -s .\tools\vinted_playwright_observer -p "test_*.py"
```
