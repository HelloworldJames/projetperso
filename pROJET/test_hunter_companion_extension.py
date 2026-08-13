import json
import unittest
from pathlib import Path


RACINE = Path(__file__).parent / "tools" / "hunter_link_scanner" / "extension"


class HunterCompanionExtensionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (RACINE / "manifest.json").read_text(encoding="utf-8")
        )

    def test_manifest_10_utilise_les_permissions_minimales(self):
        self.assertEqual(self.manifest["manifest_version"], 3)
        self.assertEqual(self.manifest["version"], "1.0.0")
        self.assertEqual(
            set(self.manifest["permissions"]),
            {"activeTab", "storage", "scripting"},
        )
        self.assertEqual(
            self.manifest["host_permissions"],
            ["http://127.0.0.1:8765/*"],
        )
        self.assertNotIn("tabs", self.manifest["permissions"])
        self.assertNotIn("alarms", self.manifest["permissions"])
        self.assertNotIn("<all_urls>", str(self.manifest))
        self.assertNotIn("https://*.facebook.com/*", self.manifest["host_permissions"])
        self.assertNotIn("https://*.vinted.fr/*", self.manifest["host_permissions"])

    def test_extracteur_leboncoin_est_separe_du_coeur_extension(self):
        scripts = self.manifest["content_scripts"][0]["js"]
        self.assertEqual(
            scripts,
            [
                "providers/leboncoin.js",
                "overlay.js",
                "companion-content.js",
            ],
        )
        self.assertNotIn("extractor.js", scripts)

        fournisseur = (
            RACINE / "providers" / "leboncoin.js"
        ).read_text(encoding="utf-8")
        self.assertIn("HunterProviders", fournisseur)
        self.assertIn(r"^\/ad\/[^/]+\/\d+", fournisseur)
        self.assertIn("adview_title", fournisseur)
        self.assertIn("adview_price", fournisseur)
        self.assertIn("adview_description_container", fournisseur)
        self.assertIn("localisationVisibleDansAnnonce", fournisseur)
        self.assertLess(
            fournisseur.index("'main h1'"),
            fournisseur.index("'[data-qa-id=\"adview_title\"]'"),
        )
        self.assertIn("contexteTechniqueVisible", fournisseur)
        self.assertIn("SELECTEURS_VENDEUR", fournisseur)
        self.assertIn("images_collectees: false", fournisseur)
        self.assertNotIn("document.cookie", fournisseur)
        self.assertNotIn("localStorage", fournisseur)
        self.assertNotIn("sessionStorage", fournisseur)

    def test_navigation_dynamique_et_onglet_visible_sont_geres(self):
        contenu = (RACINE / "companion-content.js").read_text(encoding="utf-8")
        self.assertIn("MutationObserver", contenu)
        self.assertIn("setInterval(verifierNavigation", contenu)
        self.assertIn('document.visibilityState !== "visible"', contenu)
        self.assertIn("location.href", contenu)
        self.assertIn("HUNTER_COMPANION_ANALYZE", contenu)
        self.assertIn("INVENT", contenu.upper())
        self.assertNotIn("chrome.alarms", contenu)

    def test_facebook_vinted_et_generique_sont_isoles_par_provider(self):
        scripts_par_site = [entree["js"] for entree in self.manifest["content_scripts"]]
        self.assertIn(
            [
                "providers/common.js",
                "providers/facebook-marketplace.js",
                "overlay.js",
                "companion-content.js",
            ],
            scripts_par_site,
        )
        self.assertIn(
            [
                "providers/common.js",
                "providers/vinted.js",
                "overlay.js",
                "companion-content.js",
            ],
            scripts_par_site,
        )

        facebook = (RACINE / "providers" / "facebook-marketplace.js").read_text(encoding="utf-8")
        vinted = (RACINE / "providers" / "vinted.js").read_text(encoding="utf-8")
        generique = (RACINE / "providers" / "generic.js").read_text(encoding="utf-8")
        commun = (RACINE / "providers" / "common.js").read_text(encoding="utf-8")
        self.assertIn(r"^\/marketplace\/item\/\d+", facebook)
        self.assertIn('plateforme: "Facebook Marketplace"', facebook)
        self.assertIn(r"^\/items\/\d+", vinted)
        self.assertIn('plateforme: "Vinted"', vinted)
        self.assertIn("HunterGenericProvider", generique)
        self.assertIn("SELECTEURS_SENSIBLES", commun)
        for contenu in (facebook, vinted, generique, commun):
            self.assertNotIn("document.cookie", contenu)
            self.assertNotIn("localStorage", contenu)
            self.assertNotIn("sessionStorage", contenu)

    def test_background_filtre_capture_et_ne_fait_aucune_veille(self):
        background = (RACINE / "background.js").read_text(encoding="utf-8")
        self.assertIn("CHAMPS_CAPTURE_AUTORISES", background)
        self.assertIn("filtrerCapture", background)
        self.assertIn("http://127.0.0.1:8765/import", background)
        self.assertIn("http://127.0.0.1:8765/recent", background)
        self.assertIn("HUNTER_COMPANION_INBOX", background)
        self.assertIn("urlPubliqueAcceptee", background)
        self.assertIn("analyserOngletGenerique", background)
        self.assertIn("chrome.scripting.executeScript", background)
        self.assertIn("hunter_companion_enabled", background)
        self.assertIn("hunter_companion_errors", background)
        self.assertIn("contexteErreur", background)
        self.assertNotIn("CLE_SIGNAUX_VEILLE", background)
        self.assertNotIn("INTERVALLE_VEILLE", background)
        self.assertNotIn("chrome.alarms", background)
        self.assertNotIn("capturerCatalogue", background)
        self.assertNotIn("cookie", background.lower())
        self.assertNotIn("token", background.lower())

    def test_overlay_affiche_verdict_valeur_marge_confiance_et_prix_max(self):
        overlay = (RACINE / "overlay.js").read_text(encoding="utf-8")
        self.assertIn("score_affaire", overlay)
        self.assertIn("Prix demandé", overlay)
        self.assertIn("Valeur estimée", overlay)
        self.assertIn("Marge prudente", overlay)
        self.assertIn("Confiance", overlay)
        self.assertIn("Prix maximum conseillé", overlay)
        self.assertIn("Informations insuffisantes", overlay)
        self.assertIn("Hunter refuse d’inventer", overlay)
        self.assertIn('afficherMessage(message, "insufficient")', overlay)
        self.assertIn("attachShadow", overlay)

    def test_popup_active_explicitement_et_declenche_page_courante(self):
        popup = (RACINE / "popup.html").read_text(encoding="utf-8")
        script = (RACINE / "popup.js").read_text(encoding="utf-8")
        self.assertIn('id="companion-enabled"', popup)
        self.assertIn('id="analyze-current"', popup)
        self.assertIn("Pas de cookies", popup)
        self.assertIn("HUNTER_COMPANION_SET_ENABLED", script)
        self.assertIn("HUNTER_ANALYSER_ONGLET", script)
        self.assertIn("chrome.tabs.query", script)
        self.assertIn('url: onglet.url', script)
        self.assertIn(r"/^https:\/\//i", script)
        self.assertNotIn("listing-url", popup)

    def test_pont_web_expose_uniquement_la_boite_locale(self):
        bridge = (RACINE / "content-bridge.js").read_text(encoding="utf-8")
        self.assertIn("ORIGINES_AUTORISEES", bridge)
        self.assertIn("HUNTER_COMPANION_PING", bridge)
        self.assertIn("HUNTER_COMPANION_ANALYZE", bridge)
        self.assertIn("HUNTER_COMPANION_INBOX", bridge)
        self.assertIn("HUNTER_COMPANION_INBOX_RESULT", bridge)
        self.assertIn('version: "1.0.0"', bridge)
        self.assertNotIn("HUNTER_COMPANION_SIGNALS", bridge)
        self.assertNotIn("HUNTER_RECUPERER_SIGNAUX", bridge)


if __name__ == "__main__":
    unittest.main()
