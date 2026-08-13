(() => {
  "use strict";

  const COORDONNEE_EMAIL = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g;
  const COORDONNEE_TELEPHONE = /(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)/g;
  const SELECTEURS_VENDEUR = [
    '[data-testid*="seller"]',
    '[data-qa-id*="seller"]',
    '[data-testid*="owner"]',
    '[data-qa-id*="owner"]',
    '[class*="seller"]',
    '[class*="owner"]',
    '[aria-label*="vendeur" i]',
    '[aria-label*="seller" i]',
    '[href*="/profil/"]',
    '[href*="/profile/"]',
  ];

  function textePropre(valeur, limite = 10000) {
    if (valeur === null || valeur === undefined) return null;
    const texte = String(valeur).replace(/\s+/g, " ").trim();
    return texte ? texte.slice(0, limite) : null;
  }

  function nettoyerCoordonnees(valeur, limite = 10000) {
    const texte = textePropre(valeur, limite);
    if (!texte) return null;
    return texte
      .replace(COORDONNEE_EMAIL, "[coordonnée retirée]")
      .replace(COORDONNEE_TELEPHONE, "[coordonnée retirée]");
  }

  function correspond(url = location.href) {
    try {
      const valeur = new URL(url);
      const hote = valeur.hostname.toLowerCase();
      return valeur.protocol === "https:"
        && (hote === "leboncoin.fr" || hote.endsWith(".leboncoin.fr"))
        && /^\/ad\/[^/]+\/\d+(?:\/|$)/i.test(valeur.pathname);
    } catch {
      return false;
    }
  }

  function identifiantDepuisUrl(url = location.href) {
    return new URL(url).pathname.match(/^\/ad\/[^/]+\/(\d+)/i)?.[1] ?? null;
  }

  function meta(selecteur) {
    return textePropre(document.querySelector(selecteur)?.content);
  }

  function texteSelecteur(selecteurs, limite = 10000) {
    for (const selecteur of selecteurs) {
      const element = document.querySelector(selecteur);
      if (!element || element.closest(SELECTEURS_VENDEUR.join(","))) continue;
      const valeur = textePropre(element.innerText || element.textContent, limite);
      if (valeur) return valeur;
    }
    return null;
  }

  function normaliserTitre(valeur) {
    let titre = textePropre(valeur, 500);
    if (!titre) return null;
    titre = titre
      .replace(/^Image\s*:\s*/i, "")
      .replace(/\s*[|·-]\s*Leboncoin\s*$/i, "")
      .trim();
    if (/^(?:leboncoin(?:\.fr)?|voir l['’]?annonce|annonce)$/i.test(titre)) {
      return null;
    }
    return titre || null;
  }

  function convertirPrix(valeur) {
    if (typeof valeur === "number" && Number.isFinite(valeur)) return valeur;
    const texte = textePropre(valeur, 100);
    if (!texte) return null;
    const resultat = texte.match(
      /(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:€|EUR)?/i,
    );
    if (!resultat) return null;
    const entier = resultat[1].replace(/[ .\u00a0]/g, "");
    const decimal = resultat[2] ? `.${resultat[2]}` : "";
    const nombre = Number(`${entier}${decimal}`);
    return Number.isFinite(nombre) && nombre > 0 ? nombre : null;
  }

  function parcourirJson(valeur, resultat, profondeur = 0) {
    if (!valeur || typeof valeur !== "object" || profondeur > 10) return;
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

  function objetsProduitJsonLd() {
    const resultat = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach((script) => {
      try {
        parcourirJson(JSON.parse(script.textContent), resultat);
      } catch {
        // Une balise JSON-LD invalide ne doit pas bloquer les champs visibles.
      }
    });
    return resultat;
  }

  function localisationApproximate(valeur) {
    if (!valeur) return null;
    if (typeof valeur === "object") {
      const adresse = valeur.address && typeof valeur.address === "object"
        ? valeur.address
        : valeur;
      const ville = textePropre(adresse.addressLocality || adresse.city, 150);
      const code = textePropre(adresse.postalCode || adresse.zipcode, 10);
      const departement = /^\d{5}$/.test(code || "") ? code.slice(0, 2) : null;
      return ville ? `${ville}${departement ? ` (${departement})` : ""}` : null;
    }

    const texte = nettoyerCoordonnees(valeur, 300);
    if (!texte) return null;
    const codeVille = texte.match(/\b(\d{5})\s+([^·,|]{2,100})/);
    if (codeVille) return `${codeVille[2].trim()} (${codeVille[1].slice(0, 2)})`;
    return texte.replace(/\b(\d{2})\d{3}\b/g, "($1)");
  }

  function localisationVisibleDansAnnonce() {
    const selecteursBlocs = [
      '[data-qa-id="adview_spotlight_description_container"]',
      '[data-qa-id="adview_delivery_container"]',
    ];
    for (const selecteur of selecteursBlocs) {
      const bloc = document.querySelector(selecteur);
      if (!bloc) continue;
      const candidats = [...bloc.querySelectorAll("p, span")]
        .map((element) => textePropre(element.textContent, 200))
        .filter(Boolean);
      const localisation = candidats.find((texte) => /^À\s+[^.]{2,100}$/i.test(texte));
      if (localisation) return localisation.replace(/^À\s+/i, "");
    }
    return null;
  }

  function contexteTechniqueVisible() {
    const sections = [];
    const selecteurs = [
      '[data-qa-id*="criteria"]',
      '[data-testid*="criteria"]',
      '[data-qa-id*="attribute"]',
      '[data-testid*="attribute"]',
      '[data-qa-id="adview_description_container"]',
      '[data-qa-id="adview_spotlight_description_container"]',
    ];
    document.querySelectorAll(selecteurs.join(",")).forEach((element) => {
      if (element.closest(SELECTEURS_VENDEUR.join(","))) return;
      const copie = element.cloneNode(true);
      copie.querySelectorAll([
        ...SELECTEURS_VENDEUR,
        "script",
        "style",
        "form",
        "button",
        "input",
        "textarea",
      ].join(",")).forEach((enfant) => enfant.remove());
      const texte = nettoyerCoordonnees(copie.innerText || copie.textContent, 8000);
      if (texte) sections.push(texte);
    });
    return textePropre([...new Set(sections)].join(" · "), 15000);
  }

  function detecterControle() {
    const texte = `${document.title} ${document.body?.innerText || ""}`
      .slice(0, 50000)
      .toLocaleLowerCase("fr");
    const motif = [
      "captcha",
      "verify you are human",
      "vérifiez que vous êtes humain",
      "activité inhabituelle",
      "security check",
      "access denied",
    ].find((element) => texte.includes(element));
    return motif || null;
  }

  function extraireCaracteristiques(texte) {
    const contenu = texte || "";
    const etat = contenu.match(
      /\b(très bon état|bon état|état neuf|comme neuf|satisfaisant)\b/i,
    )?.[1] ?? null;
    const annee = contenu.match(/\b(?:année|modèle)\s*[: -]?\s*(20\d{2})\b/i)?.[1] ?? null;
    const ram = contenu.match(/\b(?:ram|mémoire vive)\s*[: -]?\s*(\d+)\s*(?:go|gb)\b/i)?.[1] ?? null;
    const stockage = contenu.match(
      /\b(?:stockage|ssd|nvme|disque(?: dur)?)\s*[: -]?\s*(\d+)\s*(?:go|gb)\b/i,
    )?.[1] ?? null;
    const garantie = contenu.match(
      /garantie\s+jusqu['’]?[aàu]*\s*[: -]?\s*(\d{1,2}\/\d{4})/i,
    )?.[1] ?? null;
    const marque = /\b(?:macbook|imac|apple)\b/i.test(contenu)
      ? "Apple"
      : contenu.match(/\b(Lenovo|Dell|ASUS|Acer|HP|MSI)\b/i)?.[1] ?? null;
    return {
      etat,
      marque,
      annee: annee ? Number(annee) : null,
      ram_go: ram ? Number(ram) : null,
      stockage_go: stockage ? Number(stockage) : null,
      garantie_jusqu_au: garantie,
    };
  }

  function extraire() {
    if (!correspond()) return null;
    const controle = detecterControle();
    if (controle) {
      return {
        plateforme: "Leboncoin",
        identifiant: identifiantDepuisUrl(),
        url: location.href,
        etat_page: "controle",
        motif_controle: controle,
      };
    }

    const objets = objetsProduitJsonLd();
    const produit = objets.find((objet) =>
      /Product|Vehicle|IndividualProduct/i.test(String(objet["@type"] || "")),
    );
    const offreProduit = Array.isArray(produit?.offers) ? produit.offers[0] : produit?.offers;
    const offre = offreProduit || objets.find((objet) =>
      /Offer/i.test(String(objet["@type"] || "")),
    );

    const titre = normaliserTitre(produit?.name)
      || normaliserTitre(texteSelecteur([
        'main h1',
        '[data-qa-id="adview_title"]',
        '[data-testid="item-title"]',
      ], 500))
      || normaliserTitre(meta('meta[property="og:title"]'));

    const prix = convertirPrix(
      offre?.price
      || produit?.price
      || meta('meta[property="product:price:amount"]')
      || texteSelecteur([
        '[data-qa-id="adview_price"]',
        '[data-testid="item-price"]',
        '[itemprop="price"]',
      ], 100),
    );

    const description = nettoyerCoordonnees(
      produit?.description
      || texteSelecteur([
        '[data-qa-id="adview_description_container"]',
        '[data-testid="item-description"]',
        '[itemprop="description"]',
      ], 10000)
      || meta('meta[property="og:description"]'),
      10000,
    );
    const contexteTechnique = contexteTechniqueVisible();
    const localisation = localisationApproximate(
      produit?.contentLocation
      || produit?.location
      || offre?.availableAtOrFrom
      || localisationVisibleDansAnnonce()
      || texteSelecteur([
        '[data-qa-id="adview_location_informations"]',
        '[data-testid="item-location"]',
        '[aria-label*="localisation" i]',
      ], 300),
    );
    const datePublication = textePropre(
      produit?.datePublished
      || produit?.datePosted
      || offre?.availabilityStarts
      || meta('meta[property="article:published_time"]'),
      100,
    );
    const caracteristiques = extraireCaracteristiques(
      [titre, description, contexteTechnique].filter(Boolean).join(" "),
    );

    return {
      schema_version: "hunter-companion-1",
      mode_acquisition: "companion_local",
      plateforme: "Leboncoin",
      identifiant: identifiantDepuisUrl(),
      url: location.href,
      titre,
      prix,
      description,
      contexte_technique: contexteTechnique,
      localisation,
      date_publication: datePublication,
      date_detection: new Date().toISOString(),
      images_collectees: false,
      images: [],
      etat_page: "ok",
      motif_controle: null,
      ...caracteristiques,
    };
  }

  globalThis.HunterProviders = globalThis.HunterProviders || [];
  globalThis.HunterProviders.push({
    id: "leboncoin",
    nom: "Leboncoin",
    correspond,
    extraire,
  });
})();
