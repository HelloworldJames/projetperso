export function extraireAnnonceVisible() {
  function textePropre(valeur, limite = 10000) {
    if (valeur === null || valeur === undefined) return null;
    const texte = String(valeur).replace(/\s+/g, " ").trim();
    return texte ? texte.slice(0, limite) : null;
  }

  function plateformeVisible() {
    const hote = location.hostname.toLowerCase();
    if (hote === "leboncoin.fr" || hote.endsWith(".leboncoin.fr")) return "Leboncoin";
    if (hote === "vinted.fr" || hote.endsWith(".vinted.fr")) return "Vinted";
    if (hote === "facebook.com" || hote.endsWith(".facebook.com")) return "Facebook Marketplace";
    if (hote.includes("paruvendu.fr")) return "ParuVendu";
    if (hote.includes("vivastreet.")) return "Vivastreet";
    if (hote.includes("ebay.")) return "eBay";
    return hote;
  }

  function identifiantVisible() {
    const chemin = location.pathname;
    const motifs = [
      /\/ad\/[^/]+\/(\d+)/i,
      /\/items\/(\d+)/i,
      /\/marketplace\/item\/(\d+)/i,
      /\/itm\/(?:[^/]+\/)?(\d+)/i,
    ];
    for (const motif of motifs) {
      const resultat = chemin.match(motif);
      if (resultat) return resultat[1];
    }
    return null;
  }

  function normaliserTitre(valeur) {
    let titre = textePropre(valeur, 500);
    if (!titre) return null;
    titre = titre
      .replace(/^Image\s*:\s*/i, "")
      .replace(/\s*[|·-]\s*(?:Leboncoin|Vinted|eBay)\s*$/i, "")
      .trim();
    if (/^(?:leboncoin(?:\.fr)?|vinted|un instant|just a moment)$/i.test(titre)) return null;
    return titre || null;
  }

  function etatPageVisible() {
    const texte = `${document.title} ${document.body?.innerText || ""}`
      .slice(0, 80000)
      .toLowerCase();
    const motif = [
      "captcha",
      "verify you are human",
      "vÃ©rifiez que vous Ãªtes humain",
      "security check",
      "just a moment",
      "un instant",
      "access denied",
    ].find((element) => texte.includes(element));
    return motif ? { etat: "controle", motif } : { etat: "ok", motif: null };
  }

  function meta(selecteur) {
    return textePropre(document.querySelector(selecteur)?.content);
  }

  function texteSelecteur(selecteurs, limite = 10000) {
    for (const selecteur of selecteurs) {
      const element = document.querySelector(selecteur);
      const valeur = textePropre(element?.innerText || element?.textContent, limite);
      if (valeur) return valeur;
    }
    return null;
  }

  function contexteTechniqueVisible() {
    const source = document.querySelector("main, article, [role='main']");
    if (!source) return null;

    const copie = source.cloneNode(true);
    copie.querySelectorAll([
      "script",
      "style",
      "nav",
      "footer",
      "aside",
      "form",
      "button",
      "input",
      '[data-testid*="seller"]',
      '[data-qa-id*="seller"]',
      '[class*="seller"]',
      '[aria-label*="vendeur"]',
      '[aria-label*="seller"]',
    ].join(",")).forEach((element) => element.remove());

    const texte = textePropre(copie.innerText || copie.textContent, 30000);
    if (!texte) return null;

    return texte
      .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, "[coordonnée retirée]")
      .replace(/(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)/g, "[coordonnée retirée]");
  }

  function parcourirJson(valeur, resultat, profondeur = 0) {
    if (!valeur || typeof valeur !== "object" || profondeur > 12) return;
    if (Array.isArray(valeur)) {
      valeur.forEach((element) => parcourirJson(element, resultat, profondeur + 1));
      return;
    }

    const type = Array.isArray(valeur["@type"])
      ? valeur["@type"].join(" ")
      : String(valeur["@type"] || "");
    if (/Product|Offer|Vehicle|IndividualProduct/i.test(type)) resultat.push(valeur);

    Object.values(valeur).forEach((enfant) =>
      parcourirJson(enfant, resultat, profondeur + 1),
    );
  }

  function objetsJsonLd() {
    const resultat = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach((script) => {
      try {
        parcourirJson(JSON.parse(script.textContent), resultat);
      } catch (_) {
        // Une balise invalide ne doit pas bloquer les autres informations.
      }
    });
    return resultat;
  }

  function convertirPrix(valeur) {
    if (typeof valeur === "number" && Number.isFinite(valeur)) return valeur;
    if (!valeur) return null;

    const correspondance = String(valeur).match(
      /(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:\u20ac|EUR)?/i,
    );
    if (!correspondance) return null;

    const entier = correspondance[1].replace(/[ .\u00a0]/g, "");
    const decimal = correspondance[2] ? `.${correspondance[2]}` : "";
    const nombre = Number(`${entier}${decimal}`);
    return Number.isFinite(nombre) && nombre >= 0 ? nombre : null;
  }

  function adresseLisible(valeur) {
    if (!valeur) return null;
    if (typeof valeur === "string") return textePropre(valeur, 300);
    if (typeof valeur !== "object") return null;
    const adresse = valeur.address && typeof valeur.address === "object"
      ? valeur.address
      : valeur;
    const morceaux = [
      adresse.addressLocality,
      adresse.postalCode,
      adresse.addressRegion,
    ].map((element) => textePropre(element, 100)).filter(Boolean);
    return morceaux.length ? [...new Set(morceaux)].join(" ") : null;
  }

  const objets = objetsJsonLd();
  const produit = objets.find((objet) =>
    /Product|Vehicle|IndividualProduct/i.test(String(objet["@type"] || "")),
  );
  const offreProduit = Array.isArray(produit?.offers) ? produit.offers[0] : produit?.offers;
  const offre = offreProduit || objets.find((objet) =>
    /Offer/i.test(String(objet["@type"] || "")),
  );

  const titre = normaliserTitre(produit?.name)
    || texteSelecteur([
      '[data-qa-id="adview_title"]',
      '[data-testid="item-title"]',
      '[data-testid*="item-title"]',
      '[data-testid="item-name"]',
      '[data-test-id*="title"]',
      'main h1',
      'h1',
    ], 500)
    || normaliserTitre(meta('meta[property="og:title"]'))
    || normaliserTitre(document.title);

  const prixTexte = offre?.price
    || produit?.price
    || meta('meta[property="product:price:amount"]')
    || meta('meta[itemprop="price"]')
    || texteSelecteur([
      '[data-qa-id="adview_price"]',
      '[data-qa-id*="price"]',
      '[data-testid="item-price"]',
      '[data-testid*="item-price"]',
      '[data-test-id*="price"]',
      '[itemprop="price"]',
    ], 100);

  const description = textePropre(produit?.description)
    || texteSelecteur([
      '[data-qa-id="adview_description_container"]',
      '[data-qa-id*="description"]',
      '[data-testid="item-description"]',
      '[data-testid*="item-description"]',
      '[data-test-id*="description"]',
      '[itemprop="description"]',
    ])
    || meta('meta[name="description"]')
    || meta('meta[property="og:description"]');

  const localisation = adresseLisible(produit?.contentLocation)
    || adresseLisible(produit?.location)
    || adresseLisible(offre?.availableAtOrFrom)
    || adresseLisible(offre?.areaServed)
    || texteSelecteur([
      '[data-qa-id="adview_location_informations"]',
      '[data-qa-id*="location"]',
      '[data-testid="item-location"]',
      '[data-testid*="item-location"]',
      '[data-test-id*="location"]',
      '[aria-label*="Localisation"]',
      '[aria-label*="localisation"]',
    ], 300)
    || meta('meta[name="geo.placename"]');

  const datePublication = textePropre(
    produit?.datePublished
      || produit?.datePosted
      || offre?.availabilityStarts,
    100,
  ) || meta('meta[property="article:published_time"]');

  const diagnosticPage = etatPageVisible();
  return {
    identifiant: identifiantVisible(),
    url: location.href,
    plateforme: plateformeVisible(),
    titre: normaliserTitre(titre),
    prix: convertirPrix(prixTexte),
    description,
    localisation,
    date_publication: datePublication,
    contexte_technique: contexteTechniqueVisible(),
    etat_page: diagnosticPage.etat,
    motif_controle: diagnosticPage.motif,
  };
}

export function extraireAnnoncesCatalogueVisibles() {
  function textePropre(valeur, limite = 1000) {
    if (valeur === null || valeur === undefined) return null;
    const texte = String(valeur).replace(/\s+/g, " ").trim();
    return texte ? texte.slice(0, limite) : null;
  }

  function convertirPrix(valeur) {
    if (!valeur) return null;
    if (/^gratuit$/i.test(valeur.trim())) return 0;

    const correspondance = valeur.match(
      /(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:€|EUR|\$US|USD|\$)/i,
    );
    if (!correspondance) return null;

    const entier = correspondance[1].replace(/[ .\u00a0]/g, "");
    const decimal = correspondance[2] ? `.${correspondance[2]}` : "";
    const nombre = Number(`${entier}${decimal}`);
    return Number.isFinite(nombre) && nombre >= 0 ? nombre : null;
  }

  const annonces = [];
  const identifiants = new Set();
  const liens = document.querySelectorAll('a[href*="/marketplace/item/"]');

  liens.forEach((lien) => {
    const href = lien.getAttribute("href");
    const correspondanceId = href?.match(/\/marketplace\/item\/(\d+)/i);
    if (!correspondanceId || identifiants.has(correspondanceId[1])) return;

    const lignes = String(lien.innerText || lien.textContent || "")
      .split(/\r?\n/)
      .map((ligne) => textePropre(ligne, 500))
      .filter(Boolean);
    const indexPrix = lignes.findIndex((ligne) =>
      /^gratuit$/i.test(ligne)
      || /\d\s*(?:€|EUR|\$US|USD|\$)/i.test(ligne),
    );
    if (indexPrix < 0) return;

    const informations = lignes
      .slice(indexPrix + 1)
      .filter((ligne) => !/^annonce récente$/i.test(ligne));
    const titre = informations[0] ?? null;
    const localisation = informations.length > 1
      ? informations[informations.length - 1]
      : null;
    if (!titre) return;

    const url = new URL(`/marketplace/item/${correspondanceId[1]}`, location.origin).href;
    const recente = lignes.find((ligne) => /^annonce récente$/i.test(ligne)) ?? null;
    identifiants.add(correspondanceId[1]);
    annonces.push({
      identifiant: correspondanceId[1],
      url,
      titre,
      prix: convertirPrix(lignes[indexPrix]),
      description: `Annonce détectée dans la veille Marketplace : ${titre}`,
      localisation,
      date_publication: recente,
      source_catalogue: location.href,
    });
  });

  return annonces;
}
