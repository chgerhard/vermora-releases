"""Bilder und Abbildungen (Issue #1234 D1): Alternativtext, feste Groesse, Untertitel, Dateien.

  - jedes <img> hat einen nicht leeren `alt`, `width` und `height` (kein Layoutsprung, WCAG 1.1.1)
  - jedes <figure> enthaelt ein <figcaption> mit Text (ausser Stimmungsfotos `class="foto"`)
  - jede in `src`/`srcset` genannte oertliche Datei existiert

Fremde Adressen prueft `extern` in pruefen.py, nicht dieses Modul. Gibt nur Fundstellen aus.
"""
from __future__ import annotations

import re
from pathlib import Path

from pruefen_angaben import zeile as _zeile
from pruefen_html import ATTR, attr as _attr, eigene_dateien, ohne_kommentare

_IMG_RE = re.compile(rf"<img\b({ATTR})>", re.IGNORECASE | re.DOTALL)
_FIGUR_RE = re.compile(r"<figure\b([^>]*)>(.*?)</figure>", re.IGNORECASE | re.DOTALL)
_CAPTION_RE = re.compile(r"<figcaption\b[^>]*>(.*?)</figcaption>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]*>")
_VIDEO_RE = re.compile(rf"<video\b({ATTR})>(.*?)</video>", re.IGNORECASE | re.DOTALL)
_SOURCE_RE = re.compile(rf"<source\b({ATTR})>", re.IGNORECASE | re.DOTALL)


def _dateien(attrs: str) -> list[str]:
    ziele: list[str] = []
    src = _attr(attrs, "src")
    if src:
        ziele.append(src.strip())
    for teil in (_attr(attrs, "srcset") or "").split(","):
        if teil.strip():
            ziele.append(teil.split()[0])
    return ziele


def pruefe_bilder_text(roh: str, rel: str, basis: Path, src_wurzel: Path) -> list[str]:
    """Befunde fuer den Text einer Seite. `basis` ist der Ordner der Seite."""
    funde: list[str] = []
    text = ohne_kommentare(roh)
    for m in _IMG_RE.finditer(text):
        attrs, z = m.group(1), _zeile(text, m.start())
        if not (_attr(attrs, "alt") or "").strip():
            funde.append(f"{rel}:{z} -- <img> ohne Alternativtext (WCAG 1.1.1)")
        for name in ("width", "height"):
            if not (_attr(attrs, name) or "").strip().isdigit():
                funde.append(f"{rel}:{z} -- <img> ohne {name} (Layoutsprung)")
        for ziel in _dateien(attrs):
            if ziel.startswith(("http:", "https:", "//", "data:")):
                continue  # Fremdes meldet `extern`
            rein = ziel.split("#", 1)[0].split("?", 1)[0]
            wurzel = src_wurzel if rein.startswith("/") else basis
            if not (wurzel / rein.lstrip("/")).is_file():
                funde.append(f"{rel}:{z} -- Bilddatei fehlt: {ziel}")
    for m in _FIGUR_RE.finditer(text):
        if re.search(r"""class\s*=\s*["'][^"']*\bfoto\b""", m.group(1)):
            continue  # Stimmungsfoto (Styleguide 6): Alternativtext traegt es, kein Untertitel
        kap = _CAPTION_RE.search(m.group(2))
        if not kap or not _TAG_RE.sub("", kap.group(1)).strip():
            funde.append(f"{rel}:{_zeile(text, m.start())} -- <figure> ohne <figcaption> mit Text")
    funde += _pruefe_video(text, rel, basis, src_wurzel)
    return funde


def _pruefe_video(text: str, rel: str, basis: Path, src_wurzel: Path) -> list[str]:
    """Kurzvideo (Issue #1234 D2): eigene Steuerung, kein Selbstablauf, feste Groesse, Dateien da."""
    funde: list[str] = []
    for m in _VIDEO_RE.finditer(text):
        attrs, inhalt, z = m.group(1), m.group(2), _zeile(text, m.start())
        if not re.search(r"(?:^|\s)controls(?=[\s=>/]|$)", attrs):
            funde.append(f"{rel}:{z} -- <video> ohne controls (WCAG 2.1.1)")
        if re.search(r"(?:^|\s)autoplay(?=[\s=>/]|$)", attrs):
            funde.append(f"{rel}:{z} -- <video> mit autoplay (WCAG 2.2.2, kein Selbstablauf)")
        for name in ("width", "height"):
            if not (_attr(attrs, name) or "").strip().isdigit():
                funde.append(f"{rel}:{z} -- <video> ohne {name} (Layoutsprung)")
        ziele = [(_attr(attrs, "poster") or "").strip()]
        ziele += [(_attr(s, "src") or "").strip() for s in _SOURCE_RE.findall(inhalt)]
        if not ziele[1:] or not any(ziele[1:]):
            funde.append(f"{rel}:{z} -- <video> ohne <source src>")
        for ziel in ziele:
            if not ziel or ziel.startswith(("http:", "https:", "//", "data:")):
                continue  # Fremdes meldet `extern`
            rein = ziel.split("#", 1)[0].split("?", 1)[0]
            wurzel = src_wurzel if rein.startswith("/") else basis
            if not (wurzel / rein.lstrip("/")).is_file():
                funde.append(f"{rel}:{z} -- Videodatei fehlt: {ziel}")
    return funde


def pruefe_bilder(src: Path, wurzel: Path) -> list[str]:
    funde: list[str] = []
    for pfad in eigene_dateien(src, "*.html"):
        funde += pruefe_bilder_text(
            pfad.read_text(encoding="utf-8"), pfad.relative_to(wurzel).as_posix(), pfad.parent, src
        )
    return funde
