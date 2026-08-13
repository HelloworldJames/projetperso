# Diagnostic des notifications Windows

Cet outil est isolé de PC Hunter. Il ne modifie ni `main.py`, ni les
providers, ni la base SQLite, ni Discord. Il n'effectue aucune requête réseau.

Il utilise l'API Windows officielle
`Windows.UI.Notifications.Management.UserNotificationListener`. Cette API
exige une application Windows déclarant la capacité
`userNotificationListener` et une autorisation explicite de l'utilisateur.

## Construction

Dans PowerShell, depuis la racine de PC Hunter :

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows_notification_diagnostic\build.ps1
```

## Première inscription et lancement

1. Active le **Mode développeur** dans
   `Paramètres Windows > Système > Pour les développeurs`.
2. Exécute :

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows_notification_diagnostic\build.ps1 -Register -Launch
```

3. Accepte la demande Windows d'accès aux notifications.
4. Laisse la console ouverte et attends une notification Leboncoin.
5. Arrête le diagnostic avec `CTRL+C`.

Par défaut, l'outil affiche seulement :

- une notification dont la source est Leboncoin ;
- une notification Mobile connecté dont un champ texte mentionne Leboncoin ;
- une notification Mobile connecté contenant exactement le message générique
  connu `De nouveaux résultats sont disponibles`.

Dans le dernier cas, l'outil affiche `ACTIVITÉ LEBONCOIN DÉTECTÉE — TRIGGER
GÉNÉRIQUE`. Il ne déduit ni annonce, ni prix, ni URL de ce seul message.

L'option `--all`, destinée uniquement au dépannage local, affiche toutes les
notifications accessibles. Elle peut révéler le contenu d'autres
notifications privées dans la console ; aucune donnée n'est enregistrée.

Pour une lecture unique des notifications actuellement présentes :

```powershell
.\tools\windows_notification_diagnostic\build\DiagnosticNotificationsWindows.exe --snapshot --no-pause
```

Pour exécuter le test ciblé du filtre sans demander l'accès aux notifications :

```powershell
.\tools\windows_notification_diagnostic\build\DiagnosticNotificationsWindows.exe --test-filter --no-pause
```

Si l'état retourné est `Denied`, ouvre
`Paramètres Windows > Confidentialité et sécurité > Notifications`, autorise
l'accès des applications aux notifications, puis relance l'outil inscrit.

## Limite officielle de l'API

`UserNotificationListener` expose l'application, l'identifiant, l'heure de
création et le contenu visuel avec ses bindings et ses textes. Il n'expose pas
les boutons/actions ni la cible d'activation de la notification d'une autre
application. Le diagnostic le signale clairement et affiche seulement les URI
qui seraient déjà visibles dans les textes ou hints fournis par Windows.
