const SOURCE_WEB = "hunteria-web";
const SOURCE_COMPAGNON = "hunter-companion";
const ORIGINES_AUTORISEES = new Set([
  "https://hunter-ia-radar.lesaint215.chatgpt.site",
  "http://localhost:3000",
]);

function repondre(type, requestId, payload = null) {
  window.postMessage(
    { source: SOURCE_COMPAGNON, type, requestId, payload },
    window.location.origin,
  );
}

window.addEventListener("message", (evenement) => {
  if (
    evenement.source !== window
    || !ORIGINES_AUTORISEES.has(evenement.origin)
    || evenement.data?.source !== SOURCE_WEB
  ) {
    return;
  }

  const { type, requestId, url, limite } = evenement.data;
  if (type === "HUNTER_COMPANION_PING") {
    repondre("HUNTER_COMPANION_PONG", requestId, { version: "1.0.0" });
    return;
  }

  let commande;
  let typeReponse;
  if (type === "HUNTER_COMPANION_ANALYZE" && typeof url === "string") {
    commande = { type: "HUNTER_ANALYSER_URL", url };
    typeReponse = "HUNTER_COMPANION_RESULT";
  } else if (type === "HUNTER_COMPANION_INBOX") {
    commande = { type: "HUNTER_COMPANION_INBOX", limite };
    typeReponse = "HUNTER_COMPANION_INBOX_RESULT";
  } else {
    return;
  }

  chrome.runtime.sendMessage(
    commande,
    (resultat) => {
      if (chrome.runtime.lastError) {
        repondre(typeReponse, requestId, {
          ok: false,
          erreur: chrome.runtime.lastError.message,
        });
        return;
      }
      repondre(typeReponse, requestId, resultat);
    },
  );
});
