(() => {
  "use strict";

  const DELAI_REESSAI_MS = 650;
  const NOMBRE_ESSAIS = 8;
  let active = false;
  let urlObservee = location.href;
  let urlAnalysee = null;
  let generation = 0;
  let minuteur = null;

  function envoyer(message) {
    return new Promise((resolution, rejet) => {
      chrome.runtime.sendMessage(message, (reponse) => {
        if (chrome.runtime.lastError) {
          rejet(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolution(reponse);
      });
    });
  }

  function fournisseurCourant() {
    return (globalThis.HunterProviders || []).find((provider) =>
      provider.correspond(location.href),
    ) || null;
  }

  function attendre(delai) {
    return new Promise((resolution) => setTimeout(resolution, delai));
  }

  function champsAbsents(capture) {
    const absents = [];
    if (!capture?.titre) absents.push("titre");
    if (capture?.prix === null || capture?.prix === undefined) absents.push("prix");
    if (!capture?.description && !capture?.contexte_technique) absents.push("description/caractéristiques");
    if (!capture?.localisation) absents.push("localisation");
    return absents;
  }

  async function extraireAvecAttente(provider, numeroGeneration) {
    let derniere = null;
    for (let essai = 0; essai < NOMBRE_ESSAIS; essai += 1) {
      if (numeroGeneration !== generation || !provider.correspond(location.href)) return null;
      derniere = provider.extraire();
      if (derniere?.etat_page === "controle") return derniere;
      if (derniere?.titre && derniere?.prix !== null && derniere?.prix !== undefined) {
        return derniere;
      }
      await attendre(DELAI_REESSAI_MS);
    }
    return derniere;
  }

  async function analyserPage({ force = false } = {}) {
    const provider = fournisseurCourant();
    if (!provider) {
      urlAnalysee = null;
      globalThis.HunterOverlay?.retirer();
      return;
    }
    if (!force && (!active || document.visibilityState !== "visible")) return;
    if (!force && urlAnalysee === location.href) return;

    const numeroGeneration = ++generation;
    const urlDebut = location.href;
    globalThis.HunterOverlay?.chargement(
      `Hunter reconnaît la fiche ${provider.nom || provider.id || "occasion"} et lit les champs produit visibles…`,
    );

    try {
      const capture = await extraireAvecAttente(provider, numeroGeneration);
      if (numeroGeneration !== generation || location.href !== urlDebut) return;
      if (!capture) throw new Error("La fiche annonce n’a pas pu être reconnue.");
      if (capture.etat_page === "controle") {
        throw new Error("La plateforme demande une vérification manuelle. Hunter s’arrête ici.");
      }

      const absents = champsAbsents(capture);
      if (!capture.titre || capture.prix === null || capture.prix === undefined) {
        urlAnalysee = location.href;
        globalThis.HunterOverlay?.insuffisant(
          `Analyse impossible : ${absents.join(", ") || "données produit insuffisantes"}.\nHunter n’invente aucune estimation.`,
        );
        return;
      }

      const reponse = await envoyer({
        type: "HUNTER_COMPANION_ANALYZE",
        capture,
      });
      if (!reponse?.ok) throw new Error(reponse?.erreur || "Le moteur Hunter n’a pas répondu.");
      urlAnalysee = location.href;
      globalThis.HunterOverlay?.analyse(capture, reponse.resultat?.analyse);
    } catch (erreur) {
      urlAnalysee = location.href;
      console.warn("[Hunter Companion]", erreur.message);
      const moteurInjoignable = /moteur|récepteur|fetch|http|répondu/i.test(erreur.message);
      globalThis.HunterOverlay?.erreur(
        moteurInjoignable
          ? `${erreur.message}\n\nVérifiez que le récepteur Hunter local est lancé.`
          : erreur.message,
      );
    }
  }

  function planifier() {
    clearTimeout(minuteur);
    minuteur = setTimeout(() => void analyserPage(), 250);
  }

  function verifierNavigation() {
    if (location.href === urlObservee) return;
    urlObservee = location.href;
    urlAnalysee = null;
    generation += 1;
    planifier();
  }

  chrome.runtime.onMessage.addListener((message, _expediteur, repondre) => {
    if (message?.type !== "HUNTER_ANALYZE_CURRENT") return false;
    analyserPage({ force: true })
      .then(() => repondre({ ok: true }))
      .catch((erreur) => repondre({ ok: false, erreur: erreur.message }));
    return true;
  });

  chrome.storage.onChanged.addListener((changements, zone) => {
    if (zone !== "local" || !changements.hunter_companion_enabled) return;
    active = Boolean(changements.hunter_companion_enabled.newValue);
    urlAnalysee = null;
    if (active) planifier();
    else globalThis.HunterOverlay?.retirer();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") planifier();
  });
  new MutationObserver(verifierNavigation).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  setInterval(verifierNavigation, 750);

  chrome.storage.local.get("hunter_companion_enabled", (resultat) => {
    active = Boolean(resultat.hunter_companion_enabled);
    if (active) planifier();
  });
})();
