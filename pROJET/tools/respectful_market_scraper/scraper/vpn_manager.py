"""Verification en lecture seule d'un VPN connecte manuellement.

Ce module ne connecte, ne deconnecte et ne change jamais de serveur. Son seul
role est d'arreter une session lorsque l'operateur a explicitement exige un VPN
manuel mais qu'aucune connexion NordVPN active n'est detectee.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


class VpnManuelRequis(RuntimeError):
    """Le VPN manuel demande n'est pas detecte comme actif."""


@dataclass(frozen=True)
class StatutVpn:
    disponible: bool
    connecte: bool
    fournisseur: str
    detail: str


def _analyser_ipconfig(contenu: str) -> StatutVpn:
    blocs = re.split(r"(?:\r?\n){2,}", contenu)
    blocs_nordvpn = [bloc for bloc in blocs if "nord" in bloc.casefold()]
    if not blocs_nordvpn:
        return StatutVpn(True, False, "NordVPN", "Aucun adaptateur NordVPN detecte.")

    motif_ipv4 = re.compile(
        r"(?:adresse\s+ipv4|ipv4\s+address)[^\r\n]*:\s*"
        r"\d{1,3}(?:\.\d{1,3}){3}",
        re.IGNORECASE,
    )
    if any(motif_ipv4.search(bloc) for bloc in blocs_nordvpn):
        return StatutVpn(True, True, "NordVPN", "Tunnel NordVPN actif.")
    return StatutVpn(True, False, "NordVPN", "Adaptateur present mais sans adresse IPv4.")


def _statut_windows(timeout: float = 8) -> StatutVpn:
    try:
        resultat = subprocess.run(
            ["ipconfig", "/all"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as erreur:
        return StatutVpn(False, False, "NordVPN", type(erreur).__name__)

    if resultat.returncode != 0:
        return StatutVpn(
            False,
            False,
            "NordVPN",
            f"ipconfig a retourne le code {resultat.returncode}.",
        )
    return _analyser_ipconfig(resultat.stdout)


def _statut_linux(timeout: float = 8) -> StatutVpn:
    executable = shutil.which("nordvpn")
    if not executable:
        return StatutVpn(False, False, "NordVPN", "Commande nordvpn absente.")
    try:
        resultat = subprocess.run(
            [executable, "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as erreur:
        return StatutVpn(False, False, "NordVPN", type(erreur).__name__)
    texte = f"{resultat.stdout} {resultat.stderr}".casefold()
    connecte = resultat.returncode == 0 and "connected" in texte and "disconnected" not in texte
    return StatutVpn(True, connecte, "NordVPN", "Connecte." if connecte else "Non connecte.")


def lire_statut_vpn(timeout: float = 8) -> StatutVpn:
    if sys.platform == "win32":
        return _statut_windows(timeout)
    return _statut_linux(timeout)


def exiger_vpn_manuel(timeout: float = 8) -> StatutVpn:
    statut = lire_statut_vpn(timeout)
    if not statut.disponible:
        raise VpnManuelRequis(f"Verification VPN indisponible : {statut.detail}")
    if not statut.connecte:
        raise VpnManuelRequis(
            "Connectez NordVPN manuellement avant la session puis relancez la commande."
        )
    return statut
