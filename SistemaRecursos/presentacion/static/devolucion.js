document.querySelectorAll(".fila-devolucion-pendiente").forEach((fila) => {
    const seleccionar = fila.querySelector('input[name="detalles"]');
    const estado = fila.querySelector('select[name^="estado_"]');
    const observaciones = fila.querySelector('input[name^="observacion_"]');
    if (!seleccionar || !estado || !observaciones) return;
    const actualizar = () => {
        const obligatoria = seleccionar.checked && estado.value !== "DISPONIBLE";
        observaciones.required = obligatoria;
        observaciones.placeholder = estado.value === "DISPONIBLE" ? "Opcional" : "Describe la condición";
    };
    seleccionar.addEventListener("change", actualizar);
    estado.addEventListener("change", actualizar);
    actualizar();
});
