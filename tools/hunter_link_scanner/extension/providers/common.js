(() => {
  "use strict";

  if (globalThis.HunterProviderUtils) return;

  const COORDONNEE_EMAIL = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g;
  const COORDONNEE_TELEPHONE = /(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)/g;
  const SELECTEURS_SENSIBLES = [
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
    '[href*="/member/"]',
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

  function meta(selecteur) {
    return textePropre(document.querySelector(selecteur)?.content);
  }

  function elementAutorise(element) {
    return Boolean(element) && !element.closest(SELECTEURS_SENSIBLES.join(","));
  }

  function texteSelecteur(selecteurs, limite = 10000) {
    for (const selecteur of selecteurs || []) {
      const element = document.querySelector(selecteur);
      if (!elementAutorise(element)) continue;
      const valeur = nettoyerCoordonnees(
        element.innerText || element.textContent || element.content,
        limite,
      );
      if (valeur) return valeur;
    }
    return null;
  }

  function convertirPrix(valeur) {
    if (typeof valeur === "number" && Number.isFinite(valeur)) return valeur;
    const texte = textePropre(valeur, 160);
    if (!texte) return null;
    const resultat = texte.match(
      /(\d{1,3}(?:[ .\u00a0]\d{3})*|\d+)(?:[,.](\d{1,2}))?\s*(?:€|EUR)/i,
    ) || texte.match(/^(\d+(?:[,.]\d{1,2})?)$/);
    if (!resultat) return null;
    const nombre = Number(
      `${resultat[1].replace(/[ .\u00a0]/g, "")}${resultat[2] ? `.${resultat[2]}` : ""}`,
    );
    return Number.isFinite(nombre) && nombre > 0 ? nombre : null;
  }

  function premierPrix(selecteurs) {
    for (const selecteur of selecteurs || []) {
      for (const element of document.querySelectorAll(selecteur)) {
        if (!elementAutorise(element)) continue;
        const prix = convertirPrix(element.content || element.innerText || element.textContent);
        if (prix !== null) return prix;
      }
    }
    return null;
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
    Object.values(valeur).forEach((enfant) => parcourirJson(enfant, resultat, profondeur + 1));
  }

  function objetsJsonLd() {
    const resultat = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach((script) => {
      try {
        parcourirJson(JSON.parse(script.textContent), resultat);
      } catch {
        // Une donnée structurée invalide ne bloque pas les champs visibles.
      }
    });
    return resultat;
  }

  function donneesStructurees() {
    const objets = objetsJsonLd();
    const produit = objets.find((objet) =>
      /Product|Vehicle|IndividualProduct/i.test(String(objet["@type"] || "")),
    );
    const offreProduit = Array.isArray(produit?.offers) ? produit.offers[0] : produit?.offers;
    const offre = offreProduit || objets.find((objet) =>
      /Offer/i.test(String(objet["@type"] || "")),
    );
    return { produit, offre };
  }

  function normaliserTitre(valeur, plateforme) {
    const titre = textePropre(valeur, 500);
    if (!titre) return null;
    const suffixe = plateforme
      ? new RegExp(`\\s*[|·-]\\s*${plateforme.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*$`, "i")
      : null;
    const nettoye = titre
      .replace(/^Image\s*:\s*/i, "")
      .replace(suffixe || /$^/, "")
      .trim();
    return nettoye || null;
  }

  function localisationApproximate(valeur) {
    if (!valeur) return null;
    if (typeof valeur === "object") {
      const adresse = valeur.address && typeof valeur.address === "object"
        ? valeur.address
        : valeur;
      const ville = textePropre(adresse.addressLocality || adresse.city, 150);
      const code = textePropre(adresse.postalCode || adresse.zipcode, 10);
      return ville ? `${ville}${code ? ` ${code}` : ""}` : null;
    }
    return nettoyerCoordonnees(valeur, 300);
  }

  function contexteTechnique(selecteurs) {
    const sections = [];
    document.querySelectorAll((selecteurs || []).join(",")).forEach((element) => {
      if (!elementAutorise(element)) return;
      const copie = element.cloneNode(true);
      copie.querySelectorAll([
        ...SELECTEURS_SENSIBLES,
        "script", "style", "form", "button", "input", "textarea",
      ].join(",")).forEach((enfant) => enfant.remove());
      const texte = nettoyerCoordonnees(copie.innerText || copie.textContent, 6000);
      if (texte) sections.push(texte);
    });
    return textePropre([...new Set(sections)].join(" · "), 15000);
  }

  function detecterControle() {
    const texte = `${document.title} ${document.body?.innerText || ""}`
      .slice(0, 50000)
      .toLocaleLowerCase("fr");
    return [
      "captcha",
      "verify you are human",
      "vérifiez que vous êtes humain",
      "activité inhabituelle",
      "security check",
      "access denied",
    ].find((motif) => texte.includes(motif)) || null;
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
    const marque = /\b(?:macbook|imac|apple)\b/i.test(contenu)
      ? "Apple"
      : contenu.match(/\b(Lenovo|Dell|ASUS|Acer|HP|MSI)\b/i)?.[1] ?? null;
    return {
      etat,
      marque,
      annee: annee ? Number(annee) : null,
      ram_go: ram ? Number(ram) : null,
      stockage_go: stockage ? Number(stockage) : null,
    };
  }

  function creerCapture(options) {
    const controle = detecterControle();
    if (controle) {
      return {
        plateforme: options.plateforme,
        identifiant: options.identifiant(),
        url: location.href,
        etat_page: "controle",
        motif_controle: controle,
      };
    }

    const { produit, offre } = donneesStructurees();
    const titre = normaliserTitre(
      produit?.name
      || texteSelecteur(options.titreSelecteurs, 500)
      || meta('meta[property="og:title"]')
      || document.title,
      options.plateforme,
    );
    const prix = convertirPrix(
      offre?.price
      || produit?.price
      || meta('meta[property="product:price:amount"]'),
    ) ?? premierPrix(options.prixSelecteurs);
    const description = nettoyerCoordonnees(
      produit?.description
      || texteSelecteur(options.descriptionSelecteurs, 10000)
      || meta('meta[property="og:description"]')
      || meta('meta[name="description"]'),
      10000,
    );
    const contexte = contexteTechnique(options.contexteSelecteurs);
    const localisation = localisationApproximate(
      produit?.contentLocation
      || produit?.location
      || offre?.availableAtOrFrom
      || texteSelecteur(options.localisationSelecteurs, 300),
    );
    const datePublication = textePropre(
      produit?.datePublished
      || produit?.datePosted
      || offre?.availabilityStarts
      || meta('meta[property="article:published_time"]'),
      100,
    );

    return {
      schema_version: "hunter-companion-1",
      mode_acquisition: "companion_local",
      plateforme: options.plateforme,
      identifiant: options.identifiant(),
      url: location.href,
      titre,
      prix,
      description,
      contexte_technique: contexte,
      localisation,
      date_publication: datePublication,
      date_detection: new Date().toISOString(),
      images_collectees: false,
      images: [],
      etat_page: "ok",
      motif_controle: null,
      ...extraireCaracteristiques([titre, description, contexte].filter(Boolean).join(" ")),
    };
  }

  function enregistrerProvider(provider) {
    globalThis.HunterProviders = globalThis.HunterProviders || [];
    if (!globalThis.HunterProviders.some((element) => element.id === provider.id)) {
      globalThis.HunterProviders.push(provider);
    }
  }

  globalThis.HunterProviderUtils = {
    creerCapture,
    enregistrerProvider,
    textePropre,
  };
})();
