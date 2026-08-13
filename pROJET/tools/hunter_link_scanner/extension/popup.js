const INTERRUPTEUR = document.getElementById("companion-enabled");
const BOUTON_ANALYSER = document.getElementById("analyze-current");
const RECEPTEUR_STATUT = document.getElementById("receiver-state");
const STATUT = document.getElementById("status");

function afficher(message, classe = "") {
  STATUT.textContent = message;
  STATUT.className = classe;
}

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

async function initialiser() {
  try {
    const [reglages, recepteur] = await Promise.all([
      envoyer({ type: "HUNTER_COMPANION_GET_SETTINGS" }),
      envoyer({ type: "HUNTER_RECEIVER_STATUS" }),
    ]);
    INTERRUPTEUR.checked = Boolean(reglages?.active);
    RECEPTEUR_STATUT.textContent = recepteur?.disponible
      ? "Moteur Hunter local connecté"
      : "Moteur local arrêté — lancez Lancer-Compagnon-Hunter.cmd";
    RECEPTEUR_STATUT.classList.toggle("connected", Boolean(recepteur?.disponible));
  } catch (erreur) {
    afficher(erreur.message, "erreur");
  }
}

INTERRUPTEUR.addEventListener("change", async () => {
  INTERRUPTEUR.disabled = true;
  try {
    const resultat = await envoyer({
      type: "HUNTER_COMPANION_SET_ENABLED",
      active: INTERRUPTEUR.checked,
    });
    if (!resultat?.ok) throw new Error(resultat?.erreur || "Réglage refusé.");
    afficher(
      resultat.active
        ? "Hunter reconnaîtra les fiches Leboncoin, Marketplace et Vinted visibles."
        : "Analyse automatique désactivée.",
      resultat.active ? "ok" : "attention",
    );
  } catch (erreur) {
    INTERRUPTEUR.checked = !INTERRUPTEUR.checked;
    afficher(erreur.message, "erreur");
  } finally {
    INTERRUPTEUR.disabled = false;
  }
});

BOUTON_ANALYSER.addEventListener("click", async () => {
  BOUTON_ANALYSER.disabled = true;
  afficher("Hunter lance l’analyse dans la page…");
  try {
    const [onglet] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!onglet?.id || !/^https:\/\//i.test(onglet.url || "")) {
      throw new Error("Ouvrez d’abord une fiche annonce publique en HTTPS.");
    }
    const reponse = await envoyer({
      type: "HUNTER_ANALYSER_ONGLET",
      tabId: onglet.id,
      url: onglet.url,
    });
    if (!reponse?.ok) throw new Error(reponse?.erreur || "Analyse impossible.");
    afficher("Le résultat s’affiche directement dans la page.", "ok");
  } catch (erreur) {
    afficher(erreur.message, "erreur");
  } finally {
    BOUTON_ANALYSER.disabled = false;
  }
});

void initialiser();
