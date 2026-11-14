// La selección del tipo solo cambia los campos visibles. El dominio vuelve a validarlos.
const tipoPersona = document.querySelector('[name="tipo"]');
function mostrarDatosInstitucionales() {
  document.querySelectorAll('[data-tipo]').forEach(grupo => {
    const visible = grupo.dataset.tipo === tipoPersona?.value;
    grupo.hidden = !visible;
    grupo.disabled = !visible;
  });
}
tipoPersona?.addEventListener('change', mostrarDatosInstitucionales);
mostrarDatosInstitucionales();
document.querySelectorAll('[data-volver]').forEach(boton => {
  boton.addEventListener('click', () => window.history.back());
});

const recursoReserva = document.querySelector('[data-condiciones-reserva]');
function mostrarCondicionesReserva() {
  const texto = document.querySelector('[data-texto-condiciones-reserva]');
  if (texto) texto.textContent = recursoReserva.selectedOptions[0]?.dataset.condiciones || 'Selecciona un recurso con política vigente.';
}
recursoReserva?.addEventListener('change', mostrarCondicionesReserva);
mostrarCondicionesReserva();

const formularioPrestamo = document.querySelector('[data-condiciones-prestamo]');
if (formularioPrestamo) {
  const documento = formularioPrestamo.elements.dni_persona;
  const panel = formularioPrestamo.querySelector('[data-texto-condiciones-prestamo]');
  let tarea, consulta;
  function agregarTexto(texto) {
    const parrafo = document.createElement('p');
    parrafo.textContent = texto;
    panel.append(parrafo);
  }
  async function consultarCondiciones() {
    consulta?.abort();
    panel.replaceChildren();
    if (!/^[0-9]{8}$/.test(documento.value.trim())) {
      agregarTexto('Completa un DNI de ocho dígitos.');
      return;
    }
    consulta = new AbortController();
    const parametros = new URLSearchParams({dni_persona: documento.value.trim()});
    try {
      const respuesta = await fetch(`${formularioPrestamo.dataset.condicionesPrestamo}?${parametros}`, {signal: consulta.signal});
      if (!respuesta.ok) throw new Error('Consulta no disponible');
      const datos = await respuesta.json();
      agregarTexto(`${datos.solicitante}: ${datos.pendientes} bienes pendientes. Máximo total: ${datos.limite ?? 'sin configurar'}.`);
      if (datos.horario) agregarTexto(`Atención de ${datos.horario.apertura} a ${datos.horario.cierre} de Lima. Los plazos en horas terminan al cierre.`);
      for (const politica of datos.politicas) {
        agregarTexto(`${politica.categoria}: ${politica.plazo_maximo} ${politica.unidad_plazo.toLowerCase()}; salida externa ${politica.permite_salida ? 'permitida' : 'no permitida'}.`);
      }
      if (!datos.politicas.length) agregarTexto('No hay políticas vigentes para este tipo de persona.');
    } catch (error) {
      if (error.name !== 'AbortError') agregarTexto('No se pudieron consultar las condiciones. Revisa el DNI y el estado de la persona.');
    }
  }
  documento.addEventListener('input', () => {
    clearTimeout(tarea);
    consulta?.abort();
    tarea = setTimeout(consultarCondiciones, 300);
  });
}
