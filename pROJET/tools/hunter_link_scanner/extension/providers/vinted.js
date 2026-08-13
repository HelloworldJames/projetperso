(() => {
  "use strict";

  const outils = globalThis.HunterProviderUtils;
  if (!outils) return;

  function correspond(url = location.href) {
    try {
      const valeur = new URL(url);
      const hote = valeur.hostname.toLowerCase();
      return valeur.protocol === "https:"
        && (hote === "vinted.fr" || hote.endsWith(".vinted.fr"))
        && /^\/items\/\d+(?:[-/]|$)/i.test(valeur.pathname);
    } catch {
      return false;
    }
  }

  function identifiant() {
    return location.pathname.match(/^\/items\/(\d+)/i)?.[1] ?? null;
  }

  function extraire() {
    if (!correspond()) return null;
    return outils.creerCapture({
      plateforme: "Vinted",
      identifiant,
      titreSelecteurs: [
        '[data-testid="item-title"]',
        '[data-testid*="item_title"]',
        'main h1',
        'h1',
      ],
      prixSelecteurs: [
        '[data-testid="item-price"]',
        '[data-testid*="item_price"]',
        '[itemprop="price"]',
      ],
      descriptionSelecteurs: [
        '[data-testid="item-description"]',
        '[data-testid*="description"]',
        '[itemprop="description"]',
      ],
      localisationSelecteurs: [
        '[data-testid*="location"]',
        '[itemprop="availableAtOrFrom"]',
      ],
      contexteSelecteurs: [
        '[data-testid="item-description"]',
        '[data-testid*="item_attributes"]',
        '[data-testid*="description"]',
        '[itemprop="description"]',
      ],
    });
  }

  outils.enregistrerProvider({
    id: "vinted",
    nom: "Vinted",
    correspond,
    extraire,
  });
})();
