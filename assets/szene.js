/* Schemata bauen sich einmal auf, sobald sie ins Sichtfeld kommen (Issue #1005,
   Styleguide Paragraph 4). Einziges Skript der Seite, keine fremde Quelle, keine Daten.
   Ohne dieses Skript oder ohne IntersectionObserver steht sofort das fertige Bild:
   site.css versteckt die Schritte nur unter html.js. */
(function () {
  if (!('IntersectionObserver' in window)) return;
  document.documentElement.classList.add('js');
  document.addEventListener('DOMContentLoaded', function () {
    var beobachter = new IntersectionObserver(function (eintraege) {
      eintraege.forEach(function (eintrag) {
        if (!eintrag.isIntersecting) return;
        eintrag.target.classList.add('laeuft');
        beobachter.unobserve(eintrag.target);
      });
    }, { threshold: 0.4 });
    document.querySelectorAll('.szene-aufbau').forEach(function (szene) {
      beobachter.observe(szene);
    });
  });
})();
