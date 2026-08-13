(() => {
  "use strict";

  const outils = globalThis.HunterProviderUtils;
  if (!outils) return;

  function plateforme() {
    const hote = location.hostname.toLowerCase().replace(/^www\./, "");
    return hote || "Source externe";
  }

  function identifiant() {
    const segment = location.pathname.split("/").filter(Boolean).pop();
    return outils.textePropre(segment, 200);
  }

  function extraire() {
    if (location.protocol !== "https:") return null;
    return outils.creerCapture({
      plateforme: plateforme(),
      identifiant,
      titreSelecteurs: ['[itemprop="name"]', 'main h1', 'article h1', 'h1'],
      prixSelecteurs: [
        '[itemprop="price"]',
        '[data-testid*="price"]',
        '[data-test*="price"]',
        'main [class*="price"]',
      ],
      descriptionSelecteurs: [
        '[itemprop="description"]',
        '[data-testid*="description"]',
        '[data-test*="description"]',
        'article [class*="description"]',
      ],
      localisationSelecteurs: [
        '[itemprop="availableAtOrFrom"]',
        '[data-testid*="location"]',
        '[data-test*="location"]',
      ],
      contexteSelecteurs: [
        '[itemprop="description"]',
        '[data-testid*="description"]',
        '[data-testid*="attribute"]',
        '[data-test*="description"]',
        '[data-test*="attribute"]',
      ],
    });
  }

  globalThis.HunterGenericProvider = { extraire };
})();
