# Prompt de reprise — PC Hunter V1.5

Tu reprends le projet PC Hunter AI, un radar Python et une application web de détection de bonnes affaires PC d'occasion.

Lis d'abord intégralement `AGENTS.md`, `CODEX_HANDOFF.md`, `docs/VERSION_1_5.md`, `docs/STRATEGIE_SOURCES_V15.md` et le diff Git. Ne remplace pas l'architecture existante et ne touche pas aux fichiers modifiés récemment avant d'avoir inspecté leur diff.

État attendu :

- ParuVendu et Vivastreet actifs ;
- filtre géographique strict 50 km autour de Tonnay-Charente ;
- SQLite pour annonces, présence, prix, watchlist, observations marché et analyses Hunter ;
- moteur immédiat `analyzer/instant.py` retournant décision, score, estimation, prix d'achat maximum, marge prudente et ROI ;
- captures nettoyées via `analyzer/capture_enrichment.py` ;
- IA explicative optionnelle via `analyzer/ai_advisor.py`, jamais autorisée à changer le calcul économique ;
- Compagnon navigateur 0.7 transmettant les pages visibles sans donnée vendeur ;
- provider eBay fondé sur l'API Browse officielle mais désactivé jusqu'à validation des identifiants ;
- Discord : `/analyse`, `/pepites`, `/veille`, `/disparues`, `/sources` en plus des commandes existantes ;
- application web Hunter IA affichant uniquement les captures et analyses réelles de l'appareil, avec Top 20 et suivi des baisses.

Règles absolues :

1. ne collecte ni identité, ni téléphone, ni email vendeur ;
2. ne contourne jamais un 403, CAPTCHA, robots.txt ou une restriction par stealth, rotation IP/VPN ou proxy ;
3. utilise une API officielle, un partenariat, un index autorisé ou le Compagnon dans la session visible de l'utilisateur ;
4. n'invente jamais un prix si la configuration PC est insuffisante ;
5. traite les comparables comme des prix affichés, pas comme des ventes confirmées ;
6. conserve les signatures publiques ;
7. compile chaque fichier Python modifié et ajoute des tests ciblés ;
8. protège les modifications utilisateur déjà présentes.

Prochaine priorité : exécuter la suite complète, corriger uniquement les régressions liées à la V1.5, valider un scénario réel de bout en bout avec le récepteur local et le Compagnon, puis documenter les étapes d'activation eBay, Discord et IA. Ensuite, préparer un dossier de partenariat Leboncoin décrivant la minimisation des données, le rythme de collecte, les cas d'usage et le bénéfice utilisateur.

À chaque livraison, indique clairement : fichiers modifiés, tests, limites réelles, ce qui est actif et ce qui demande encore une clé ou un partenariat.
