const mostrarClave = document.querySelector('[data-mostrar-clave]');
document.querySelectorAll('[data-guardar-modificada]').forEach(formulario => {
  const guardar = formulario.querySelector('[data-guardar-cambios]');
  if (!guardar) return;
  const inicial = new URLSearchParams(new FormData(formulario)).toString();
  function actualizarGuardado() {
    guardar.hidden = new URLSearchParams(new FormData(formulario)).toString() === inicial;
  }
  formulario.addEventListener('input', actualizarGuardado);
  formulario.addEventListener('change', actualizarGuardado);
  actualizarGuardado();
});
document.querySelectorAll('[data-abrir-dialogo]').forEach(boton => {
  boton.addEventListener('click', () => {
    const dialogo = document.getElementById(boton.dataset.abrirDialogo);
    if (!dialogo || dialogo.open) return;
    dialogo.showModal();
    dialogo.querySelector('input:not([type="hidden"]), select, textarea')?.focus();
  });
});
document.querySelectorAll('[data-cerrar-dialogo]').forEach(boton => {
  boton.addEventListener('click', () => boton.closest('dialog')?.close());
});
document.querySelectorAll('[data-desplegar-bienes]').forEach(boton => {
  boton.addEventListener('click', () => {
    const inventario = document.getElementById(boton.dataset.desplegarBienes);
    if (!inventario) return;
    inventario.hidden = !inventario.hidden;
    boton.setAttribute('aria-expanded', String(!inventario.hidden));
  });
});
const selectorReporte = document.querySelector('[data-seleccionar-reporte]');
selectorReporte?.addEventListener('change', () => selectorReporte.form.requestSubmit());
document.querySelectorAll('[data-filtrar-al-cambiar]').forEach(selector => {
  selector.addEventListener('change', () => selector.form.requestSubmit());
});
mostrarClave?.addEventListener('change', () => {
  const clave = document.getElementById('clave');
  if (clave) clave.type = mostrarClave.checked ? 'text' : 'password';
});

const botonMenu = document.getElementById('menu-toggle');
const sombraMenu = document.getElementById('menu-sombra');
function cambiarMenu(abierto) {
  document.body.classList.toggle('menu-abierto', abierto);
  botonMenu?.setAttribute('aria-expanded', String(abierto));
  if (sombraMenu) sombraMenu.hidden = !abierto;
}
botonMenu?.addEventListener('click', () => cambiarMenu(!document.body.classList.contains('menu-abierto')));
sombraMenu?.addEventListener('click', () => cambiarMenu(false));
document.addEventListener('keydown', evento => {
  if (evento.key === 'Escape' && document.body.classList.contains('menu-abierto')) {
    cambiarMenu(false);
    botonMenu?.focus();
  }
});

// La selección del tipo solo cambia los campos visibles. El dominio vuelve a validarlos.
const tipoPersona = document.querySelector('[name="tipo"]');
function mostrarDatosInstitucionales() {
  const correo = document.querySelector('[name="correo"]');
  if (correo && tipoPersona) correo.required = tipoPersona.value !== 'ESTUDIANTE';
  document.querySelectorAll('[data-tipo]').forEach(grupo => {
    const visible = grupo.dataset.tipo === tipoPersona?.value;
    grupo.hidden = !visible;
    grupo.disabled = !visible;
  });
}
tipoPersona?.addEventListener('change', mostrarDatosInstitucionales);
mostrarDatosInstitucionales();

document.querySelectorAll('[data-abrir-detalle]').forEach(enlace => {
  enlace.addEventListener('click', () => {
    const detalle = document.getElementById(enlace.dataset.abrirDetalle);
    if (detalle) detalle.open = true;
  });
});

function normalizarBusqueda(texto) {
  return texto.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}
document.querySelectorAll('[data-filtrar-filas]').forEach(campo => {
  function filtrar() {
    const consulta = normalizarBusqueda(campo.value);
    document.querySelectorAll(`#${campo.dataset.filtrarFilas} [data-busqueda]`).forEach(fila => {
      fila.hidden = !normalizarBusqueda(fila.dataset.busqueda).includes(consulta);
    });
  }
  campo.addEventListener('input', filtrar);
  const limpiar = document.querySelector(`[data-limpiar-busqueda="${campo.dataset.filtrarFilas}"]`);
  limpiar?.addEventListener('click', () => { campo.value = ''; filtrar(); campo.focus(); });
});
document.querySelectorAll('[data-volver]').forEach(boton => {
  boton.addEventListener('click', () => window.history.back());
});
document.querySelectorAll('form[data-confirmar]').forEach(formulario => {
  formulario.addEventListener('submit', evento => {
    if (!window.confirm(formulario.dataset.confirmar)) evento.preventDefault();
  });
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
      agregarTexto('Ingresa el DNI de ocho dígitos.');
      return;
    }
    consulta = new AbortController();
    const parametros = new URLSearchParams({dni_persona: documento.value.trim()});
    try {
      const respuesta = await fetch(`${formularioPrestamo.dataset.condicionesPrestamo}?${parametros}`, {signal: consulta.signal});
      if (!respuesta.ok) throw new Error('Consulta no disponible');
      const datos = await respuesta.json();
      documento.dataset.documento = documento.value;
      documento.dataset.nombre = datos.solicitante;
      actualizarResumen();
      agregarTexto(`${datos.pendientes} ${datos.pendientes === 1 ? 'bien pendiente' : 'bienes pendientes'}. Máximo permitido: ${datos.limite ?? 'sin configurar'}.`);
      if (datos.horario) agregarTexto(`Atención: ${datos.horario.apertura} a ${datos.horario.cierre}. Los plazos en horas terminan al cierre.`);
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

  const busqueda = formularioPrestamo.querySelector('[data-busqueda-persona]');
  const resultados = formularioPrestamo.querySelector('[data-resultados-persona]');
  const buscarBien = formularioPrestamo.querySelector('[data-buscar-bien]');
  let esperaPersona, consultaPersona;
  function actualizarResumen() {
    const modalidad = formularioPrestamo.elements.tipo_prestamo.value;
    const grupal = modalidad === 'GRUPAL';
    const integrantes = formularioPrestamo.querySelector('[data-integrantes-grupo]');
    integrantes.hidden = !grupal;
    formularioPrestamo.elements.participantes.disabled = !grupal;
    if (documento.dataset.documento !== documento.value) delete documento.dataset.nombre;
    const nombre = documento.dataset.nombre || documento.value || 'Sin seleccionar';
    formularioPrestamo.querySelector('[data-resumen-solicitante]').textContent = nombre;
    formularioPrestamo.querySelector('[data-resumen-modalidad]').textContent = grupal ? 'Grupal' : 'Individual';
    formularioPrestamo.querySelector('[data-resumen-uso]').textContent = formularioPrestamo.elements.salida_solicitada.checked ? 'Fuera de la institución' : 'Dentro de la institución';
    const seleccionados = [...formularioPrestamo.querySelectorAll('[name="bienes"]:checked')];
    formularioPrestamo.querySelector('[data-resumen-bienes]').textContent = String(seleccionados.length);
    formularioPrestamo.querySelector('[data-confirmar-prestamo]').disabled = !(
      /^[0-9]{8}$/.test(documento.value.trim()) && seleccionados.length && formularioPrestamo.elements.acepta_condiciones.checked
    );
  }
  formularioPrestamo.addEventListener('input', actualizarResumen);
  formularioPrestamo.addEventListener('change', actualizarResumen);
  actualizarResumen();
  buscarBien?.addEventListener('input', () => {
    const consultaBien = normalizarBusqueda(buscarBien.value);
    formularioPrestamo.querySelectorAll('[data-bien-texto]').forEach(fila => {
      fila.hidden = !normalizarBusqueda(fila.dataset.bienTexto).includes(consultaBien);
    });
  });
  async function consultarPersonas() {
    consultaPersona?.abort();
    resultados.replaceChildren();
    if (busqueda.value.trim().length < 2) return;
    consultaPersona = new AbortController();
    try {
      const parametros = new URLSearchParams({q: busqueda.value.trim()});
      const respuesta = await fetch(`${formularioPrestamo.dataset.buscarPersonas}?${parametros}`, {signal: consultaPersona.signal});
      if (!respuesta.ok) throw new Error('Búsqueda no disponible');
      const personas = await respuesta.json();
      for (const persona of personas) {
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.textContent = `${persona.nombres} ${persona.apellidos} · ${persona.dni}`;
        boton.addEventListener('click', () => {
          documento.value = persona.dni;
          documento.dataset.documento = persona.dni;
          documento.dataset.nombre = `${persona.nombres} ${persona.apellidos}`;
          resultados.replaceChildren();
          busqueda.value = documento.dataset.nombre;
          documento.dispatchEvent(new Event('input', {bubbles: true}));
        });
        resultados.append(boton);
      }
      if (!personas.length) resultados.textContent = 'No se encontraron registros.';
    } catch (error) {
      if (error.name !== 'AbortError') resultados.textContent = 'No se pudo consultar. Puedes introducir el DNI directamente.';
    }
  }
  busqueda?.addEventListener('input', () => {
    clearTimeout(esperaPersona);
    consultaPersona?.abort();
    esperaPersona = setTimeout(consultarPersonas, 250);
  });
}
