const RECEPTEUR = "http://127.0.0.1:8765/import";
const SANTE_RECEPTEUR = "http://127.0.0.1:8765/health";
const RESULTATS_RECENTS = "http://127.0.0.1:8765/recent";
const CLE_ACTIVATION = "hunter_companion_enabled";
const CLE_ERREURS = "hunter_companion_errors";
const LIMITE_ERREURS = 30;

const CHAMPS_CAPTURE_AUTORISES = [
  "schema_version",
  "mode_acquisition",
  "plateforme",
  "identifiant",
  "url",
  "titre",
  "prix",
  "description",
  "contexte_technique",
  "localisation",
  "date_publication",
  "date_detection",
  "etat",
  "marque",
  "annee",
  "ram_go",
  "stockage_go",
  "garantie_jusqu_au",
];

function urlPubliqueAcceptee(valeur) {
  try {
    const url = new URL(valeur);
    const hote = url.hostname.toLowerCase();
    const hotePrive = hote === "localhost"
      || hote === "127.0.0.1"
      || hote === "::1"
      || /^10\./.test(hote)
      || /^192\.168\./.test(hote)
      || /^172\.(?:1[6-9]|2\d|3[01])\./.test(hote);
    return url.protocol === "https:"
      && Boolean(hote)
      && !url.username
      && !url.password
      && !hotePrive;
  } catch {
    return false;
  }
}

function plateformeDepuisUrl(valeur) {
  const url = new URL(valeur);
  const hote = url.hostname.toLowerCase();
  if (hote === "leboncoin.fr" || hote.endsWith(".leboncoin.fr")) return "Leboncoin";
  if (hote === "facebook.com" || hote.endsWith(".facebook.com")) return "Facebook Marketplace";
  if (hote === "vinted.fr" || hote.endsWith(".vinted.fr")) return "Vinted";
  return hote.replace(/^www\./, "");
}

function analyseAutomatiqueSupportee(valeur) {
  const url = new URL(valeur);
  const hote = url.hostname.toLowerCase();
  return (
    ((hote === "leboncoin.fr" || hote.endsWith(".leboncoin.fr"))
      && /^\/ad\/[^/]+\/\d+(?:\/|$)/i.test(url.pathname))
    || ((hote === "facebook.com" || hote.endsWith(".facebook.com"))
      && /^\/marketplace\/item\/\d+(?:\/|$)/i.test(url.pathname))
    || ((hote === "vinted.fr" || hote.endsWith(".vinted.fr"))
      && /^\/items\/\d+(?:[-/]|$)/i.test(url.pathname))
  );
}

function nettoyerTexte(valeur, limite) {
  if (valeur === null || valeur === undefined) return null;
  const texte = String(valeur)
    .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, "[coordonnée retirée]")
    .replace(/(?<!\d)(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)/g, "[coordonnée retirée]")
    .replace(/\s+/g, " ")
    .trim();
  return texte ? texte.slice(0, limite) : null;
}

function filtrerCapture(capture) {
  if (!capture || typeof capture !== "object") {
    throw new Error("La capture Hunter est invalide.");
  }
  if (!urlPubliqueAcceptee(capture.url)) {
    throw new Error("Hunter Companion accepte uniquement une fiche publique HTTPS.");
  }

  const resultat = {};
  for (const champ of CHAMPS_CAPTURE_AUTORISES) {
    if (Object.hasOwn(capture, champ)) resultat[champ] = capture[champ];
  }
  resultat.plateforme = nettoyerTexte(resultat.plateforme, 100)
    || plateformeDepuisUrl(resultat.url);
  resultat.mode_acquisition = "companion_local";
  resultat.titre = nettoyerTexte(resultat.titre, 500);
  resultat.description = nettoyerTexte(resultat.description, 10000);
  resultat.contexte_technique = nettoyerTexte(resultat.contexte_technique, 15000);
  resultat.localisation = nettoyerTexte(resultat.localisation, 300);
  resultat.date_publication = nettoyerTexte(resultat.date_publication, 100);
  return resultat;
}

function contexteErreur(url) {
  try {
    const valeur = new URL(url);
    return `${valeur.hostname}${valeur.pathname}`.slice(0, 220);
  } catch {
    return "page-inconnue";
  }
}

async function journaliserErreur(type, erreur, url = null) {
  const stockage = await chrome.storage.local.get(CLE_ERREURS);
  const journal = Array.isArray(stockage[CLE_ERREURS])
    ? stockage[CLE_ERREURS]
    : [];
  const entree = {
    date: new Date().toISOString(),
    type: String(type || "erreur").slice(0, 80),
    message: nettoyerTexte(erreur?.message || erreur, 300),
    page: contexteErreur(url),
  };
  await chrome.storage.local.set({
    [CLE_ERREURS]: [entree, ...journal].slice(0, LIMITE_ERREURS),
  });
}

async function recepteurDisponible() {
  const controleur = new AbortController();
  const minuteur = setTimeout(() => controleur.abort(), 1500);
  try {
    const reponse = await fetch(SANTE_RECEPTEUR, { signal: controleur.signal });
    return reponse.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(minuteur);
  }
}

async function lireResultatsRecents(limite = 50) {
  const valeurLimite = Math.max(1, Math.min(Number(limite) || 50, 100));
  const controleur = new AbortController();
  const minuteur = setTimeout(() => controleur.abort(), 2500);
  try {
    const reponse = await fetch(`${RESULTATS_RECENTS}?limit=${valeurLimite}`, {
      signal: controleur.signal,
    });
    const resultat = await reponse.json();
    if (!reponse.ok || !resultat.ok) {
      throw new Error(resultat.erreur || `Synchronisation refusee (HTTP ${reponse.status}).`);
    }
    return resultat;
  } catch (erreur) {
    await journaliserErreur("inbox", erreur);
    throw erreur;
  } finally {
    clearTimeout(minuteur);
  }
}

async function envoyerAuMoteur(captureBrute) {
  const capture = filtrerCapture(captureBrute);
  try {
    const reponse = await fetch(RECEPTEUR, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(capture),
    });
    let resultat;
    try {
      resultat = await reponse.json();
    } catch {
      throw new Error(`Réponse Hunter illisible (HTTP ${reponse.status}).`);
    }
    if (!reponse.ok || !resultat.ok) {
      throw new Error(resultat.erreur || `Import refusé (HTTP ${reponse.status}).`);
    }
    return { ok: true, capture, resultat };
  } catch (erreur) {
    await journaliserErreur("backend", erreur, capture.url);
    throw erreur;
  }
}

async function lireReglages() {
  const stockage = await chrome.storage.local.get(CLE_ACTIVATION);
  return { ok: true, active: Boolean(stockage[CLE_ACTIVATION]) };
}

async function definirActivation(active) {
  const valeur = Boolean(active);
  await chrome.storage.local.set({ [CLE_ACTIVATION]: valeur });
  return { ok: true, active: valeur };
}

async function analyserOngletGenerique(tabId, url) {
  if (!urlPubliqueAcceptee(url)) {
    throw new Error("Ouvrez une fiche annonce publique en HTTPS.");
  }

  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["providers/common.js", "providers/generic.js", "overlay.js"],
  });
  const executions = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => globalThis.HunterGenericProvider?.extraire() ?? null,
  });
  const capture = executions?.[0]?.result;
  if (!capture) throw new Error("Cette page ne ressemble pas à une fiche annonce exploitable.");

  const reponse = await envoyerAuMoteur(capture);
  await chrome.scripting.executeScript({
    target: { tabId },
    args: [reponse.capture, reponse.resultat?.analyse, reponse.resultat?.champs_manquants || []],
    func: (captureNettoyee, analyse, champsManquants) => {
      if (!captureNettoyee?.titre || captureNettoyee?.prix === null || captureNettoyee?.prix === undefined) {
        globalThis.HunterOverlay?.insuffisant(
          `Analyse incomplète : ${champsManquants.join(", ") || "titre ou prix absent"}.`,
        );
        return;
      }
      globalThis.HunterOverlay?.analyse(captureNettoyee, analyse);
    },
  });
  return { ...reponse, mode: "generique" };
}

async function analyserOnglet(tabId, url) {
  if (!Number.isInteger(tabId)) throw new Error("Onglet Hunter invalide.");
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "HUNTER_ANALYZE_CURRENT" });
  } catch (erreur) {
    await journaliserErreur("onglet-generique", erreur, url);
    return analyserOngletGenerique(tabId, url);
  }
}

async function ouvrirAnnonce(url) {
  if (!urlPubliqueAcceptee(url)) {
    throw new Error("Seules les fiches publiques HTTPS sont prises en charge.");
  }
  const automatique = analyseAutomatiqueSupportee(url);
  await chrome.tabs.create({ url, active: true });
  return {
    ok: true,
    mode: "ouverture",
    action_requise: !automatique,
    resultat: {
      statut: automatique ? "analyse_dans_la_page" : "action_requise",
      avertissement: automatique
        ? null
        : "Cliquez sur Analyser cette annonce dans Companion après le chargement.",
    },
  };
}

chrome.runtime.onMessage.addListener((message, _expediteur, repondre) => {
  let action;
  if (message?.type === "HUNTER_COMPANION_ANALYZE") {
    action = envoyerAuMoteur(message.capture);
  } else if (message?.type === "HUNTER_COMPANION_GET_SETTINGS") {
    action = lireReglages();
  } else if (message?.type === "HUNTER_COMPANION_SET_ENABLED") {
    action = definirActivation(message.active);
  } else if (message?.type === "HUNTER_RECEIVER_STATUS") {
    action = recepteurDisponible().then((disponible) => ({ ok: true, disponible }));
  } else if (message?.type === "HUNTER_COMPANION_INBOX") {
    action = lireResultatsRecents(message.limite);
  } else if (message?.type === "HUNTER_ANALYSER_ONGLET") {
    action = analyserOnglet(message.tabId, message.url);
  } else if (message?.type === "HUNTER_ANALYSER_URL") {
    action = ouvrirAnnonce(message.url);
  } else if (message?.type === "HUNTER_COMPANION_GET_ERRORS") {
    action = chrome.storage.local.get(CLE_ERREURS).then((stockage) => ({
      ok: true,
      erreurs: Array.isArray(stockage[CLE_ERREURS]) ? stockage[CLE_ERREURS] : [],
    }));
  } else {
    action = Promise.reject(new Error("Commande Hunter inconnue."));
  }

  action
    .then((resultat) => repondre(resultat))
    .catch((erreur) => repondre({ ok: false, erreur: erreur.message }));
  return true;
});

chrome.runtime.onInstalled.addListener(async () => {
  const stockage = await chrome.storage.local.get(CLE_ACTIVATION);
  if (!Object.hasOwn(stockage, CLE_ACTIVATION)) {
    await chrome.storage.local.set({ [CLE_ACTIVATION]: false });
  }
});
