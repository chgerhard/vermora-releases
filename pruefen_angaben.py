"""Eigene Angaben: Marken in `src/` gegen angaben.ini [angaben] (Issue #1234/#1244).

Seiten und security.txt tragen Marken `[PLATZHALTER-KEY: Hinweis]` in EINER Zeile. Beim
Veroeffentlichen (GitHub Pages, Workflow in vermora-releases) setzt `angaben_einsetzen` die
Werte aus den Actions-Secrets `ANGABE_<KEY>` in die gebaute Kopie (`--einsetzen DIST`) ein.
Es gibt kein PHP-Gegenstueck mehr: diese Datei ist die einzige Stelle fuer `ANGABE_RE` und
`wert_gueltig`. Dieses Modul prueft und setzt ein:

  pruefe_angaben             Bei jedem Bau: Marken in src/ und Schluessel in
                             angaben.beispiel.ini passen in beide Richtungen zusammen, die
                             Vorlage traegt keine Werte (Datenschutz im Repo), und kein
                             `PLATZHALTER-` steht ausserhalb einer wohlgeformten Marke.
  veroeffentlichung_angaben  Nur mit `--veroeffentlichung`: die echte ini-Datei (liegt NEBEN
                             dem Repo, nie darin) hat fuer jede Marke einen gueltigen Wert.
                             Ohne ini-Datei ist jeder Schluessel rot (Sperre wie bisher).

  angaben_einsetzen          Nur im Veroeffentlichungsweg (`--einsetzen DIST`): ersetzt jede
                             Marke in der gebauten Kopie durch den gueltigen Wert.

Gibt nie einen Wert aus, nur Schluessel und Fundstellen.
"""
from __future__ import annotations

import html
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from pruefen_html import eigene_dateien

ANGABE_RE = re.compile(r"\[PLATZHALTER-([A-Z][A-Z0-9_]*)(?::[^\]\r\n]*)?\]")
_ENDUNGEN = (".html", ".txt", ".svg", ".js")
_AUSGENOMMEN: tuple[str, ...] = ()
_MAX_ZEICHEN = 300
_ATOM = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
# Gegenstueck zu FILTER_VALIDATE_EMAIL: Punkt-Atom ASCII, Domain mit mind. zwei Labels.
_MAIL_RE = re.compile(rf"{_ATOM}(?:\.{_ATOM})*@{_LABEL}(?:\.{_LABEL})+")
_MAIL_MAX = 254
_MAIL_LOKAL_MAX = 64
_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
SICHERHEIT_MAX_TAGE = 366
# PayPal-Link des Geschenk-Hinweises: ganze URL auf paypal.me oder paypal.com, nichts anderes
# (Secret ANGABE_PAYPAL_LINK; der Wert ist eine Zieladresse, kein Zugang).
_PAYPAL_RE = re.compile(r"https://(?:www\.)?paypal\.(?:me|com)/[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]+")

# Getarnte Form (nur index.html, #1281): `[PLATZHALTER-EMAIL_GETARNT: ...]` nimmt den Wert des
# Schluessels `email`; kein eigener Schluessel in der ini. Impressum/Datenschutz/security.txt
# tragen weiter die Klartext-Marke EMAIL (rechtlich noetig).
ALIAS = {"email_getarnt": "email"}
GETARNT_DATEIEN = ("index.html",)

# Nur diese Dateien setzen Marken ein (`angaben_einsetzen`).
BEDIENTE_DATEIEN = (
    "index.html",
    "recht/impressum.html",
    "recht/datenschutz.html",
    ".well-known/security.txt",
)


def zeile(text: str, pos: int) -> int:
    """1-basierte Zeilennummer der Position (einzige Kopie, pruefen.py importiert sie)."""
    return text.count("\n", 0, pos) + 1


def ini_lesen(pfad: Path) -> dict[str, dict[str, str]]:
    """Liest eine ini-Datei: Abschnitt -> Schluessel -> Wert; oberste Schluessel unter ''."""
    aus: dict[str, dict[str, str]] = {"": {}}
    sektion = ""
    for roh in pfad.read_text(encoding="utf-8").splitlines():
        z = roh.strip()
        if not z or z.startswith((";", "#")):
            continue
        m = re.fullmatch(r"\[([^\]]+)\]\s*(?:;.*)?", z)
        if m:
            sektion = m.group(1).strip()
            aus.setdefault(sektion, {})
            continue
        if "=" not in z:
            continue
        key, _, wert = z.partition("=")
        wert = wert.strip()
        if wert[:1] in ('"', "'"):
            ende = wert.find(wert[0], 1)
            wert = wert[1:ende] if ende > 0 else wert[1:]
        else:
            wert = wert.split(";", 1)[0].strip()
        aus[sektion][key.strip()] = wert.strip()
    return aus


def _dateien(src: Path) -> list[Path]:
    return [
        p for p in eigene_dateien(src)
        if p.suffix.lower() in _ENDUNGEN and p.name not in _AUSGENOMMEN
    ]


def marker_finden(src: Path) -> dict[str, list[tuple[str, int]]]:
    """Schluessel (klein) -> Fundstellen (relativer Pfad, Zeile) ueber alle Quelldateien."""
    funde: dict[str, list[tuple[str, int]]] = {}
    for pfad in _dateien(src):
        roh = pfad.read_text(encoding="utf-8")
        rel = pfad.relative_to(src).as_posix()
        for m in ANGABE_RE.finditer(roh):
            key = m.group(1).lower()
            funde.setdefault(ALIAS.get(key, key), []).append((rel, zeile(roh, m.start())))
    return funde


def _datum(wert: str, muster: re.Pattern[str], fmt: str) -> date | None:
    """Echtes Kalenderdatum (wie checkdate() in PHP) oder None."""
    if muster.fullmatch(wert) is None:
        return None
    try:
        return datetime.strptime(wert, fmt).date()
    except ValueError:
        return None


def ablauf_ausserhalb(wert: str, heute: date | None = None) -> bool:
    """security_ablauf (gueltig) liegt nicht in [morgen, heute + 366 Tage]."""
    d = _datum(wert, _ISO_RE, "%Y-%m-%d")
    heute = heute or date.today()
    return d is None or d <= heute or d > heute + timedelta(days=SICHERHEIT_MAX_TAGE)


def wert_gueltig(key: str, wert: str) -> bool:
    """Gueltigkeit eines Wertes je Schluessel (einzige Regelstelle)."""
    if not wert or len(wert) > _MAX_ZEICHEN:
        return False
    if re.search(r"[\x00-\x1f\x7f]", wert) or "PLATZHALTER-" in wert:
        return False
    if key == "email":
        lokal = wert.partition("@")[0]
        return len(wert) <= _MAIL_MAX and len(lokal) <= _MAIL_LOKAL_MAX and _MAIL_RE.fullmatch(wert) is not None
    if key == "security_ablauf":
        return _datum(wert, _ISO_RE, "%Y-%m-%d") is not None
    if key == "stand_datenschutz":
        return _datum(wert, _DE_RE, "%d.%m.%Y") is not None
    if key == "paypal_link":
        return _PAYPAL_RE.fullmatch(wert) is not None
    return True


def pruefe_angaben(src: Path, beispiel: Path) -> list[str]:
    """Konsistenz Quelle <-> Vorlage, laeuft bei jedem Bau."""
    funde: list[str] = []
    marker = marker_finden(src)
    if not beispiel.is_file():
        return [f"{beispiel.name} fehlt -- dort stehen die Schluessel des Abschnitts [angaben]."]
    vorlage = ini_lesen(beispiel).get("angaben")
    if vorlage is None:
        return [f"{beispiel.name}: Abschnitt [angaben] fehlt"]
    for key, stellen in sorted(marker.items()):
        if key not in vorlage:
            rel, z = stellen[0]
            funde.append(f"{rel}:{z} -- Marke {key.upper()} ohne Schluessel '{key}' in {beispiel.name} [angaben]")
    for key, wert in sorted(vorlage.items()):
        if key not in marker:
            funde.append(f"{beispiel.name}: Schluessel '{key}' wird von keiner Marke in src/ genutzt")
        if wert != "":
            funde.append(f"{beispiel.name}: Schluessel '{key}' hat einen Wert -- im Repo bleiben Werte leer (Datenschutz)")
    for key, stellen in sorted(marker.items()):
        for rel, z in stellen:
            if rel not in BEDIENTE_DATEIEN:
                funde.append(f"{rel}:{z} -- Marke {key.upper()} in einer Datei, die der Bau nicht einsetzt")
    for pfad in _dateien(src):
        roh = pfad.read_text(encoding="utf-8")
        rest = ANGABE_RE.sub(lambda m: " " * len(m.group(0)), roh)
        for m in re.finditer("PLATZHALTER-", rest):
            funde.append(
                f"{pfad.relative_to(src).as_posix()}:{zeile(rest, m.start())} -- "
                "PLATZHALTER- ausserhalb einer wohlgeformten Marke (eine Zeile, [PLATZHALTER-KEY: Hinweis])"
            )
    return funde


def veroeffentlichung_angaben(src: Path, ini: Path, wurzel: Path) -> list[str]:
    """Sperre fuer den Live-Gang: jede Marke braucht einen gueltigen Wert in der echten ini."""
    funde: list[str] = []
    marker = marker_finden(src)
    try:
        ini.resolve().relative_to(wurzel.resolve())
        funde.append("angaben.ini liegt im Repo -- die echte Datei gehoert daneben, nie hinein (Datenschutz)")
        return funde
    except ValueError:
        pass
    werte: dict[str, str] = {}
    if ini.is_file():
        werte = ini_lesen(ini).get("angaben", {})
    for key, stellen in sorted(marker.items()):
        rel, z = stellen[0]
        if not wert_gueltig(key, werte.get(key, "")):
            funde.append(f"Angabe {key} fehlt in angaben.ini [angaben] ({rel}:{z})")
        elif key == "security_ablauf" and ablauf_ausserhalb(werte[key]):
            funde.append(f"Angabe security_ablauf ausserhalb des Rahmens (morgen bis {SICHERHEIT_MAX_TAGE} Tage)")
    return funde


_VORSCHAU = "Örtliche Vorschau"
# Expires in security.txt: ISO-Literal oder genau die Marke SECURITY_ABLAUF plus fester Uhrzeit.
ABLAUF_MARKE_RE = re.compile(r"\[PLATZHALTER-SECURITY_ABLAUF(?::[^\]\r\n]*)?\]T00:00:00Z")


def vorschau_fusszeile(src: Path, wurzel: Path) -> list[str]:
    """Live-Sperre: die Fusszeile 'Örtliche Vorschau' darf nicht ausgeliefert werden (C7)."""
    return [
        f"{p.relative_to(wurzel).as_posix()}: Vorschau-Fusszeile -- vor Live-Gang entfernen (C7)"
        for p in eigene_dateien(src, "*.html")
        if _VORSCHAU in p.read_text(encoding="utf-8")
    ]


def mail_getarnt(wert: str) -> str:
    """HTML-Span ohne zusammenhaengende Adresse: Anzeigetext `name [at] domain [punkt] tld`,
    `data-u`/`data-d` tragen Lokalteil und Domain rueckwaerts; assets/mail.js baut den Link."""
    lokal, _, domain = wert.partition("@")

    def text(t: str) -> str:
        return html.escape(t.replace(".", " [punkt] "), quote=True)

    def rueck(t: str) -> str:
        return html.escape(t[::-1], quote=True)

    return (
        f'<span class="mail-getarnt" data-u="{rueck(lokal)}" data-d="{rueck(domain)}">'
        f"{text(lokal)} [at] {text(domain)}</span>"
    )


def angaben_einsetzen(dist: Path, werte: dict[str, str]) -> list[str]:
    """Setzt die Marken in der gebauten Kopie `dist` ein (ein Durchlauf je Datei).

    html: `html.escape(quote=True)`; .txt: Wert ohne Leerraum (security.txt ist zeilenweise).
    Ungueltiger oder fehlender Wert: Marke bleibt stehen, Befund nennt nur Schluessel und
    Fundstelle, nie den Wert. Ein Befund je Schluessel.
    """
    funde: list[str] = []
    gemeldet: set[str] = set()

    for rel in BEDIENTE_DATEIEN:
        pfad = dist / rel
        if not pfad.is_file():
            continue
        roh = pfad.read_bytes().decode("utf-8")

        def ersatz(m: re.Match[str]) -> str:
            roh_key = m.group(1).lower()
            getarnt = roh_key in ALIAS
            key = ALIAS.get(roh_key, roh_key)
            wert = werte.get(key, "")
            ok = wert_gueltig(key, wert) and not (key == "security_ablauf" and ablauf_ausserhalb(wert))
            if not ok:
                if key not in gemeldet:
                    gemeldet.add(key)
                    funde.append(f"Angabe {key} fehlt oder ist ungueltig ({rel}:{zeile(roh, m.start())})")
                return m.group(0)
            if getarnt and rel not in GETARNT_DATEIEN:
                if key not in gemeldet:
                    gemeldet.add(key)
                    funde.append(f"Getarnte Marke {roh_key} nur in index.html erlaubt ({rel}:{zeile(roh, m.start())})")
                return m.group(0)
            if getarnt:
                return mail_getarnt(wert)
            if pfad.suffix.lower() == ".txt":
                return "".join(wert.split())
            return html.escape(wert, quote=True)

        neu = ANGABE_RE.sub(ersatz, roh)
        if neu != roh:
            pfad.write_bytes(neu.encode("utf-8"))
    return funde


def main(argv: list[str] | None = None) -> int:
    """`python pruefen_angaben.py --einsetzen DIST`: Werte aus ANGABE_<KEY> (Umgebung)."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "--einsetzen":
        print("Aufruf: python pruefen_angaben.py --einsetzen DIST")
        return 2
    dist = Path(args[1])
    if not dist.is_dir():
        print(f"FEHLER: {dist} ist kein Ordner")
        return 2
    werte = {k[len("ANGABE_"):].lower(): v for k, v in os.environ.items() if k.startswith("ANGABE_")}
    funde = angaben_einsetzen(dist, werte)
    for f in funde:
        print(f"  ROT  {f}")
    print(f"{len(funde)} Befund(e)." if funde else "Alle Angaben eingesetzt.")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
