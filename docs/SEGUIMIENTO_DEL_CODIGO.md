# Cómo seguir las operaciones en el código

Busca la acción que quieras demostrar. La función del controlador es el primer punto de entrada. El recorrido indica qué servicio aplica las reglas y dónde se consulta o se guarda la información.

En el IDE, usa **Ir a definición** desde la llamada del controlador. Si llegas a `IRepositorio…`, estás en el contrato. `crear_servicios()` conecta ese servicio a su implementación SQL y `registrar_controladores()` conecta las rutas. [app.py](../SistemaRecursos/app.py)

`GET` muestra una pantalla o consulta datos. `POST` ejecuta una acción. Cuando el formulario usa la misma ruta para ambos pasos, aparecen los dos métodos.

## Inicio y acceso

[controlador_inicio.py](../SistemaRecursos/presentacion/controladores/controlador_inicio.py) · [controlador_acceso.py](../SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_acceso.py) · [servicio_acceso.py](../SistemaRecursos/servicios/personas_usuarios/servicio_acceso.py) · [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py) · [repositorio_acceso_sql.py](../SistemaRecursos/repositorio/personas_usuarios/repositorio_acceso_sql.py) · [seguridad.py](../SistemaRecursos/presentacion/seguridad.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Ver el panel de inicio | GET `/` | `inicio()` | `consultar_resumen_prestamos()`, `contar_reservas_pendientes()`, `contar_bienes_disponibles()` y, según el rol, `consultar_solicitudes_ampliacion()` y `consultar_estado_procesador()`. |
| Iniciar sesión | GET / POST `/login` | `iniciar_sesion()` | `autenticar_cuenta()` → `crear_sesion_de_cuenta()` → repositorio `crear_sesion()`. El controlador llama a `establecer_sesion()`. |
| Cerrar sesión | POST `/logout` | `cerrar_sesion()` | `cerrar_sesion()` del servicio → `cerrar_sesion()` del repositorio. El controlador limpia la sesión de Flask. |

En cada petición, `recuperar_sesion()` valida la sesión del servidor y recupera la cuenta activa. `requiere_permiso()` aplica los permisos definidos por rol.

## Personas, cuentas y roles

[controlador_persona.py](../SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_persona.py) · [controlador_cuenta.py](../SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_cuenta.py) · [servicio_persona.py](../SistemaRecursos/servicios/personas_usuarios/servicio_persona.py) · [servicio_cuenta.py](../SistemaRecursos/servicios/personas_usuarios/servicio_cuenta.py) · [persona.py](../SistemaRecursos/dominio/gestion_personas_usuarios/persona.py) · [cuenta.py](../SistemaRecursos/dominio/gestion_personas_usuarios/cuenta.py) · [rol.py](../SistemaRecursos/dominio/gestion_personas_usuarios/rol.py) · [repositorio_persona_sql.py](../SistemaRecursos/repositorio/personas_usuarios/repositorio_persona_sql.py) · [repositorio_cuenta_sql.py](../SistemaRecursos/repositorio/personas_usuarios/repositorio_cuenta_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Listar y filtrar personas | GET `/personas` | `consultar_personas()` | `consultar_personas()` del servicio valida filtros → el repositorio aplica búsqueda, orden y paginación. |
| Buscar persona para el formulario | GET `/personas/buscar` | `buscar_personas()` | `buscar_personas()` del servicio → `buscar_personas()` del repositorio → `validar_elegibilidad_del_solicitante()` para marcar el resultado. |
| Ver ficha e historial de cambios de tipo | GET `/personas/<documento>` | `consultar_persona()` | `consultar_persona()` y `consultar_cambios_tipo_persona()` → repositorio de personas. El controlador comprueba si tiene cuenta. |
| Registrar una persona | GET / POST `/personas/nueva` | `registrar_persona()` | `registrar_persona()` → `_validar_y_guardar_persona()` → `Persona.desde_datos()` → `guardar_persona()` registra la ficha y el tipo institucional. |
| Editar una persona o cambiar su tipo | GET / POST `/personas/<documento>/editar` | `editar_persona()` | `actualizar_persona()` → `_validar_y_guardar_persona()` → `guardar_persona()`. Para cambiar el tipo, `cambiar_tipo_persona()` registra el motivo y el historial. |
| Desactivar una persona | POST `/personas/<documento>/desactivar` | `desactivar_persona()` | `desactivar_persona()` → `actualizar_persona()` verifica la protección de cuentas y guarda el nuevo estado. |
| Crear cuenta para una persona | GET / POST `/cuentas/<documento>/nueva` | `registrar_cuenta()` | `registrar_cuenta()` → `_validar_persona_sin_cuenta()` → `generar_codigo_de_activacion()` → repositorio `registrar_cuenta()`. |
| Editar cuenta, asignar rol o cambiar estado | GET / POST `/cuentas/<documento>/editar` | `actualizar_cuenta()` | `actualizar_cuenta()` → `_validar_datos_de_edicion_de_cuenta()` y `proteger_administradores()` → repositorio `actualizar_cuenta()`. |
| Activar cuenta con código | GET / POST `/cuentas/activar` | `activar_cuenta()` | `activar_cuenta()` → `codigo_de_activacion_valido()` → `actualizar_cuenta()` guarda la contraseña elegida mediante su hash. |
| Cambiar mi contraseña | GET / POST `/cuentas/mi-contrasena` | `cambiar_clave_propia()` | `cambiar_clave_propia()` → `consultar_cuenta_para_cambiar_clave()` → `actualizar_cuenta()` y `cerrar_sesiones_de_cuenta()`. |
| Restablecer acceso de otra cuenta | POST `/cuentas/<documento>/restablecer` | `restablecer_clave()` | `restablecer_clave()` → `generar_codigo_de_activacion()` → `actualizar_cuenta()`, cierre de sesiones e historial. |

## Catálogo, categorías, inventario y mantenimiento

[controlador_recurso.py](../SistemaRecursos/presentacion/controladores/recursos/controlador_recurso.py) · [controlador_bien_material.py](../SistemaRecursos/presentacion/controladores/recursos/controlador_bien_material.py) · [servicio_recurso.py](../SistemaRecursos/servicios/recursos/servicio_recurso.py) · [servicio_bien_material.py](../SistemaRecursos/servicios/recursos/servicio_bien_material.py) · [recurso.py](../SistemaRecursos/dominio/gestion_recursos/recurso.py) · [bien_material.py](../SistemaRecursos/dominio/gestion_recursos/bien_material.py) · [mantenimiento.py](../SistemaRecursos/dominio/gestion_recursos/mantenimiento.py) · [repositorio_recurso_sql.py](../SistemaRecursos/repositorio/recursos/repositorio_recurso_sql.py) · [repositorio_bien_material_sql.py](../SistemaRecursos/repositorio/recursos/repositorio_bien_material_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Ver el catálogo | GET `/recursos` | `consultar_recursos()` | `consultar_recursos()` → `validar_filtros_inventario()` → consulta SQL del catálogo. |
| Ver la ficha de un recurso | GET `/recursos/<int:identificador>` | `consultar_recurso()` | `consultar_recurso()` → repositorio. El controlador reúne los ejemplares y las condiciones de préstamo que correspondan. |
| Administrar recursos e inventario | GET `/recursos/administracion` | `consultar_administracion_recursos()` | `consultar_administracion_recursos()` junta las consultas `consultar_recursos()` y `consultar_bienes_materiales()` por recurso. |
| Registrar un recurso | GET / POST `/recursos/nuevo` | `registrar_recurso()` | `registrar_recurso()` → `_validar_y_guardar_recurso()` → `guardar_recurso()`. Si se ingresa el código de inventario, también llama a `guardar_bien_material()`. |
| Editar un recurso | GET / POST `/recursos/<int:identificador>/editar` | `editar_recurso()` | `actualizar_recurso()` → `_validar_y_guardar_recurso()` → `guardar_recurso()`. |
| Eliminar un recurso | POST `/recursos/<int:identificador>/eliminar` | `eliminar_recurso()` | `eliminar_recurso()` revisa `consultar_relaciones_recurso()` antes de eliminarlo en SQL. |
| Ver las categorías | GET `/recursos/categorias` | `consultar_categorias()` | `consultar_categorias()` del servicio → `consultar_categorias()` del repositorio. |
| Registrar o editar categoría | POST `/recursos/categorias` | `guardar_categoria()` | `registrar_categoria()` o `actualizar_categoria()` → `_validar_y_guardar_categoria()` → `guardar_categoria()` en `categoria_recurso`. |
| Eliminar categoría | POST `/recursos/categorias/<int:identificador>/eliminar` | `eliminar_categoria()` | `eliminar_categoria()` verifica `consultar_relaciones_categoria()` antes de eliminarla en SQL. |
| Listar y filtrar ejemplares | GET `/bienes` | `consultar_bienes_materiales()` | `consultar_bienes_materiales()` valida filtros y llama al repositorio. |
| Ver ficha, historial y mantenimientos del ejemplar | GET `/bienes/<int:identificador>` | `consultar_bien_material()` | `consultar_detalle_bien_material()` reúne el ejemplar, el historial y las órdenes de mantenimiento. |
| Registrar un ejemplar | GET / POST `/bienes/nuevo` | `registrar_bien_material()` | `registrar_bien_material()` → `_validar_y_guardar_bien_material()` → `BienMaterial.desde_datos()` → `guardar_bien_material()`. |
| Editar un ejemplar | GET / POST `/bienes/<int:identificador>/editar` | `editar_bien_material()` | `actualizar_bien_material()` → `_validar_y_guardar_bien_material()` → `guardar_bien_material()`. |
| Cambiar estado del ejemplar | POST `/bienes/<int:identificador>/estado` | `cambiar_estado_bien_material()` | `cambiar_estado_bien_material()` → `validar_cambio_estado_bien_material()` → repositorio `cambiar_estado_bien_material()`. |
| Eliminar un ejemplar | POST `/bienes/<int:identificador>/eliminar` | `eliminar_bien_material()` | `eliminar_bien_material()` verifica `consultar_relaciones_bien_material()` antes de eliminarlo en SQL. |
| Abrir un mantenimiento | POST `/bienes/<int:identificador>/mantenimiento/abrir` | `abrir_mantenimiento()` | `abrir_mantenimiento()` → `AperturaMantenimiento` y `validar_apertura_mantenimiento()` → `abrir_mantenimiento()` en SQL. |
| Cerrar un mantenimiento | POST `/bienes/<int:identificador>/mantenimiento/cerrar` | `cerrar_mantenimiento()` | `cerrar_mantenimiento()` → `CierreMantenimiento` y `consultar_mantenimiento_abierto()` → `cerrar_mantenimiento()` en SQL. |

## Préstamos y devoluciones

[controlador_prestamo.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_prestamo.py) · [servicio_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_prestamo.py) · [prestamo.py](../SistemaRecursos/dominio/gestion_prestamos/prestamo.py) · [devolucion.py](../SistemaRecursos/dominio/gestion_prestamos/devolucion.py) · [repositorio_prestamo_sql.py](../SistemaRecursos/repositorio/prestamos/repositorio_prestamo_sql.py) · [operaciones_sancion.py](../SistemaRecursos/servicios/control/operaciones_sancion.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Listar préstamos o Mis préstamos | GET `/prestamos` | `consultar_prestamos()` | `consultar_prestamos()` aplica filtros y el alcance de la cuenta → repositorio `consultar_prestamos()`. |
| Ver ficha del préstamo | GET `/prestamos/<int:identificador>` | `consultar_prestamo()` | `consultar_prestamo()` comprueba el alcance de la persona y obtiene préstamo y detalles del repositorio. |
| Ver condiciones de un solicitante | GET `/prestamos/condiciones` | `consultar_condiciones_prestamo()` | `consultar_condiciones_prestamo()` del servicio llama a la consulta SQL y verifica la elegibilidad. |
| Buscar ejemplares disponibles en el formulario | GET `/prestamos/bienes` | `consultar_bienes_disponibles()` | El controlador llama a `consultar_bienes_materiales()` con estado `DISPONIBLE`. |
| Registrar préstamo individual o grupal | GET / POST `/prestamos/nuevo` | `registrar_prestamo()` | `registrar_prestamo()` → `registrar_entrega_prestamo_en_transaccion()` → `consultar_datos_para_validar_prestamo()` → `validar_entrega_y_calcular_plazos()` → `guardar_entrega_prestamo()`. |
| Registrar devolución total o parcial | POST `/prestamos/<int:identificador>/devolver` | `registrar_devolucion()` | `registrar_devolucion()` → `validar_bien_pendiente_de_devolucion()` y `validar_codigo_recibido()` → repositorio `registrar_devolucion()` → `calcular_estado_prestamo()`. El servicio evalúa retraso, daño y regularización. |
| Registrar una discrepancia de recepción | POST `/prestamos/<int:identificador>/detalles/<int:detalle_id>/discrepancia` | `registrar_discrepancia_devolucion()` | `registrar_discrepancia_devolucion()` → verifica que el detalle siga pendiente → `registrar_historial_estado()`. |
| Rectificar una devolución | POST `/prestamos/<int:identificador>/detalles/<int:detalle_id>/rectificar` | `rectificar_devolucion()` | `rectificar_devolucion()` valida permiso, sanciones y movimientos posteriores → repositorio `rectificar_devolucion()` → `calcular_estado_prestamo()`. |
| Reportar pérdida | POST `/prestamos/<int:identificador>/detalles/<int:detalle_id>/perdida` | `registrar_perdida_bien_material()` | `registrar_perdida_bien_material()` → `aplicar_o_reevaluar_sancion()` → repositorio `registrar_perdida_bien_material()`. |
| Autorizar entrega o recepción propia | POST `/prestamos/autorizaciones` | `autorizar_operacion_propia()` | `autorizar_operacion_propia()` → `guardar_autorizacion_propia()`. La entrega o devolución posterior valida y consume la autorización. |
| Registrar vencimientos manualmente | POST `/prestamos/vencimientos` | `actualizar_estados_prestamos_vencidos()` | `actualizar_estados_prestamos_vencidos()` → `calcular_estado_prestamo()` → `actualizar_estado_prestamo()`. |

## Reservas y atención de solicitudes

[controlador_reserva.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_reserva.py) · [servicio_reserva.py](../SistemaRecursos/servicios/prestamos/servicio_reserva.py) · [reserva.py](../SistemaRecursos/dominio/gestion_prestamos/reserva.py) · [repositorio_reserva_sql.py](../SistemaRecursos/repositorio/prestamos/repositorio_reserva_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Ver reservas o Mis reservas | GET `/reservas` | `consultar_reservas()` | `consultar_reservas()` aplica filtros y alcance → repositorio `consultar_reservas()`. |
| Ver ficha de reserva e historial | GET `/reservas/<int:identificador>` | `consultar_reserva()` | `consultar_reserva()` → repositorio `consultar_reserva()` y `consultar_historial_estado()`. |
| Registrar reserva | GET / POST `/reservas/nueva` | `registrar_reserva()` | `registrar_reserva()` → `Reserva.desde_formulario()` → `validar_solicitante_y_recurso_para_reserva()` → `validar_cupo_articulos()` → `guardar_nueva_reserva()`. |
| Preparar todos los bienes para retiro | POST `/reservas/<int:identificador>/preparar` | `preparar_reserva()` | `_procesar_accion_reserva()` → `_asignar_bienes_para_retiro()` valida la prioridad de cada recurso y aparta todos los bienes en la misma transacción. |
| Entregar la reserva y crear el préstamo | POST `/reservas/<int:identificador>/entregar` | `entregar_reserva()` | `entregar_reserva()` → `_registrar_prestamo_de_reserva()` → `registrar_entrega_prestamo_en_transaccion()` valida el horario y calcula el plazo desde la entrega real → `marcar_atendida_con_prestamo()` → `_guardar_estado_e_historial_reserva()`. |
| Cancelar reserva | POST `/reservas/<int:identificador>/cancelar` | `cancelar_reserva()` | `cancelar_reserva()` → `_procesar_accion_reserva()` → `cerrar_sin_entrega()` → libera el ejemplar si estaba asignado y guarda el estado. |
| Rechazar reserva | POST `/reservas/<int:identificador>/rechazar` | `rechazar_reserva()` | `rechazar_reserva()` → `_procesar_accion_reserva()` → `cerrar_sin_entrega()` → registra el rechazo y el motivo. |
| Marcar reserva vencida | POST `/reservas/<int:identificador>/expirar` | `expirar_reserva()` | `expirar_reserva()` → `validar_accion_reserva()` verifica que venció → `cerrar_sin_entrega()` → libera el ejemplar si corresponde. |

## Ampliaciones de plazo

[controlador_ampliacion_prestamo.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_ampliacion_prestamo.py) · [servicio_ampliacion_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_ampliacion_prestamo.py) · [ampliacion_prestamo.py](../SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py) · [solicitud_ampliacion.py](../SistemaRecursos/dominio/gestion_prestamos/solicitud_ampliacion.py) · [repositorio_ampliacion_prestamo_sql.py](../SistemaRecursos/repositorio/prestamos/repositorio_ampliacion_prestamo_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Previsualizar una ampliación | GET `/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliacion-previa` | `previsualizar_ampliacion_prestamo()` | `previsualizar_ampliacion_prestamo()` → `consultar_datos_para_validar_ampliacion()` → `_validar_y_calcular_nuevo_plazo()` devuelve la fecha candidata. |
| Ampliar directamente el plazo | POST `/prestamos/<int:identificador>/detalles/<int:detalle_id>/ampliar` | `ampliar_prestamo()` | `ampliar_prestamo()` → `_validar_y_calcular_nuevo_plazo()` → `actualizar_plazo_prestamo()` y `_registrar_historial_ampliacion()`. |
| Solicitar una ampliación | POST `/prestamos/<int:identificador>/detalles/<int:detalle_id>/solicitar-ampliacion` | `solicitar_ampliacion()` | `solicitar_ampliacion()` → `exigir_titular_del_prestamo_para_ampliacion()` → `registrar_solicitud_ampliacion()`. |
| Ver solicitudes de ampliación | GET `/ampliaciones/solicitudes` | `consultar_solicitudes_ampliacion()` | `consultar_solicitudes_ampliacion()` del servicio → `consultar_solicitudes_ampliacion()` del repositorio. |
| Aprobar una ampliación | POST `/ampliaciones/solicitudes/<int:identificador>/aprobar` | `aprobar_solicitud_ampliacion()` | `aprobar_solicitud_ampliacion()` → `exigir_solicitud_ampliacion_pendiente()` → actualiza el plazo, resuelve la solicitud y registra el historial. |
| Rechazar una ampliación | POST `/ampliaciones/solicitudes/<int:identificador>/rechazar` | `rechazar_solicitud_ampliacion()` | `rechazar_solicitud_ampliacion()` → `exigir_solicitud_ampliacion_pendiente()` → `resolver_solicitud_ampliacion()` e historial. |

## Políticas, horario y cupos

[controlador_politica_prestamo.py](../SistemaRecursos/presentacion/controladores/control/controlador_politica_prestamo.py) · [servicio_politica_prestamo.py](../SistemaRecursos/servicios/control/servicio_politica_prestamo.py) · [politica_prestamo.py](../SistemaRecursos/dominio/gestion_control/politica_prestamo.py) · [repositorio_politica_prestamo_sql.py](../SistemaRecursos/repositorio/control/repositorio_politica_prestamo_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Consultar políticas, horario y cupos | GET `/politicas` | `consultar_politicas_prestamo()` | `consultar_politicas_prestamo()`, `consultar_horario_y_plazos_de_reserva()` y `consultar_limites_articulos()`. |
| Registrar una política de préstamo | GET / POST `/politicas/nueva` | `registrar_politica_prestamo()` | `registrar_politica_prestamo()` → `_guardar_nueva_version_de_politica()` → `PoliticaPrestamo.desde_datos()` → `insertar_politica_prestamo()`. |
| Editar política de préstamo | GET / POST `/politicas/<int:identificador>/editar` | `editar_politica_prestamo()` | `actualizar_politica_prestamo()` → `_guardar_nueva_version_de_politica()` → `desactivar_politica_prestamo()` e `insertar_politica_prestamo()` si hubo cambios. |
| Eliminar una política sin préstamos asociados | POST `/politicas/<int:identificador>/eliminar` | `eliminar_politica_prestamo()` | `eliminar_politica_prestamo()` del servicio → `eliminar_politica_prestamo()` del repositorio. |
| Configurar horario y plazos de reserva | POST `/politicas/configuracion` | `guardar_horario_y_plazos_de_reserva()` | `guardar_horario_y_plazos_de_reserva()` → `HorarioAtencion` y `ConfiguracionReservas` → repositorio `guardar_horario_y_plazos_de_reserva()`. |
| Guardar el cupo de un tipo de persona | POST `/politicas/limite` | `guardar_limite_articulos()` | `guardar_limite_articulos()` → `_validar_y_guardar_limites_por_tipo_de_persona()` → `guardar_limite_articulos()` en SQL. |
| Guardar los cupos de todos los tipos | POST `/politicas/limites` | `guardar_limites_articulos()` | `guardar_limites_articulos()` → `_validar_y_guardar_limites_por_tipo_de_persona()` guarda el conjunto en una transacción. |

## Sanciones e incidencias

[controlador_sancion.py](../SistemaRecursos/presentacion/controladores/control/controlador_sancion.py) · [servicio_sancion.py](../SistemaRecursos/servicios/control/servicio_sancion.py) · [operaciones_sancion.py](../SistemaRecursos/servicios/control/operaciones_sancion.py) · [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py) · [incidencia.py](../SistemaRecursos/dominio/gestion_control/incidencia.py) · [repositorio_sancion_sql.py](../SistemaRecursos/repositorio/control/repositorio_sancion_sql.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Listar y filtrar sanciones | GET `/sanciones` | `consultar_sanciones()` | `consultar_sanciones()` → repositorio `consultar_sanciones()` → `calcular_alertas_de_sancion()`. |
| Ver ficha e historial de una sanción | GET `/sanciones/<int:identificador>` | `consultar_sancion()` | `consultar_sancion()` → `consultar_detalle_sancion()` y `consultar_historial_estado()`. |
| Aplicar una sanción manual | POST `/sanciones/prestamos/<int:prestamo_id>/detalles/<int:detalle_id>` | `aplicar_sancion_a_bien_prestado()` | `aplicar_sancion_a_bien_prestado()` → `_evaluar_falta_del_bien_prestado()` → `aplicar_o_reevaluar_sancion()` → `_crear_sancion_vinculada_a_incidencia()`. |
| Reevaluar una sanción registrada | POST `/sanciones/<int:identificador>/evaluar` | `evaluar_sancion()` | `evaluar_sancion()` → `_evaluar_falta_del_bien_prestado()` → `validar_gravedad_y_motivo_de_sancion()` y `calcular_cambios_de_sancion()` → `actualizar_sancion()`. |
| Regularizar por recuperación, reposición, reparación o verificación | POST `/sanciones/<int:identificador>/regularizar` | `regularizar_sancion()` | `regularizar_sancion()` → `validar_regularizacion_sancion()` → aplica el método según el tipo → `registrar_regularizacion_sancion()`. |
| Levantar una sanción | POST `/sanciones/<int:identificador>/levantar` | `levantar_sancion()` | `levantar_sancion()` → `validar_levantamiento_de_sancion()` → `registrar_cierre_sancion()` con estado `LEVANTADA`. |
| Anular una sanción por error | POST `/sanciones/<int:identificador>/anular` | `anular_sancion()` | `anular_sancion()` comprueba rol y estado → `registrar_cierre_sancion()` con estado `ANULADA`. |
| Registrar recuperación del original después de la reposición | POST `/sanciones/<int:identificador>/recuperar-original` | `registrar_recuperacion_del_bien_original()` | `registrar_recuperacion_del_bien_original()` → `abrir_mantenimiento()` → actualiza inventario, sanción e historial. |
| Configurar plazos de sanción | POST `/sanciones/configuracion` | `guardar_configuracion_sanciones()` | `guardar_configuracion_sanciones()` → `ConfiguracionSanciones` → repositorio `guardar_configuracion_sanciones()`. |

## Reportes, historiales y exportaciones

[controlador_reporte.py](../SistemaRecursos/presentacion/controladores/reportes/controlador_reporte.py) · [servicio_reporte.py](../SistemaRecursos/servicios/reportes/servicio_reporte.py) · [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py) · [historial.py](../SistemaRecursos/servicios/reportes/historial.py) · [repositorio_reporte_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_reporte_sql.py) · [repositorio_historial_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_historial_sql.py) · [csv_reportes.py](../SistemaRecursos/presentacion/reportes/csv_reportes.py) · [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py)

| Operación | Ruta | Función del controlador | Recorrido |
|---|---|---|---|
| Consultar reportes o historial de persona y bien | GET `/reportes` | `consultar_reportes()` | `consultar_reporte_filtrado()` → `FiltroReporte.desde_datos()` → `consultar_filas_reporte()` o `_consultar_y_construir_historial()`. |
| Exportar reporte o historial a CSV | GET `/reportes/exportar.csv` | `exportar_reportes_csv()` | `consultar_reporte_filtrado()` → `generar_csv_reporte()`. |
| Exportar reporte o historial a PDF | GET `/reportes/exportar.pdf` | `exportar_reportes_pdf()` | `consultar_reporte_filtrado()` → `generar_pdf_reporte()` o `generar_pdf_historial()`. |
| Consultar Mi historial | GET `/reportes/mi-historial` | `consultar_historial_propio()` | `consultar_historial_propio()` toma el DNI de la sesión → `_consultar_y_construir_historial()` → `construir_cronologia_historial()`. |
| Exportar Mi historial a CSV | GET `/reportes/mi-historial/exportar.csv` | `exportar_historial_propio_csv()` | `consultar_historial_propio()` → `generar_csv_reporte()`. |
| Exportar Mi historial a PDF | GET `/reportes/mi-historial/exportar.pdf` | `exportar_historial_propio_pdf()` | `consultar_historial_propio()` → `generar_pdf_historial()`. |

`_preparar_consulta_sql_del_reporte()` selecciona la consulta de personas, préstamos, devoluciones, bienes atrasados, inventario, reservas, sanciones o daños y pérdidas. `RepositorioHistorialSQL.consultar_historial()` obtiene los eventos por persona o bien.

## Operaciones automáticas y de instalación

- **Vencimientos automáticos.** `iniciar_procesador_vencimientos()` inicia el ciclo. `ejecutar_revision_de_vencimientos()` coordina `procesar_sanciones_por_vencimiento()` y `expirar_reservas_vencidas()`, y registra el resultado de la revisión. [Inicio del procesador](../SistemaRecursos/arranque/procesador_vencimientos.py) · [Servicio del procesador](../SistemaRecursos/servicios/control/servicio_procesador.py) · [Repositorio del procesador](../SistemaRecursos/repositorio/control/repositorio_procesador_sql.py)
- **Sanciones por retraso y cumplimiento.** `procesar_sanciones_por_vencimiento()` consulta los detalles vencidos y llama a `registrar_sancion_por_retraso()`. Para las sanciones activas que corresponde revisar, `marcar_sancion_cumplida_si_corresponde()` aplica la regla `puede_marcarse_sancion_cumplida()`. [Servicio de sanciones](../SistemaRecursos/servicios/control/servicio_sancion.py) · [Operaciones de sanción](../SistemaRecursos/servicios/control/operaciones_sancion.py)
- **Primer administrador.** `run.ps1 -CrearAdministrador` pide los datos y llama a `registrar_primer_administrador()` → `registrar_primera_cuenta_administradora()`. El código que muestra sirve para activar la cuenta. [Inicializar administrador](../SistemaRecursos/arranque/inicializar_administrador.py) · [Guía de instalación](GUIA_INSTALACION.md)
- **Instalación desde cero.** Importa `schema.sql` o `datos_prueba.sql`. `run.ps1` prepara el entorno y arranca la aplicación. [Guía de instalación](GUIA_INSTALACION.md)

## Utilidades y pruebas

| Dónde buscar | Nombres en el código |
|---|---|
| Validar datos del formulario | `validar_entero()`, `validar_dni()`, `validar_lista_de_ids_de_bienes()` y `convertir_fecha_local_de_lima_a_utc()`. [Validación compartida](../SistemaRecursos/dominio/compartido/validacion.py) |
| Abrir una conexión y ejecutar una escritura | `sesion()`, `ejecutar_escritura_sql()` e `insertar_fila_sql()`. [Conexión MySQL](../SistemaRecursos/repositorio/base_datos/conexion_mysql.py) · [Repositorio SQL base](../SistemaRecursos/repositorio/base_datos/base_sql.py) |
| Recuperar un formulario con errores | `recuperar_formulario_tras_error()` identifica el formulario y recupera sus campos. `campo_de_formulario()` y `selector_de_opciones()` los muestran. [Control de formularios](../SistemaRecursos/presentacion/formularios.py) · [Macros](../SistemaRecursos/presentacion/vistas/parciales/formularios.html) |
| Actualizar un formulario en el navegador | `actualizarCamposDeDevolucion()` ajusta los campos de recepción. `buscarPersonasPorTermino()` y `buscarBienesDisponibles()` cargan resultados para registrar un préstamo. [JavaScript general](../SistemaRecursos/presentacion/static/aplicacion.js) · [JavaScript de préstamos](../SistemaRecursos/presentacion/static/prestamo.js) |
| Preparar Python y la conexión antes de ejecutar un comando | `Obtener-EjecutablePythonDelProyecto` y `Configurar-ConexionMySqlDelProyecto`. [Script de arranque](../SistemaRecursos/run.ps1) |
| Encontrar una prueba por el resultado que comprueba | `test_no_aprueba_ampliacion_de_bien_ya_devuelto()` y `test_mantenimiento_bloquea_prestamo_hasta_su_cierre()`. Para montar una prueba web con un rol, busca `crear_cliente_con_sesion_simulada()`. [Pruebas con MySQL](../SistemaRecursos/tests/integracion/test_cierre_mysql.py) · [Utilidades de pruebas](../SistemaRecursos/tests/soporte_roles.py) |

## Lista completa de renombres

La lista reúne los renombres del código vigente. Los enlaces apuntan a la definición actual.

### Arranque y scripts

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `clave_local()` | `obtener_clave_de_sesion_flask()` | [app.py](../SistemaRecursos/app.py#L56) |
| `main()` | `iniciar_servidor_web()` | [app.py](../SistemaRecursos/app.py#L146) |
| `main()` | `inicializar_administrador_desde_consola()` | [inicializar_administrador.py](../SistemaRecursos/arranque/inicializar_administrador.py#L14) |
| `main()` | `ejecutar_procesador_desde_consola()` | [procesador_vencimientos.py](../SistemaRecursos/arranque/procesador_vencimientos.py#L29) |
| `Obtener-PythonProyecto` | `Obtener-EjecutablePythonDelProyecto` | [run.ps1](../SistemaRecursos/run.ps1) |
| `Configurar-ConexionProyecto` | `Configurar-ConexionMySqlDelProyecto` | [run.ps1](../SistemaRecursos/run.ps1) |

### Dominio y validación

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `texto()` | `validar_texto()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L19) |
| `entero()` | `validar_entero()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L31) |
| `dni()` | `validar_dni()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L44) |
| `instante()` | `normalizar_fecha_hora_utc()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L51) |
| `fecha_local()` | `convertir_fecha_local_de_lima_a_utc()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L59) |
| `ids()` | `validar_lista_de_ids_de_bienes()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L71) |
| `version()` | `calcular_version_de_registro()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L80) |
| `comprobar_version()` | `exigir_version_vigente()` | [validacion.py](../SistemaRecursos/dominio/compartido/validacion.py#L86) |
| `consultar_sancion_detalle()` | `consultar_sancion_por_detalle_prestamo()` | [contratos_control.py](../SistemaRecursos/dominio/gestion_control/contratos_control.py#L32) |
| `consultar_detalles_vencidos()` | `consultar_detalles_de_prestamo_vencidos()` | [contratos_control.py](../SistemaRecursos/dominio/gestion_control/contratos_control.py#L49) |
| `consultar_sanciones_a_revisar()` | `consultar_sanciones_activas_para_revision()` | [contratos_control.py](../SistemaRecursos/dominio/gestion_control/contratos_control.py#L50) |
| `hora()` | `validar_hora_de_atencion()` | [politica_prestamo.py](../SistemaRecursos/dominio/gestion_control/politica_prestamo.py#L25) |
| `cierre()` | `obtener_cierre_si_hay_atencion()` | [politica_prestamo.py](../SistemaRecursos/dominio/gestion_control/politica_prestamo.py#L57) |
| `vencimiento()` | `calcular_fecha_limite_devolucion()` | [politica_prestamo.py](../SistemaRecursos/dominio/gestion_control/politica_prestamo.py#L116) |
| `vencimiento()` | `calcular_vencimiento_de_reserva()` | [politica_prestamo.py](../SistemaRecursos/dominio/gestion_control/politica_prestamo.py#L147) |
| `falta_por_retraso()` | `determinar_falta_por_retraso()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L50) |
| `regularizacion_por_devolucion()` | `determinar_regularizacion_por_devolucion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L68) |
| `esta_regularizado()` | `sancion_tiene_regularizacion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L122) |
| `validar_levantamiento()` | `validar_levantamiento_de_sancion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L137) |
| `validar_reparacion()` | `validar_aceptacion_de_reparacion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L192) |
| `validar_verificacion()` | `validar_devolucion_para_verificacion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L199) |
| `alertas_revision()` | `calcular_alertas_de_sancion()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L218) |
| `datos()` | `como_diccionario()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L101) · [persona.py](../SistemaRecursos/dominio/gestion_personas_usuarios/persona.py#L88) |
| `medida()` | `calcular_periodo_por_gravedad()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L104) |
| `fecha_revision_perdida()` | `calcular_fecha_revision_por_perdida()` | [sancion.py](../SistemaRecursos/dominio/gestion_control/sancion.py#L113) |
| `permite()` | `tiene_permiso()` | [acceso.py](../SistemaRecursos/dominio/gestion_personas_usuarios/acceso.py#L35) |
| `nombre_usuario_disponible()` | `elegir_nombre_de_usuario_disponible()` | [cuenta.py](../SistemaRecursos/dominio/gestion_personas_usuarios/cuenta.py#L53) |
| `activa()` | `es_cuenta_administradora_activa()` | [cuenta.py](../SistemaRecursos/dominio/gestion_personas_usuarios/cuenta.py#L107) |
| `validar_elegibilidad()` | `validar_elegibilidad_del_solicitante()` | [persona.py](../SistemaRecursos/dominio/gestion_personas_usuarios/persona.py#L101) |
| `huella_sesion()` | `calcular_huella_del_token_de_sesion()` | [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py#L24) |
| `minutos_bloqueo()` | `calcular_minutos_de_bloqueo_restantes()` | [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py#L55) |
| `registrar_fallo()` | `registrar_intento_de_acceso_fallido()` | [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py#L65) |
| `limpiar()` | `borrar_intentos_y_bloqueo()` | [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py#L77) |
| `_depurar()` | `_eliminar_intentos_y_bloqueos_expirados()` | [sesion.py](../SistemaRecursos/dominio/gestion_personas_usuarios/sesion.py#L82) |
| `calcular()` | `calcular_nuevo_plazo_de_devolucion()` | [ampliacion_prestamo.py](../SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py#L43) |

### Servicios y reportes

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `consultar_solicitudes_prestamo()` | `consultar_solicitudes_de_ampliacion_del_prestamo()` | [servicio_ampliacion_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_ampliacion_prestamo.py#L172) |
| `participa_en_prestamo()` | `es_titular_o_integrante_del_prestamo()` | [servicio_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_prestamo.py#L71) |
| `exigir_operador_ajeno()` | `exigir_operador_que_no_participe_en_el_prestamo()` | [servicio_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_prestamo.py#L75) |
| `autorizar_recepcion_propia()` | `validar_autorizacion_si_es_recepcion_propia()` | [servicio_prestamo.py](../SistemaRecursos/servicios/prestamos/servicio_prestamo.py#L80) |
| `_validar_tipo()` | `_validar_tipo_de_reporte()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L37) |
| `_limpiar_filtros()` | `_descartar_filtros_ajenos_al_reporte()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L41) |
| `_normalizar_textos()` | `_normalizar_textos_e_identificadores()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L55) |
| `_validar_rango()` | `_validar_rango_de_fechas()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L74) |
| `_utc()` | `_convertir_medianoche_de_lima_a_utc()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L95) |
| `inicio()` | `inicio_del_rango_utc()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L99) |
| `fin()` | `fin_exclusivo_del_rango_utc()` | [filtro_reporte.py](../SistemaRecursos/servicios/reportes/filtro_reporte.py#L103) |
| `_identificar_ampliacion()` | `_identificar_detalle_de_ampliacion()` | [historial.py](../SistemaRecursos/servicios/reportes/historial.py#L19) |
| `_etiqueta_cierre()` | `_etiquetar_cierre_de_sancion()` | [historial.py](../SistemaRecursos/servicios/reportes/historial.py#L30) |
| `agregar()` | `agregar_evento_a_cronologia()` | [historial.py](../SistemaRecursos/servicios/reportes/historial.py#L42) |

### Repositorios y base de datos

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `ejecutar()` | `ejecutar_escritura_sql()` | [base_sql.py](../SistemaRecursos/repositorio/base_datos/base_sql.py#L54) |
| `insertar()` | `insertar_fila_sql()` | [base_sql.py](../SistemaRecursos/repositorio/base_datos/base_sql.py#L67) |
| `leer()` | `leer_resultados_con_cursor()` | [base_sql.py](../SistemaRecursos/repositorio/base_datos/base_sql.py#L45) |
| `registrar_error()` | `registrar_error_del_procesador()` | [repositorio_procesador_sql.py](../SistemaRecursos/repositorio/control/repositorio_procesador_sql.py#L35) |
| `consultar_sancion_detalle()` | `consultar_sancion_por_detalle_prestamo()` | [repositorio_sancion_sql.py](../SistemaRecursos/repositorio/control/repositorio_sancion_sql.py#L82) |
| `consultar_detalles_vencidos()` | `consultar_detalles_de_prestamo_vencidos()` | [repositorio_sancion_sql.py](../SistemaRecursos/repositorio/control/repositorio_sancion_sql.py#L130) |
| `consultar_sanciones_a_revisar()` | `consultar_sanciones_activas_para_revision()` | [repositorio_sancion_sql.py](../SistemaRecursos/repositorio/control/repositorio_sancion_sql.py#L138) |
| `cargar_cuentas_para_actualizar()` | `consultar_y_bloquear_cuentas_para_edicion()` | [repositorio_cuenta_sql.py](../SistemaRecursos/repositorio/personas_usuarios/repositorio_cuenta_sql.py#L7) |
| `consultar_balance_cola()` | `contar_disponibles_y_reservas_en_espera()` | [repositorio_prestamo_sql.py](../SistemaRecursos/repositorio/prestamos/repositorio_prestamo_sql.py#L245) |
| `_buscar_sujetos()` | `_buscar_personas_o_bienes_del_historial()` | [repositorio_historial_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_historial_sql.py#L21) |
| `_where()` | `_armar_clausula_where()` | [repositorio_reporte_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_reporte_sql.py#L71) |
| `_filtros_comunes()` | `_construir_filtros_sql_comunes()` | [repositorio_reporte_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_reporte_sql.py#L74) |
| `_filtros_personas()` | `_agregar_filtros_sql_de_personas()` | [repositorio_reporte_sql.py](../SistemaRecursos/repositorio/reportes/repositorio_reporte_sql.py#L100) |

### Controladores y utilidades web

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `_mostrar_codigo()` | `_mostrar_codigo_de_activacion()` | [controlador_cuenta.py](../SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_cuenta.py#L98) |
| `_mostrar_cuenta()` | `_mostrar_formulario_de_cuenta()` | [controlador_cuenta.py](../SistemaRecursos/presentacion/controladores/personas_usuarios/controlador_cuenta.py#L107) |
| `_mostrar_prestamo()` | `_mostrar_ficha_del_prestamo()` | [controlador_ampliacion_prestamo.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_ampliacion_prestamo.py#L116) |
| `_bien_formulario()` | `_preparar_bien_para_formulario_prestamo()` | [controlador_prestamo.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_prestamo.py#L9) |
| `_contexto_estados()` | `_proporcionar_estados_de_reserva()` | [controlador_reserva.py](../SistemaRecursos/presentacion/controladores/prestamos/controlador_reserva.py#L31) |
| `_mostrar_categorias()` | `_mostrar_listado_de_categorias()` | [controlador_recurso.py](../SistemaRecursos/presentacion/controladores/recursos/controlador_recurso.py#L163) |
| `registrar_errores()` | `registrar_manejadores_de_errores_http()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L8) |
| `mostrar_error()` | `renderizar_pagina_de_error()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L9) |
| `conflicto()` | `responder_conflicto()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L13) |
| `valor_invalido()` | `responder_error_de_validacion()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L17) |
| `no_encontrado()` | `responder_registro_no_encontrado()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L21) |
| `sin_permiso()` | `responder_acceso_denegado()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L25) |
| `error_http()` | `responder_excepcion_http()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L29) |
| `error_base()` | `responder_error_de_base_de_datos()` | [errores_http.py](../SistemaRecursos/presentacion/errores_http.py#L44) |
| `registrar_filtros()` | `registrar_filtros_de_plantillas()` | [filtros_plantillas.py](../SistemaRecursos/presentacion/filtros_plantillas.py#L7) |
| `fecha()` | `formatear_fecha_en_lima()` | [filtros_plantillas.py](../SistemaRecursos/presentacion/filtros_plantillas.py#L18) |
| `hora()` | `formatear_hora_de_atencion()` | [filtros_plantillas.py](../SistemaRecursos/presentacion/filtros_plantillas.py#L27) |
| `_normalizar()` | `_normalizar_mensaje_de_error()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L12) |
| `recuperar_formulario()` | `recuperar_formulario_tras_error()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L18) |
| `_campos_del_error()` | `_asociar_mensaje_al_campo_del_formulario()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L54) |
| `identificador_campo()` | `generar_id_del_campo()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L111) |
| `decorar()` | `decorar_recuperacion_del_formulario()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L19) |
| `protegida()` | `ejecutar_con_recuperacion_del_formulario()` | [formularios.py](../SistemaRecursos/presentacion/formularios.py#L21) |
| `regreso_prestamos()` | `obtener_url_de_regreso_a_prestamos()` | [navegacion.py](../SistemaRecursos/presentacion/navegacion.py#L8) |
| `detalle_prestamo()` | `obtener_url_del_detalle_de_prestamo()` | [navegacion.py](../SistemaRecursos/presentacion/navegacion.py#L25) |
| `_celda_csv()` | `_sanear_valor_para_csv()` | [csv_reportes.py](../SistemaRecursos/presentacion/reportes/csv_reportes.py#L10) |
| `ceil_segmentos()` | `calcular_segmentos_del_sector()` | [dibujos_reportes.py](../SistemaRecursos/presentacion/reportes/dibujos_reportes.py#L39) |
| `dibujos_graficos()` | `dibujar_graficos_de_reporte()` | [dibujos_reportes.py](../SistemaRecursos/presentacion/reportes/dibujos_reportes.py#L65) |
| `_rango()` | `_clasificar_atraso_por_intervalo()` | [graficos_reportes.py](../SistemaRecursos/presentacion/reportes/graficos_reportes.py#L21) |
| `_serie()` | `_calcular_serie_de_frecuencias()` | [graficos_reportes.py](../SistemaRecursos/presentacion/reportes/graficos_reportes.py#L31) |
| `_fecha_lima()` | `_formatear_fecha_pdf_en_lima()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L51) |
| `_celda_pdf()` | `_formatear_celda_del_reporte_pdf()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L59) |
| `_peso_columna()` | `_calcular_peso_de_columna_pdf()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L84) |
| `_preparar_pdf()` | `_preparar_documento_pdf()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L100) |
| `_datos_pdf()` | `_formatear_datos_de_ficha_pdf()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L200) |
| `_prestamo_pdf()` | `_construir_ficha_de_prestamo_pdf()` | [pdf_reportes.py](../SistemaRecursos/presentacion/reportes/pdf_reportes.py#L241) |
| `decorar()` | `decorar_verificacion_de_permisos()` | [seguridad.py](../SistemaRecursos/presentacion/seguridad.py#L28) |
| `protegida()` | `ejecutar_con_verificacion_de_permisos()` | [seguridad.py](../SistemaRecursos/presentacion/seguridad.py#L30) |

### JavaScript y macros de Jinja

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `actualizar()` | `actualizarCamposDeDevolucion()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L82) |
| `consultar()` | `consultarFechaPreviaDeAmpliacion()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L106) |
| `programar()` | `programarConsultaDeAmpliacion()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L132) |
| `actualizarGuardado()` | `habilitarGuardadoSiHayCambios()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L143) |
| `cambiarMenu()` | `ajustarVisibilidadDelMenu()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L183) |
| `filtrar()` | `filtrarFilasPorBusqueda()` | [aplicacion.js](../SistemaRecursos/presentacion/static/aplicacion.js#L248) |
| `etiquetaTipo()` | `obtenerEtiquetaDelTipoDePersona()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L36) |
| `textoIdentificacion()` | `formatearDocumentosDePersona()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L45) |
| `pintarParticipantes()` | `mostrarParticipantesDelPrestamo()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L144) |
| `politicaDelBien()` | `obtenerPoliticaAplicableAlBien()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L173) |
| `horarioActual()` | `consultarHorarioDeAtencionActual()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L183) |
| `actualizarPoliticas()` | `actualizarCondicionesDeEntrega()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L210) |
| `actualizarResumen()` | `actualizarResumenDelPrestamo()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L239) |
| `crearFilaBien()` | `crearFilaDeBienSeleccionado()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L267) |
| `pintarBienes()` | `mostrarBienesSeleccionados()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L325) |
| `consultarPersonas()` | `configurarBusquedaDePersonas()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L336) |
| `consultar()` | `buscarPersonasPorTermino()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L353) |
| `consultarBienes()` | `configurarBusquedaDeBienes()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L430) |
| `consultar()` | `buscarBienesDisponibles()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L443) |
| `recuperarPersona()` | `buscarPersonaPorDni()` | [prestamo.js](../SistemaRecursos/presentacion/static/prestamo.js#L548) |
| `evaluacion_sancion()` | `formulario_de_evaluacion_de_sancion()` | [formularios_sancion.html](../SistemaRecursos/presentacion/vistas/control/parciales/formularios_sancion.html#L2) |
| `indicador()` | `tarjeta_indicadora()` | [componentes.html](../SistemaRecursos/presentacion/vistas/parciales/componentes.html#L1) |
| `estado()` | `insignia_de_estado()` | [componentes.html](../SistemaRecursos/presentacion/vistas/parciales/componentes.html#L29) |
| `csrf()` | `campo_oculto_csrf()` | [formularios.html](../SistemaRecursos/presentacion/vistas/parciales/formularios.html#L2) |
| `campo()` | `campo_de_formulario()` | [formularios.html](../SistemaRecursos/presentacion/vistas/parciales/formularios.html#L5) |
| `opciones()` | `selector_de_opciones()` | [formularios.html](../SistemaRecursos/presentacion/vistas/parciales/formularios.html#L23) |
| `historial()` | `tabla_de_historial()` | [formularios.html](../SistemaRecursos/presentacion/vistas/parciales/formularios.html#L43) |
| `continuar_registro()` | `acciones_tras_registrar_recurso()` | [fragmentos_recursos.html](../SistemaRecursos/presentacion/vistas/recursos/parciales/fragmentos_recursos.html#L3) |
| `icono_recurso()` | `mostrar_icono_del_recurso()` | [fragmentos_recursos.html](../SistemaRecursos/presentacion/vistas/recursos/parciales/fragmentos_recursos.html#L14) |
| `categorias_recursos()` | `panel_de_categorias()` | [fragmentos_recursos.html](../SistemaRecursos/presentacion/vistas/recursos/parciales/fragmentos_recursos.html#L74) |
| `filtro_opciones()` | `selector_de_filtro()` | [vista_reporte.html](../SistemaRecursos/presentacion/vistas/reportes/vista_reporte.html#L5) |

### Pruebas y utilidades de pruebas

| Nombre anterior | Nombre actual | Definición |
|---|---|---|
| `intentar()` | `capturar_resultado_o_excepcion()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L29) |
| `prestar()` | `registrar_prestamo_de_prueba()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L68) |
| `detalle()` | `consultar_detalle_por_prestamo_y_bien()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L75) |
| `app()` | `crear_aplicacion_de_prueba()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L79) |
| `iniciar_sesion()` | `enviar_formulario_de_inicio_de_sesion()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L83) |
| `test_seg01_limite_de_intentos_por_cuenta()` | `test_login_bloquea_intentos_por_cuenta()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L116) |
| `test_seg01_cuenta_inexistente_recibe_el_mismo_trato()` | `test_login_limita_intentos_de_cuenta_inexistente()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L127) |
| `test_seg02_cerrar_sesion_invalida_la_cookie_copiada()` | `test_cerrar_sesion_invalida_la_cookie_copiada()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L136) |
| `test_seg02_inactividad_y_duracion_maxima()` | `test_sesion_vence_por_inactividad_o_duracion_maxima()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L153) |
| `test_seg02_desactivar_cuenta_expulsa_de_inmediato()` | `test_desactivar_cuenta_cierra_el_acceso_de_inmediato()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L166) |
| `cliente_real()` | `crear_cliente_con_cuenta_de_mysql()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L270) |
| `test_seg03_permisos_en_el_servidor()` | `test_rutas_rechazan_peticion_sin_permiso_o_sin_token()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L274) |
| `test_aut01_identificadores_unicos_en_registros_simultaneos()` | `test_registros_simultaneos_de_bienes_generan_identificadores_unicos()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L297) |
| `test_aut02_edicion_no_cambia_identificador_ni_acepta_fecha_futura()` | `test_editar_bien_conserva_identificador_y_rechaza_fecha_futura()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L313) |
| `test_man01_ciclo_completo_y_bloqueo_de_prestamo()` | `test_mantenimiento_bloquea_prestamo_hasta_su_cierre()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L328) |
| `test_man01_aperturas_simultaneas_dejan_un_solo_registro()` | `test_aperturas_simultaneas_dejan_un_solo_mantenimiento()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L347) |
| `test_man01_no_entra_con_prestamo_pendiente()` | `test_no_abre_mantenimiento_con_prestamo_pendiente()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L356) |
| `test_amp01_solicitar_rechazar_y_aprobar_una_sola_vez()` | `test_solicitud_de_ampliacion_se_aprueba_una_sola_vez()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L366) |
| `test_amp01_aprobacion_rechazada_si_el_bien_ya_se_devolvio()` | `test_no_aprueba_ampliacion_de_bien_ya_devuelto()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L392) |
| `test_amp01_pedido_que_supera_la_politica_no_se_registra()` | `test_rechaza_solicitud_de_ampliacion_que_supera_la_politica()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L445) |
| `test_pru01_devolucion_parcial_y_repeticion()` | `test_devolucion_parcial_rechaza_repetir_el_mismo_bien()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L455) |
| `test_pru03_dos_prestamos_simultaneos_del_mismo_bien()` | `test_dos_prestamos_simultaneos_del_mismo_bien()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L471) |
| `test_cn06_integrante_acumula_cupo_entre_grupos_y_libera_al_devolver()` | `test_integrante_acumula_cupo_entre_grupos_y_libera_al_devolver()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L483) |
| `test_cn06_entregas_simultaneas_comparten_el_cupo_del_integrante()` | `test_entregas_simultaneas_comparten_el_cupo_del_integrante()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L503) |
| `test_ope01_exclusion_y_registro_de_ejecuciones()` | `test_revision_excluye_segundo_procesador_y_registra_el_resultado()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L620) |
| `test_ope01_revision_real_de_vencimientos()` | `test_procesador_ejecuta_revision_de_sanciones_y_reservas()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L642) |
| `test_ope01_reinicio_y_segundo_procesador_respetan_el_intervalo()` | `test_reinicio_y_segundo_procesador_respetan_intervalo_de_revision()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L650) |
| `desactivar()` | `desactivar_cuenta_en_simultaneo()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L212) |
| `entregar()` | `registrar_prestamo_grupal_en_simultaneo()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L509) |
| `falla()` | `simular_revision_con_base_caida()` | [test_cierre_mysql.py](../SistemaRecursos/tests/integracion/test_cierre_mysql.py#L631) |
| `cliente()` | `crear_cliente_para_rol()` | [test_pantalla_roles_fijos.py](../SistemaRecursos/tests/integracion/test_pantalla_roles_fijos.py#L17) · [test_pantallas_cierre.py](../SistemaRecursos/tests/integracion/test_pantallas_cierre.py#L62) · [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L111) |
| `bien()` | `crear_bien_de_prueba()` | [test_pantallas_cierre.py](../SistemaRecursos/tests/integracion/test_pantallas_cierre.py#L13) |
| `detalle_bien()` | `crear_ficha_de_bien_de_prueba()` | [test_pantallas_cierre.py](../SistemaRecursos/tests/integracion/test_pantallas_cierre.py#L22) |
| `solicitud()` | `crear_solicitud_de_ampliacion_de_prueba()` | [test_pantallas_cierre.py](../SistemaRecursos/tests/integracion/test_pantallas_cierre.py#L30) |
| `prestamo()` | `crear_prestamo_de_prueba()` | [test_pantallas_cierre.py](../SistemaRecursos/tests/integracion/test_pantallas_cierre.py#L40) |
| `consulta()` | `ejecutar_sql_de_prueba()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L58) |
| `sancion()` | `consultar_sancion_de_prueba()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L95) |
| `devolver()` | `registrar_devolucion_del_bien_de_prueba()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L98) |
| `perder()` | `reportar_perdida_del_bien_de_prueba()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L102) |
| `reponer()` | `registrar_reposicion_del_bien_de_prueba()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L105) |
| `test_configuracion_solo_admin_con_version_y_snapshot()` | `test_plazos_de_sancion_requieren_administrador_y_version_vigente()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L228) |
| `test_pantallas_permisos_y_csrf()` | `test_pantallas_de_sancion_exigen_permiso_y_token_csrf()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L473) |
| `eliminar_base()` | `eliminar_base_temporal_de_pruebas()` | [test_sanciones_mysql.py](../SistemaRecursos/tests/integracion/test_sanciones_mysql.py#L40) |
| `cliente_autenticado()` | `crear_cliente_con_sesion_simulada()` | [soporte_roles.py](../SistemaRecursos/tests/soporte_roles.py#L7) |
| `cuenta()` | `crear_cuenta_de_prueba()` | [soporte_roles.py](../SistemaRecursos/tests/soporte_roles.py#L23) |
| `test_la_huella_no_es_el_token()` | `test_huella_de_sesion_no_expone_el_token()` | [test_reglas_cierre.py](../SistemaRecursos/tests/unitarios/test_reglas_cierre.py#L91) |
| `test_valida_datos_y_estado()` | `test_solicitud_de_ampliacion_valida_datos_estado_y_titular()` | [test_reglas_cierre.py](../SistemaRecursos/tests/unitarios/test_reglas_cierre.py#L144) |
| `test_perfiles_acordados()` | `test_roles_fijos_tienen_los_permisos_definidos()` | [test_roles_fijos.py](../SistemaRecursos/tests/unitarios/test_roles_fijos.py#L17) |
