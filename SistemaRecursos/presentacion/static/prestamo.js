"use strict";

const formularioPrestamo = document.getElementById("form-prestamo");

if (formularioPrestamo) {
  const seleccionSolicitante = document.getElementById("solicitante");
  const tipoSolicitante = document.getElementById("tipo-solicitante");
  const resumenSolicitante = document.getElementById("persona-seleccionada");
  const campoSolicitante = document.getElementById("buscar-solicitante");
  const resultadosSolicitante = document.getElementById("resultados-solicitante");
  const estadoSolicitante = document.getElementById("resultado-busqueda-persona");
  const indicacionBusqueda = estadoSolicitante.textContent.trim();
  const uso = document.getElementById("uso-bienes");
  const modalidad = document.getElementById("modalidad");
  const grupo = document.getElementById("grupo");
  const participantes = new Map();
  const bienesElegidos = new Map();
  const reglas = document.getElementById("reglas").content.querySelectorAll("[data-persona]");
  const bienInicial = JSON.parse(formularioPrestamo.dataset.bien || "null");
  if (bienInicial) {
    bienesElegidos.set(String(bienInicial.id_bien), bienInicial);
  }
  const datosRecuperados = document.getElementById('datos-formulario');
  const previos = datosRecuperados ? JSON.parse(datosRecuperados.textContent).valores : null;
  if (previos) {
    bienesElegidos.clear();
    for (const bien of JSON.parse(formularioPrestamo.querySelector('[data-bienes-recuperados]')?.dataset.bienesRecuperados || '[]')) {
      bienesElegidos.set(String(bien.id_bien), bien);
    }
  }

  const formatoFecha = new Intl.DateTimeFormat("es-PE", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "America/Lima"
  });

  // Datos que se muestran de las personas.
  function obtenerEtiquetaDelTipoDePersona(tipo) {
    const etiquetas = {
      ESTUDIANTE: "Estudiante",
      DOCENTE: "Docente",
      ADMINISTRATIVO: "Administrativo"
    };
    return etiquetas[tipo] || tipo;
  }

  function formatearDocumentosDePersona(persona) {
    const documentos = [];
    if (persona.cui) {
      documentos.push("CUI: " + persona.cui);
    }
    if (persona.dni) {
      documentos.push("DNI: " + persona.dni);
    }
    return documentos.join(" · ");
  }

  function obtenerIniciales(nombre) {
    let iniciales = "";
    let cantidad = 0;
    for (const palabra of nombre.trim().split(/\s+/)) {
      if (palabra) {
        iniciales += palabra[0];
        cantidad += 1;
        if (cantidad === 2) break;
      }
    }
    return iniciales;
  }

  function crearOpcionPersona(persona, seleccionar) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "resultado-prestamo";
    boton.setAttribute("role", "option");
    const nombre = document.createElement("strong");
    nombre.textContent = persona.nombre_completo;
    const detalle = document.createElement("small");
    detalle.textContent = formatearDocumentosDePersona(persona) + " · " + obtenerEtiquetaDelTipoDePersona(persona.tipo);
    const estado = document.createElement("span");
    if (persona.elegible) {
      estado.className = "estado-persona-prestamo activa";
      estado.textContent = "Activa";
    } else {
      estado.className = "estado-persona-prestamo inactiva";
      if (persona.estado !== "ACTIVA") {
        estado.textContent = "Persona inactiva";
      } else if (persona.tipo === "ESTUDIANTE") {
        estado.textContent = "Matrícula no vigente";
      } else {
        estado.textContent = "Inactiva";
      }
    }
    boton.disabled = !persona.elegible;
    boton.append(nombre, detalle, estado);
    boton.addEventListener("click", () => seleccionar(persona));
    return boton;
  }

  // Seleccion del solicitante y de los participantes.
  function cambiarSolicitante() {
    seleccionSolicitante.value = "";
    tipoSolicitante.value = "";
    resumenSolicitante.replaceChildren();
    resumenSolicitante.hidden = true;
    document.getElementById("busqueda-solicitante").hidden = false;
    formularioPrestamo.querySelector("[name=acepta_condiciones]").checked = false;
    actualizarCondicionesDeEntrega();
    campoSolicitante.focus();
  }

  function seleccionarSolicitante(persona) {
    seleccionSolicitante.value = persona.dni;
    seleccionSolicitante.dataset.elegible = String(persona.elegible);
    tipoSolicitante.value = persona.tipo;
    const nombre = document.createElement("strong");
    nombre.textContent = persona.nombre_completo;
    const detalle = document.createElement("small");
    detalle.textContent = formatearDocumentosDePersona(persona) + " · " + obtenerEtiquetaDelTipoDePersona(persona.tipo);
    const datosPersona = document.createElement("div");
    datosPersona.append(nombre, detalle);
    const avatar = document.createElement("span");
    avatar.className = "prestamo-iniciales";
    avatar.textContent = obtenerIniciales(persona.nombre_completo);
    const cambiar = document.createElement("button");
    cambiar.type = "button";
    cambiar.className = "secundario";
    cambiar.textContent = "Cambiar";
    cambiar.addEventListener("click", cambiarSolicitante);
    resumenSolicitante.replaceChildren(avatar, datosPersona, cambiar);
    resumenSolicitante.hidden = false;
    document.getElementById("busqueda-solicitante").hidden = true;
    formularioPrestamo.querySelector("[name=acepta_condiciones]").checked = false;
    if (participantes.has(String(persona.dni))) {
      participantes.delete(String(persona.dni));
      mostrarParticipantesDelPrestamo();
    }
    actualizarCondicionesDeEntrega();
  }

  function agregarParticipante(persona) {
    participantes.set(String(persona.dni), persona);
    mostrarParticipantesDelPrestamo();
  }

  function mostrarParticipantesDelPrestamo() {
    const contenedor = document.getElementById("participantes-seleccionados");
    contenedor.replaceChildren();
    for (const persona of participantes.values()) {
      const fila = document.createElement("div");
      fila.className = "seleccion-prestamo-fila";
      const oculto = document.createElement("input");
      oculto.type = "hidden";
      oculto.name = "participantes";
      oculto.value = persona.dni;
      const etiqueta = document.createElement("span");
      etiqueta.textContent = persona.nombre_completo + " · " + formatearDocumentosDePersona(persona);
      if (!persona.elegible) etiqueta.textContent += ' · No habilitada para préstamos';
      const quitar = document.createElement("button");
      quitar.type = "button";
      quitar.className = "secundario";
      quitar.textContent = "Quitar";
      quitar.setAttribute("aria-label", "Quitar a " + persona.nombre_completo);
      quitar.addEventListener("click", () => {
        participantes.delete(String(persona.dni));
        mostrarParticipantesDelPrestamo();
      });
      fila.append(oculto, etiqueta, quitar);
      contenedor.append(fila);
    }
    actualizarCondicionesDeEntrega();
  }

  // Politicas y fechas estimadas. El servidor confirma los plazos al registrar.
  function obtenerPoliticaAplicableAlBien(bien) {
    for (const regla of reglas) {
      if (regla.dataset.persona === tipoSolicitante.value
          && regla.dataset.categoria === String(bien.id_categoria)) {
        return regla.dataset;
      }
    }
    return null;
  }

  function consultarHorarioDeAtencionActual() {
    const ahora = new Date();
    const partes = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(ahora).map(parte => [parte.type, parte.value]));
    const apertura = formularioPrestamo.dataset.apertura;
    const cierre = formularioPrestamo.dataset.cierre;
    const hora = partes.hour + ":" + partes.minute;
    const fecha = partes.year + "-" + partes.month + "-" + partes.day;
    const diaLima = (new Date(fecha + "T00:00:00Z").getUTCDay() + 6) % 7;
    const atiendeHoy = formularioPrestamo.dataset.dias.split(",").includes(String(diaLima));
    return { cerrado: !atiendeHoy || !apertura || !cierre || hora < apertura || hora >= cierre,
      cierre: new Date(fecha + "T" + cierre + ":00-05:00") };
  }

  function calcularFechaDevolucion(bien) {
    const politica = obtenerPoliticaAplicableAlBien(bien);
    if (!politica) return null;
    const limite = Date.now() + Number(politica.horas) * 3600000;
    if (politica.unidad === "HORAS") return new Date(Math.min(limite, consultarHorarioDeAtencionActual().cierre.getTime()));
    const dias = formularioPrestamo.dataset.dias.split(",");
    const diaLima = (new Date(limite - 5 * 3600000).getUTCDay() + 6) % 7;
    const espera = Math.min(...dias.map(dia => (Number(dia) - diaLima + 7) % 7));
    return new Date(limite + espera * 86400000);
  }

  function actualizarCondicionesDeEntrega() {
    const cerrado = consultarHorarioDeAtencionActual().cerrado;
    document.getElementById("atencion-cerrada").hidden = !cerrado;
    let faltaPolitica = false;
    let salidaNoPermitida = false;
    const solicitaSalida = uso.querySelector("input:checked").value === "1";
    for (const bien of bienesElegidos.values()) {
      const politica = obtenerPoliticaAplicableAlBien(bien);
      if (tipoSolicitante.value && !politica) {
        faltaPolitica = true;
      }
      if (solicitaSalida && politica && politica.salida === "0") {
        salidaNoPermitida = true;
      }
    }
    document.getElementById("politica-faltante").hidden = !faltaPolitica;
    document.getElementById("salida-no-permitida").hidden = !salidaNoPermitida;
    document.getElementById("confirmar-prestamo").disabled =
      !seleccionSolicitante.value || seleccionSolicitante.dataset.elegible !== 'true'
      || bienesElegidos.size === 0 || faltaPolitica || salidaNoPermitida || cerrado
      || [...bienesElegidos.values()].some(b => b.estado && b.estado !== 'DISPONIBLE')
      || (modalidad.querySelector("input:checked").value === "GRUPAL" && [...participantes.values()].some(p => !p.elegible))
      || !formularioPrestamo.elements.acepta_condiciones.checked
      || (modalidad.querySelector("input:checked").value === "GRUPAL" && participantes.size === 0);
    mostrarBienesSeleccionados();
    actualizarResumenDelPrestamo();
    return faltaPolitica || salidaNoPermitida || cerrado;
  }

  function actualizarResumenDelPrestamo() {
    const nombre = resumenSolicitante.querySelector("strong");
    let solicitante = "Sin seleccionar";
    if (nombre) solicitante = nombre.textContent;
    document.getElementById("resumen-persona").textContent = solicitante;

    let textoModalidad = "Individual";
    if (modalidad.querySelector("input:checked").value === "GRUPAL") {
      textoModalidad = "Grupal";
    }
    document.getElementById("resumen-modalidad").textContent = textoModalidad;
    let textoUso = "Dentro de la institución";
    if (uso.querySelector("input:checked").value === "1") {
      textoUso = "Fuera de la institución";
    }
    document.getElementById("resumen-uso").textContent = textoUso;
    document.getElementById("resumen-bienes").textContent = bienesElegidos.size;

    let primeraFecha = null;
    for (const bien of bienesElegidos.values()) {
      const fecha = calcularFechaDevolucion(bien);
      if (fecha && (!primeraFecha || fecha < primeraFecha)) primeraFecha = fecha;
    }
    let textoFecha = "—";
    if (primeraFecha) textoFecha = formatoFecha.format(primeraFecha);
    document.getElementById("resumen-devolucion").textContent = textoFecha;
  }

  function crearFilaDeBienSeleccionado(bien) {
    const fila = document.createElement("article");
    fila.className = "prestamo-bien";
    const oculto = document.createElement("input");
    oculto.type = "hidden";
    oculto.name = "bienes";
    oculto.value = bien.id_bien;
    const identidad = document.createElement("div");
    const nombre = document.createElement("strong");
    nombre.textContent = bien.recurso_nombre;
    const codigo = document.createElement("small");
    codigo.textContent = bien.codigo_inventario;
    const encabezado = document.createElement("div");
    encabezado.className = "prestamo-bien-nombre";
    encabezado.append(nombre, codigo);
    identidad.append(encabezado);

    const resumenPolitica = document.createElement("div");
    resumenPolitica.className = "prestamo-bien-reglas";
    const politica = obtenerPoliticaAplicableAlBien(bien);
    if (politica) {
      const plazo = document.createElement("strong");
      plazo.className = "prestamo-plazo";
      plazo.textContent = politica.plazo;
      let permisoSalida = "Salida no permitida";
      if (politica.salida === "1") permisoSalida = "Salida permitida";
      resumenPolitica.append(plazo, document.createTextNode(" · " + permisoSalida));
    } else if (tipoSolicitante.value) {
      resumenPolitica.textContent = "Sin política de préstamo";
    } else {
      resumenPolitica.textContent = "Selecciona un solicitante.";
    }
    identidad.append(resumenPolitica);
    if (bien.estado && bien.estado !== 'DISPONIBLE') resumenPolitica.textContent = 'Bien no disponible. Selecciona otro.';

    const devolucion = document.createElement("div");
    devolucion.className = "prestamo-bien-fecha";
    const etiqueta = document.createElement("small");
    etiqueta.textContent = "Devolución estimada";
    const fecha = document.createElement("strong");
    fecha.textContent = "—";
    if (politica) fecha.textContent = formatoFecha.format(calcularFechaDevolucion(bien));
    devolucion.append(etiqueta, fecha);

    const quitar = document.createElement("button");
    quitar.type = "button";
    quitar.className = "prestamo-quitar";
    quitar.textContent = "×";
    quitar.setAttribute("aria-label", "Quitar " + bien.codigo_inventario);
    quitar.addEventListener("click", () => {
      bienesElegidos.delete(String(bien.id_bien));
      actualizarCondicionesDeEntrega();
      document.getElementById("buscar-bien").dispatchEvent(new Event("search"));
    });
    fila.append(oculto, identidad, devolucion, quitar);
    return fila;
  }

  function mostrarBienesSeleccionados() {
    const contenedor = document.getElementById("bienes-seleccionados");
    contenedor.replaceChildren();
    document.getElementById("cantidad-bienes").textContent = "BIENES SELECCIONADOS · " + bienesElegidos.size;
    for (const bien of bienesElegidos.values()) {
      contenedor.append(crearFilaDeBienSeleccionado(bien));
    }
  }

  // Cada buscador conserva su temporizador y su solicitud pendiente.
  function configurarBusquedaDePersonas(campo, resultados, estado, paraParticipantes = false) {
    let temporizador;
    let solicitudActiva = null;

    function elegirPersona(persona) {
      if (paraParticipantes) {
        agregarParticipante(persona);
        estado.textContent = "Participante agregado.";
      } else {
        seleccionarSolicitante(persona);
        estado.textContent = "Solicitante seleccionado.";
      }
      campo.value = "";
      resultados.replaceChildren();
      resultados.hidden = true;
    }

    async function buscarPersonasPorTermino() {
      clearTimeout(temporizador);
      if (solicitudActiva) solicitudActiva.abort();
      const termino = campo.value.trim();
      resultados.replaceChildren();
      resultados.hidden = true;
      if (termino.length < 2) {
        estado.textContent = indicacionBusqueda;
        return;
      }
      const solicitud = new AbortController();
      solicitudActiva = solicitud;
      estado.textContent = "Buscando personas…";
      try {
        const url = new URL(formularioPrestamo.dataset.personasUrl, window.location.origin);
        url.searchParams.set("q", termino);
        const respuesta = await fetch(url, {headers: {Accept: "application/json"}, signal: solicitud.signal});
        if (!respuesta.ok) throw new Error("Error de búsqueda");
        const datos = {resultados: await respuesta.json(), limite: 20};
        if (solicitud.signal.aborted || solicitudActiva !== solicitud || termino !== campo.value.trim()) return;

        let cantidad = 0;
        for (const persona of datos.resultados) {
          const dniPersona = String(persona.dni);
          if (paraParticipantes && (dniPersona === seleccionSolicitante.value || participantes.has(dniPersona))) continue;
          resultados.append(crearOpcionPersona(persona, elegirPersona));
          cantidad += 1;
        }
        resultados.hidden = cantidad === 0;
        if (cantidad > 0) {
          estado.textContent = cantidad + (cantidad === 1 ? " coincidencia." : " coincidencias.");
          if (datos.resultados.length === datos.limite) estado.textContent += " Afina la búsqueda si no aparece.";
        } else {
          estado.textContent = "No se encontraron personas para seleccionar.";
        }
      } catch (error) {
        if (!solicitud.signal.aborted && solicitudActiva === solicitud && termino === campo.value.trim()) {
          estado.textContent = "No se pudo buscar. Inténtalo de nuevo.";
        }
      }
    }

    campo.addEventListener("input", () => {
      clearTimeout(temporizador);
      if (solicitudActiva) solicitudActiva.abort();
      resultados.replaceChildren();
      resultados.hidden = true;
      temporizador = setTimeout(buscarPersonasPorTermino, 250);
    });
    campo.addEventListener("keydown", evento => {
      if (evento.key === "Enter") {
        evento.preventDefault();
        buscarPersonasPorTermino();
      }
    });
    campo.addEventListener("search", () => buscarPersonasPorTermino());
  }

  function crearOpcionBien(bien, agregar) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "resultado-prestamo resultado-bien";
    boton.setAttribute("role", "option");
    const nombre = document.createElement("strong");
    nombre.textContent = bien.codigo_inventario + " · " + bien.recurso_nombre;
    const detalle = document.createElement("small");
    detalle.textContent = (bien.ubicacion || "Sin ubicación") + " · " + bien.recurso_nombre;
    const elegido = bienesElegidos.has(String(bien.id_bien));
    const accion = document.createElement("span");
    accion.textContent = "Agregar";
    if (elegido) accion.textContent = "Agregado";
    boton.disabled = elegido;
    boton.append(nombre, detalle, accion);
    boton.addEventListener("click", () => agregar(bien));
    return boton;
  }

  function configurarBusquedaDeBienes() {
    const campo = document.getElementById("buscar-bien");
    const resultados = document.getElementById("resultados-bienes");
    const estado = document.getElementById("estado-bienes");
    let temporizador;
    let solicitudActiva = null;

    function agregarBien(bien) {
      bienesElegidos.set(String(bien.id_bien), bien);
      actualizarCondicionesDeEntrega();
      buscarBienesDisponibles();
    }

    async function buscarBienesDisponibles() {
      clearTimeout(temporizador);
      if (solicitudActiva) solicitudActiva.abort();
      const termino = campo.value.trim();
      let recurso = formularioPrestamo.dataset.recurso;
      if (termino) recurso = "";
      resultados.replaceChildren();
      resultados.hidden = true;
      if (!termino && !recurso) {
        const iniciales = JSON.parse(formularioPrestamo.dataset.bienesIniciales || "[]");
        for (const bien of iniciales) resultados.append(crearOpcionBien(bien, agregarBien));
        resultados.hidden = iniciales.length === 0;
        estado.textContent = "Bienes encontrados: " + iniciales.length;
        return;
      }
      if (termino.length < 2 && !recurso) {
        estado.textContent = indicacionBusqueda;
        return;
      }
      const solicitud = new AbortController();
      solicitudActiva = solicitud;
      estado.textContent = "Buscando bienes disponibles…";
      try {
        const url = new URL(formularioPrestamo.dataset.bienesUrl, window.location.origin);
        if (termino) url.searchParams.set("q", termino);
        if (recurso) url.searchParams.set("id_recurso", recurso);
        const respuesta = await fetch(url, {headers: {Accept: "application/json"}, signal: solicitud.signal});
        if (!respuesta.ok) throw new Error("Error de búsqueda");
        const datos = await respuesta.json();
        if (solicitud.signal.aborted || solicitudActiva !== solicitud || termino !== campo.value.trim()) return;

        for (const bien of datos.resultados) resultados.append(crearOpcionBien(bien, agregarBien));
        resultados.hidden = resultados.childElementCount === 0;
        if (datos.resultados.length > 0) {
          estado.textContent = "Bienes encontrados: " + datos.resultados.length;
        } else {
          estado.textContent = "No hay bienes disponibles con esos datos.";
        }
      } catch (error) {
        if (!solicitud.signal.aborted && solicitudActiva === solicitud && termino === campo.value.trim()) {
          estado.textContent = "No se pudo buscar. Inténtalo de nuevo.";
        }
        resultados.hidden = resultados.childElementCount === 0;
      }
    }

    campo.addEventListener("input", () => {
      clearTimeout(temporizador);
      if (solicitudActiva) solicitudActiva.abort();
      resultados.replaceChildren();
      resultados.hidden = true;
      temporizador = setTimeout(buscarBienesDisponibles, 250);
    });
    campo.addEventListener("keydown", evento => {
      if (evento.key === "Enter") {
        evento.preventDefault();
        buscarBienesDisponibles();
      }
    });
    campo.addEventListener("search", () => buscarBienesDisponibles());
    buscarBienesDisponibles();
  }

  configurarBusquedaDePersonas(campoSolicitante, resultadosSolicitante, estadoSolicitante);
  configurarBusquedaDePersonas(
    document.getElementById("buscar-participante"),
    document.getElementById("resultados-participantes"),
    document.getElementById("estado-participantes"),
    true
  );
  configurarBusquedaDeBienes();
  modalidad.addEventListener("change", () => {
    grupo.hidden = modalidad.querySelector("input:checked").value !== "GRUPAL";
    grupo.disabled = grupo.hidden;
    actualizarCondicionesDeEntrega();
  });
  formularioPrestamo.elements.acepta_condiciones.addEventListener("change", actualizarCondicionesDeEntrega);
  uso.addEventListener("change", actualizarCondicionesDeEntrega);
  actualizarCondicionesDeEntrega();

  formularioPrestamo.addEventListener("submit", evento => {
    if (!seleccionSolicitante.value) {
      evento.preventDefault();
      estadoSolicitante.textContent = "Busca y selecciona a la persona que recibirá el préstamo.";
      campoSolicitante.focus();
    } else if (bienesElegidos.size === 0) {
      evento.preventDefault();
      document.getElementById("estado-bienes").textContent = "Selecciona los bienes.";
      document.getElementById("buscar-bien").focus();
    } else if (modalidad.querySelector("input:checked").value === "GRUPAL" && participantes.size === 0) {
      evento.preventDefault();
      document.getElementById("estado-participantes").textContent = "Agrega al menos otro participante.";
      document.getElementById("buscar-participante").focus();
    } else if (actualizarCondicionesDeEntrega()) {
      evento.preventDefault();
      const faltaPolitica = document.getElementById("politica-faltante");
      if (!faltaPolitica.hidden) faltaPolitica.focus();
      else if (!document.getElementById("salida-no-permitida").hidden) document.getElementById("salida-no-permitida").focus();
      else document.getElementById("atencion-cerrada").focus();
    }
  });
  setInterval(actualizarCondicionesDeEntrega, 15000);

  if (previos) {
    (async () => {
      async function buscarPersonaPorDni(dni) {
        const url = new URL(formularioPrestamo.dataset.personasUrl, window.location.origin);
        url.searchParams.set('q', dni);
        const respuesta = await fetch(url, {headers:{Accept:'application/json'}});
        if (!respuesta.ok) return null;
        return (await respuesta.json()).find(persona => persona.dni === dni);
      }
      const responsable = previos.dni_persona?.[0];
      if (responsable) {
        const persona = await buscarPersonaPorDni(responsable);
        if (persona) seleccionarSolicitante(persona);
      }
      const documentos = (previos.participantes || []).flatMap(valor => valor.split(',').map(d => d.trim())).filter(Boolean);
      for (const dni of documentos) {
        const persona = await buscarPersonaPorDni(dni);
        if (persona && dni !== responsable) participantes.set(dni, persona);
      }
      mostrarParticipantesDelPrestamo();
      grupo.hidden = modalidad.querySelector('input:checked').value !== 'GRUPAL';
      grupo.disabled = grupo.hidden;
      formularioPrestamo.elements.acepta_condiciones.checked = previos.acepta_condiciones?.includes('1') || false;
      actualizarCondicionesDeEntrega();
    })().catch(() => {
      estadoSolicitante.textContent = 'Selecciona nuevamente al solicitante.';
    });
  }

}
