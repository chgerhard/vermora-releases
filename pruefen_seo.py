"""Suchmaschinen-Grundlagen der Seiten (Issue #1234, Freigabe Christian 2026-10-25).

Geprueft wird, was ohne Nachschlagen bei einer Suchmaschine pruefbar ist:

  - keine Seite ausser `404.html` traegt `noindex` (die Seite soll gefunden werden);
  - jede Seite hat `<title>`, die Startseite zusaetzlich Beschreibung, Canonical,
    Open-Graph-Angaben mit vorhandenem Bild und JSON-LD (`SoftwareApplication`, gueltiges JSON,
    ohne Preisangabe); jede Rechtsseite hat einen Canonical;
  - `robots.txt` erlaubt alles und nennt die Sitemap; `sitemap.xml` listet jede Seite
    (ohne 404) unter https://vermora.de/ und nichts, was es nicht gibt.

Die Seiten unter anleitung/ (mkdocs) sind ausgenommen, sie bringen ihre eigene Sitemap mit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree

from pruefen_html import attr as _attr, eigene_dateien, ohne_kommentare

BASIS = "https://vermora.de/"
_META_RE = re.compile(r"<meta\b([^>]*)>", re.IGNORECASE)
_LINK_RE = re.compile(r"<link\b([^>]*)>", re.IGNORECASE)
_LD_RE = re.compile(r'<script\s+type="application/ld\+json">(.*?)</script>', re.DOTALL | re.IGNORECASE)
_NOINDEX_ERLAUBT = ("404.html",)


def _meta(roh: str, key: str, name: str) -> str | None:
    for m in _META_RE.finditer(roh):
        if (_attr(m.group(1), key) or "").lower() == name:
            return _attr(m.group(1), "content")
    return None


def _canonical(roh: str) -> str | None:
    for m in _LINK_RE.finditer(roh):
        if (_attr(m.group(1), "rel") or "").lower() == "canonical":
            return _attr(m.group(1), "href")
    return None


def pruefe_seo(src: Path, wurzel: Path) -> list[str]:
    funde: list[str] = []
    seiten = [p for p in eigene_dateien(src, "*.html")]
    urls: set[str] = set()
    for pfad in seiten:
        rel = pfad.relative_to(src).as_posix()
        roh = ohne_kommentare(pfad.read_text(encoding="utf-8"))
        robots = _meta(roh, "name", "robots") or ""
        if "noindex" in robots.lower() and rel not in _NOINDEX_ERLAUBT:
            funde.append(f"{rel} -- noindex: die Seite soll auffindbar sein (nur 404.html bleibt draussen)")
        if rel in _NOINDEX_ERLAUBT:
            continue
        url = BASIS + ("" if rel == "index.html" else rel)
        urls.add(url)
        if not re.search(r"<title>\s*\S.*?</title>", roh, re.DOTALL):
            funde.append(f"{rel} -- <title> fehlt oder ist leer")
        if _canonical(roh) != url:
            funde.append(f"{rel} -- Canonical fehlt oder weicht ab (erwartet {url})")
        if rel == "index.html":
            funde += _startseite(roh, src)
    funde += _robots_sitemap(src, urls)
    return funde


def _startseite(roh: str, src: Path) -> list[str]:
    funde: list[str] = []
    desc = _meta(roh, "name", "description") or ""
    if not 70 <= len(desc) <= 170:
        funde.append(f"index.html -- meta description {len(desc)} Zeichen, erwartet 70 bis 170")
    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
        if not _meta(roh, "property", prop):
            funde.append(f"index.html -- {prop} fehlt")
    bild = _meta(roh, "property", "og:image") or ""
    if bild.startswith(BASIS) and not (src / bild[len(BASIS):]).is_file():
        funde.append(f"index.html -- og:image zeigt auf fehlende Datei: {bild}")
    elif bild and not bild.startswith(BASIS):
        funde.append("index.html -- og:image muss eine absolute Adresse unter https://vermora.de/ sein")
    if not _meta(roh, "name", "twitter:card"):
        funde.append("index.html -- twitter:card fehlt")
    ld = _LD_RE.search(roh)
    if not ld:
        return funde + ["index.html -- JSON-LD (SoftwareApplication) fehlt"]
    try:
        daten = json.loads(ld.group(1))
    except ValueError:
        return funde + ["index.html -- JSON-LD ist kein gueltiges JSON"]
    if daten.get("@type") != "SoftwareApplication":
        funde.append("index.html -- JSON-LD @type muss SoftwareApplication sein")
    if any(k in daten for k in ("offers", "price", "author", "creator")):
        funde.append("index.html -- JSON-LD ohne Preis- und Personenangaben (Leitplanke 1, Datenschutz)")
    return funde


def _robots_sitemap(src: Path, urls: set[str]) -> list[str]:
    funde: list[str] = []
    robots = src / "robots.txt"
    if not robots.is_file():
        funde.append("robots.txt fehlt")
    else:
        text = robots.read_text(encoding="utf-8")
        if re.search(r"^Disallow:\s*/\s*$", text, re.MULTILINE):
            funde.append("robots.txt sperrt die ganze Seite (Disallow: /)")
        if f"Sitemap: {BASIS}sitemap.xml" not in text:
            funde.append(f"robots.txt nennt {BASIS}sitemap.xml nicht")
    karte = src / "sitemap.xml"
    if not karte.is_file():
        return funde + ["sitemap.xml fehlt"]
    try:
        wurzel = ElementTree.fromstring(karte.read_text(encoding="utf-8"))
    except ElementTree.ParseError:
        return funde + ["sitemap.xml ist kein gueltiges XML"]
    eintraege = {e.text.strip() for e in wurzel.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if e.text}
    for url in sorted(urls - eintraege):
        funde.append(f"sitemap.xml -- Seite fehlt: {url}")
    for url in sorted(eintraege - urls):
        funde.append(f"sitemap.xml -- Eintrag ohne Seite: {url}")
    return funde
