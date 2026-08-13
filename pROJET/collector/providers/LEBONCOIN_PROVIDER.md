# Interface Leboncoin autorisée

Ce dossier contient uniquement une couche de normalisation pour une future
API officielle, un partenariat ou une autre source explicitement autorisée.
Il ne contient aucun client HTTP Leboncoin et n'est pas chargé par le radar.

## Sources structurelles étudiées

- <https://github.com/etienne-hd/lbc>
- <https://github.com/thomasync/leboncoin-api-search>

Les deux projets publics exposent des champs comparables : `list_id`/`id`,
`subject`, `body`, `price_cents`/`price`, `url`, `first_publication_date` et un
objet `location`. PC Hunter ne reprend pas leur transport réseau. Les champs
vendeur (`owner`, `user`, téléphone et profil) sont volontairement ignorés.

## Contrat PC Hunter

Un futur provider autorisé devra produire des objets `LeboncoinResult`, puis
appeler :

```python
from collector.providers.leboncoin_normalizer import normaliser_leboncoin

annonce = normaliser_leboncoin(resultat_autorise)
```

Le résultat est un `collector.models.Annonce` contenant uniquement :

- identifiant ;
- titre ;
- prix ;
- description ;
- localisation ;
- URL ;
- date de publication ;
- plateforme fixée à `Leboncoin`.

## Limite volontaire

Les recommandations de proxy ou de réduction de fréquence évoquées par des
clients non officiels ne font pas partie de PC Hunter. Un `403` reste un arrêt
propre. L'activation dans `collector.scraper` devra attendre une autorisation
et des identifiants officiels.

## Collecteur de couverture V1.5

`collector.providers.leboncoin_collector` reste séparé du radar et accepte des
observations provenant d'un canal autorisé. Il ajoute :

- l'identifiant stable `LEBONCOIN-<id>` ;
- les champs de détection et les caractéristiques disponibles ;
- la fusion des doublons ;
- le comptage des nouvelles annonces ;
- un rapport de couverture entre les annonces visibles/notifiées et celles
  réellement détectées ;
- les états `SUCCEEDED`, `PARTIAL`, `BLOCKED`, `FAILED` et
  `EMPTY_CONFIRMED`.

Le mode de comparaison se lance sans `main.py`, SQLite, scoring ou Discord :

```powershell
python -m tools.leboncoin_collector `
  --observer-state .\tools\leboncoin_playwright_observer\state `
  --expected .\chemin\annonces_attendues.json `
  --report .\chemin\rapport_couverture.json
```

Le dernier état observé avant ce module contenait sept IDs/prix avec des titres
génériques `Voir l’annonce`. Le passage suivant a reçu HTTP 403. Dans cette
situation, le collecteur renvoie désormais `BLOCKED` et zéro résultat courant :
il ne présente jamais l'ancien snapshot comme une collecte réussie.
