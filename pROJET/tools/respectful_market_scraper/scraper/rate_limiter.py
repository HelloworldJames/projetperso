"""Temporisation aleatoire appliquee avant chaque page de contenu."""

from __future__ import annotations

import random
import time


def calculer_delai(
    minimum: float = 3,
    maximum: float = 8,
    delai_robots: float | None = None,
    generateur=random.uniform,
) -> float:
    if minimum < 0 or maximum < minimum:
        raise ValueError("Intervalle de temporisation invalide.")
    delai = float(generateur(minimum, maximum))
    if delai_robots is not None:
        delai = max(delai, float(delai_robots))
    return delai


def wait_human(
    minimum: float = 3,
    maximum: float = 8,
    delai_robots: float | None = None,
) -> float:
    delai = calculer_delai(minimum, maximum, delai_robots)
    time.sleep(delai)
    return delai
