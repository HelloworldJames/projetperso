# PC Hunter — historique synthétique depuis le démarrage

## Fondation du radar

PC Hunter a été construit comme un radar Python pour les ordinateurs d'occasion. Le pipeline central collecte, normalise, déduplique, filtre à 50 km de Tonnay-Charente, mémorise les annonces, analyse le matériel, estime la valeur, calcule la rentabilité et produit un classement.

ParuVendu et Vivastreet ont été intégrés comme premières sources actives. La pagination Vivastreet, le séparateur de milliers des prix et le filtre géographique fermé ont été corrigés et validés. La base SQLite conserve les annonces, leur présence, leur historique de prix et les observations marché sans doublons.

## Estimation et comparables

Le moteur a progressivement appris à distinguer desktop, PC gamer, laptop, laptop gamer, Mac, composant, accessoire et annonce inconnue. Des garde-fous ont été ajoutés pour éviter d'additionner des composants soudés dans les machines Apple, éviter de surévaluer les anciens Mac et refuser une estimation lorsque les références CPU/GPU sont trop vagues.

Les comparables marché V1 sont utilisés comme preuve secondaire. Ils restent des prix affichés, pas des ventes confirmées.

## TOP, Discord et radar

Le radar tourne toutes les cinq minutes. Il maintient la présence et la disparition, calcule le Top et peut notifier Discord. Les commandes historiques `/status`, `/top`, `/last` et `/stats` donnent la vue opérationnelle.

La limite du Top est désormais portée à 20. Les nouvelles commandes V1.5 ajoutent l'analyse à la demande, le Top 3 des pépites, la veille, les disparitions et l'état des sources.

## Leboncoin et ajout manuel

Les notifications iPhone relayées par Mobile connecté se sont révélées génériques et instables. L'email Leboncoin n'était pas assez fiable. Un diagnostic Windows isolé a été préparé, puis cette voie a été abandonnée comme source principale.

Une watchlist indépendante a été créée pour ajouter un lien manuellement, suivre son prix, enregistrer uniquement les changements réels et préparer une réanalyse après baisse. Aucune donnée vendeur n'est stockée.

Face aux HTTP 403, plusieurs pistes ont été étudiées. Les approches stealth, VPN/proxy rotatif et contournement de contrôles ont été écartées. La solution immédiate retenue est un Compagnon de navigateur qui lit une page ouverte dans la session normale de l'utilisateur. La solution durable pour Leboncoin reste une intégration partenaire autorisée.

## Application Hunter IA

Une application web a été créée autour d'un compagnon loup noir inspiré d'un Eurasier. Elle permet de coller une URL, détecter le Compagnon, ouvrir la page, recevoir les captures locales et maintenir une veille sur l'appareil.

Les premières versions comportaient des données de démonstration. La V1.5 les remplace par les analyses réellement reçues : Top 20, meilleur signal, confiance, comparables, baisse de prix et état de la watchlist.

## Version 1.5

La V1.5 ajoute un moteur d'analyse immédiate, une mémoire d'analyses sans doublons, un enrichissement technique nettoyé, un conseiller IA optionnel, un provider eBay officiel, un registre explicite des sources, cinq commandes Discord et le Compagnon 0.7.

Le moteur économique reste déterministe et prudent. L'IA, si elle est activée, explique le verdict mais ne peut pas changer les chiffres.

## Vision produit

Hunter vise à devenir un moteur personnel des bonnes affaires : l'utilisateur décrit son objectif, Hunter rassemble des signaux autorisés, filtre le bruit, estime le risque et propose les quelques annonces réellement utiles. La spécialisation PC doit être solide avant l'élargissement aux autres catégories.
