/* E-Mail-Adresse der Startseite (Issue #1281): Beim Veroeffentlichen steht im HTML nur
   "name [at] domain [punkt] tld" plus data-u/data-d (rueckwaerts), nie die zusammenhaengende
   Adresse -- gegen automatisches Einsammeln. Dieses Skript baut daraus fuer Menschen einen
   echten mailto-Link. Ohne Skript bleibt der lesbare Text stehen (zum Abtippen).
   Kein Netzwerkaufruf, keine Bibliothek, kein Inline-Skript (CSP). */
document.addEventListener('DOMContentLoaded', function () {
  var stellen = document.querySelectorAll('.mail-getarnt[data-u][data-d]');
  Array.prototype.forEach.call(stellen, function (stelle) {
    var u = stelle.getAttribute('data-u').split('').reverse().join('');
    var d = stelle.getAttribute('data-d').split('').reverse().join('');
    if (!u || !d) { return; }
    var adresse = u + String.fromCharCode(64) + d;
    var link = document.createElement('a');
    link.href = 'mailto:' + adresse;
    link.textContent = adresse;
    stelle.parentNode.replaceChild(link, stelle);
  });
});
