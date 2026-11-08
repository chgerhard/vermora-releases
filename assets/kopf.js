/* Aktiver Abschnitt im Kopf (Issue #1348): der Abschnitt in der Bildschirmmitte setzt
   aria-current="location" am passenden Navigationslink. Kein Scrollen, keine Daten.
   Ohne dieses Skript oder ohne IntersectionObserver bleibt die Navigation unveraendert. */
(function () {
  if (!('IntersectionObserver' in window)) return;
  document.addEventListener('DOMContentLoaded', function () {
    var links = document.querySelectorAll('.kopf nav a[href^="#"]');
    var nachId = {};
    var beobachter = new IntersectionObserver(function (eintraege) {
      eintraege.forEach(function (eintrag) {
        if (!eintrag.isIntersecting) return;
        Object.keys(nachId).forEach(function (id) {
          if (id === eintrag.target.id) nachId[id].setAttribute('aria-current', 'location');
          else nachId[id].removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Array.prototype.forEach.call(links, function (link) {
      var id = link.getAttribute('href').slice(1);
      var abschnitt = document.getElementById(id);
      if (!abschnitt || abschnitt.tagName !== 'SECTION') return;
      nachId[id] = link;
      beobachter.observe(abschnitt);
    });
  });
})();
