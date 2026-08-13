from pathlib import Path
import py_compile
import shutil

root = Path.cwd()
components_path = root / "analyzer" / "components.py"
value_path = root / "analyzer" / "value.py"

if not components_path.exists() or not value_path.exists():
    raise SystemExit(
        "ERREUR : lance ce script depuis la racine de PC Hunter."
    )

components = components_path.read_text(encoding="utf-8")
value = value_path.read_text(encoding="utf-8")

ram_needle = """    motifs = [
        (
            rf"\\b({capacites})\\s*"
            r"(?:go|gb)"
            r"\\s*(ddr[345])?"
            r"(?:\\s*(?:de\\s+)?ram)?\\b"
        ),
        (
            r"\\b(?:ram|memoire(?:\\s+vive)?)"
"""

ram_replacement = """    motifs = [
        (
            rf"\\b({capacites})\\s*"
            r"(?:go|gb)"
            r"\\s*(ddr[345])?"
            r"(?:\\s*(?:de\\s+)?ram)?\\b"
        ),
        (
            # Ex. vendeur : "32 Giga ram ddr5"
            # Après normalisation : "32 go ram ddr5"
            rf"\\b({capacites})\\s*"
            r"(?:go|gb)"
            r"\\s*(?:de\\s+)?ram"
            r"\\s*(ddr[345])?\\b"
        ),
        (
            r"\\b(?:ram|memoire(?:\\s+vive)?)"
"""

gaming_old = """def est_gaming(annonce):
    texte = texte_annonce(
        annonce
    )

    return any(
        mot in texte
        for mot in (
            "gaming",
            "gamer",
            "jeu video",
            "jeux video",
        )
    )
"""

gaming_new = """def est_gaming(annonce):
    texte = texte_annonce(
        annonce
    )

    # Signaux explicites forts.
    if any(
        mot in texte
        for mot in (
            "gaming",
            "gamer",
        )
    ):
        return True

    # Une annonce bureautique peut contenir "jeux vidéo"
    # uniquement pour dire qu'elle n'est PAS adaptée au jeu.
    motifs_negatifs = (
        r"ne\\s+convient\\s+pas.{0,100}jeux?\\s+video",
        r"pas\\s+(?:fait|adapte|concu|destine).{0,80}jeux?\\s+video",
        r"non\\s+(?:adapte|concu|destine).{0,80}jeux?\\s+video",
        r"pas\\s+pour.{0,80}jeux?\\s+video",
    )

    if any(
        re.search(
            motif,
            texte,
            flags=re.IGNORECASE,
        )
        for motif in motifs_negatifs
    ):
        return False

    return any(
        mot in texte
        for mot in (
            "jeu video",
            "jeux video",
        )
    )
"""

if "32 Giga ram ddr5" not in components:
    if ram_needle not in components:
        raise SystemExit(
            "ERREUR : bloc RAM attendu introuvable. Aucun fichier modifié."
        )
    components_new = components.replace(
        ram_needle,
        ram_replacement,
        1,
    )
else:
    components_new = components

if "motifs_negatifs" not in value:
    if gaming_old not in value:
        raise SystemExit(
            "ERREUR : fonction est_gaming attendue introuvable. "
            "Aucun fichier modifié."
        )
    value_new = value.replace(
        gaming_old,
        gaming_new,
        1,
    )
else:
    value_new = value

# Validate before touching the originals.
compile(components_new, str(components_path), "exec")
compile(value_new, str(value_path), "exec")

shutil.copy2(
    components_path,
    components_path.with_suffix(".py.bak_before_ddr5"),
)
shutil.copy2(
    value_path,
    value_path.with_suffix(".py.bak_before_gaming_negation"),
)

components_path.write_text(components_new, encoding="utf-8")
value_path.write_text(value_new, encoding="utf-8")

py_compile.compile(str(components_path), doraise=True)
py_compile.compile(str(value_path), doraise=True)

print("✅ RAM vendeur '32 Giga ram ddr5' prise en charge")
print("✅ Négation 'Ne convient pas ... Jeux vidéos' prise en charge")
print("✅ Syntaxe components.py : OK")
print("✅ Syntaxe value.py : OK")
