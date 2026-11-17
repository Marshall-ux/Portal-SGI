/* Canales de participación y reporte: «¿Cuándo usarlo?» despliega el cuadro del canal debajo
   de la fila de su tarjeta (con tres, dos o una tarjeta por fila, según el ancho).
   Se abre de a uno; se cierra con su botón, con la X del cuadro o con Escape.
   Además iguala el alto de las tarjetas, para que las filas se vean parejas. */
(function () {
  var raiz = document.querySelector("[data-canales]");
  if (!raiz) return;
  var tarjetas = Array.prototype.slice.call(raiz.querySelectorAll(".canal-tarjeta"));
  var botones = tarjetas.map(function (t) { return t.querySelector(".canal-cuando"); });
  var suave = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function panelDe(boton) {
    return document.getElementById(boton.getAttribute("aria-controls"));
  }

  function tarjetaDe(boton) {
    return tarjetas[botones.indexOf(boton)];
  }

  function abierto(boton) {
    return boton.getAttribute("aria-expanded") === "true";
  }

  /* Tarjetas por fila según el ancho actual (3, 2 o 1). Las filas se llenan en orden, así que
     la fila de cada tarjeta sale de su posición, sin importar dónde esté el cuadro abierto. */
  function porFila() {
    var hueco = parseFloat(window.getComputedStyle(raiz).columnGap) || 0;
    return Math.max(1, Math.round((raiz.clientWidth + hueco) / (tarjetas[0].offsetWidth + hueco)));
  }

  /* El cuadro va después de la última tarjeta de la fila de su canal. */
  function ubicar(boton) {
    var panel = panelDe(boton);
    var tarjeta = tarjetaDe(boton);
    var n = porFila();
    var ultima = tarjetas[Math.min((Math.floor(botones.indexOf(boton) / n) + 1) * n, tarjetas.length) - 1];
    if (ultima.nextElementSibling !== panel) {
      // Moverlo le quita el foco: se le devuelve a quien lo tenía
      var foco = panel.contains(document.activeElement) ? document.activeElement : null;
      raiz.insertBefore(panel, ultima.nextSibling);
      if (foco) foco.focus({ preventScroll: true });
    }
    // La flecha del cuadro apunta al centro de su tarjeta
    var centro = tarjeta.getBoundingClientRect().left + tarjeta.offsetWidth / 2;
    panel.style.setProperty("--flecha", (centro - panel.getBoundingClientRect().left) + "px");
  }

  function cerrar(boton) {
    boton.setAttribute("aria-expanded", "false");
    tarjetaDe(boton).classList.remove("canal-activa");
    panelDe(boton).hidden = true;
  }

  function abrir(boton) {
    botones.forEach(function (otro) { if (otro !== boton) cerrar(otro); });
    var panel = panelDe(boton);
    boton.setAttribute("aria-expanded", "true");
    tarjetaDe(boton).classList.add("canal-activa");
    panel.classList.remove("canal-quieto");  // al abrirse, aparece con su animación
    ubicar(boton);
    panel.hidden = false;
    ubicar(boton);  // ya visible: ahora se puede medir la flecha
    // El foco pasa al cuadro (así lo encuentra también el lector de pantalla) y, si quedó
    // fuera de la pantalla, se acerca solo.
    panel.focus({ preventScroll: true });
    panel.scrollIntoView({ block: "nearest", behavior: suave ? "smooth" : "auto" });
  }

  function igualarAltos() {
    tarjetas.forEach(function (t) { t.style.minHeight = ""; });
    // Con una tarjeta por fila (celular) no hace falta
    if (tarjetas.length < 2 || tarjetas[0].offsetTop !== tarjetas[1].offsetTop) return;
    var alto = Math.max.apply(null, tarjetas.map(function (t) { return t.offsetHeight; }));
    tarjetas.forEach(function (t) { t.style.minHeight = alto + "px"; });
  }

  function acomodar() {
    igualarAltos();
    botones.forEach(function (boton) {
      if (!abierto(boton)) return;
      // Si cambia de fila al achicar o agrandar la ventana, se mueve sin repetir la animación
      panelDe(boton).classList.add("canal-quieto");
      ubicar(boton);
    });
  }

  botones.forEach(function (boton) {
    var panel = panelDe(boton);
    function cerrarYVolver() { cerrar(boton); boton.focus(); }

    boton.addEventListener("click", function () {
      if (abierto(boton)) cerrar(boton); else abrir(boton);
    });
    boton.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && abierto(boton)) cerrar(boton);
    });
    panel.querySelector(".canal-cerrar").addEventListener("click", cerrarYVolver);
    panel.addEventListener("keydown", function (e) {
      if (e.key === "Escape") cerrarYVolver();
    });
  });

  var pendiente = false;
  window.addEventListener("resize", function () {
    if (pendiente) return;
    pendiente = true;
    window.requestAnimationFrame(function () { pendiente = false; acomodar(); });
  });
  acomodar();
  // Las tipografías cambian el alto de los textos: se vuelve a medir cuando terminan de cargar
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(acomodar);
})();
