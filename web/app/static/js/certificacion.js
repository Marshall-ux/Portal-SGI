/* Certificación vigente: cada norma despliega su descripción en la misma página.
   Se abre de a una; se cierra con su botón, con la X del cuadro o con Escape. */
(function () {
  var raiz = document.querySelector("[data-normas]");
  if (!raiz) return;
  var botones = Array.prototype.slice.call(raiz.querySelectorAll(".norma-boton"));

  function panelDe(boton) {
    return document.getElementById(boton.getAttribute("aria-controls"));
  }

  function abierto(boton) {
    return boton.getAttribute("aria-expanded") === "true";
  }

  function cerrar(boton) {
    boton.setAttribute("aria-expanded", "false");
    panelDe(boton).hidden = true;
  }

  function abrir(boton) {
    botones.forEach(function (otro) { if (otro !== boton) cerrar(otro); });
    var panel = panelDe(boton);
    boton.setAttribute("aria-expanded", "true");
    panel.hidden = false;
    // Si el cuadro queda fuera de la pantalla (celulares), se acerca solo.
    var suave = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    panel.scrollIntoView({ block: "nearest", behavior: suave ? "smooth" : "auto" });
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
    panel.querySelector(".norma-cerrar").addEventListener("click", cerrarYVolver);
    panel.addEventListener("keydown", function (e) {
      if (e.key === "Escape") cerrarYVolver();
    });
  });
})();
