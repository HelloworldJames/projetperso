(() => {
  "use strict";

  const outils = globalThis.HunterProviderUtils;
  if (!outils) return;

  function correspond(url = location.href) {
    try {
      const valeur = new URL(url);
      const hote = valeur.hostname.toLowerCase();
      return valeur.protocol === "https:"
        && (hote === "facebook.com" || hote.endsWith(".facebook.com"))
        && /^\/marketplace\/item\/\d+(?:\/|$)/i.test(valeur.pathname);
    } catch {
      return false;
    }
  }

  function identifiant() {
    return location.pathname.match(/^\/marketplace\/item\/(\d+)/i)?.[1] ?? null;
  }

  function extraire() {
    if (!correspond()) return null;
    return outils.creerCapture({
      plateforme: "Facebook Marketplace",
      identifiant,
      titreSelecteurs: ['[role="main"] h1', 'main h1', 'h1'],
      prixSelecteurs: [
        '[role="main"] [dir="auto"]',
        '[role="main"] span',
        '[itemprop="price"]',
      ],
      descriptionSelecteurs: [
        '[data-ad-rendering-role="story_message"]',
        '[data-testid="marketplace_pdp_description"]',
        '[itemprop="description"]',
      ],
      localisationSelecteurs: [
        '[data-testid="marketplace_pdp_location"]',
        '[aria-label*="lieu" i]',
        '[aria-label*="location" i]',
      ],
      contexteSelecteurs: [
        '[data-ad-rendering-role="story_message"]',
        '[data-testid="marketplace_pdp_description"]',
        '[itemprop="description"]',
      ],
    });
  }

  outils.enregistrerProvider({
    id: "facebook-marketplace",
    nom: "Facebook Marketplace",
    correspond,
    extraire,
  });
})();
