# PC Hunter V1.5 — état de livraison

Date : 10 août 2026

Application publiée : https://hunter-ia-radar.lesaint215.chatgpt.site — version Sites 11.

## Résultat produit

Hunter sait maintenant transformer une capture de page visible dans le navigateur en verdict exploitable sans exiger que l'utilisateur saisisse manuellement le titre, le prix, la description et la localisation.

Le parcours Companion cible est :

1. l'utilisateur ouvre volontairement une fiche annonce dans son navigateur ;
2. si le Companion est activé, il reconnaît l'URL `/ad/...`, y compris après une navigation dynamique ;
3. il extrait uniquement les informations produit visibles, sans donnée vendeur ;
4. le récepteur local crée ou met à jour la watchlist puis appelle le moteur Hunter ;
5. Hunter calcule l'estimation, la marge prudente, le prix d'achat maximum et un verdict ;
6. le résultat apparaît dans un panneau directement sur la fiche consultée ;
7. la capture nettoyée et le verdict rejoignent une boîte locale dédupliquée,
   synchronisée dans la webapp au retour de l'administrateur.

Hunter Radar reste séparé : il collecte les sources automatiquement accessibles.
Le Companion n'effectue aucune veille de catalogue et n'ouvre aucune annonce en
arrière-plan.

## Nouveau moteur d'analyse immédiate

Le moteur `analyzer/instant.py` orchestre désormais les briques existantes : classification, composants, cohérence, valeur, comparables marché, réparation, rentabilité, opportunité et classement.

Il produit notamment :

- `decision` : `PEPITE`, `BONNE_AFFAIRE`, `INTERESSANTE`, `A_NEGOCIER`, `A_ECARTER`, `INFORMATIONS_INSUFFISANTES` ou `HORS_CIBLE` ;
- `score_affaire` sur 100 ;
- `valeur_basse`, `valeur_probable` et `valeur_haute` ;
- `prix_achat_max` ;
- `marge_nette_prudente` ;
- `roi_prudent` ;
- raisons et action recommandée.

La marge prudente part de la valeur basse et retire 8 % de sécurité, 20 euros de frais fixes et le coût maximal des réparations détectées. Les prix de comparables sont considérés comme des prix affichés et non comme des ventes confirmées. La calibration marché exige au moins trois comparables stricts et reste plafonnée à plus ou moins 20 % de l'estimation interne.

Une configuration trop vague ne reçoit pas une valeur inventée : Hunter retourne `INFORMATIONS_INSUFFISANTES`.

## Capture et minimisation des données

Le Compagnon Hunter 1.0 :

- est désactivé par défaut et s'active explicitement depuis sa fenêtre ;
- reconnaît les fiches Leboncoin, Facebook Marketplace et Vinted ouvertes par l'utilisateur ;
- propose une lecture générique manuelle d'une autre fiche publique HTTPS,
  uniquement après un clic de l'utilisateur et sans permission `<all_urls>` ;
- gère les changements d'URL sans rechargement complet ;
- ignore les onglets masqués et les pages qui ne sont pas des fiches annonce ;
- privilégie le JSON-LD produit puis les champs visibles strictement ciblés ;
- ajoute un contexte technique de secours quand la description structurée manque ;
- supprime les formulaires, boutons, zones de navigation et sélecteurs vendeur du contexte ;
- masque les emails et numéros de téléphone ;
- ne lit ni cookies, ni session, ni compte, ni messages privés, ni historique général ;
- n'enregistre jamais le contexte brut et ne conserve que des erreurs techniques nettoyées ;
- affiche clairement une analyse impossible ou des informations insuffisantes.
- expose uniquement ses résultats nettoyés à la webapp via l'extension et le
  récepteur local ; aucun cookie ou contenu de compte n'est transféré.

Le récepteur conserve sa compatibilité avec le pipeline existant. Le Companion
n'invente pas de valeur si les caractéristiques nécessaires à l'estimation ne
sont pas disponibles. Cela ne relâche pas le filtre géographique du radar
principal, qui reste fermé en cas de localisation inconnue.

## Mémoire d'analyse

La table SQLite `analyses_hunter` conserve les verdicts. Une signature calculée à partir des données utiles évite de créer un doublon quand la même annonce est analysée à nouveau sans changement.

Une variation réelle de prix provoque une nouvelle signature, une nouvelle analyse et permet à la baisse de prix de changer le verdict.

Ces captures constituent le premier corpus privé de calibration de Hunter. Le
système accumule des observations et des verdicts auditables ; il ne prétend pas
encore réentraîner automatiquement un modèle d'IA à partir de ces données.

## Discord

Les nouvelles commandes sont :

- `/analyse <URL ou identifiant>` : dernier verdict connu ;
- `/pepites` : Top 3 des décisions `PEPITE` et `BONNE_AFFAIRE` ;
- `/veille` : état des liens suivis ;
- `/disparues` : annonces plus vues, sans prétendre qu'elles sont vendues ;
- `/sources` : état et mode d'accès de chaque source.

Le Top principal est configuré pour conserver jusqu'à 20 résultats.

## Application web

La V1.5 retire les chiffres et opportunités de démonstration. Les compteurs, le radar, le meilleur signal, le Top 20, la confiance, les comparables et les baisses de prix sont dérivés des captures réellement présentes sur l'appareil.

Le résultat d'analyse affiche le verdict, le score, l'estimation probable, la marge prudente et le prix d'achat maximum. Le prototype local de référence est le Compagnon 1.0. La webapp importe la boîte locale au chargement et à chaque retour au premier plan, puis signale uniquement les identifiants de capture qu'elle n'a pas encore vus.

## Sources

- ParuVendu : collecte actuelle active ;
- Vivastreet : collecte actuelle active ;
- eBay : provider fondé sur l'API Browse officielle, désactivé tant que les identifiants OAuth ne sont pas valides ;
- Leboncoin : premier extracteur du Companion, limité à la fiche actuellement consultée, et partenariat officiel visé ;
- Facebook Marketplace et Vinted : extracteurs Companion dédiés actifs sur la fiche visible ;
- Brave Search : piste optionnelle de découverte de liens par index, sans lecture forcée des pages et uniquement avec une clé et les droits de stockage adaptés.

Les Actors communautaires Apify, le stealth, les VPN/proxies rotatifs et les contournements de CAPTCHA ne sont pas intégrés.

## Décision d'architecture — Collector Engine

La prochaine fondation de la V1.5 est un moteur de collecte indépendant de
Hunter. Il reprend les principes utiles d'Apify — exécutions isolées, file de
requêtes, datasets, état clé-valeur, planification et événements — tout en
conservant les règles d'accès et de minimisation de données de PC Hunter.

La conception détaillée et les lots de livraison sont définis dans
`docs/COLLECTOR_ENGINE_V15.md`.

## IA optionnelle

`analyzer/ai_advisor.py` peut ajouter une explication en langage naturel via OpenAI Responses API ou un modèle Ollama local. L'IA reçoit seulement la fiche nettoyée et le calcul déterministe. Elle n'a pas le droit de modifier l'estimation, la marge ou le verdict économique.

Sans clé OpenAI ou modèle Ollama configuré, Hunter fonctionne entièrement avec le moteur déterministe.

## État des validations

- Companion 1.0, import et moteur V1.5 : 22 tests ciblés réussis ;
- Discord : 7 tests réussis ;
- application web : build réussi, lint réussi et 9 tests réussis ;
- suite Python complète : 70 tests réussis ;
- extraction contrôlée sur une fiche Leboncoin réelle et overlay vérifié dans ses états succès et informations insuffisantes ;
- provider eBay : tests simulés réussis, mais les identifiants disponibles renvoient actuellement HTTP 401 en sandbox comme en production ;
- une validation complète de toute la suite est requise avant étiquetage final.

## Actions encore nécessaires pour l'exploitation

1. recharger l'extension 1.0 dans Chrome/Edge ;
2. lancer le récepteur local Hunter avant une analyse complète ;
3. synchroniser les nouvelles commandes Discord en redémarrant le bot ;
4. remplacer ou régénérer des identifiants eBay valides avant d'activer le provider ;
5. choisir un fournisseur IA seulement si une explication conversationnelle est souhaitée ;
6. poursuivre la demande de partenariat Leboncoin pour une couverture serveur officielle et multi-utilisateur.
