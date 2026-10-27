# Sicherheitslücken melden

Vermora ist ein privates Projekt. Ich nehme Hinweise auf Sicherheitslücken ernst und kümmere
mich darum, so schnell ich kann – eine feste Reaktionszeit kann ich nicht zusagen.

## Welche Fassung gepflegt wird

Gepflegt wird nur die jeweils **neueste veröffentlichte Fassung**. Eine Korrektur erscheint
als neue Fassung; ältere Fassungen erhalten keine eigenen Korrekturen.

| Fassung              | Gepflegt |
| -------------------- | -------- |
| neueste Fassung      | ja       |
| alle älteren Fassungen | nein   |

Welche Fassung die neueste ist, steht in [`releases.v1.txt`](releases.v1.txt) und in der
Anwendung unter *Einstellungen → Update*.

## Wie Sie eine Lücke melden

Bitte **nicht** über ein öffentliches Issue, sondern vertraulich:

1. **Über GitHub:** Reiter *Security* → *Report a vulnerability*. Die Meldung sehen nur Sie und ich.
2. **Per E-Mail** an die Adresse in <https://vermora.de/.well-known/security.txt> (steht auch im Impressum).

Hilfreich sind:

- betroffene Fassung (z. B. 5.15.0) und Betriebsort (Windows, NAS, Server),
- Schritte, mit denen sich die Lücke nachvollziehen lässt,
- was ein Angreifer damit erreichen könnte.

**Bitte keine eigenen Finanzdaten, Kontoauszüge, Datenbanken oder Sicherungen mitschicken** –
auch nicht in Bildschirmfotos oder Protokollauszügen. Für die Nachstellung genügen erfundene Werte.

## Was danach passiert

1. Ich bestätige den Eingang und melde mich, sobald ich die Meldung bewertet habe.
2. Bestätigt sich die Lücke, erscheint eine korrigierte Fassung. Im Änderungsprotokoll und
   hier unter *Security → Advisories* steht, was betroffen war und ab welcher Fassung es
   behoben ist.
3. Bitte veröffentlichen Sie Einzelheiten erst, wenn die korrigierte Fassung verfügbar ist.
   Wenn Sie möchten, nenne ich Sie im Hinweis; sonst bleibt die Meldung anonym.

## Was hier dazugehört

- die Anwendung Vermora (Abbild und Starterpaket),
- die Update-Prüfung und die Signatur der Fassungsliste,
- die Website vermora.de.

Nicht dazu gehören Lücken in Docker, im Betriebssystem, im NAS oder in Erweiterungen, die Sie
selbst eingebunden haben. Bitte melden Sie diese beim jeweiligen Hersteller.

## Wie ich selbst prüfe

Ich verlasse mich nicht allein auf Meldungen von außen. Einmal pro Woche, montags früh,
untersucht eine automatische Prüfung zwei Dinge auf bekannte Sicherheitslücken in
Bibliotheken und Systempaketen: das Vermora-Abbild und das mitgelieferte Caddy-Abbild
(der Webserver davor).

- **Was gemeldet wird:** Funde, für die es bereits eine korrigierte Fassung des betroffenen
  Pakets gibt. Funde ohne verfügbare Korrektur zähle ich nur mit, damit sie nicht jede
  Woche dieselbe Meldung erzeugen.
- **Was ich ernst nehme:** Kritische Funde und alle Funde der Stufe „hoch“ lege ich als
  eigenen Befund an und gehe sie vorrangig an.
- **Was daraus wird:** Ein behobener Fund erscheint mit der nächsten veröffentlichten
  Fassung. Das Änderungsprotokoll nennt, was betroffen war.

Das ist meine eigene Arbeitsweise, keine Zusage. Eine Frist für Korrekturen verspreche ich
damit nicht, und auch eine Prüfung ohne Fund ist keine Garantie, dass keine Lücke besteht.

## Gut zu wissen

Vermora sendet keine Nutzungs- oder Fehlerdaten an mich. Aus Ihrer Instanz erfahre ich nichts. Hinweise auf Lücken
bekomme ich nur durch meine Prüfung des Abbilds oder wenn Sie mir etwas melden. Ihre Instanz läuft bei Ihnen; ich habe keinen Zugriff darauf und
kann eine Korrektur nicht selbst einspielen – das Update führen Sie aus.
