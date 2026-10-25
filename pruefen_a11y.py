"""Barrierefreiheit, maschinell pruefbare Teile (Issue #1234, WCAG-Befunde W-01..W-13).

Seiten (src/**/*.html):
  - `<meta name="color-scheme">` (W-12), `<main tabindex="-1">` als Ziel des Sprunglinks (W-10)
  - jeder waagerecht rollende Rahmen (`.szene`, `.tabellen-rahmen`) ist fokussierbar und benannt:
    tabindex="0", role="group", aria-label (W-01, WCAG 2.1.1)
  - jeder Logo-Link `a.marke-block` traegt auf allen Seiten denselben Namen (W-09)
  - jedes Pflichtfeld (`required`) steht an einem Label mit "Pflichtfeld" (W-08, WCAG 3.3.2)
Stil und Skript:
  - site.css: overflow-wrap auf Ueberschriften (W-02), color-scheme (W-12), scroll-padding-top (W-03),
    Kopf nur oberhalb einer Mindestbreite sticky (W-04)
  - bildstrecke.js setzt kein role="group" auf <figure> (W-06)
Gibt nur Fundstellen aus.
"""
from __future__ import annotations

import re
from pathlib import Path

from pruefen_angaben import zeile
from pruefen_html import ATTR, attr as _attr, eigene_dateien, ohne_kommentare

_TAG_RE = re.compile(rf"<(\w+)\b({ATTR})>", re.DOTALL)


def _klassen(attrs: str) -> list[str]:
    return (_attr(attrs, "class") or "").split()


def pruefe_a11y_text(roh: str, rel: str) -> tuple[list[str], list[str]]:
    """Befunde und die Namen der Logo-Links einer Seite."""
    funde: list[str] = []
    text = ohne_kommentare(roh)
    if not re.search(r"""<meta\s+name\s*=\s*["']color-scheme["']""", text):
        funde.append(f'{rel} -- <meta name="color-scheme"> fehlt (native Bedienelemente im Dunkelmodus)')
    namen: list[str] = []
    pflicht: list[tuple[str, int]] = []
    for m in _TAG_RE.finditer(text):
        tag, attrs = m.group(1).lower(), m.group(2)
        z = zeile(text, m.start())
        klassen = _klassen(attrs)
        if tag == "main" and _attr(attrs, "tabindex") != "-1":
            funde.append(f'{rel}:{z} -- <main> ohne tabindex="-1" (Sprunglink-Ziel)')
        if set(klassen) & {"szene", "tabellen-rahmen"}:
            ok = (
                _attr(attrs, "tabindex") == "0"
                and _attr(attrs, "role") == "group"
                and (_attr(attrs, "aria-label") or "").strip()
            )
            if not ok:
                funde.append(
                    f'{rel}:{z} -- rollender Rahmen ohne tabindex="0" role="group" aria-label (WCAG 2.1.1)'
                )
        if tag == "a" and "marke-block" in klassen:
            namen.append(_attr(attrs, "aria-label") or "")
        if tag in ("input", "textarea", "select") and _attr(attrs, "required") is not None:
            pflicht.append((_attr(attrs, "id") or "", z))
    for ident, z in pflicht:
        lab = re.search(
            rf"""<label\b[^>]*\bfor\s*=\s*["']{re.escape(ident)}["'][^>]*>(.*?)</label>""", text, re.DOTALL
        )
        if not ident or not lab or "Pflichtfeld" not in lab.group(1):
            funde.append(f'{rel}:{z} -- Pflichtfeld "{ident}": Label nennt "Pflichtfeld" nicht (WCAG 3.3.2)')
    return funde, namen


def pruefe_css_text(css: str, rel: str) -> list[str]:
    funde: list[str] = []
    ohne = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    kopf = re.search(r"(?:^|\})\s*h1\s*,\s*h2[^{]*\{([^}]*)\}", ohne)
    if not kopf or "overflow-wrap" not in kopf.group(1):
        funde.append(f"{rel} -- Ueberschriften ohne overflow-wrap (Querlauf bei 320 px, WCAG 1.4.10)")
    if not re.search(r"color-scheme\s*:\s*light\s+dark", ohne):
        funde.append(f"{rel} -- color-scheme: light dark fehlt")
    if not re.search(r"scroll-padding-top\s*:", ohne):
        funde.append(f"{rel} -- scroll-padding-top fehlt (Anker unter dem klebenden Kopf, WCAG 2.4.11)")
    sticky = re.search(r"\.kopf\s*\{[^}]*position\s*:\s*sticky", ohne)
    schmal = re.search(r"@media[^{]*max-(?:width|height)[^{]*\{\s*\.kopf\s*\{[^}]*position\s*:\s*static", ohne)
    if sticky and not schmal:
        funde.append(f"{rel} -- klebender Kopf ohne static-Rueckfall bei schmalem/niedrigem Fenster (WCAG 1.4.10)")
    return funde


def pruefe_skript_text(js: str, rel: str) -> list[str]:
    if re.search(r"""setAttribute\(\s*['"]role['"]\s*,\s*['"]group['"]""", js):
        return [f'{rel} -- role="group" auf <figure> ist laut ARIA in HTML nicht erlaubt (W-06)']
    return []


def pruefe_a11y(src: Path, wurzel: Path) -> list[str]:
    funde: list[str] = []
    namen: dict[str, str] = {}
    for pfad in eigene_dateien(src, "*.html"):
        rel = pfad.relative_to(wurzel).as_posix()
        f, n = pruefe_a11y_text(pfad.read_text(encoding="utf-8"), rel)
        funde += f
        for name in n:
            namen[rel] = name
    if len(set(namen.values())) > 1:
        funde.append(f"Logo-Link heisst nicht ueberall gleich (WCAG 3.2.4): {sorted(set(namen.values()))}")
    css = src / "assets" / "site.css"
    if css.is_file():
        funde += pruefe_css_text(css.read_text(encoding="utf-8"), css.relative_to(wurzel).as_posix())
    js = src / "assets" / "bildstrecke.js"
    if js.is_file():
        funde += pruefe_skript_text(js.read_text(encoding="utf-8"), js.relative_to(wurzel).as_posix())
    return funde
