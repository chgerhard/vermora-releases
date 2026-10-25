/* Issue #1284: Tastaturbedienung des Seitenmenues der Anleitung bei schmalem Fenster.
   Ursache im Material-Standard: Das Menue-Symbol (label[for=__drawer]) ist kein Tastaturziel,
   und die Links im ausgeblendeten Seitenmenue bleiben per Tab erreichbar (unsichtbarer Fokus).
   Abhilfe: Symbol wird zur Schaltflaeche (Tab, Enter/Leertaste, aria-expanded), das geschlossene
   Menue wird bei schmalem Fenster inert, Esc schliesst und gibt den Fokus zurueck.
   Fortschreitende Verbesserung, kein Netzwerkaufruf, kein Inline-Skript (CSP der Website). */
(function () {
  'use strict';
  var schalter = document.getElementById('__drawer');
  var knopf = document.querySelector('label.md-header__button[for="__drawer"]');
  var menue = document.querySelector('.md-sidebar--primary');
  if (!schalter || !knopf || !menue) { return; }

  var schmal = window.matchMedia('(max-width: 76.1875em)');

  knopf.setAttribute('tabindex', '0');
  knopf.setAttribute('role', 'button');
  knopf.setAttribute('aria-label', 'Navigation');
  menue.id = menue.id || 'md-sidebar-primary';
  knopf.setAttribute('aria-controls', menue.id);

  function abgleichen() {
    var offen = schalter.checked;
    knopf.setAttribute('aria-expanded', offen ? 'true' : 'false');
    // Breites Fenster: Menue ist die feste Seitenleiste und bedienbar. Schmal und zu: unsichtbar.
    if (schmal.matches && !offen) {
      menue.setAttribute('inert', '');
    } else {
      menue.removeAttribute('inert');
    }
  }

  function umschalten() {
    schalter.checked = !schalter.checked;
    schalter.dispatchEvent(new Event('change', { bubbles: true }));
    if (schalter.checked) {
      var erster = menue.querySelector('a[href]');
      if (erster) { erster.focus(); }
    }
  }

  knopf.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      e.preventDefault();
      umschalten();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && schmal.matches && schalter.checked) {
      schalter.checked = false;
      schalter.dispatchEvent(new Event('change', { bubbles: true }));
      knopf.focus();
    }
  });

  schalter.addEventListener('change', abgleichen);
  if (schmal.addEventListener) { schmal.addEventListener('change', abgleichen); }
  abgleichen();
})();
