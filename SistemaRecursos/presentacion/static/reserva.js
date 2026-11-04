"use strict";

const tipoGestion = document.getElementById("tipo-gestion");
const fechaReserva = document.getElementById("fecha-reserva");
const campoFechaReserva = document.getElementById("campo-fecha-reserva");

if (tipoGestion && fechaReserva && campoFechaReserva) {
  function actualizarFechaReserva() {
    const esReserva = tipoGestion.value === "RESERVA";
    campoFechaReserva.hidden = !esReserva;
    fechaReserva.required = esReserva;
    fechaReserva.disabled = !esReserva;
  }
  tipoGestion.addEventListener("change", actualizarFechaReserva);
  actualizarFechaReserva();
}

const formularioReserva = document.getElementById("form-reserva");
if (formularioReserva) {
  let hayPolitica = false;
  const tipoPersona = formularioReserva.dataset.tipoPersona;
  for (const fila of document.querySelectorAll("[data-politica-persona]")) {
    fila.hidden = fila.dataset.politicaPersona !== tipoPersona;
    if (!fila.hidden) hayPolitica = true;
  }
  document.getElementById("politica-no-disponible").hidden = hayPolitica;
  formularioReserva.querySelector("button.boton-principal").disabled = !hayPolitica;
}
