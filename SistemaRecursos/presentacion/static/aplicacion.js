const datosFormulario = document.getElementById('datos-formulario');
const recuperacionFormulario = datosFormulario ? JSON.parse(datosFormulario.textContent) : null;
function esFormularioRecuperado(formulario) {
  if (!recuperacionFormulario) return false;
  const destino = new URL(formulario.getAttribute('action') || window.location.pathname, window.location.origin);
  if (destino.pathname !== recuperacionFormulario.destino) return false;
  const identificador = recuperacionFormulario.valores._formulario?.[0];
  if (identificador && formulario.querySelector('[name="_formulario"]')?.value !== identificador) return false;
  const documento = formulario.querySelector('input[type="hidden"][name="dni"]');
  return !documento || !recuperacionFormulario.valores.dni || recuperacionFormulario.valores.dni.includes(documento.value);
}
if (recuperacionFormulario) {
  for (const formulario of document.querySelectorAll('form')) {
    if (!esFormularioRecuperado(formulario)) continue;
    for (const campo of formulario.elements) {
      if (!campo.name || campo.type === 'password' || campo.name === 'csrf_token') continue;
      const valores = recuperacionFormulario.valores[campo.name];
      if (campo.type === 'checkbox') campo.checked = Boolean(valores?.includes(campo.value));
      else if (campo.type === 'radio' && valores) campo.checked = valores.includes(campo.value);
      else if (valores) campo.value = valores[0];
    }
    const detalle = formulario.closest('details');
    if (detalle) detalle.open = true;
    const dialogo = formulario.closest('dialog');
    if (dialogo && !dialogo.open) dialogo.showModal();
  }
}

let numeroErrorCampo = 0;
let primerCampoConError;
function mostrarErrorCampo(campo, mensaje) {
  const etiqueta = campo.closest('label');
  if (!etiqueta) return;
  let texto = etiqueta.querySelector('.error-campo');
  if (!texto && mensaje) {
    texto = document.createElement('small');
    texto.className = 'error-campo';
    texto.id = `error-formulario-${++numeroErrorCampo}`;
    etiqueta.append(texto);
    campo.setAttribute('aria-describedby', `${campo.getAttribute('aria-describedby') || ''} ${texto.id}`.trim());
  }
  if (texto) { texto.textContent = mensaje; texto.hidden = !mensaje; }
  campo.setAttribute('aria-invalid', String(Boolean(mensaje)));
}
for (const formulario of document.querySelectorAll('form')) {
  formulario.addEventListener('invalid', evento => mostrarErrorCampo(evento.target, evento.target.validationMessage), true);
  formulario.addEventListener('input', evento => {
    if (evento.target.getAttribute('aria-invalid') === 'true') {
      mostrarErrorCampo(evento.target, evento.target.validity.valid ? '' : evento.target.validationMessage);
    }
  });
  if (esFormularioRecuperado(formulario)) {
    for (const campo of formulario.elements) {
      if (recuperacionFormulario.errores[campo.name]) {
        mostrarErrorCampo(campo, recuperacionFormulario.errores[campo.name]);
        if (campo.getClientRects().length && !campo.disabled && campo.type !== 'hidden') {
          primerCampoConError ??= campo;
        }
      }
    }
  }
}
if (recuperacionFormulario) {
  const destinoError = primerCampoConError || document.querySelector('.error-formulario');
  destinoError?.focus();
}

document.querySelectorAll('[data-fila-devolucion]').forEach(fila => {
  const seleccionar = fila.querySelector('[name="detalles"]');
  const condicion = fila.querySelector('select[name^="condicion_"]');
  const codigo = fila.querySelector('input[name^="codigo_recibido_"]');
  const observacion = fila.querySelector('input[name^="observacion_"]');
  const avisoDanio = fila.querySelector('[data-aviso-danio]');
  if (!seleccionar || !condicion || !observacion) return;
  const aviso = document.createElement('small');
  aviso.className = 'suave';
  aviso.textContent = 'Obligatoria para recibir un bien dañado.';
  observacion.closest('label').append(aviso);
  if (avisoDanio) {
    condicion.setAttribute('aria-describedby', [condicion.getAttribute('aria-describedby'), avisoDanio.id].filter(Boolean).join(' '));
  }
  function actualizar() {
    if (codigo) codigo.required = seleccionar.checked;
    observacion.required = seleccionar.checked && condicion.value === 'DANADO';
    observacion.setAttribute('aria-required', String(observacion.required));
    observacion.placeholder = condicion.value === 'DANADO' ? 'Describe el daño del bien' : 'Opcional';
    aviso.hidden = !observacion.required;
    if (avisoDanio) {
      avisoDanio.hidden = condicion.value !== 'DANADO';
      avisoDanio.textContent = avisoDanio.hidden ? '' : fila.dataset.condicionEntrega === 'BUENO'
        ? 'Al registrar un daño nuevo se aplica una sanción grave. Describe el daño observado.'
        : 'Este bien se entregó con daño registrado. Describe su condición al recibirlo.';
    }
    if (!observacion.required && !observacion.value) mostrarErrorCampo(observacion, '');
  }
  seleccionar.addEventListener('change', actualizar);
  condicion.addEventListener('change', actualizar);
  actualizar();
});

document.querySelectorAll('[data-ampliacion-previa]').forEach(formulario => {
  const resultado = formulario.querySelector('[data-resultado-ampliacion]');
  const boton = formulario.querySelector('button[type="submit"], button:not([type])');
  const formato = new Intl.DateTimeFormat('es-PE', {timeZone:'America/Lima', dateStyle:'short', timeStyle:'short'});
  let temporizador, solicitud;
  async function consultar() {
    solicitud?.abort();
    const cantidad = formulario.elements.cantidad.value;
    if (!cantidad) { resultado.textContent = 'Indica el tiempo adicional para ver la nueva fecha de devolución.'; boton.disabled = false; return; }
    if (!Number.isInteger(Number(cantidad)) || Number(cantidad) < 1) {
      resultado.textContent = 'Indica una cantidad entera y positiva.'; boton.disabled = true; return;
    }
    const actual = new AbortController();
    solicitud = actual;
    const parametros = new URLSearchParams({cantidad, unidad:formulario.elements.unidad.value, fecha_actual:formulario.elements.fecha_actual.value});
    resultado.textContent = 'Consultando la nueva fecha…';
    boton.disabled = true;
    try {
      const respuesta = await fetch(`${formulario.dataset.ampliacionPrevia}?${parametros}`, {signal:actual.signal, headers:{Accept:'application/json'}});
      const datos = await respuesta.json();
      if (actual.signal.aborted || solicitud !== actual) return;
      if (!respuesta.ok) { resultado.textContent = datos.error || 'No se pudo calcular la ampliación.'; return; }
      resultado.textContent = `Nueva devolución estimada en Lima: ${formato.format(new Date(datos.fecha))}. Se confirma al guardar.`;
      boton.disabled = false;
    } catch (error) {
      if (error.name !== 'AbortError' && solicitud === actual) {
        resultado.textContent = 'No se pudo consultar la fecha. La ampliación se validará al guardar.';
        boton.disabled = false;
      }
    }
  }
  function programar() { clearTimeout(temporizador); solicitud?.abort(); boton.disabled = true; temporizador = setTimeout(consultar, 250); }
  formulario.elements.cantidad.addEventListener('input', programar);
  formulario.elements.unidad.addEventListener('change', programar);
  if (formulario.elements.cantidad.value) consultar();
});

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
const menuPrincipal = document.getElementById('menu-principal');
const vistaMenuMovil = window.matchMedia('(max-width: 1000px)');
function cambiarMenu(abierto) {
  if (!menuPrincipal || !botonMenu || !sombraMenu) return;
  const estabaAbierto = document.body.classList.contains('menu-abierto');
  if (estabaAbierto && !abierto && vistaMenuMovil.matches) botonMenu.focus();
  document.body.classList.toggle('menu-abierto', abierto);
  botonMenu.setAttribute('aria-expanded', String(abierto));
  botonMenu.setAttribute('aria-label', abierto ? 'Cerrar menú' : 'Abrir menú');
  sombraMenu.hidden = !abierto;
  menuPrincipal.inert = vistaMenuMovil.matches && !abierto;
  if (abierto) menuPrincipal.querySelector('nav a')?.focus();
}
botonMenu?.addEventListener('click', () => cambiarMenu(!document.body.classList.contains('menu-abierto')));
sombraMenu?.addEventListener('click', () => cambiarMenu(false));
vistaMenuMovil.addEventListener('change', () => cambiarMenu(false));
cambiarMenu(false);
document.addEventListener('keydown', evento => {
  if (!document.body.classList.contains('menu-abierto')) return;
  if (evento.key === 'Escape') {
    evento.preventDefault();
    cambiarMenu(false);
  } else if (evento.key === 'Tab') {
    const enlaces = menuPrincipal.querySelectorAll('a[href], button:not([disabled])');
    const primero = enlaces[0];
    const ultimo = enlaces[enlaces.length - 1];
    if (!menuPrincipal.contains(document.activeElement) ||
        (evento.shiftKey ? document.activeElement === primero : document.activeElement === ultimo)) {
      evento.preventDefault();
      (evento.shiftKey ? ultimo : primero)?.focus();
    }
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
  const cambioTipo = document.querySelector('[data-motivo-cambio-tipo]');
  if (cambioTipo && tipoPersona) {
    const cambio = tipoPersona.value !== cambioTipo.dataset.motivoCambioTipo;
    cambioTipo.hidden = !cambio;
    const motivo = cambioTipo.querySelector('input');
    motivo.required = cambio;
    motivo.disabled = !cambio;
  }
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

document.querySelector('[data-cambiar-tema]')?.addEventListener('click', () => {
  const raiz = document.documentElement;
  const oscuroActual = raiz.dataset.theme
    ? raiz.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  const tema = oscuroActual ? 'light' : 'dark';
  raiz.dataset.theme = tema;
  try { localStorage.setItem('tema', tema); } catch (e) { /* almacenamiento no disponible */ }
});
