"use strict";

// La validación definitiva del plazo y la categoría permanece en el servidor.
for (const formulario of document.querySelectorAll(".politica-celda")) {
  const unidad = formulario.elements.unidad_plazo;
  const plazo = formulario.elements.plazo_maximo;
  const actualizar = () => {
    plazo.max = unidad.value === "HORAS" ? "87600" : "3650";
  };
  unidad.addEventListener("change", actualizar);
  actualizar();
}

const buscar = document.getElementById("buscar-categoria-politicas");
const filas = [...document.querySelectorAll("[data-categoria-politicas]")];
const normalizar = texto => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
if (buscar) {
  const filtrar = () => {
    let visibles = 0;
    for (const fila of filas) {
      fila.hidden = !normalizar(fila.dataset.nombre).includes(normalizar(buscar.value.trim()));
      if (!fila.hidden) visibles++;
    }
    document.getElementById("politicas-sin-resultados").hidden = visibles !== 0 || filas.length === 0;
  };
  buscar.addEventListener("input", filtrar);
  document.getElementById("limpiar-filtros-politicas").addEventListener("click", () => {
    buscar.value = ""; filtrar(); buscar.focus();
  });
}
