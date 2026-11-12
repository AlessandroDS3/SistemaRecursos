document.querySelectorAll(".fila-devolucion-pendiente").forEach((fila) => {
    const seleccionar = fila.querySelector('input[name="detalles"]');
    const condicion = fila.querySelector('select[name^="condicion_"]');
    const observaciones = fila.querySelector('input[name^="observacion_"]');
    if (!seleccionar || !condicion || !observaciones) return;
    const actualizar = () => {
        const obligatoria = seleccionar.checked && condicion.value !== "BUENO";
        observaciones.required = obligatoria;
        observaciones.placeholder = condicion.value === "BUENO" ? "Opcional" : "Describe la condición";
    };
    seleccionar.addEventListener("change", actualizar);
    condicion.addEventListener("change", actualizar);
    actualizar();
});
