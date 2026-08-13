(() => {
  "use strict";

  const ID_HOTE = "hunter-companion-overlay";
  let hote = null;
  let racine = null;

  function assurer() {
    if (hote?.isConnected && racine) return racine;
    hote = document.createElement("div");
    hote.id = ID_HOTE;
    hote.style.all = "initial";
    hote.style.position = "fixed";
    hote.style.top = "18px";
    hote.style.right = "18px";
    hote.style.zIndex = "2147483647";
    racine = hote.attachShadow({ mode: "closed" });
    racine.innerHTML = `
      <style>
        :host { all: initial; }
        .hunter { width: 330px; overflow: hidden; color: #f5f3eb; border: 1px solid rgba(230,183,94,.35); border-radius: 14px; background: #0b0f0d; box-shadow: 0 18px 55px rgba(0,0,0,.42); font: 13px/1.45 Inter, ui-sans-serif, system-ui, sans-serif; }
        .head { display: flex; align-items: center; gap: 10px; padding: 13px 14px; border-bottom: 1px solid rgba(255,255,255,.08); background: linear-gradient(135deg, rgba(40,83,65,.44), rgba(11,15,13,.95)); }
        .mark { width: 31px; height: 31px; display: grid; place-items: center; border: 1px solid #d6a64f; border-radius: 9px; color: #efc56f; font-weight: 900; }
        .identity { flex: 1; min-width: 0; }
        .identity strong { display: block; color: #fff; font-size: 13px; letter-spacing: .04em; }
        .identity span { color: #8e9992; font-size: 10px; }
        button { border: 0; color: #89938d; background: transparent; cursor: pointer; font: 18px/1 system-ui; }
        .body { padding: 14px; }
        .verdict { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
        .score { color: #efc56f; font-size: 25px; font-weight: 850; }
        .decision { color: #8fe0b8; font-size: 12px; font-weight: 750; text-align: right; }
        .decision.warning { color: #e6c783; }
        .decision.error { color: #ef9c9c; }
        .grid { display: grid; grid-template-columns: 1fr auto; gap: 6px 12px; padding: 10px 0; border-top: 1px solid rgba(255,255,255,.07); border-bottom: 1px solid rgba(255,255,255,.07); }
        .grid span { color: #8d9791; }
        .grid b { color: #f0f1ed; font-weight: 720; text-align: right; }
        .section { margin-top: 11px; }
        .section strong { color: #bac2bc; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
        ul { margin: 6px 0 0; padding-left: 18px; color: #c6ccc8; }
        li { margin: 3px 0; }
        .message { color: #c8ceca; white-space: pre-wrap; }
        .action { margin-top: 11px; padding: 9px 10px; border-radius: 8px; color: #e8c98d; background: rgba(230,183,94,.08); }
        .privacy { margin-top: 10px; color: #626c66; font-size: 9px; }
      </style>
      <section class="hunter" role="status" aria-live="polite">
        <div class="head">
          <div class="mark">H</div>
          <div class="identity"><strong>HUNTER COMPANION</strong><span>Analyse locale de cette annonce</span></div>
          <button id="close" type="button" aria-label="Fermer">×</button>
        </div>
        <div class="body" id="body"></div>
      </section>
    `;
    racine.getElementById("close").addEventListener("click", retirer);
    (document.documentElement || document.body).appendChild(hote);
    return racine;
  }

  function retirer() {
    hote?.remove();
    hote = null;
    racine = null;
  }

  function corps() {
    return assurer().getElementById("body");
  }

  function ajouterTexte(parent, classe, texte) {
    const element = document.createElement("div");
    element.className = classe;
    element.textContent = texte;
    parent.appendChild(element);
    return element;
  }

  function afficherMessage(message, type = "loading") {
    const zone = corps();
    zone.replaceChildren();
    const verdict = document.createElement("div");
    verdict.className = "verdict";
    ajouterTexte(verdict, "score", "HUNTER");
    const classe = type === "error" ? "error" : "warning";
    const libelle = {
      error: "Analyse impossible",
      insufficient: "Informations insuffisantes",
      loading: "Analyse en cours",
    }[type] || "Analyse en cours";
    ajouterTexte(verdict, `decision ${classe}`, libelle);
    zone.appendChild(verdict);
    ajouterTexte(zone, "message", message);
    ajouterTexte(zone, "privacy", "Aucun cookie, compte, message privé ou historique n’est lu.");
  }

  function euro(valeur) {
    return valeur === null || valeur === undefined
      ? "—"
      : `${Math.round(Number(valeur)).toLocaleString("fr-FR")} €`;
  }

  function confiance(estimation) {
    const score = Number(estimation?.confiance_score || 0);
    if (score >= 70) return "Élevée";
    if (score >= 40) return "Moyenne";
    return "Faible";
  }

  function libelleDecision(decision) {
    return {
      PEPITE: "🟢 Pépite",
      BONNE_AFFAIRE: "🟢 Bonne opportunité",
      INTERESSANTE: "🟢 Intéressante",
      A_NEGOCIER: "🟠 À négocier",
      A_ECARTER: "🔴 À écarter",
      INFORMATIONS_INSUFFISANTES: "⚠️ Informations insuffisantes",
      HORS_CIBLE: "⚠️ Hors cible Hunter",
    }[decision] || "⚠️ Analyse limitée";
  }

  function afficherAnalyse(capture, analyse) {
    if (!analyse || analyse.decision === "INFORMATIONS_INSUFFISANTES") {
      const raisons = analyse?.raisons?.join("\n• ") || "Des caractéristiques essentielles manquent.";
      afficherMessage(`Hunter refuse d’inventer une estimation.\n\n• ${raisons}`, "insufficient");
      return;
    }

    const zone = corps();
    zone.replaceChildren();
    const verdict = document.createElement("div");
    verdict.className = "verdict";
    ajouterTexte(verdict, "score", `${analyse.score_affaire ?? 0}/100`);
    const classe = ["A_ECARTER", "HORS_CIBLE"].includes(analyse.decision)
      ? "error"
      : analyse.decision === "A_NEGOCIER" ? "warning" : "";
    ajouterTexte(verdict, `decision ${classe}`, libelleDecision(analyse.decision));
    zone.appendChild(verdict);

    const grille = document.createElement("div");
    grille.className = "grid";
    const lignes = [
      ["Prix demandé", euro(capture.prix)],
      ["Valeur estimée", euro(analyse.estimation?.valeur_probable)],
      ["Marge prudente", euro(analyse.marge_nette_prudente)],
      ["Confiance", confiance(analyse.estimation)],
      ["Prix maximum conseillé", euro(analyse.prix_achat_max)],
    ];
    lignes.forEach(([libelle, valeur]) => {
      const etiquette = document.createElement("span");
      etiquette.textContent = libelle;
      const resultat = document.createElement("b");
      resultat.textContent = valeur;
      grille.append(etiquette, resultat);
    });
    zone.appendChild(grille);

    const raisons = Array.isArray(analyse.raisons) ? analyse.raisons.slice(0, 5) : [];
    if (raisons.length) {
      const section = document.createElement("div");
      section.className = "section";
      section.appendChild(Object.assign(document.createElement("strong"), { textContent: "Points à retenir" }));
      const liste = document.createElement("ul");
      raisons.forEach((raison) => liste.appendChild(
        Object.assign(document.createElement("li"), { textContent: String(raison) }),
      ));
      section.appendChild(liste);
      zone.appendChild(section);
    }
    if (analyse.action_recommandee) ajouterTexte(zone, "action", analyse.action_recommandee);
    ajouterTexte(zone, "privacy", "Analyse de la fiche courante uniquement · aucune donnée de compte collectée.");
  }

  globalThis.HunterOverlay = {
    retirer,
    chargement: (message = "Lecture des informations visibles…") => afficherMessage(message),
    erreur: (message) => afficherMessage(message, "error"),
    insuffisant: (message) => afficherMessage(message, "insufficient"),
    analyse: afficherAnalyse,
  };
})();
