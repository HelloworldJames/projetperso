# Hunter Companion 1.0 — analyse multi-plateforme

Hunter Companion et Hunter Radar sont deux systèmes séparés :

- **Radar** collecte automatiquement les sources accessibles et configurées ;
- **Companion** analyse uniquement la fiche annonce que l'utilisateur consulte
  volontairement dans son navigateur.

Le Companion n'effectue aucune veille de catalogue, n'ouvre pas de pages en
arrière-plan et ne transforme pas ses utilisateurs en nœuds de collecte.

## Fonctionnement

1. L'utilisateur active **Analyse automatique** dans le popup.
2. Il consulte normalement une fiche Leboncoin, Facebook Marketplace ou Vinted.
3. Le script reconnaît la fiche, y compris après une navigation dynamique sans
   rechargement complet.
4. L'extracteur isolé de la plateforme lit uniquement les champs produit
   visibles et les métadonnées structurées utiles.
5. Le service worker applique une seconde liste blanche puis transmet la fiche
   au récepteur local `127.0.0.1:8765`.
6. Le pipeline Hunter existant calcule le verdict.
7. Un panneau isolé visuellement s'affiche directement dans la page.
8. La capture et son analyse rejoignent une boîte locale que la webapp Hunter
   peut synchroniser au retour de l'administrateur.

Si le titre ou le prix manque, si le moteur local est arrêté ou si Hunter ne
dispose pas d'assez d'informations, l'overlay l'indique explicitement. Aucune
estimation n'est inventée.

## Installation en trois étapes

### 1. Lancer le moteur local

Double-cliquer sur `Lancer-Compagnon-Hunter.cmd` à la racine du projet. La
fenêtre doit annoncer :

```text
Hunter Link Scanner actif sur http://127.0.0.1:8765
```

### 2. Recharger l'extension

1. ouvrir `edge://extensions` ou `chrome://extensions` ;
2. activer le mode développeur ;
3. charger ou recharger le dossier
   `tools\hunter_link_scanner\extension` ;
4. épingler Hunter Companion.

### 3. Analyser une annonce

1. ouvrir une fiche Leboncoin `/ad/...` ;
2. activer **Analyse automatique** une seule fois dans le popup, ou cliquer sur
   **Analyser cette annonce maintenant** ;
3. lire le résultat dans le panneau Hunter situé en haut à droite de la page.

## Confidentialité

Permissions actives :

- `activeTab` : déclenchement manuel sur l'onglet courant ;
- `storage` : uniquement le réglage activé/désactivé et un petit journal
  d'erreurs techniques nettoyé ;
- accès réseau limité au récepteur local `127.0.0.1:8765`.

Le content script Leboncoin est présent pour reconnaître les navigations SPA,
mais reste inactif hors d'une URL `/ad/...` ou lorsque le Companion est
désactivé.

Ne sont jamais collectés : cookies, tokens, sessions, identifiants de connexion,
historique général, messages privés, données du compte ou champs vendeur. Les
coordonnées éventuellement présentes dans la description sont masquées. Les
images ne sont pas transmises dans le prototype 1.0. La boîte synchronisée ne
contient que les champs produit déjà autorisés et le résultat Hunter.

## Plateformes prises en charge

- Leboncoin `/ad/...` : automatique lorsque Companion est activé ;
- Facebook Marketplace `/marketplace/item/...` : automatique ;
- Vinted `/items/...` : automatique ;
- autre fiche publique HTTPS : analyse générique manuelle après un clic sur le
  bouton du popup. Cette méthode privilégie JSON-LD, Open Graph et les champs
  produit ciblés ; elle indique les données manquantes au lieu d'inventer.

La permission `scripting` sert uniquement à injecter l'extracteur générique
dans l'onglet courant après l'action explicite de l'utilisateur. Le manifeste
ne demande pas `<all_urls>`.

## Architecture extensible

```text
providers/leboncoin.js ─┐
providers/ebay.js       ├─> companion-content.js -> background.js
providers/...           ┘                         -> backend Hunter
                                                    -> overlay.js
```

Ajouter une plateforme nécessitera un provider isolé implémentant
`correspond(url)` et `extraire()`. Le contrôleur, le backend et l'overlay ne
dépendent pas du DOM Leboncoin.
