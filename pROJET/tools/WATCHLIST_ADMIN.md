# Watchlist manuelle PC Hunter

La watchlist permet à un administrateur d'enregistrer rapidement une URL
d'annonce absente des sources automatiques. Elle ne récupère pas la page
Leboncoin et ne contourne aucune protection : elle conserve uniquement les
informations saisies manuellement.

Aucune donnée vendeur n'est stockée.

## Ajout direct depuis Discord

Un administrateur du serveur peut utiliser la commande slash :

```text
/ajouter url:https://www.leboncoin.fr/ad/ordinateurs/1234567890
```

Une URL seule entre immediatement **en etude**. Pour permettre l'analyse
automatique au prochain passage du radar, les quatre informations utiles
peuvent etre ajoutees dans la meme commande :

```text
/ajouter url:URL titre:"PC Ryzen 5" prix:300 description:"Ryzen 5, 16 Go, SSD 512 Go" localisation:"Rochefort 17300"
```

La commande peut etre relancee avec la meme URL pour completer une fiche
existante. Discord confirme si l'annonce reste en etude ou si elle est prete
pour le prochain scan. La permission administrateur est verifiee a la fois
par Discord et par le bot.

## Ajouter rapidement un lien en PowerShell

Depuis la racine du projet :

```powershell
python .\tools\watchlist_admin.py ajouter "URL_DE_L_ANNONCE"
```

La plateforme et l'identifiant Leboncoin sont détectés depuis l'URL lorsque
le format le permet.

Avec les informations déjà connues :

```powershell
python .\tools\watchlist_admin.py ajouter "URL" --titre "PC Ryzen 5" --prix 300 --description "Ryzen 5, 16 Go, SSD 512 Go" --localisation "Rochefort 17300"
```

Un nouvel ajout tente immédiatement une notification Discord neutre
`NOUVELLE ANNONCE DÉTECTÉE`. Cette notification signifie seulement que
l'annonce entre en étude. Utilise `--sans-discord` pour un import de test ou
pour préparer plusieurs entrées avant un résumé groupé.

## Consulter et administrer

```powershell
python .\tools\watchlist_admin.py lister
python .\tools\watchlist_admin.py prix 1 260
python .\tools\watchlist_admin.py desactiver 1
python .\tools\watchlist_admin.py lister --toutes
python .\tools\watchlist_admin.py notifier
```

Le nombre `1` est l'identifiant local affiché par la commande `lister`.
La désactivation est logique : aucune donnée n'est détruite et un nouvel ajout
de la même URL réactive l'annonce.

La commande `notifier` regroupe toutes les annonces encore non notifiées dans
un résumé Discord unique, automatiquement découpé si la limite Discord est
atteinte.

## Limite actuelle

L'URL n'est jamais téléchargée par le module de watchlist. Une fiche active
contenant titre, prix, description et localisation est toutefois convertie en
`collector.models.Annonce`, puis rejoint la déduplication, le filtre 50 km et
le pipeline d'analyse normal de PC Hunter. Une fiche incomplète reste en étude
sans estimation financière.
