# Hunter Collector Engine V1.5

Date de décision : 10 août 2026

## Vision

Le Collector Engine devient un sous-système indépendant de PC Hunter. Son rôle
est de découvrir, planifier, collecter, normaliser et historiser des annonces.
Hunter conserve son rôle d'analyse : composants, estimation, risque, marge,
classement et alertes.

L'objectif est de construire une infrastructure inspirée des bonnes briques
d'Apify, mais spécialisée pour Hunter et hébergeable localement au départ.

```text
Sources autorisées
        |
        v
Collector Jobs -> Request Queue -> Collector Workers
                                      |
                                      v
                              Dataset normalisé
                                      |
                                      v
                           collector.models.Annonce
                                      |
                                      v
                              Analyse PC Hunter
```

## Briques reprises comme principes d'architecture

La documentation officielle Apify distingue trois stockages : Dataset pour les
résultats structurés, Request Queue pour les URLs à traiter et Key-Value Store
pour l'état ou les objets non tabulaires. Elle associe aussi chaque exécution à
un statut, permet une planification et produit des événements de réussite ou
d'échec.

Hunter utilisera les équivalents suivants :

| Concept Apify | Équivalent Hunter |
| --- | --- |
| Actor | `CollectorTask` versionnée |
| Actor Run | `CollectorRun` isolé et journalisé |
| Request Queue | file SQLite d'URLs dédupliquées |
| Dataset | observations normalisées immuables |
| Key-Value Store | état et curseurs d'un connecteur |
| Schedule | planificateur de tâches |
| Webhook | événement interne, puis Discord/API après validation |

Références officielles :

- https://docs.apify.com/storage
- https://docs.apify.com/storage/request-queue
- https://docs.apify.com/actors/running/schedules
- https://docs.apify.com/integrations/webhooks/events

## Contrat d'un connecteur

Chaque connecteur annonce explicitement :

- son nom de source ;
- son mode d'accès (`api_officielle`, `page_autorisee`, `flux_partenaire`,
  `capture_utilisateur`, `index_autorise` ou `ajout_admin`) ;
- les URLs qu'il accepte ;
- son intervalle minimal ;
- son état de santé ;
- ses limites connues ;
- sa fonction de normalisation vers `collector.models.Annonce`.

Interface cible :

```python
class CollectorConnector:
    source_name: str
    access_mode: str

    def can_handle(self, url: str) -> bool: ...
    def collect(self, request, context): ...
    def normalize(self, raw_item): ...
```

Un connecteur ne doit jamais modifier directement le TOP, Discord ou les tables
d'analyse. Il produit des observations ; Hunter décide ensuite de leur intérêt.

## États d'une exécution

Une exécution doit terminer dans un état non ambigu :

- `SUCCEEDED` : collecte complète et exploitable ;
- `PARTIAL` : certains éléments ont été collectés, mais le résultat est
  incomplet ;
- `BLOCKED` : accès refusé, vérification manuelle ou canal indisponible ;
- `FAILED` : erreur technique interne ;
- `EMPTY_CONFIRMED` : source consultée avec succès et réellement vide.

`BLOCKED`, `FAILED` et `PARTIAL` ne doivent jamais provoquer une disparition
massive. Une disparition individuelle est confirmée uniquement après plusieurs
exécutions saines, selon la politique du connecteur.

## Modèle SQLite initial

Le premier moteur peut rester local et utiliser SQLite :

- `collector_tasks` : configuration et planification ;
- `collector_runs` : début, fin, statut, compteurs et erreur nettoyée ;
- `collector_requests` : URL, clé unique, priorité, tentatives et prochaine
  exécution ;
- `collector_items` : données normalisées et empreinte anti-doublon ;
- `collector_state` : curseurs et état clé-valeur par connecteur ;
- `collector_source_health` : dernier succès, erreurs consécutives et délai de
  reprise ;
- `collector_events` : nouvelle annonce, prix modifié, disparition confirmée et
  intervention manuelle.

Les résultats sont idempotents : rejouer une tâche avec la même annonce et le
même prix ne crée ni doublon ni fausse alerte.

## Canaux autorisés

Le Collector Engine orchestre plusieurs canaux sans supposer qu'une URL donne
automatiquement un droit de lecture :

1. APIs officielles et flux partenaires ;
2. pages publiques dont la collecte est autorisée ;
3. capture d'une page ouverte par l'utilisateur avec le Compagnon ;
4. URLs et données minimales ajoutées par un administrateur ;
5. index de recherche dont le contrat autorise l'usage et le stockage.

Un HTTP 403, 429 ou une vérification anti-robot produit `BLOCKED` et un délai de
reprise. Il ne déclenche ni stealth, ni rotation d'IP, ni CAPTCHA automatique.

## Rôle de l'IA

L'IA intervient après l'acquisition pour :

- reconnaître le type de produit ;
- extraire les composants depuis un texte ou une capture autorisée ;
- évaluer la qualité et les informations manquantes ;
- expliquer le verdict Hunter ;
- proposer une priorité de revue humaine.

Elle ne remplace pas le connecteur et ne transforme pas un accès refusé en accès
autorisé. Les calculs financiers déterministes restent la source de vérité.

## Découpage de livraison

### Lot 1 — noyau local

- modèles `CollectorTask`, `CollectorRun`, `CollectorRequest` et
  `CollectorResult` ;
- stockage SQLite et migrations ;
- file dédupliquée ;
- statuts de source explicites ;
- adaptateurs autour de ParuVendu, Vivastreet et Watchlist sans casser leurs
  signatures publiques.

### Lot 2 — orchestration

- planification indépendante du radar ;
- reprise après erreur avec délai progressif ;
- concurrence limitée par source ;
- métriques et journal par exécution ;
- branchement sûr au suivi de présence.

### Lot 3 — administration

- API locale pour créer une tâche et ajouter une URL ;
- commandes Discord administrateur ;
- page application : sources, tâches, exécutions, erreurs et intervention
  manuelle ;
- import/export JSON des datasets.

### Lot 4 — déploiement

- worker séparé de l'application ;
- API authentifiée ;
- stockage serveur remplaçable ;
- webhooks d'événements ;
- montée en charge seulement pour les sources disposant d'un canal autorisé.

## Définition de terminé pour le noyau

Le Lot 1 sera considéré comme terminé lorsque :

- une tâche peut être créée et rejouée sans doublon ;
- une URL n'est traitée qu'une fois par version utile ;
- chaque exécution possède un statut et des compteurs fiables ;
- une panne d'une source ne touche pas la présence des autres ;
- une observation valide devient une `Annonce` sans donnée vendeur ;
- le pipeline Hunter actuel continue de fonctionner sans modification de ses
  signatures publiques ;
- les migrations, la file et les états d'échec disposent de tests ciblés.
