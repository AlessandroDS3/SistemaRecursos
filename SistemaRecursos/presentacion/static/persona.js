"use strict";

const selectorTipoPersona = document.getElementById("tipo");
const formularioPersona = document.getElementById("form-persona");

if (selectorTipoPersona && formularioPersona) {
  function mostrarTipo() {
    let titulo = "Datos del tipo de persona";
    if (selectorTipoPersona.value) {
      titulo = selectorTipoPersona.selectedOptions[0].textContent;
    }
    document.getElementById("titulo-datos-academicos").textContent = titulo;

    for (const grupo of document.querySelectorAll("fieldset[data-tipo]")) {
      grupo.hidden = grupo.dataset.tipo !== selectorTipoPersona.value;
      grupo.disabled = grupo.hidden;
    }
  }

  function mostrarErrorPersona(campo) {
    const error = document.getElementById("error-" + campo.name);
    if (!error) return;
    let mensaje = "";
    if (!campo.validity.valid) {
      if (campo.name === "cui" || campo.name === "dni") {
        mensaje = "El " + campo.name.toUpperCase() + " debe tener exactamente 8 dígitos.";
      } else if (campo.validity.valueMissing) {
        if (campo.tagName === "SELECT") mensaje = "Selecciona una opción.";
        else mensaje = "Este campo es obligatorio.";
      } else if (campo.type === "email") {
        mensaje = "Ingresa un correo válido, por ejemplo nombre@dominio.com.";
      } else if (campo.name === "ciclo") {
        mensaje = "El ciclo debe ser un entero positivo o quedar vacío.";
      } else {
        mensaje = "Revisa el valor ingresado.";
      }
    }
    error.textContent = mensaje;
    campo.setAttribute("aria-invalid", String(Boolean(mensaje)));
  }

  selectorTipoPersona.addEventListener("change", mostrarTipo);
  mostrarTipo();
  formularioPersona.addEventListener("invalid", evento => mostrarErrorPersona(evento.target), true);
  for (const campo of formularioPersona.querySelectorAll("input:not([type=hidden]), select")) {
    campo.addEventListener("input", () => mostrarErrorPersona(campo));
    campo.addEventListener("change", () => mostrarErrorPersona(campo));
  }
}
