"use strict";

// Menu lateral.
const controlMenu = document.getElementById("menu-toggle");
const sombraMenu = document.getElementById("menu-sombra");
const menuLateral = document.getElementById("menu-principal");
const pantallaAmplia = window.matchMedia("(min-width: 901px)");

function actualizarAccesoMenu() {
  if (menuLateral) {
    menuLateral.inert = !pantallaAmplia.matches && !document.body.classList.contains("menu-lateral-abierto");
  }
}

function cerrarMenu() {
  document.body.classList.remove("menu-lateral-abierto");
  if (controlMenu) {
    controlMenu.setAttribute("aria-expanded", "false");
    controlMenu.setAttribute("aria-label", "Abrir menú");
  }
  if (sombraMenu) sombraMenu.hidden = true;
  actualizarAccesoMenu();
}

if (controlMenu) {
  controlMenu.addEventListener("click", () => {
    const abrir = !document.body.classList.contains("menu-lateral-abierto");
    document.body.classList.toggle("menu-lateral-abierto", abrir);
    controlMenu.setAttribute("aria-expanded", String(abrir));
    if (abrir) controlMenu.setAttribute("aria-label", "Cerrar menú");
    else controlMenu.setAttribute("aria-label", "Abrir menú");
    if (sombraMenu) sombraMenu.hidden = !abrir;
    actualizarAccesoMenu();
  });
}
if (sombraMenu) sombraMenu.addEventListener("click", cerrarMenu);
document.addEventListener("keydown", evento => {
  if (evento.key === "Escape" && document.body.classList.contains("menu-lateral-abierto")) {
    cerrarMenu();
    if (controlMenu) controlMenu.focus();
  }
});
pantallaAmplia.addEventListener("change", cerrarMenu);
actualizarAccesoMenu();

// Mostrar u ocultar la contrasena.
const mostrarClave = document.getElementById("mostrar-clave");
const campoClave = document.getElementById("clave");
if (mostrarClave && campoClave) {
  mostrarClave.addEventListener("change", () => {
    if (mostrarClave.checked) campoClave.type = "text";
    else campoClave.type = "password";
  });
}

// Todos los enlaces de registro abren el mismo formulario.
for (const enlace of document.querySelectorAll("[data-abrir-registro]")) {
  enlace.addEventListener("click", () => {
    const registro = document.getElementById("registro-recurso");
    if (registro) registro.open = true;
  });
}

// Limite del plazo segun la unidad elegida.
const unidadPlazoPolitica = document.getElementById("unidad-plazo-politica");
const plazoMaximoPolitica = document.getElementById("plazo-maximo-politica");
const ayudaPlazoPolitica = document.getElementById("ayuda-plazo-politica");
if (unidadPlazoPolitica && plazoMaximoPolitica && ayudaPlazoPolitica) {
  function actualizarLimitePlazo() {
    if (unidadPlazoPolitica.value === "HORAS") {
      plazoMaximoPolitica.max = "87600";
      ayudaPlazoPolitica.textContent = "Máximo: 87600 horas.";
    } else {
      plazoMaximoPolitica.max = "3650";
      ayudaPlazoPolitica.textContent = "Máximo: 3650 días.";
    }
  }
  unidadPlazoPolitica.addEventListener("change", actualizarLimitePlazo);
  actualizarLimitePlazo();
}
