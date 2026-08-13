# PC Hunter V1.5 — stratégie de sources autorisées

## Principe

Un HTTP 403 n'est pas une donnée à contourner : c'est une indication que la voie serveur utilisée n'est pas autorisée ou pas disponible. Hunter doit changer de canal d'acquisition au lieu de masquer son automatisation.

## Canaux retenus

### 1. API officielle

À privilégier dès qu'elle existe. Le provider eBay utilise l'API Browse officielle. Pour Leboncoin, la cible est un partenariat ou une intégration autorisée produisant directement `collector.models.Annonce`.

### 2. Compagnon privé dans le navigateur

Pour une annonce que l'utilisateur consulte déjà, le Compagnon lit le DOM visible dans sa session et transmet seulement les données nécessaires. Il ne réutilise pas les cookies côté serveur, ne contourne pas les contrôles et s'arrête si une vérification manuelle apparaît.

Ce canal permet :

- l'analyse immédiate d'un lien ;
- la remise à jour du prix lors d'une nouvelle consultation ;
- une veille locale sur une page catalogue lorsque la plateforme et la session l'autorisent ;
- l'analyse de captures Marketplace, Vinted ou Leboncoin visibles par l'utilisateur.

### 3. Index de recherche

Un moteur de recherche peut découvrir des URLs et des extraits sans donner à Hunter le droit de lire ensuite une page bloquée. Brave Search API est la piste recommandée à évaluer. Le stockage de résultats doit être activé uniquement si le contrat choisi donne les droits nécessaires.

Google Custom Search JSON API n'est pas retenu pour une nouvelle intégration : il n'accepte plus de nouveaux clients et son arrêt est annoncé pour le 1er janvier 2027.

### 4. Saisie assistée

Quand une page ne fournit pas assez d'informations structurées, l'utilisateur peut encore compléter un champ visible. Ce mode reste une solution de secours, pas le parcours principal.

### 5. Partenariats et flux marchands

Pour devenir réellement le « Google des affaires » à grande échelle, Hunter devra négocier des flux officiels ou des accords d'affiliation avec les plateformes majeures. La disponibilité d'une application Leboncoin officielle dans ChatGPT confirme qu'un accès catalogue autorisé est techniquement possible via partenariat.

## Canaux écartés

- `playwright-stealth` ou faux signaux navigateur destinés à tromper la détection ;
- rotation de VPN, d'IP ou de proxies pour échapper à une restriction ;
- résolution ou délégation automatique de CAPTCHA ;
- réutilisation des cookies de comptes utilisateurs sur un serveur Hunter ;
- Actors Apify communautaires présentés comme une autorisation générale ;
- extraction de données vendeur ou de coordonnées.

Apify fournit une infrastructure et des Actors communautaires, mais ses conditions laissent à l'utilisateur la responsabilité des droits et de la conformité. L'existence commerciale d'un scraper n'est donc pas une permission donnée à PC Hunter.

## Architecture cible

```text
API officielle ───────────────┐
Compagnon navigateur ─────────┤
Index de recherche autorisé ──┼─> Normalisation Annonce
Ajout admin ──────────────────┤        │
Partenariats ─────────────────┘        v
                                Analyse Hunter V1.5
                                        │
                     Top 20 / Top 3 / veille / baisses / disparues
```

Chaque source doit annoncer son mode, son statut, ses limites, et ne produire que les champs minimaux utiles : plateforme, ID public, titre, prix, description technique, localisation, URL et date de publication.

Cette normalisation sera portée par le sous-système indépendant décrit dans
`docs/COLLECTOR_ENGINE_V15.md`. Le Collector Engine sera responsable des tâches,
des files d'URL, des exécutions, des reprises et de la santé des sources ; Hunter
restera responsable de l'estimation et de la décision économique.
