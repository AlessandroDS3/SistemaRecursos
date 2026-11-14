document.querySelectorAll('.formulario-ampliacion').forEach((formulario) => {
  const cantidad = formulario.elements.cantidad;
  const unidad = formulario.elements.unidad;
  const resultado = formulario.querySelector('.resultado-ampliacion');
  const formato = new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short',
  });

  function mostrarVencimiento() {
    const valor = Number(cantidad.value);
    const factor = unidad.value === 'HORAS' ? 3600000 : 86400000;
    const fecha = new Date(Date.parse(formulario.dataset.fechaActual) + valor * factor);
    if (!Number.isInteger(valor) || valor < 1 || valor > 720 || Number.isNaN(fecha.getTime())) {
      resultado.textContent = 'Indica una cantidad entera y positiva.';
      return;
    }
    resultado.textContent = `Nuevo vencimiento en Lima: ${formato.format(fecha)}. Se validará la política al confirmar.`;
  }

  cantidad.addEventListener('input', mostrarVencimiento);
  unidad.addEventListener('change', mostrarVencimiento);
});
