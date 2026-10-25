"""Guards fuer die Website vermora.de (Issue #612, Umsetzungsplan vom 20.09.2026).

Zwoelf Pruefungen, jede einzeln waehlbar ueber `--nur <name>`:

  digest    Fingerabdruck der aus dem Produkt-Repo erzeugten Dateien gegen ihren Inhalt.
            Quelle ist `src/assets/sync-stand.json`, geschrieben von `styleguide_sync.ps1`
            im Produkt-Repo (Issue #613). Fehlt die Datei, wird die Pruefung mit Hinweis
            uebersprungen -- #613 ist noch nicht gebaut.
  wortliste Treffer der Wortliste aus der Beratungsabgrenzung (Issue #881 Welle 1) im
            Seitentext. Quelle ist `src/assets/wortliste.json`, ebenfalls aus #613.
            Ratsche: `known_hits.json` -- bestehende Treffer sind geduldet, die Liste darf
            nur schrumpfen. Fehlt die Wortliste, wird uebersprungen.
  hinweis   Der zentrale Haftungssatz steht woertlich so auf der Seite wie in der
            Anwendung. Quelle ist `src/assets/hinweistexte.json` (Issue #615).
  preis     Harte Regel aus dem Fahrplan (Leitplanke 1, K1 / Konzept 11.3): Auf der Seite
            steht keine Zahl mit Waehrung, kein "ab X" und keine Zeitangabe je Zeitraum,
            solange der Pilotbetrieb nicht gelaufen ist. Preisaussagen sind ueberall rot;
            ein sonstiger Geldbetrag ist nur in einem als Beispielansicht gekennzeichneten
            Block erlaubt (`data-beispiel`, Leitplanke 3).
  hexwerte  Farbwerte stehen ausschliesslich in der erzeugten `tokens.css` -- eine zweite
            Palette driftet (K22).
  zeichen   Jede Seite traegt das Markenzeichen, und zwar als Platzhalter `<!--zeichen-->`;
            die Geometrie wird nie von Hand kopiert (Quelle: docs/MARKENZEICHEN.md).
  recht     Die drei Pflichtseiten (Impressum, Datenschutz, Nutzungsbedingungen) liegen unter
            `src/recht/` und tragen keine Entwurfs- oder Klammer-Marke mehr (Freigabe 2026-10-24).
  verweise  Jeder Verweis auf eine oertliche Datei muss existieren (auch das Formularziel).
  verkauf   Kein Verkaufs- und Lizenzwortschatz auf der Seite: Vermora wird verschenkt, nicht
            verkauft (Issue #1234, #1236). Schriftlizenz-Woerter bleiben erlaubt.
  extern    Keine Einbettung von fremden Servern (Skript, Bild, Quelle, Frame, Stylesheet,
            Formularziel): macht den Kopfkommentar "keine externen Aufrufe (K23)" wahr.
  sicherheit  `.well-known/security.txt` besteht, hat Contact und genau ein Expires (RFC 9116).
  bilder    Jedes <img> hat Alternativtext, width und height, jede <figure> ein <figcaption> mit
            Text, jede genannte Bilddatei existiert (Issue #1234 D1, Modul `pruefen_bilder.py`).
  a11y      Rollende Rahmen fokussierbar, color-scheme, main tabindex -1, Pflichtfeld-Label, gleicher
            Logo-Link-Name, overflow-wrap/scroll-padding/Kopf-Rueckfall in site.css (WCAG-Befunde
            W-01..W-13, Modul `pruefen_a11y.py`).
  angaben   Marken `[PLATZHALTER-KEY: Hinweis]` in `src/` und Schluessel in
            `angaben.beispiel.ini` [angaben] passen zusammen, die Vorlage ist leer
            (Issue #1234/#1244, Modul `pruefen_angaben.py`).

Zusaetzlich `--veroeffentlichung`: Sperre fuer den spaeteren Live-Gang -- jede Marke braucht einen gueltigen Wert in der echten
angaben.ini (`--angaben PFAD`, Standard `../vermora-geheim/angaben.ini` neben dem Repo); und `security.txt` muss ein
Ablaufdatum in der Zukunft (hoechstens 366 Tage) tragen, `.nojekyll` und `404.html` muessen
vorhanden sein (GitHub Pages, Issue #1234).

`--dist PFAD`: Die Pruefungen laufen auf dem gebauten Ordner statt auf `src/` (Veroeffentlichungs-
weg: dort sind die Marken schon eingesetzt). Nur Quellpruefungen (digest, wortliste, hinweis,
zeichen, angaben) entfallen -- sie brauchen Dateien, die der Bau nicht ausliefert.

Gescannt wird ausschliesslich `src/`. `entwurf/` ist Arbeitsmaterial (Entwuerfe, Prompts)
und geht nicht auf die Seite -- dort gelten die Regeln bewusst nicht.

Aufruf:
    python pruefen.py                      # alle Pruefungen
    python pruefen.py --nur preis           # nur eine
    python pruefen.py --schreibe-ratsche    # known_hits.json neu schreiben
    python pruefen.py --veroeffentlichung --angaben PFAD   # Live-Sperre mit echter ini
    python pruefen.py --dist dist --veroeffentlichung      # auf dem gebauten Ordner
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pruefen_angaben import ABLAUF_MARKE_RE, ANGABE_RE, pruefe_angaben, veroeffentlichung_angaben, vorschau_fusszeile
from pruefen_angaben import SICHERHEIT_MAX_TAGE as _SICHERHEIT_MAX_TAGE
from pruefen_angaben import zeile as _zeile
from pruefen_a11y import pruefe_a11y
from pruefen_bilder import pruefe_bilder
from pruefen_seo import pruefe_seo
from pruefen_html import KOMMENTAR_RE as _KOMMENTAR_RE
from pruefen_html import FREMDE_BAUTEN, eigene_dateien

REPO = Path(__file__).resolve().parent  # Dateien des Repos (Ratsche, RECHT-STATUS, Vorlage)
WURZEL = REPO  # Bezug fuer angezeigte Pfade; mit --dist der gebaute Ordner
SRC = WURZEL / "src"
SYNC_STAND = SRC / "assets" / "sync-stand.json"
WORTLISTE_JSON = SRC / "assets" / "wortliste.json"
RATSCHE = REPO / "known_hits.json"

_TAG_RE = re.compile(r"<[^>]*>")
_SKRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)


def _seiten() -> list[Path]:
    return eigene_dateien(SRC, "*.html")


def _leer(m: re.Match[str]) -> str:
    """Ersatz fuer einen Treffer: Leerzeichen, Zeilenumbrueche bleiben (Fundstellen stimmen)."""
    return re.sub(r"[^\n]", " ", m.group(0))


def _ohne_kommentare(roh: str) -> str:
    return _KOMMENTAR_RE.sub(_leer, roh)


def _text_aus(roh: str) -> str:
    """Sichtbarer Text -- ohne Skript, Stil, Marken und Kommentare.

    Ersetzt wird zeichenweise durch Leerzeichen, nicht geloescht: So bleiben Zeilennummern
    und Fundstellen die der Quelldatei.
    """
    ohne = _SKRIPT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), roh)
    ohne = _KOMMENTAR_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), ohne)
    return _TAG_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), ohne)


def _text(pfad: Path) -> str:
    return _text_aus(pfad.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# digest
# ---------------------------------------------------------------------------
# Textdateien werden zeilenenden-normalisiert gehasht (CRLF -> LF, sonst ist der Guard auf
# einem CRLF-Windows-Rechner dauerhaft rot), Binaerdateien roh -- eine Normalisierung wuerde
# ein WOFF2 inhaltlich veraendern und den Digest dauerhaft falsch machen. Regel muss exakt zu
# styleguide_sync.ps1 (Produkt-Repo, Issue #613) passen.
_TEXT_ENDUNGEN = (".md", ".css", ".json", ".txt")


def pruefe_digest() -> list[str]:
    if not SYNC_STAND.exists():
        print("  uebersprungen: src/assets/sync-stand.json fehlt (Issue #613 noch offen)")
        return []
    stand = json.loads(SYNC_STAND.read_text(encoding="utf-8"))
    funde: list[str] = []
    for name, erwartet in sorted(stand.get("dateien", {}).items()):
        ziel = SRC / "assets" / name
        if not ziel.exists():
            funde.append(f"{name}: erzeugte Datei fehlt, styleguide_sync.ps1 erneut fahren")
            continue
        roh = ziel.read_bytes()
        if ziel.suffix.lower() in _TEXT_ENDUNGEN:
            roh = roh.replace(b"\r\n", b"\n")
        ist = hashlib.sha256(roh).hexdigest()
        if ist != erwartet:
            funde.append(
                f"{name}: von Hand geaendert (Fingerabdruck weicht ab). "
                "Aenderung gehoert ins Produkt-Repo, danach styleguide_sync.ps1 fahren"
            )
    return funde


# ---------------------------------------------------------------------------
# wortliste
# ---------------------------------------------------------------------------
def _muster(wort: str) -> re.Pattern[str]:
    """Wortliste-Eintrag zu Regex. '*' = beliebige Fortsetzung, Wortgrenzen sind Pflicht."""
    teile = [re.escape(t) for t in wort.split("*")]
    kern = r"\w*".join(teile)
    vorn = r"\b" if wort[:1].isalnum() else ""
    hinten = r"\b" if wort.endswith("*") is False and wort[-1:].isalnum() else ""
    return re.compile(vorn + kern + hinten, re.IGNORECASE)


def _wortliste_treffer() -> list[dict]:
    daten = json.loads(WORTLISTE_JSON.read_text(encoding="utf-8"))
    treffer: list[dict] = []
    for pfad in _seiten():
        text = _text(pfad)
        rel = pfad.relative_to(WURZEL).as_posix()
        for wort in daten.get("woerter", []):
            for m in _muster(wort).finditer(text):
                treffer.append({"datei": rel, "wort": wort, "zeile": _zeile(text, m.start())})
    return treffer


def pruefe_wortliste() -> list[str]:
    if not WORTLISTE_JSON.exists():
        print("  uebersprungen: src/assets/wortliste.json fehlt (Issue #613 noch offen)")
        return []
    treffer = _wortliste_treffer()
    geduldet = json.loads(RATSCHE.read_text(encoding="utf-8")) if RATSCHE.exists() else []
    schluessel = {(e["datei"], e["wort"], e["zeile"]) for e in geduldet}
    funde = [
        f"{t['datei']}:{t['zeile']} -- '{t['wort']}' (Wortliste #881 W1)"
        for t in treffer
        if (t["datei"], t["wort"], t["zeile"]) not in schluessel
    ]
    heute = {(t["datei"], t["wort"], t["zeile"]) for t in treffer}
    veraltet = schluessel - heute
    if veraltet:
        funde.append(
            f"known_hits.json: {len(veraltet)} Eintrag/Eintraege trifft nicht mehr zu -- "
            "Ratsche mit --schreibe-ratsche nachziehen (sie darf nur schrumpfen)"
        )
    return funde


def schreibe_ratsche() -> None:
    if not WORTLISTE_JSON.exists():
        print("wortliste.json fehlt -- nichts zu schreiben")
        return
    treffer = sorted(_wortliste_treffer(), key=lambda t: (t["datei"], t["zeile"], t["wort"]))
    RATSCHE.write_text(
        json.dumps(treffer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"known_hits.json geschrieben: {len(treffer)} Eintrag/Eintraege")


# ---------------------------------------------------------------------------
# preis
# ---------------------------------------------------------------------------
_BETRAG = r"\d[\d.,]*\s*(?:€|EUR\b|Euro\b)"

# Ebene 1 -- Preisaussage. Rot ueberall, auch innerhalb einer Beispielansicht.
_PREIS_HART: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Preisanker 'ab X'", re.compile(rf"\bab\s+(?:ca\.\s*)?{_BETRAG}", re.IGNORECASE)),
    ("Betrag je Zeitraum", re.compile(rf"{_BETRAG}?\s*(?:/|je|pro|im)\s*(?:Jahr|Monat)\b", re.IGNORECASE)),
    (
        "Betrag im Preiszusammenhang",
        re.compile(
            rf"(?:Preis|Lizenz|kostet|Kosten|Abo|Tarif|Gebuehr|Gebühr)[^.!?]{{0,60}}{_BETRAG}"
            rf"|{_BETRAG}[^.!?]{{0,60}}(?:Preis|Lizenz|kostet|Kosten|Abo|Tarif|Gebuehr|Gebühr)",
            re.IGNORECASE,
        ),
    ),
)

# Ebene 2 -- irgendein Geldbetrag. Erlaubt nur in einem Block, der als Beispielansicht
# gekennzeichnet ist (Leitplanke 3: „Demozahlen sind als Beispielansicht zu kennzeichnen").
_PREIS_WEICH: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Betrag mit Waehrung", re.compile(_BETRAG, re.IGNORECASE)),
    ("Waehrung vor Betrag", re.compile(r"(?:€|EUR\b)\s*\d", re.IGNORECASE)),
)

_BEISPIEL_AUF = re.compile(r"<(\w+)(?=[^>]*\bdata-beispiel\b)[^>]*>", re.IGNORECASE)


def _ohne_beispielbloecke(roh: str) -> str:
    """Entfernt Elemente mit `data-beispiel` -- Zeilennummern bleiben erhalten.

    Leitplanke 3 verlangt, dass Demozahlen als Beispielansicht gekennzeichnet sind. Genau
    diese Kennzeichnung ist hier der Schluessel: Was gekennzeichnet ist, darf Zahlen tragen;
    alles andere nicht. So prueft ein Guard beide Leitplanken statt nur einer.
    """
    aus = roh
    while True:
        auf = _BEISPIEL_AUF.search(aus)
        if not auf:
            return aus
        name = auf.group(1)
        tiefe = 1
        pos = auf.end()
        gleiche = re.compile(rf"<(/?){re.escape(name)}\b[^>]*>", re.IGNORECASE)
        ende = len(aus)
        for m in gleiche.finditer(aus, pos):
            tiefe += -1 if m.group(1) else 1
            if tiefe == 0:
                ende = m.end()
                break
        block = aus[auf.start() : ende]
        aus = aus[: auf.start()] + re.sub(r"[^\n]", " ", block) + aus[ende:]


def pruefe_preis() -> list[str]:
    funde: list[str] = []
    for pfad in _seiten():
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(WURZEL).as_posix()
        alles = _text(pfad)
        ohne_beispiel = _text_aus(_ohne_beispielbloecke(roh))
        for name, muster in _PREIS_HART:
            funde += _befunde(rel, alles, muster, name, "Leitplanke 1, K1/Konzept 11.3")
        for name, muster in _PREIS_WEICH:
            funde += _befunde(
                rel, ohne_beispiel, muster, name,
                "Leitplanke 1/3: Geldbetrag nur in einem als Beispielansicht "
                "gekennzeichneten Block (data-beispiel)",
            )
    return funde


def _befunde(rel: str, text: str, muster: re.Pattern[str], name: str, regel: str) -> list[str]:
    raus = []
    for m in muster.finditer(text):
        schnipsel = " ".join(text[max(0, m.start() - 30) : m.end() + 30].split())
        raus.append(f"{rel}:{_zeile(text, m.start())} -- {name}: …{schnipsel}… ({regel})")
    return raus


# ---------------------------------------------------------------------------
# verweise
# ---------------------------------------------------------------------------
_VERWEIS_RE = re.compile(r"""\b(?:href|src|action)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_EXTERN = ("http://", "https://", "mailto:", "tel:", "data:", "//")


def pruefe_verweise() -> list[str]:
    funde: list[str] = []
    for pfad in _seiten():
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(WURZEL).as_posix()
        for m in _VERWEIS_RE.finditer(roh):
            ziel = m.group(1).strip()
            if not ziel or ziel.startswith("#") or ziel.startswith(_EXTERN):
                continue
            rein = ziel.split("#", 1)[0].split("?", 1)[0]
            if not rein or ANGABE_RE.fullmatch(ziel):
                continue  # Marke als ganzer Verweis: der Bau setzt die Adresse ein (pruefen_angaben)
            if rein.split("/", 1)[0] in FREMDE_BAUTEN and not (SRC / rein.split("/", 1)[0]).is_dir():
                continue  # eigener Bau (mkdocs, build-site.ps1), fehlt nur in src/
            if rein.lower().endswith(".md"):
                funde.append(f"{rel}:{_zeile(roh, m.start())} -- Verweis auf Markdown-Datei: {ziel} (echte GitHub-URL oder Seite verlinken)")
                continue
            basis = SRC if rein.startswith("/") else pfad.parent
            kandidat = (basis / rein.lstrip("/")).resolve()
            if kandidat.is_dir():
                kandidat = kandidat / "index.html"
            if not kandidat.exists():
                funde.append(f"{rel}:{_zeile(roh, m.start())} -- Verweis ins Leere: {ziel}")
    return funde


# ---------------------------------------------------------------------------
# verkauf
# ---------------------------------------------------------------------------
_VERKAUF: tuple[str, ...] = (
    r"Lizenzdatei", r"Lizenz\s+holen", r"Lizenzbedingungen", r"Lizenznehmer", r"Preis",
    r"Pilotbetrieb", r"Abo", r"Kunde\w*", r"Bestell\w*", r"Laufzeit", r"Spende\w*",
    r"Trinkgeld", r"Kostenbeitrag", r"Jetzt\s+unterst\w+", r"Spendenziel",
    r"Unterst\w+tzerliste", r"Wero",
)
_VERKAUF_RE = re.compile(r"\b(?:" + "|".join(_VERKAUF) + r")\b", re.IGNORECASE)


def pruefe_verkauf() -> list[str]:
    """Kein Verkaufs- oder Lizenzwortschatz im sichtbaren Text jeder Seite (Issue #1234/#1236).

    Vermora ist kostenlos; ein Geschenk an den Entwickler ist keine Gegenleistung. Ein Wort
    wie "Lizenz holen" oder "Spende" liesse die Seite wie ein Angebot lesen -- das ist im Ton
    und rechtlich das Gegenteil des Beschlossenen. "kostenlos" loest auch `preis` nicht aus.
    """
    funde: list[str] = []
    for pfad in _seiten():
        rel = pfad.relative_to(WURZEL).as_posix()
        funde += _befunde(
            rel, _text(pfad), _VERKAUF_RE, "Verkaufswortschatz",
            "Issue #1234/#1236: Geschenkmodell, kein Verkauf",
        )
    return funde


# ---------------------------------------------------------------------------
# extern
# ---------------------------------------------------------------------------
_ATTR = r"""(?:[^>"']|"[^"]*"|'[^']*')*?"""
_EXTERN_HTML = re.compile(
    rf"""<(?:script|img|source|iframe|link|form|video|audio|embed|object)\b{_ATTR}\b"""
    r"""(?:src|href|srcset|action|data|poster)\s*=\s*["']?\s*(?:https?:)?//""",
    re.IGNORECASE | re.DOTALL,
)
# CSS: url(http...) und @import, in .css-Dateien und in style-Attributen/-Bloecken
_EXTERN_CSS = re.compile(
    r"""url\(\s*["']?\s*(?:https?:)?//|@import\s+(?:url\(\s*)?["']?\s*(?:https?:)?//""",
    re.IGNORECASE,
)
_SCHNIPSEL = 80


def pruefe_extern() -> list[str]:
    """Nichts wird von einem fremden Server geladen oder dorthin gesendet (K23).

    Gemeint sind Einbettungen (Skript, Bild, Quelle, Frame, Stylesheet-Link, Formularziel,
    auch ohne Anfuehrungszeichen) sowie `url(...)` und `@import` in CSS. Ein gewoehnlicher
    Link `<a href>` auf eine fremde Seite bleibt erlaubt: Er laedt nichts. Gleiches gilt fuer
    `<link rel="canonical">`.
    """
    funde: list[str] = []
    dateien = _seiten() + eigene_dateien(SRC, "*.css")
    for pfad in dateien:
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(WURZEL).as_posix()
        ohne = _ohne_kommentare(roh) if pfad.suffix == ".html" else re.sub(
            r"/\*.*?\*/", _leer, roh, flags=re.DOTALL)
        muster = (_EXTERN_HTML, _EXTERN_CSS) if pfad.suffix == ".html" else (_EXTERN_CSS,)
        for mu in muster:
            for m in mu.finditer(ohne):
                if re.search(r"rel\s*=\s*[\"']?canonical", m.group(0), re.IGNORECASE):
                    continue  # Canonical laedt nichts, es nennt nur die eigene Adresse
                funde.append(
                    f"{rel}:{_zeile(roh, m.start())} -- externe Einbettung: "
                    f"{' '.join(m.group(0).split())[:_SCHNIPSEL]} (K23)"
                )
    return funde


# ---------------------------------------------------------------------------
# sicherheit
# ---------------------------------------------------------------------------
SECURITY_TXT = SRC / ".well-known" / "security.txt"
_EXPIRES_RE = re.compile(r"^Expires:\s*(\S+)\s*$", re.MULTILINE)


def _security_ablauf(text: str) -> datetime | None:
    m = _EXPIRES_RE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def pruefe_sicherheit() -> list[str]:
    """`security.txt` nach RFC 9116: Contact und genau ein Expires im ISO-8601-Format."""
    if not SECURITY_TXT.exists():
        return ["src/.well-known/security.txt fehlt (RFC 9116, Issue #1234)"]
    text = SECURITY_TXT.read_text(encoding="utf-8")
    funde: list[str] = []
    if not re.search(r"^Contact:\s*\S+", text, re.MULTILINE):
        funde.append("security.txt: Feld Contact fehlt")
    if len(re.findall(r"^Expires:", text, re.MULTILINE)) != 1:
        funde.append("security.txt: genau ein Feld Expires erwartet")
    elif _security_ablauf(text) is None and not re.search(
        rf"^Expires:\s*{ABLAUF_MARKE_RE.pattern}\s*$", text, re.MULTILINE
    ):
        funde.append("security.txt: Expires nicht im Format JJJJ-MM-TTThh:mm:ssZ (ISO 8601)")
    return funde


# ---------------------------------------------------------------------------
# hinweis
# ---------------------------------------------------------------------------
HINWEISTEXTE_JSON = SRC / "assets" / "hinweistexte.json"


def pruefe_hinweis() -> list[str]:
    """Der Haftungssatz muss woertlich so auf der Seite stehen wie in der Anwendung.

    Die Wortliste faengt ein einzelnes Urteilswort -- sie faengt nicht, wenn der zentrale
    Hinweissatz hier leicht anders lautet als in der Anwendung. Genau dieser Satz ist der
    rechtlich tragende (Issue #881 W1.1, Konzept 12.5/12.7), und eine Abweichung faellt
    niemandem auf, solange beide Fassungen fuer sich gelesen plausibel klingen. Quelle ist
    `assets/hinweistexte.json` aus `styleguide_sync.ps1` (Issue #613/#615).
    """
    if not HINWEISTEXTE_JSON.exists():
        print("  uebersprungen: src/assets/hinweistexte.json fehlt (styleguide_sync.ps1 fahren)")
        return []
    daten = json.loads(HINWEISTEXTE_JSON.read_text(encoding="utf-8"))
    satz = daten.get("beratung", "").strip()
    if not satz:
        return ["hinweistexte.json: Feld 'beratung' fehlt oder ist leer"]
    treffer = 0
    for pfad in _seiten():
        text = " ".join(_text(pfad).split())
        if satz in text:
            treffer += 1
    if treffer == 0:
        return [
            "Der zentrale Hinweissatz steht auf keiner Seite (oder nicht woertlich). "
            f"Erwartet: \"{satz[:70]}…\" -- Wortlaut aus assets/hinweistexte.json "
            "uebernehmen, nicht umformulieren (Quelle: Produkt-Repo, Issue #881 W1.1)."
        ]
    return []


# ---------------------------------------------------------------------------
# hexwerte
# ---------------------------------------------------------------------------
# Issue-Nummern wie "#615" sind formal gueltige Drei-Zeichen-Hexwerte -- ein naiver
# Ausdruck meldet jede Quellenangabe in einem Kommentar. Deshalb: sechs oder acht Stellen
# (die Schreibweise des Styleguides), oder drei bis vier Stellen NUR mit einem Buchstaben
# darin (#abc). Ein reiner Ziffern-Kurzwert wie "#613" faellt damit durch das Raster --
# bewusst: Der Styleguide schreibt sechsstellig, und ein Fehlalarm bei jeder Issue-Nummer
# waere ein Guard, den man binnen einer Woche abschaltet.
_HEX_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|(?=[0-9a-fA-F]{3,4}\b)[0-9a-fA-F]*[a-fA-F][0-9a-fA-F]*)\b"
)
_HEX_ERLAUBT = ("tokens.css",)


def pruefe_hexwerte() -> list[str]:
    """Farbwerte gehoeren ausschliesslich in die erzeugte `tokens.css`.

    Steht auch nur ein Hexwert daneben, gibt es zwei Paletten -- und die driften. Genau so
    ist der Bruch entstanden, den K22 aufloesen musste (Anwendung auf Tailwind-Blau,
    Website-Entwurf auf Indigo).
    """
    funde: list[str] = []
    for pfad in eigene_dateien(SRC):
        if pfad.suffix.lower() not in (".html", ".css"):
            continue
        if pfad.name in _HEX_ERLAUBT:
            continue
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(WURZEL).as_posix()
        for m in _HEX_RE.finditer(roh):
            funde.append(
                f"{rel}:{_zeile(roh, m.start())} -- Farbwert {m.group(0)} ausserhalb von "
                "tokens.css. Rolle aus dem Styleguide verwenden (--vm-...), Wert im "
                "Produkt-Repo aendern."
            )
    return funde


# ---------------------------------------------------------------------------
# recht
# ---------------------------------------------------------------------------
RECHT_DIR = SRC / "recht"
RECHT_SEITEN = ("impressum.html", "datenschutz.html", "nutzungsbedingungen.html")
ANGABEN_INI = REPO.parent / "vermora-geheim" / "angaben.ini"


def pruefe_recht() -> list[str]:
    """Die drei Pflichtseiten muessen vorhanden sein; Entwurfs-/Kanzlei-Vermerke gibt es nicht
    mehr (Freigabe Christian 2026-10-24, Issue #1234). `noindex` ist eine eigene Entscheidung
    und wird hier weder verlangt noch verboten."""
    if not RECHT_DIR.exists():
        return []
    return [f"src/recht/{n} fehlt" for n in RECHT_SEITEN if not (RECHT_DIR / n).is_file()]


def veroeffentlichung_erlaubt(ini: Path | None = None) -> list[str]:
    """Sperre fuer den spaeteren Veroeffentlichungsweg (Issue #944).

    Fehlende Pflichtdateien (.nojekyll, 404.html), offene Angaben-Marken, Vorschau-Fusszeile und
    abgelaufene security.txt sperren den Live-Gang.
    """
    if not RECHT_DIR.exists():
        return ["src/recht/ fehlt -- ohne Pflichtseiten geht nichts live (Konzept 12.1)."]
    funde: list[str] = []
    for pflicht in (".nojekyll", "404.html"):
        if not (SRC / pflicht).is_file():
            funde.append(f"{pflicht} fehlt -- GitHub Pages braucht die Datei (Jekyll-Aus, eigene 404-Seite)")
    return funde + _veroeffentlichung_offen(ini or ANGABEN_INI)


def _veroeffentlichung_offen(ini: Path) -> list[str]:
    """Offene Daten (Issue #1234): Angaben-Marken, abgelaufene security.txt."""
    funde: list[str] = veroeffentlichung_angaben(SRC, ini, REPO) + vorschau_fusszeile(SRC, WURZEL)
    if SECURITY_TXT.exists():
        ablauf = _security_ablauf(SECURITY_TXT.read_text(encoding="utf-8"))
        jetzt = datetime.now(timezone.utc)
        if ablauf is not None and ablauf < jetzt:
            funde.append("security.txt: Expires liegt in der Vergangenheit -- erneuern (RFC 9116)")
        elif ablauf is not None and ablauf > jetzt + timedelta(days=_SICHERHEIT_MAX_TAGE):
            funde.append(f"security.txt: Expires liegt mehr als {_SICHERHEIT_MAX_TAGE} Tage voraus -- kuerzer setzen")
    return funde


# ---------------------------------------------------------------------------
# zeichen
# ---------------------------------------------------------------------------
ZEICHEN_SVG = SRC / "assets" / "zeichen.svg"
_ZEICHEN_PLATZHALTER = "<!--zeichen-->"
# Anfang des ersten Bogens -- wer die Geometrie von Hand hereinkopiert, traegt diesen Pfad.
_ZEICHEN_GEOMETRIE = "M12 3C7 3"


def pruefe_zeichen() -> list[str]:
    """Das Markenzeichen steht auf jeder Seite -- und zwar als Platzhalter, nie abgetippt.

    Die Geometrie hat eine einzige Fundstelle (`docs/MARKENZEICHEN.md` im Produkt-Repo,
    Issue #604). Sie kommt ueber den Sync als `assets/zeichen.svg` hierher und wird beim
    Bau an jeder `<!--zeichen-->`-Stelle eingesetzt. Eine von Hand kopierte Pfadangabe
    waere die fuenfte Kopie derselben Kurve -- und die naechste, die stehen bleibt, wenn
    sich das Zeichen aendert.
    """
    funde: list[str] = []
    seiten = _seiten()
    if not seiten:
        return funde
    if not ZEICHEN_SVG.exists():
        funde.append(
            "src/assets/zeichen.svg fehlt -- styleguide_sync.ps1 im Produkt-Repo fahren "
            "(die Datei wird aus docs/MARKENZEICHEN.md erzeugt)."
        )
    for pfad in seiten:
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(WURZEL).as_posix()
        if _ZEICHEN_PLATZHALTER not in roh:
            funde.append(
                f"{rel}: kein {_ZEICHEN_PLATZHALTER} -- die Seite traegt das Markenzeichen nicht."
            )
        if _ZEICHEN_GEOMETRIE in roh:
            funde.append(
                f"{rel}:{_zeile(roh, roh.index(_ZEICHEN_GEOMETRIE))} -- Zeichen-Geometrie von "
                f"Hand kopiert. Stattdessen {_ZEICHEN_PLATZHALTER} setzen; der Bau kopiert "
                "die erzeugte assets/zeichen.svg hinein."
            )
    return funde


def pruefe_anleitung_start() -> list[str]:
    """/anleitung/ muss auf das Ueberblickskapitel weiterleiten (Issue #1284).

    Gilt nur, wo ein gebauter Ordner anleitung/ liegt (also mit --dist); auf src/ gruen.
    Meta-Refresh (kein Skript, CSP), kanonische Adresse, sichtbarer Link, Ziel vorhanden.
    """
    ordner = SRC / "anleitung"
    if not ordner.is_dir():
        return []
    start = ordner / "index.html"
    if not start.is_file():
        return ["anleitung/index.html fehlt: /anleitung/ waere eine tote Adresse"]
    roh = start.read_text(encoding="utf-8")
    funde = []
    if not re.search(r"""<meta\s+http-equiv=["']refresh["']\s+content=["']0;\s*url=00-ueberblick/["']""", roh):
        funde.append("anleitung/index.html: Meta-Refresh auf 00-ueberblick/ fehlt")
    if not re.search(r"""<link\s+rel=["']canonical["']\s+href=["']https://vermora\.de/anleitung/00-ueberblick/["']""", roh):
        funde.append("anleitung/index.html: canonical auf /anleitung/00-ueberblick/ fehlt")
    if not re.search(r"""<a\s+href=["']00-ueberblick/["']""", roh):
        funde.append("anleitung/index.html: sichtbarer Link auf 00-ueberblick/ fehlt")
    if not (ordner / "00-ueberblick" / "index.html").is_file():
        funde.append("anleitung/00-ueberblick/index.html fehlt: Weiterleitungsziel tot")
    return funde


PRUEFUNGEN = {
    "digest": pruefe_digest,
    "wortliste": pruefe_wortliste,
    "hinweis": pruefe_hinweis,
    "preis": pruefe_preis,
    "hexwerte": pruefe_hexwerte,
    "zeichen": pruefe_zeichen,
    "recht": pruefe_recht,
    "verweise": pruefe_verweise,
    "verkauf": pruefe_verkauf,
    "extern": pruefe_extern,
    "sicherheit": pruefe_sicherheit,
    "bilder": lambda: pruefe_bilder(SRC, WURZEL),
    "a11y": lambda: pruefe_a11y(SRC, WURZEL),
    "angaben": lambda: pruefe_angaben(SRC, REPO / "angaben.beispiel.ini"),
    "seo": lambda: pruefe_seo(SRC, WURZEL),
    "anleitung_start": pruefe_anleitung_start,
}


# Brauchen Dateien, die der Bau nicht ausliefert, oder Marken, die der Veroeffentlichungsweg
# schon eingesetzt hat -- mit --dist laufen sie nicht (auf src/ bei jedem Bau schon).
QUELL_PRUEFUNGEN = frozenset({"digest", "wortliste", "hinweis", "zeichen", "angaben"})


def _auf_dist(dist: Path) -> None:
    """Richtet die Modulpfade auf den gebauten Ordner (`--dist`); Repo-Dateien bleiben am Repo."""
    global WURZEL, SRC, SYNC_STAND, WORTLISTE_JSON, SECURITY_TXT, HINWEISTEXTE_JSON, RECHT_DIR, ZEICHEN_SVG
    WURZEL = SRC = dist
    SYNC_STAND = SRC / "assets" / "sync-stand.json"
    WORTLISTE_JSON = SRC / "assets" / "wortliste.json"
    SECURITY_TXT = SRC / ".well-known" / "security.txt"
    HINWEISTEXTE_JSON = SRC / "assets" / "hinweistexte.json"
    RECHT_DIR = SRC / "recht"
    ZEICHEN_SVG = SRC / "assets" / "zeichen.svg"


def main() -> int:
    # Windows-Konsole laeuft auf cp1252; ein Textschnipsel aus der Seite enthaelt aber
    # Pfeile, Gedankenstriche, Auslassungspunkte. Ohne diese Zeile stirbt die Ausgabe an
    # einem Fund -- also ausgerechnet dann, wenn der Guard etwas zu sagen hat.
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - alte Python-Stroeme
            pass

    p = argparse.ArgumentParser(description="Guards fuer die Website vermora.de")
    p.add_argument("--nur", action="append", choices=sorted(PRUEFUNGEN), help="nur diese Pruefung")
    p.add_argument("--schreibe-ratsche", action="store_true", help="known_hits.json neu schreiben")
    p.add_argument(
        "--veroeffentlichung",
        action="store_true",
        help="zusaetzliche Sperre fuer den Live-Gang: offene Angaben, Pflichtdateien, security.txt",
    )
    p.add_argument(
        "--angaben",
        type=Path,
        default=ANGABEN_INI,
        help="echte angaben.ini fuer --veroeffentlichung (nie im Repo ablegen)",
    )
    p.add_argument("--dist", type=Path, help="gebauten Ordner pruefen statt src/ (Marken schon eingesetzt)")
    args = p.parse_args()

    if args.schreibe_ratsche:
        schreibe_ratsche()
        return 0

    if args.dist is not None:
        if not args.dist.is_dir():
            print(f"FEHLER: {args.dist} ist kein Ordner")
            return 2
        _auf_dist(args.dist.resolve())

    if not SRC.exists():
        print("FEHLER: src/ fehlt")
        return 2

    namen = args.nur or list(PRUEFUNGEN)
    rot = 0
    for name in namen:
        print(f"[{name}]")
        if args.dist is not None and name in QUELL_PRUEFUNGEN:
            print("  uebersprungen: Quellpruefung (laeuft auf src/)")
            continue
        funde = PRUEFUNGEN[name]()
        for f in funde:
            print(f"  ROT  {f}")
        if funde:
            rot += len(funde)
        else:
            print("  gruen")
    if args.veroeffentlichung:
        print("[veroeffentlichung]")
        sperren = veroeffentlichung_erlaubt(args.angaben)
        for s in sperren:
            print(f"  ROT  {s}")
        if sperren:
            rot += len(sperren)
        else:
            print("  gruen")

    if rot:
        print(f"\n{rot} Befund(e) -- Bau abgebrochen.")
        return 1
    print("\nAlle Pruefungen gruen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
