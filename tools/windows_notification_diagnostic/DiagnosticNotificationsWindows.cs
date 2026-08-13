using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

using Windows.UI.Notifications;
using Windows.UI.Notifications.Management;


namespace PCHunter.WindowsNotificationDiagnostic
{
    internal static class Program
    {
        private const int DefaultPollIntervalMs = 1000;

        private enum LeboncoinMatchKind
        {
            None,
            Identified,
            GenericTrigger
        }

        private static readonly Regex UriPattern = new Regex(
            @"\b(?:https?://|leboncoin://|ms-phone-link://)[^\s<>""']+",
            RegexOptions.IgnoreCase | RegexOptions.Compiled
        );

        private static bool stopRequested;
        private static bool pauseOnFailure = true;


        [STAThread]
        private static int Main(string[] args)
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            pauseOnFailure = !args.Any(
                value => string.Equals(
                    value,
                    "--no-pause",
                    StringComparison.OrdinalIgnoreCase
                )
            );

            try
            {
                return Run(args);
            }
            catch (Exception error)
            {
                Console.Error.WriteLine();
                Console.Error.WriteLine("ERREUR DIAGNOSTIC WINDOWS");
                Console.Error.WriteLine(error.GetType().FullName);
                Console.Error.WriteLine(error.Message);
                PauseBeforeExit();
                return 1;
            }
        }


        private static int Run(string[] args)
        {
            bool testFilter = args.Any(
                value => string.Equals(
                    value,
                    "--test-filter",
                    StringComparison.OrdinalIgnoreCase
                )
            );

            if (testFilter)
            {
                return RunFilterSelfTest();
            }

            bool showAll = args.Any(
                value => string.Equals(
                    value,
                    "--all",
                    StringComparison.OrdinalIgnoreCase
                )
            );

            bool snapshotOnly = args.Any(
                value => string.Equals(
                    value,
                    "--snapshot",
                    StringComparison.OrdinalIgnoreCase
                )
            );

            int pollIntervalMs = ReadPollInterval(args);

            PrintHeader(showAll, snapshotOnly, pollIntervalMs);

            UserNotificationListener listener = (
                UserNotificationListener.Current
            );

            UserNotificationListenerAccessStatus accessStatus = (
                listener.GetAccessStatus()
            );

            if (accessStatus == UserNotificationListenerAccessStatus.Unspecified)
            {
                Console.WriteLine(
                    "Windows demande l'autorisation de lire les notifications."
                );

                accessStatus = WaitForOperation(
                    listener.RequestAccessAsync()
                );
            }

            Console.WriteLine("Accès UserNotificationListener : " + accessStatus);

            if (accessStatus != UserNotificationListenerAccessStatus.Allowed)
            {
                Console.WriteLine();
                Console.WriteLine("Accès refusé.");
                Console.WriteLine(
                    "Ouvre Paramètres Windows > Confidentialité et sécurité, " +
                    "puis autorise PC Hunter Notification Diagnostic à accéder " +
                    "aux notifications."
                );
                PauseBeforeExit();
                return 2;
            }

            Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs eventArgs)
            {
                eventArgs.Cancel = true;
                stopRequested = true;
            };

            HashSet<string> seenNotifications = new HashSet<string>(
                StringComparer.Ordinal
            );

            while (!stopRequested)
            {
                IReadOnlyList<UserNotification> notifications = (
                    WaitForOperation(
                        listener.GetNotificationsAsync(NotificationKinds.Toast)
                    )
                );

                foreach (UserNotification notification in notifications)
                {
                    string key = BuildNotificationKey(notification);

                    if (!seenNotifications.Add(key))
                    {
                        continue;
                    }

                    List<string> textValues = ReadTextValues(notification);
                    LeboncoinMatchKind matchKind = (
                        ClassifyLeboncoinNotification(notification, textValues)
                    );

                    if (!showAll && matchKind == LeboncoinMatchKind.None)
                    {
                        continue;
                    }

                    PrintNotification(notification, textValues, matchKind);
                }

                if (snapshotOnly)
                {
                    break;
                }

                Thread.Sleep(pollIntervalMs);
            }

            Console.WriteLine();
            Console.WriteLine("Diagnostic arrêté. Aucune donnée n'a été enregistrée.");
            return 0;
        }


        private static int ReadPollInterval(string[] args)
        {
            const string prefix = "--interval-ms=";

            foreach (string argument in args)
            {
                if (!argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                int value;

                if (int.TryParse(argument.Substring(prefix.Length), out value))
                {
                    return Math.Max(500, value);
                }
            }

            return DefaultPollIntervalMs;
        }


        private static void PauseBeforeExit()
        {
            if (!pauseOnFailure)
            {
                return;
            }

            Console.WriteLine();
            Console.WriteLine("Appuie sur ENTRÉE pour fermer cette fenêtre.");
            Console.ReadLine();
        }


        private static T WaitForOperation<T>(
            Windows.Foundation.IAsyncOperation<T> operation
        )
        {
            using (ManualResetEventSlim completion = new ManualResetEventSlim(false))
            {
                Windows.Foundation.AsyncStatus finalStatus = (
                    Windows.Foundation.AsyncStatus.Started
                );

                operation.Completed = delegate(
                    Windows.Foundation.IAsyncOperation<T> completedOperation,
                    Windows.Foundation.AsyncStatus status
                )
                {
                    finalStatus = status;
                    completion.Set();
                };

                completion.Wait();

                if (finalStatus == Windows.Foundation.AsyncStatus.Completed)
                {
                    return operation.GetResults();
                }

                if (finalStatus == Windows.Foundation.AsyncStatus.Canceled)
                {
                    throw new OperationCanceledException(
                        "L'opération WinRT a été annulée."
                    );
                }

                throw (
                    operation.ErrorCode
                    ??
                    new InvalidOperationException(
                        "L'opération WinRT a échoué."
                    )
                );
            }
        }


        private static void PrintHeader(
            bool showAll,
            bool snapshotOnly,
            int pollIntervalMs
        )
        {
            Console.WriteLine("============================================================");
            Console.WriteLine("PC HUNTER - DIAGNOSTIC NOTIFICATIONS WINDOWS");
            Console.WriteLine("============================================================");
            Console.WriteLine("Réseau : aucun accès");
            Console.WriteLine("Stockage : aucun");
            Console.WriteLine(
                "Filtre : " +
                (showAll ? "toutes les notifications (--all)" : "Leboncoin uniquement")
            );
            Console.WriteLine(
                "Mode : " +
                (snapshotOnly ? "instantané" : "écoute continue")
            );
            Console.WriteLine("Intervalle de lecture : " + pollIntervalMs + " ms");
            Console.WriteLine("Arrêt : CTRL+C");
            Console.WriteLine("============================================================");
            Console.WriteLine();
        }


        private static string BuildNotificationKey(UserNotification notification)
        {
            string appUserModelId = SafeRead(
                delegate { return notification.AppInfo.AppUserModelId; },
                "app-inconnue"
            );

            return string.Join(
                "|",
                appUserModelId,
                notification.Id.ToString(),
                notification.CreationTime.UtcDateTime.Ticks.ToString()
            );
        }


        private static LeboncoinMatchKind ClassifyLeboncoinNotification(
            UserNotification notification,
            IEnumerable<string> textValues
        )
        {
            List<string> sourceValues = new List<string>();

            sourceValues.Add(
                SafeRead(
                    delegate { return notification.AppInfo.DisplayInfo.DisplayName; },
                    string.Empty
                )
            );

            sourceValues.Add(
                SafeRead(
                    delegate { return notification.AppInfo.AppUserModelId; },
                    string.Empty
                )
            );

            sourceValues.Add(
                SafeRead(
                    delegate { return notification.AppInfo.PackageFamilyName; },
                    string.Empty
                )
            );

            string source = string.Join(" ", sourceValues);
            string texts = string.Join(" ", textValues);

            return ClassifyRelevantSourceAndText(source, texts);
        }


        private static LeboncoinMatchKind ClassifyRelevantSourceAndText(
            string source,
            string texts
        )
        {
            source = (source ?? string.Empty).ToLowerInvariant();
            texts = (texts ?? string.Empty).ToLowerInvariant();

            bool isLeboncoinSource = ContainsLeboncoin(source);
            bool isPhoneLink = IsPhoneLinkSource(source);
            bool isLocalDiagnostic = (
                source.Contains("pchunter.notificationdiagnostic")
            );

            if (
                ContainsGenericLeboncoinTrigger(texts)
                &&
                (isLeboncoinSource || isPhoneLink)
            )
            {
                return LeboncoinMatchKind.GenericTrigger;
            }

            if (
                isLeboncoinSource
                ||
                ((isPhoneLink || isLocalDiagnostic) && ContainsLeboncoin(texts))
            )
            {
                return LeboncoinMatchKind.Identified;
            }

            return LeboncoinMatchKind.None;
        }


        private static int RunFilterSelfTest()
        {
            Console.WriteLine("TEST DU FILTRE DE NOTIFICATIONS");
            Console.WriteLine();

            bool success = true;

            success &= PrintFilterTestCase(
                "Source Leboncoin directe",
                "leboncoin",
                "Une nouvelle annonce correspond à votre recherche",
                LeboncoinMatchKind.Identified
            );
            success &= PrintFilterTestCase(
                "Mobile connecté + texte Leboncoin",
                "Microsoft.YourPhone_8wekyb3d8bbwe",
                "leboncoin - PC portable",
                LeboncoinMatchKind.Identified
            );
            success &= PrintFilterTestCase(
                "Mobile connecté + texte générique connu",
                "Microsoft.YourPhone_8wekyb3d8bbwe",
                "De nouveaux résultats sont disponibles",
                LeboncoinMatchKind.GenericTrigger
            );
            success &= PrintFilterTestCase(
                "Diagnostic local + texte Leboncoin",
                "PCHunter.NotificationDiagnostic_fse26f93m3mk6",
                "leboncoin - TEST PC Hunter",
                LeboncoinMatchKind.Identified
            );
            success &= PrintFilterTestCase(
                "ChatGPT mentionnant Leboncoin",
                "OpenAI.Codex_2p2nqsd0c76g0",
                "Le diagnostic a trouvé une notification leboncoin",
                LeboncoinMatchKind.None
            );
            success &= PrintFilterTestCase(
                "Mobile connecté sans Leboncoin",
                "Microsoft.YourPhone_8wekyb3d8bbwe",
                "Nouveau message reçu",
                LeboncoinMatchKind.None
            );
            success &= PrintFilterTestCase(
                "Autre application + texte générique",
                "Exemple.AutreApplication",
                "De nouveaux résultats sont disponibles",
                LeboncoinMatchKind.None
            );

            Console.WriteLine();
            Console.WriteLine(
                success
                    ? "RÉSULTAT : filtre validé."
                    : "RÉSULTAT : échec du filtre."
            );

            return success ? 0 : 3;
        }


        private static bool PrintFilterTestCase(
            string name,
            string source,
            string texts,
            LeboncoinMatchKind expected
        )
        {
            LeboncoinMatchKind actual = (
                ClassifyRelevantSourceAndText(source, texts)
            );
            bool success = actual == expected;

            Console.WriteLine(
                (success ? "[OK] " : "[ÉCHEC] ")
                + name
                + " — attendu="
                + expected
                + ", obtenu="
                + actual
            );

            return success;
        }


        private static bool ContainsLeboncoin(string value)
        {
            return (
                value.Contains("leboncoin")
                ||
                value.Contains("le bon coin")
            );
        }


        private static bool ContainsGenericLeboncoinTrigger(string value)
        {
            return (
                value.Contains("de nouveaux résultats sont disponibles")
                ||
                value.Contains("de nouveaux resultats sont disponibles")
            );
        }


        private static bool IsPhoneLinkSource(string source)
        {
            return (
                source.Contains("microsoft.yourphone")
                ||
                source.Contains("yourphone")
                ||
                source.Contains("mobile connecté")
                ||
                source.Contains("mobile connecte")
                ||
                source.Contains("phone link")
                ||
                source.Contains("lien avec windows")
            );
        }


        private static List<string> ReadTextValues(UserNotification notification)
        {
            List<string> values = new List<string>();

            Notification content = notification.Notification;

            if (content == null || content.Visual == null)
            {
                return values;
            }

            foreach (NotificationBinding binding in content.Visual.Bindings)
            {
                foreach (AdaptiveNotificationText textElement in binding.GetTextElements())
                {
                    if (!string.IsNullOrWhiteSpace(textElement.Text))
                    {
                        values.Add(textElement.Text.Trim());
                    }
                }
            }

            return values;
        }


        private static void PrintNotification(
            UserNotification notification,
            List<string> textValues,
            LeboncoinMatchKind matchKind
        )
        {
            string displayName = SafeRead(
                delegate { return notification.AppInfo.DisplayInfo.DisplayName; },
                "Inconnue"
            );

            string appId = SafeRead(
                delegate { return notification.AppInfo.Id; },
                "Non exposé"
            );

            string appUserModelId = SafeRead(
                delegate { return notification.AppInfo.AppUserModelId; },
                "Non exposé"
            );

            string packageFamilyName = SafeRead(
                delegate { return notification.AppInfo.PackageFamilyName; },
                "Non exposé"
            );

            Console.WriteLine();
            Console.WriteLine("############################################################");

            if (matchKind == LeboncoinMatchKind.GenericTrigger)
            {
                Console.WriteLine("ACTIVITÉ LEBONCOIN DÉTECTÉE — TRIGGER GÉNÉRIQUE");
            }
            else if (matchKind == LeboncoinMatchKind.Identified)
            {
                Console.WriteLine("NOTIFICATION LEBONCOIN IDENTIFIÉE");
            }
            else
            {
                Console.WriteLine("NOTIFICATION WINDOWS OBSERVÉE (--all)");
            }

            Console.WriteLine("############################################################");
            Console.WriteLine("Application/source : " + displayName);
            Console.WriteLine("AppInfo.Id : " + appId);
            Console.WriteLine("AppUserModelId : " + appUserModelId);
            Console.WriteLine("PackageFamilyName : " + packageFamilyName);
            Console.WriteLine("Notification ID : " + notification.Id);
            Console.WriteLine(
                "CreationTime : " + notification.CreationTime.ToString("O")
            );

            string title = textValues.Count > 0 ? textValues[0] : "Non exposé";
            Console.WriteLine("Titre : " + title);

            string mainText = (
                textValues.Count > 1
                    ? string.Join(" | ", textValues.Skip(1))
                    : "Non exposé"
            );
            Console.WriteLine("Texte : " + mainText);

            if (matchKind == LeboncoinMatchKind.GenericTrigger)
            {
                Console.WriteLine(
                    "Interprétation : simple trigger; aucune annonce ni URL " +
                    "n'est déduite de ce texte générique."
                );
            }

            Notification content = notification.Notification;

            if (content == null)
            {
                Console.WriteLine("Contenu Notification : absent");
                PrintUnavailableInteractiveMetadata(new List<string>());
                Console.WriteLine("############################################################");
                return;
            }

            Console.WriteLine(
                "ExpirationTime : " +
                (content.ExpirationTime.HasValue
                    ? content.ExpirationTime.Value.ToString("O")
                    : "Non définie")
            );

            NotificationVisual visual = content.Visual;

            if (visual == null)
            {
                Console.WriteLine("Visual : absent");
                PrintUnavailableInteractiveMetadata(new List<string>());
                Console.WriteLine("############################################################");
                return;
            }

            Console.WriteLine("Langue Visual : " + EmptyAsUnavailable(visual.Language));
            Console.WriteLine("Nombre de bindings : " + visual.Bindings.Count);
            Console.WriteLine(
                "Groupes : non exposés séparément par cette API; " +
                "GetTextElements() restitue les textes disponibles."
            );

            List<string> exposedUris = new List<string>();

            for (int bindingIndex = 0; bindingIndex < visual.Bindings.Count; bindingIndex++)
            {
                NotificationBinding binding = visual.Bindings[bindingIndex];

                Console.WriteLine();
                Console.WriteLine("Binding #" + bindingIndex);
                Console.WriteLine("  Template : " + EmptyAsUnavailable(binding.Template));
                Console.WriteLine("  Langue : " + EmptyAsUnavailable(binding.Language));
                PrintHints("  Hints", binding.Hints, exposedUris);

                IReadOnlyList<AdaptiveNotificationText> elements = (
                    binding.GetTextElements()
                );

                Console.WriteLine("  Champs texte : " + elements.Count);

                for (int textIndex = 0; textIndex < elements.Count; textIndex++)
                {
                    AdaptiveNotificationText element = elements[textIndex];
                    string value = element.Text ?? string.Empty;

                    Console.WriteLine("    Texte #" + textIndex + " : " + value);
                    Console.WriteLine(
                        "      Langue : " + EmptyAsUnavailable(element.Language)
                    );
                    PrintHints("      Hints", element.Hints, exposedUris);

                    foreach (Match match in UriPattern.Matches(value))
                    {
                        AddUnique(exposedUris, match.Value);
                    }
                }
            }

            PrintUnavailableInteractiveMetadata(exposedUris);
            Console.WriteLine("############################################################");
        }


        private static void PrintHints(
            string label,
            IEnumerable<KeyValuePair<string, string>> hints,
            List<string> exposedUris
        )
        {
            List<KeyValuePair<string, string>> values = hints.ToList();

            if (values.Count == 0)
            {
                Console.WriteLine(label + " : aucun");
                return;
            }

            Console.WriteLine(label + " :");

            foreach (KeyValuePair<string, string> hint in values)
            {
                Console.WriteLine("    " + hint.Key + " = " + hint.Value);

                foreach (Match match in UriPattern.Matches(hint.Value ?? string.Empty))
                {
                    AddUnique(exposedUris, match.Value);
                }
            }
        }


        private static void PrintUnavailableInteractiveMetadata(
            List<string> exposedUris
        )
        {
            Console.WriteLine();
            Console.WriteLine(
                "Boutons/actions : non exposés par UserNotificationListener."
            );
            Console.WriteLine(
                "Activation target/deep-link : non exposé par UserNotificationListener."
            );

            if (exposedUris.Count == 0)
            {
                Console.WriteLine("URI visibles dans les textes/hints : aucune");
            }
            else
            {
                Console.WriteLine("URI visibles dans les textes/hints :");

                foreach (string uri in exposedUris)
                {
                    Console.WriteLine("  - " + uri);
                }
            }
        }


        private static void AddUnique(List<string> values, string value)
        {
            if (!values.Contains(value, StringComparer.OrdinalIgnoreCase))
            {
                values.Add(value);
            }
        }


        private static string EmptyAsUnavailable(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "Non exposé" : value;
        }


        private static string SafeRead(Func<string> reader, string fallback)
        {
            try
            {
                return EmptyAsUnavailable(reader());
            }
            catch
            {
                return fallback;
            }
        }
    }
}
