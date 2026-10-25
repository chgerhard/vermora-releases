/* Bildstrecke (Issue #1234 D1): macht aus der Liste der Bilder ein Karussell mit Zurueck/Weiter.
   Fortschreitende Verbesserung: ohne dieses Skript stehen alle Bilder untereinander und sind
   erreichbar. Kein Netzwerkaufruf, keine Bibliothek.

   Beim Scrollen (Wunsch Christian 20.10.2026, Ausnahme zu Styleguide "Bewegung"):
   - Die Strecke bleibt im Fenster stehen (position: sticky, normales Scrollen, nichts wird
     abgefangen); jedes Stueck Scrollweg schaltet das naechste Bild, nach dem letzten laeuft die
     Seite mit dem naechsten Text weiter. Zurueckscrollen schaltet zurueck.
   - Zurueck/Weiter und Pfeiltasten scrollen zum jeweiligen Bild (kein eigener Weg am Scrollen vorbei).
   - Bei prefers-reduced-motion und in kleinen/niedrigen Fenstern gibt es kein Festhalten und
     keine an das Scrollen gekoppelte Bewegung: dort schalten nur Zurueck/Weiter, ohne Uebergang.
   Die Ansage fuer Vorleseprogramme (aria-live) wird nur nach einer Bedienung befuellt,
   nie beim Laden und nie beim Scrollen. */
document.addEventListener('DOMContentLoaded', function () {
  var wurzel = document.querySelector('.bildstrecke');
  if (!wurzel) { return; }
  var folien = Array.prototype.slice.call(wurzel.querySelectorAll('.bs-folie'));
  var behaelter = wurzel.querySelector('.bs-folien');
  if (folien.length < 2 || !behaelter) { return; }

  var n = folien.length;
  var index = 0;
  var scrollModus = !!(window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: no-preference) and (min-height: 37.5rem)').matches);
  var SCHRITT = 0.55;  // Scrollweg je Bild, in Fensterhoehen

  wurzel.setAttribute('aria-roledescription', 'Karussell');
  wurzel.classList.add('aktiv');
  if (!behaelter.id) { behaelter.id = 'bs-folien'; }

  folien.forEach(function (f, i) {
    f.setAttribute('aria-roledescription', 'Folie');
    f.setAttribute('aria-label', (i + 1) + ' von ' + n);
  });

  function knopf(text) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'knopf';
    b.textContent = text;
    b.setAttribute('aria-controls', behaelter.id);
    return b;
  }

  var leiste = document.createElement('div');
  leiste.className = 'bs-leiste';
  var zurueck = knopf('Zurück');
  var weiter = knopf('Weiter');
  var zaehler = document.createElement('p');
  zaehler.className = 'bs-zaehler';
  var ansage = document.createElement('p');
  ansage.className = 'sr-hinweis';
  ansage.setAttribute('aria-live', 'polite');
  ansage.setAttribute('aria-atomic', 'true');
  leiste.appendChild(zurueck);
  leiste.appendChild(zaehler);
  leiste.appendChild(weiter);
  leiste.appendChild(ansage);

  var spur = null;
  var buehne = null;
  if (scrollModus) {
    spur = document.createElement('div');
    spur.className = 'bs-spur';
    buehne = document.createElement('div');
    buehne.className = 'bs-buehne';
    wurzel.insertBefore(spur, behaelter);
    spur.appendChild(buehne);
    buehne.appendChild(leiste);
    buehne.appendChild(behaelter);
    wurzel.classList.add('bs-scroll');
  } else {
    wurzel.insertBefore(leiste, behaelter);
  }

  function zeige(neu, nachBedienung) {
    index = Math.max(0, Math.min(n - 1, neu));
    folien.forEach(function (f, i) { f.classList.toggle('ist', i === index); });
    var text = 'Bild ' + (index + 1) + ' von ' + n;
    zaehler.textContent = text;
    zurueck.disabled = (index === 0);
    weiter.disabled = (index === n - 1);
    if (nachBedienung) { ansage.textContent = text; }
  }

  /* --- Scrollmodus -------------------------------------------------------- */
  function schritt() { return SCHRITT * window.innerHeight; }

  function obenAbstand() {
    return parseFloat(window.getComputedStyle(buehne).top) || 0;
  }

  function spurHoehe() {
    spur.style.height = (buehne.offsetHeight + n * schritt()) + 'px';
  }

  function ausScrollen() {
    var r = spur.getBoundingClientRect();
    var weg = obenAbstand() - r.top;  // wie weit die Spur ueber den Haltepunkt gelaufen ist
    var neu = Math.floor(weg / schritt());
    neu = Math.max(0, Math.min(n - 1, neu));
    if (neu !== index) { zeige(neu, false); }
  }

  function zuBild(neu) {
    var ziel = Math.max(0, Math.min(n - 1, neu));
    var r = spur.getBoundingClientRect();
    var spurOben = window.pageYOffset + r.top - obenAbstand();
    var y = spurOben + (ziel + 0.5) * schritt();
    var sanft = window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
    window.scrollTo({ top: y, behavior: sanft ? 'smooth' : 'auto' });
    zeige(ziel, true);
  }

  function bedient(neu) {
    if (scrollModus) { zuBild(neu); } else { zeige(neu, true); }
  }

  zurueck.addEventListener('click', function () { bedient(index - 1); });
  weiter.addEventListener('click', function () { bedient(index + 1); });
  wurzel.addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) { return; }
    if (e.key === 'ArrowLeft') { e.preventDefault(); bedient(index - 1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); bedient(index + 1); }
  });

  if (scrollModus) {
    var wartet = false;
    window.addEventListener('scroll', function () {
      if (wartet) { return; }
      wartet = true;
      window.requestAnimationFrame(function () { wartet = false; ausScrollen(); });
    }, { passive: true });
    window.addEventListener('resize', function () { spurHoehe(); ausScrollen(); });
    window.addEventListener('load', function () { spurHoehe(); ausScrollen(); });
    spurHoehe();
    ausScrollen();
  }

  zeige(index, false);
});
