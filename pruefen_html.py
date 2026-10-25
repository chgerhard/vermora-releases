"""Gemeinsame HTML-Bausteine der Pruefmodule (einzige Kopie, Paragraph 16).

pruefen.py, pruefen_a11y.py und pruefen_bilder.py lesen Kommentare und Attribute ueber diese
Funktionen statt je einer eigenen Kopie. Zeilennummern: `pruefen_angaben.zeile`.
"""
from __future__ import annotations

import re
from pathlib import Path

# Eigene Baeume mit eigenem Bau und eigenen Regeln (Issue #1234): die Installationsanleitung
# (mkdocs, Portfolio-Repo, Guards test_issue589_*/test_issue925_*) liegt im ausgelieferten Ordner
# unter anleitung/, folgt aber nicht den Regeln der Handseiten (Farbwerte, Schriften, Alt-Texte ...).
FREMDE_BAUTEN = ("anleitung",)

KOMMENTAR_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Attributteil eines Tags: alles bis '>' ausser in Anfuehrungszeichen (gierig)
ATTR = r"""(?:[^>"']|"[^"]*"|'[^']*')*"""


def eigene_dateien(src: Path, muster: str = "*") -> list[Path]:
    """Dateien unter `src` ohne die fremden Baeume (`FREMDE_BAUTEN`), sortiert."""
    return sorted(
        p for p in src.rglob(muster)
        if p.is_file() and p.relative_to(src).parts[0] not in FREMDE_BAUTEN
    )


def ohne_kommentare(roh: str) -> str:
    """Kommentare durch gleich viele Zeilenumbrueche ersetzen, damit Zeilennummern stimmen."""
    return KOMMENTAR_RE.sub(lambda m: "\n" * m.group(0).count("\n"), roh)


def attr(attrs: str, name: str) -> str | None:
    """Wert eines Attributs, "" fuer ein Attribut ohne Wert, None wenn es fehlt."""
    m = re.search(
        rf"""(?<![\w-]){name}(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?(?=[\s/>]|$)""",
        attrs,
        re.IGNORECASE,
    )
    if not m:
        return None
    return next((g for g in m.groups() if g is not None), "")
