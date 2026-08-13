# Observateur Leboncoin Playwright

Prototype isolé : il n'est relié ni au radar, ni à Discord, ni aux providers.

Il utilise Playwright standard avec Chromium visible. Aucun mode stealth, faux
user-agent, proxy ou résolution automatique de CAPTCHA n'est utilisé.

## Fonctionnement

- ouvre une URL Leboncoin dont les filtres sont déjà présents ;
- conserve la session dans le dossier local `profile/` sans exporter ni
  afficher les cookies ;
- attend les cartes présentes dans le DOM puis récupère identifiant, titre,
  prix et URL ;
- enregistre le dernier état dans `state/listings.json` ;
- écrit les nouveaux identifiants dans la console et `state/events.jsonl` ;
- attend aléatoirement entre 240 et 360 secondes ;
- signale une intervention manuelle sur HTTP 401/403/429, CAPTCHA ou page de
  vérification.

## Lancer un seul passage

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\leboncoin_playwright_observer\run.ps1 `
  -Url "URL_LEBONCOIN_AVEC_FILTRES" `
  -Once
```

## Vérification d'une heure

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\leboncoin_playwright_observer\run.ps1 `
  -Url "URL_LEBONCOIN_AVEC_FILTRES" `
  -DurationMinutes 60
```

Au premier passage, la liste sert de référence et ne déclenche pas de fausse
alerte. Les passages suivants n'affichent que les nouveaux identifiants.

## Mesurer la couverture du collecteur V1.5

Préparez un JSON contenant les annonces réellement visibles ou notifiées. Une
référence peut contenir l'ID/URL, ou au minimum le titre et le prix :

```json
{
  "attendues": [
    {
      "titre": "MacBook Neo",
      "prix": 495,
      "localisation": "Saint-Jean-d'Angély"
    }
  ]
}
```

Puis lancez, depuis la racine du projet :

```powershell
python -m tools.leboncoin_collector `
  --observer-state .\tools\leboncoin_playwright_observer\state `
  --expected .\tools\leboncoin_expected.example.json `
  --report .\tools\leboncoin_coverage.json
```

Le rapport affiche : annonces trouvées, nouvelles annonces, doublons, fiches
incomplètes, erreurs, durée et couverture. Un ancien `listings.json` n'est pas
réutilisé lorsque le statut courant est HTTP 403/429.

Codes de sortie de l'observateur : `0` pour une lecture exploitable, `1` pour
une lecture incomplète/erreur et `2` lorsqu'une intervention manuelle est
requise.

## État du transport au 10 août 2026

- un passage a exposé 13 IDs et prix ;
- les fallbacks de titre ont alors été rejetés car ils lisaient des noms de
  profils ; le snapshot concerné a été supprimé ;
- seuls les sélecteurs explicites de titre/prix d'annonce sont désormais admis ;
- le passage de validation suivant a reçu HTTP 403 avant chargement des cartes ;
- la qualité des titres corrigés reste donc à valider sur un prochain passage
  HTTP 200 avant toute intégration à Hunter.
