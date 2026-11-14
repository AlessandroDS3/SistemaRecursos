# Comparación de las dos copias

Comparación del contenido actual en disco, incluidas las modificaciones locales pendientes. No compara solamente commits.

- Anterior: `D:\TI_sistema_recursos\SistemaRecursos_local`.
- Reescrita: `D:\TI_sistema_recursos\SistemaRecursos_rehecho`.

Se excluyen Git, entornos virtuales, cachés, archivos locales de configuración, datos locales y este informe. Los totales de archivos incluyen pruebas, documentación y recursos estáticos. Las funciones y líneas Python se cuentan únicamente en producción: app, dominio, servicios, repositorios y presentación.

| Medida | Anterior | Reescrita |
| --- | ---: | ---: |
| Archivos incluidos | 153 | 116 |
| Módulos Python de producción, con inicializadores | 104 | 67 |
| Líneas Python de producción, con comentarios y blancos | 7135 | 4078 |
| Definiciones de funciones y métodos de producción | 575 | 376 |

Archivos: **32 añadidos**, **69 retirados**, **62 modificados en la misma ruta**.

Definiciones: **264 añadidas**, **463 retiradas**, **110 modificadas conservando ruta y nombre**, **2 con AST idéntico**.

Una definición se identifica por ruta y nombre cualificado. El recuento incluye constructores, métodos de contratos, funciones internas y auxiliares. Mover o renombrar una función cuenta como retirada y añadida; estos números no equivalen a funcionalidades de usuario ganadas o perdidas. Los métodos con el mismo nombre repetido, como propiedades con setter, se distinguen por orden de aparición. Las modificaciones se comparan mediante AST, sin contar cambios de formato.

## Comparación funcional

| Operación | Resultado en la reescrita |
| --- | --- |
| Login y recuperación de sesión | Se conservan; cuenta mínima en acceso.py y repositorio exclusivo de acceso. |
| Administración de cuentas | Se conserva; se separan controlador_cuenta.py y repositorio_cuenta_sql.py. |
| Personas, roles, recursos, bienes y políticas | Se conservan sus operaciones principales; se reorganizan modelos, contratos y formularios. |
| Préstamos individuales y grupales, devolución parcial, pérdida y ampliación directa | Se conservan; las decisiones puras quedan en el dominio y las escrituras relacionadas comparten transacción. |
| Reservas, cola, preparación, entrega, cancelación, rechazo y vencimiento | Se conservan, incluidos filtros y resolución manual. |
| Sanciones por retraso y levantamiento | Se conservan; se añade una pantalla central de sanciones. |
| Reportes y CSV | Se conservan filtros de préstamos; se añade un selector específico de devoluciones con fechas de devolución. |
| Selección en el formulario de préstamo | Cambia: entrada de DNI y lista de bienes; el buscador dinámico anterior se sustituye por una interfaz más sencilla y consulta de condiciones. |

Las rutas y firmas internas cambiaron. Esta comparación no certifica equivalencia completa de todas las interacciones de las dos interfaces.

## Ejemplos de funciones renombradas o reunidas

| Servicio | Antes | Ahora |
| --- | --- | --- |
| Acceso | consultar_usuario_activo | consultar_cuenta_activa |
| Cuenta | registrar_cuenta | registrar_cuenta |
| Cuenta | consultar_cuenta | consultar_cuenta |
| Cuenta | actualizar_cuenta y cambiar_estado_cuenta | actualizar_cuenta |
| Rol | actualizar_matriz_permisos | guardar_matriz_permisos; el controlador convierte el formulario |
| Préstamo | registrar_prestamo | registrar_prestamo |
| Préstamo | registrar_en_operacion | registrar_prestamo_en_operacion |
| Reserva | registrar_reserva | registrar_reserva |
| Reserva | preparar_reserva, entregar_reserva, cancelar_reserva, rechazar_reserva, expirar_reserva | Los mismos nombres públicos; comparten _resolver_reserva como coordinador privado |

Estos ejemplos son correspondencias de casos de uso; las firmas y los resultados no son intercambiables automáticamente.

## Corrección posterior a la reescritura

Se añadió validar_clave en dominio/gestion_personas_usuarios/cuenta.py. ServicioAplicacionCuenta._actualizar valida la contraseña aunque no se envíe nombre_usuario. La clave vacía conserva la actual; una clave nueva exige texto de 12 a 256 caracteres. Se añadieron pruebas de entradas inválidas, actualización parcial y formulario HTTP.

Verificación actual tras uniformar los nombres: **81 pruebas correctas, sin omisiones, en 140,158 segundos**, incluida la corrección de contraseñas. Registro local: `SistemaRecursos/datos_locales/nombres_uniformes_final.log`.

## Archivos añadidos

- `README.md`
- `SistemaRecursos/dominio/compartido/__init__.py`
- `SistemaRecursos/dominio/compartido/contratos.py`
- `SistemaRecursos/dominio/compartido/validacion.py`
- `SistemaRecursos/dominio/gestion_control/incidencia.py`
- `SistemaRecursos/dominio/gestion_control/reporte.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/acceso.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/cuenta.py`
- `SistemaRecursos/presentacion/controladores/controlador_cuenta.py`
- `SistemaRecursos/presentacion/controladores/controlador_sancion.py`
- `SistemaRecursos/presentacion/static/aplicacion.js`
- `SistemaRecursos/presentacion/vistas/error.html`
- `SistemaRecursos/presentacion/vistas/formularios.html`
- `SistemaRecursos/presentacion/vistas/inicio.html`
- `SistemaRecursos/presentacion/vistas/vista_cuenta.html`
- `SistemaRecursos/presentacion/vistas/vista_sancion.html`
- `SistemaRecursos/pyproject.toml`
- `SistemaRecursos/repositorio/base_sql.py`
- `SistemaRecursos/repositorio/repositorio_ampliacion_prestamo_sql.py`
- `SistemaRecursos/repositorio/repositorio_cuenta_sql.py`
- `SistemaRecursos/requirements-dev.txt`
- `SistemaRecursos/tests/caso_mysql.py`
- `SistemaRecursos/tests/test_acceso.py`
- `SistemaRecursos/tests/test_arquitectura.py`
- `SistemaRecursos/tests/test_dominio.py`
- `SistemaRecursos/tests/test_flujo_web.py`
- `SistemaRecursos/tests/test_persona_cuenta.py`
- `SistemaRecursos/tests/test_prestamo.py`
- `SistemaRecursos/tests/test_recursos.py`
- `SistemaRecursos/tests/test_reporte.py`
- `SistemaRecursos/tests/test_reserva.py`
- `SistemaRecursos/tests/test_servicios_sin_mysql.py`

## Archivos retirados

- `SistemaRecursos/dominio/gestion_control/fabrica_politica_prestamo.py`
- `SistemaRecursos/dominio/gestion_control/horario_atencion.py`
- `SistemaRecursos/dominio/gestion_control/i_repositorio_politica_prestamo.py`
- `SistemaRecursos/dominio/gestion_control/i_repositorio_reporte.py`
- `SistemaRecursos/dominio/gestion_control/i_repositorio_sancion.py`
- `SistemaRecursos/dominio/gestion_control/politica_vencimiento_reserva.py`
- `SistemaRecursos/dominio/gestion_control/tipo_persona.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/administrativo.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/docente.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/estudiante.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/fabrica_persona.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/i_repositorio_persona.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/i_repositorio_rol.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/nombre_rol.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/permiso.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/usuario_sistema.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/validacion_persona.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/version_edicion.py`
- `SistemaRecursos/dominio/gestion_prestamos/contexto_entrega.py`
- `SistemaRecursos/dominio/gestion_prestamos/detalle_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/fabrica_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/i_operacion_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/i_operacion_reserva.py`
- `SistemaRecursos/dominio/gestion_prestamos/i_repositorio_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/i_repositorio_reserva.py`
- `SistemaRecursos/dominio/gestion_prestamos/incidencia.py`
- `SistemaRecursos/dominio/gestion_prestamos/participante_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/solicitud_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/tipo_incidencia.py`
- `SistemaRecursos/dominio/gestion_prestamos/tipo_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/validacion_prestamo.py`
- `SistemaRecursos/dominio/gestion_recursos/categoria_recurso.py`
- `SistemaRecursos/dominio/gestion_recursos/fabrica_bien_material.py`
- `SistemaRecursos/dominio/gestion_recursos/fabrica_recurso.py`
- `SistemaRecursos/dominio/gestion_recursos/i_repositorio_bien_material.py`
- `SistemaRecursos/dominio/gestion_recursos/i_repositorio_recurso.py`
- `SistemaRecursos/dominio/gestion_recursos/validacion_recurso.py`
- `SistemaRecursos/dominio/resultados_consulta.py`
- `SistemaRecursos/presentacion/formularios.py`
- `SistemaRecursos/presentacion/static/ampliacion.js`
- `SistemaRecursos/presentacion/static/devolucion.js`
- `SistemaRecursos/presentacion/static/interfaz.js`
- `SistemaRecursos/presentacion/static/persona.js`
- `SistemaRecursos/presentacion/static/politica.js`
- `SistemaRecursos/presentacion/static/prestamo.js`
- `SistemaRecursos/presentacion/static/reserva.js`
- `SistemaRecursos/presentacion/vistas/__init__.py`
- `SistemaRecursos/presentacion/vistas/ampliaciones_prestamo.html`
- `SistemaRecursos/presentacion/vistas/formulario_alta_cuenta.html`
- `SistemaRecursos/presentacion/vistas/vista_bien_material.py`
- `SistemaRecursos/presentacion/vistas/vista_persona.py`
- `SistemaRecursos/presentacion/vistas/vista_politica_prestamo.py`
- `SistemaRecursos/presentacion/vistas/vista_prestamo.py`
- `SistemaRecursos/presentacion/vistas/vista_recurso.py`
- `SistemaRecursos/presentacion/vistas/vista_rol.py`
- `SistemaRecursos/repositorio/politica_vencimiento_reserva_sql.py`
- `SistemaRecursos/repositorio/sanciones_vencimiento_sql.py`
- `SistemaRecursos/servicios/validacion_identificadores.py`
- `SistemaRecursos/tests/soporte_prestamos.py`
- `SistemaRecursos/tests/test_acceso_flask.py`
- `SistemaRecursos/tests/test_ampliacion_prestamo.py`
- `SistemaRecursos/tests/test_configuracion_general.py`
- `SistemaRecursos/tests/test_coordinacion_prestamos.py`
- `SistemaRecursos/tests/test_devolucion_integrada.py`
- `SistemaRecursos/tests/test_estado_bien.py`
- `SistemaRecursos/tests/test_personas_acceso.py`
- `SistemaRecursos/tests/test_proteccion_administrador.py`
- `SistemaRecursos/tests/test_recursos_opcionales.py`
- `SistemaRecursos/tests/test_reportes.py`

## Archivos modificados en la misma ruta

- `SistemaRecursos/README.md`
- `SistemaRecursos/app.py`
- `SistemaRecursos/dominio/gestion_control/politica_prestamo.py`
- `SistemaRecursos/dominio/gestion_control/sancion.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/persona.py`
- `SistemaRecursos/dominio/gestion_personas_usuarios/rol.py`
- `SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/devolucion.py`
- `SistemaRecursos/dominio/gestion_prestamos/prestamo.py`
- `SistemaRecursos/dominio/gestion_prestamos/reserva.py`
- `SistemaRecursos/dominio/gestion_recursos/bien_material.py`
- `SistemaRecursos/dominio/gestion_recursos/recurso.py`
- `SistemaRecursos/presentacion/controladores/controlador_acceso.py`
- `SistemaRecursos/presentacion/controladores/controlador_ampliacion_prestamo.py`
- `SistemaRecursos/presentacion/controladores/controlador_bien_material.py`
- `SistemaRecursos/presentacion/controladores/controlador_persona.py`
- `SistemaRecursos/presentacion/controladores/controlador_politica_prestamo.py`
- `SistemaRecursos/presentacion/controladores/controlador_prestamo.py`
- `SistemaRecursos/presentacion/controladores/controlador_recurso.py`
- `SistemaRecursos/presentacion/controladores/controlador_reporte.py`
- `SistemaRecursos/presentacion/controladores/controlador_reserva.py`
- `SistemaRecursos/presentacion/controladores/controlador_rol.py`
- `SistemaRecursos/presentacion/seguridad.py`
- `SistemaRecursos/presentacion/static/estilos.css`
- `SistemaRecursos/presentacion/vistas/base.html`
- `SistemaRecursos/presentacion/vistas/vista_acceso.html`
- `SistemaRecursos/presentacion/vistas/vista_bien_material.html`
- `SistemaRecursos/presentacion/vistas/vista_persona.html`
- `SistemaRecursos/presentacion/vistas/vista_politica_prestamo.html`
- `SistemaRecursos/presentacion/vistas/vista_prestamo.html`
- `SistemaRecursos/presentacion/vistas/vista_recurso.html`
- `SistemaRecursos/presentacion/vistas/vista_reporte.html`
- `SistemaRecursos/presentacion/vistas/vista_reserva.html`
- `SistemaRecursos/presentacion/vistas/vista_rol.html`
- `SistemaRecursos/repositorio/conexion_mysql.py`
- `SistemaRecursos/repositorio/repositorio_acceso_sql.py`
- `SistemaRecursos/repositorio/repositorio_bien_material_sql.py`
- `SistemaRecursos/repositorio/repositorio_persona_sql.py`
- `SistemaRecursos/repositorio/repositorio_politica_prestamo_sql.py`
- `SistemaRecursos/repositorio/repositorio_prestamo_sql.py`
- `SistemaRecursos/repositorio/repositorio_recurso_sql.py`
- `SistemaRecursos/repositorio/repositorio_reporte_sql.py`
- `SistemaRecursos/repositorio/repositorio_reserva_sql.py`
- `SistemaRecursos/repositorio/repositorio_rol_sql.py`
- `SistemaRecursos/repositorio/repositorio_sancion_sql.py`
- `SistemaRecursos/run.ps1`
- `SistemaRecursos/servicios/procesador_vencimientos.py`
- `SistemaRecursos/servicios/servicio_acceso.py`
- `SistemaRecursos/servicios/servicio_ampliacion_prestamo.py`
- `SistemaRecursos/servicios/servicio_bien_material.py`
- `SistemaRecursos/servicios/servicio_cuenta.py`
- `SistemaRecursos/servicios/servicio_persona.py`
- `SistemaRecursos/servicios/servicio_politica_prestamo.py`
- `SistemaRecursos/servicios/servicio_prestamo.py`
- `SistemaRecursos/servicios/servicio_recurso.py`
- `SistemaRecursos/servicios/servicio_reporte.py`
- `SistemaRecursos/servicios/servicio_reserva.py`
- `SistemaRecursos/servicios/servicio_rol.py`
- `SistemaRecursos/servicios/servicio_sancion.py`
- `SistemaRecursos/tests/soporte_mysql.py`
- `SistemaRecursos/tests/test_estructura_sql.py`
- `SistemaRecursos/verificar.py`

## Definiciones añadidas

### SistemaRecursos/app.py

- `clave_local` (línea 54).
- `create_app.error_base` (línea 159).
- `create_app.fecha` (línea 133).
- `create_app.hora` (línea 141).
- `create_app.mostrar_error` (línea 149).
### SistemaRecursos/dominio/compartido/contratos.py

- `IRepositorioTransaccional.consultar_cuenta_actor` (línea 10).
- `IRepositorioTransaccional.consultar_fecha_actual` (línea 11).
- `IRepositorioTransaccional.consultar_historial_estado` (línea 21).
- `IRepositorioTransaccional.registrar_historial_estado` (línea 12).
- `IRepositorioTransaccional.transaccion` (línea 9).
### SistemaRecursos/dominio/compartido/validacion.py

- `comprobar_version` (línea 84).
- `dni` (línea 45).
- `entero` (línea 31).
- `fecha_local` (línea 59).
- `ids` (línea 69).
- `instante` (línea 51).
- `texto` (línea 19).
- `version` (línea 78).
### SistemaRecursos/dominio/gestion_control/incidencia.py

- `hay_retraso` (línea 10).
### SistemaRecursos/dominio/gestion_control/politica_prestamo.py

- `ConfiguracionReservas.__post_init__` (línea 93).
- `ConfiguracionReservas.vencimiento` (línea 108).
- `HorarioAtencion.__post_init__` (línea 30).
- `HorarioAtencion.cierre` (línea 35).
- `IRepositorioPoliticaPrestamo.consultar_configuracion_general` (línea 119).
- `IRepositorioPoliticaPrestamo.consultar_limites_articulos` (línea 116).
- `IRepositorioPoliticaPrestamo.consultar_politica_prestamo` (línea 115).
- `IRepositorioPoliticaPrestamo.consultar_politicas_prestamo` (línea 114).
- `IRepositorioPoliticaPrestamo.desactivar_politica_prestamo` (línea 117).
- `IRepositorioPoliticaPrestamo.eliminar_politica_prestamo` (línea 118).
- `IRepositorioPoliticaPrestamo.guardar_configuracion_general` (línea 121).
- `IRepositorioPoliticaPrestamo.guardar_limite_articulos` (línea 122).
- `IRepositorioPoliticaPrestamo.guardar_politica_prestamo` (línea 120).
- `PoliticaPrestamo.desde_datos` (línea 71).
- `PoliticaPrestamo.duracion` (línea 78).
- `PoliticaPrestamo.vencimiento` (línea 81).
- `hora` (línea 9).
### SistemaRecursos/dominio/gestion_control/reporte.py

- `FiltroReporte.__post_init__` (línea 21).
- `FiltroReporte._utc` (línea 45).
- `FiltroReporte.fin` (línea 53).
- `FiltroReporte.inicio` (línea 49).
- `IRepositorioReporte.consultar_reportes` (línea 66).
- `celda_csv` (línea 57).
### SistemaRecursos/dominio/gestion_control/sancion.py

- `IRepositorioSancion.consultar_detalle_prestamo` (línea 20).
- `IRepositorioSancion.consultar_detalles_vencidos` (línea 19).
- `IRepositorioSancion.consultar_incidencia_retraso` (línea 15).
- `IRepositorioSancion.consultar_sancion` (línea 13).
- `IRepositorioSancion.consultar_sanciones` (línea 14).
- `IRepositorioSancion.existen_sanciones_activas` (línea 16).
- `IRepositorioSancion.levantar_sancion` (línea 21).
- `IRepositorioSancion.registrar_incidencia` (línea 17).
- `IRepositorioSancion.registrar_sancion` (línea 18).
- `validar_levantamiento` (línea 6).
### SistemaRecursos/dominio/gestion_personas_usuarios/acceso.py

- `CuentaAcceso.nombre_completo` (línea 22).
- `CuentaAcceso.permite` (línea 32).
- `CuentaAcceso.puede_acceder` (línea 29).
- `CuentaAcceso.version_credenciales` (línea 26).
- `IRepositorioAcceso.consultar_cuenta_por_id` (línea 38).
- `IRepositorioAcceso.consultar_cuenta_por_usuario` (línea 37).
- `IRepositorioAcceso.registrar_acceso` (línea 39).
- `exigir_permiso` (línea 42).
### SistemaRecursos/dominio/gestion_personas_usuarios/cuenta.py

- `IRepositorioCuenta.actualizar_cuenta` (línea 42).
- `IRepositorioCuenta.buscar_cuentas` (línea 43).
- `IRepositorioCuenta.consultar_cuenta` (línea 38).
- `IRepositorioCuenta.consultar_cuentas_bloqueadas` (línea 39).
- `IRepositorioCuenta.consultar_estado_persona` (línea 40).
- `IRepositorioCuenta.registrar_cuenta` (línea 41).
- `proteger_administradores` (línea 22).
- `proteger_administradores.activa` (línea 26).
- `validar_clave` (línea 14).
- `validar_credenciales_nuevas` (línea 8).
### SistemaRecursos/dominio/gestion_personas_usuarios/persona.py

- `IRepositorioPersona.buscar_personas` (línea 96).
- `IRepositorioPersona.consultar_cuentas_bloqueadas` (línea 94).
- `IRepositorioPersona.consultar_persona` (línea 91).
- `IRepositorioPersona.consultar_personas` (línea 92).
- `IRepositorioPersona.desactivar_persona` (línea 95).
- `IRepositorioPersona.guardar_persona` (línea 93).
- `Persona.datos` (línea 77).
- `Persona.desde_datos` (línea 66).
- `validar_elegibilidad` (línea 81).
### SistemaRecursos/dominio/gestion_personas_usuarios/rol.py

- `IRepositorioRol.consultar_matriz_permisos` (línea 33).
- `IRepositorioRol.guardar_matriz_permisos` (línea 34).
- `validar_matriz` (línea 23).
### SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py

- `AmpliacionPrestamo.calcular` (línea 22).
- `IRepositorioAmpliacionPrestamo.actualizar_plazo_prestamo` (línea 48).
- `IRepositorioAmpliacionPrestamo.consultar_contexto_ampliacion_prestamo` (línea 47).
### SistemaRecursos/dominio/gestion_prestamos/devolucion.py

- `Devolucion.validar` (línea 21).
### SistemaRecursos/dominio/gestion_prestamos/prestamo.py

- `IRepositorioPrestamo.actualizar_estado_prestamo` (línea 120).
- `IRepositorioPrestamo.consultar_condiciones_prestamo` (línea 112).
- `IRepositorioPrestamo.consultar_contexto_entrega_prestamo` (línea 117).
- `IRepositorioPrestamo.consultar_prestamo` (línea 115).
- `IRepositorioPrestamo.consultar_prestamos` (línea 116).
- `IRepositorioPrestamo.registrar_devolucion` (línea 119).
- `IRepositorioPrestamo.registrar_entrega_prestamo` (línea 118).
- `IRepositorioPrestamo.registrar_perdida_bien_material` (línea 121).
- `IRepositorioPrestamo.sanciones` (línea 114).
- `SolicitudPrestamo.__post_init__` (línea 24).
- `SolicitudPrestamo.observaciones_registro` (línea 48).
- `SolicitudPrestamo.planificar` (línea 56).
- `SolicitudPrestamo.solicitantes` (línea 44).
- `estado_prestamo` (línea 102).
### SistemaRecursos/dominio/gestion_prestamos/reserva.py

- `IRepositorioReserva.actualizar_reserva` (línea 88).
- `IRepositorioReserva.bloquear_recurso` (línea 91).
- `IRepositorioReserva.cambiar_estado_bien_reservado` (línea 94).
- `IRepositorioReserva.consultar_bien_disponible` (línea 93).
- `IRepositorioReserva.consultar_configuracion_general` (línea 90).
- `IRepositorioReserva.consultar_contexto_reserva` (línea 89).
- `IRepositorioReserva.consultar_primera_reserva_en_espera` (línea 92).
- `IRepositorioReserva.consultar_recursos_para_reserva` (línea 80).
- `IRepositorioReserva.consultar_reserva` (línea 83).
- `IRepositorioReserva.consultar_reservas` (línea 84).
- `IRepositorioReserva.consultar_reservas_vencidas` (línea 97).
- `IRepositorioReserva.prestamos` (línea 82).
- `IRepositorioReserva.registrar_reserva` (línea 87).
- `nueva_reserva` (línea 19).
- `validar_accion` (línea 53).
- `validar_solicitud` (línea 39).
### SistemaRecursos/dominio/gestion_recursos/bien_material.py

- `IRepositorioBienMaterial.cambiar_estado_bien_material` (línea 49).
- `IRepositorioBienMaterial.consultar_bien_material` (línea 46).
- `IRepositorioBienMaterial.consultar_bienes_materiales` (línea 47).
- `IRepositorioBienMaterial.consultar_prestamo_pendiente` (línea 52).
- `IRepositorioBienMaterial.eliminar_bien_material` (línea 53).
- `IRepositorioBienMaterial.guardar_bien_material` (línea 48).
- `validar_cambio_estado` (línea 36).
### SistemaRecursos/dominio/gestion_recursos/recurso.py

- `IRepositorioRecurso.consultar_categorias` (línea 30).
- `IRepositorioRecurso.consultar_recurso` (línea 27).
- `IRepositorioRecurso.consultar_recursos` (línea 26).
- `IRepositorioRecurso.eliminar_categoria` (línea 33).
- `IRepositorioRecurso.eliminar_recurso` (línea 29).
- `IRepositorioRecurso.guardar_bien_material` (línea 32).
- `IRepositorioRecurso.guardar_categoria` (línea 31).
- `IRepositorioRecurso.guardar_recurso` (línea 28).
### SistemaRecursos/presentacion/controladores/controlador_acceso.py

- `ControladorAcceso.cerrar_sesion` (línea 30).
- `ControladorAcceso.iniciar_sesion` (línea 16).
### SistemaRecursos/presentacion/controladores/controlador_ampliacion_prestamo.py

- `ControladorAmpliacionPrestamo.ampliar_prestamo` (línea 17).
### SistemaRecursos/presentacion/controladores/controlador_bien_material.py

- `ControladorBienMaterial.consultar_bien_material` (línea 55).
- `ControladorBienMaterial.gestionar_formulario_bien_material` (línea 65).
### SistemaRecursos/presentacion/controladores/controlador_cuenta.py

- `ControladorCuenta.__init__` (línea 6).
- `ControladorCuenta.actualizar_cuenta` (línea 33).
- `ControladorCuenta.registrar_cuenta` (línea 20).
### SistemaRecursos/presentacion/controladores/controlador_persona.py

- `ControladorPersona.buscar_personas` (línea 36).
- `ControladorPersona.gestionar_formulario_persona` (línea 45).
### SistemaRecursos/presentacion/controladores/controlador_politica_prestamo.py

- `ControladorPoliticaPrestamo.consultar_politicas_prestamo` (línea 41).
- `ControladorPoliticaPrestamo.eliminar_politica_prestamo` (línea 88).
- `ControladorPoliticaPrestamo.gestionar_formulario_politica_prestamo` (línea 52).
- `ControladorPoliticaPrestamo.guardar_configuracion_general` (línea 72).
- `ControladorPoliticaPrestamo.guardar_limite_articulos` (línea 78).
### SistemaRecursos/presentacion/controladores/controlador_prestamo.py

- `ControladorPrestamo.consultar_condiciones_prestamo` (línea 48).
- `ControladorPrestamo.registrar_perdida_bien_material` (línea 88).
- `ControladorPrestamo.registrar_vencimientos_prestamos` (línea 96).
### SistemaRecursos/presentacion/controladores/controlador_recurso.py

- `ControladorRecurso.gestionar_categorias` (línea 76).
- `ControladorRecurso.gestionar_formulario_recurso` (línea 54).
### SistemaRecursos/presentacion/controladores/controlador_reporte.py

- `ControladorReporte.consultar_reportes` (línea 15).
- `ControladorReporte.exportar_reportes_csv` (línea 21).
### SistemaRecursos/presentacion/controladores/controlador_reserva.py

- `ControladorReserva._resolver_reserva` (línea 84).
### SistemaRecursos/presentacion/controladores/controlador_rol.py

- `ControladorRol.asignar_rol_cuenta` (línea 40).
- `ControladorRol.guardar_matriz_permisos` (línea 31).
### SistemaRecursos/presentacion/controladores/controlador_sancion.py

- `ControladorSancion.__init__` (línea 6).
- `ControladorSancion.consultar_sanciones` (línea 18).
- `ControladorSancion.levantar_sancion` (línea 22).
### SistemaRecursos/presentacion/seguridad.py

- `configurar_seguridad` (línea 40).
- `configurar_seguridad.recuperar_sesion` (línea 44).
- `csrf_token` (línea 10).
- `iniciar_sesion` (línea 16).
### SistemaRecursos/repositorio/base_sql.py

- `RepositorioSQL.__init__` (línea 10).
- `RepositorioSQL.consultar_cuenta_actor` (línea 52).
- `RepositorioSQL.consultar_fecha_actual` (línea 49).
- `RepositorioSQL.consultar_historial_estado` (línea 85).
- `RepositorioSQL.consultar_sql` (línea 22).
- `RepositorioSQL.consultar_sql.leer` (línea 23).
- `RepositorioSQL.ejecutar` (línea 32).
- `RepositorioSQL.insertar` (línea 38).
- `RepositorioSQL.registrar_historial_estado` (línea 69).
- `RepositorioSQL.transaccion` (línea 15).
### SistemaRecursos/repositorio/repositorio_acceso_sql.py

- `RepositorioAccesoSQL._consultar_cuenta` (línea 6).
- `RepositorioAccesoSQL.consultar_cuenta_por_usuario` (línea 22).
### SistemaRecursos/repositorio/repositorio_ampliacion_prestamo_sql.py

- `RepositorioAmpliacionPrestamoSQL.actualizar_plazo_prestamo` (línea 32).
- `RepositorioAmpliacionPrestamoSQL.consultar_contexto_ampliacion_prestamo` (línea 7).
### SistemaRecursos/repositorio/repositorio_bien_material_sql.py

- `RepositorioBienMaterialSQL.guardar_bien_material` (línea 31).
### SistemaRecursos/repositorio/repositorio_cuenta_sql.py

- `RepositorioCuentaSQL.actualizar_cuenta` (línea 42).
- `RepositorioCuentaSQL.buscar_cuentas` (línea 53).
- `RepositorioCuentaSQL.consultar_cuenta` (línea 13).
- `RepositorioCuentaSQL.consultar_cuentas_bloqueadas` (línea 21).
- `RepositorioCuentaSQL.consultar_estado_persona` (línea 24).
- `RepositorioCuentaSQL.registrar_cuenta` (línea 30).
- `cargar_cuentas_bloqueadas` (línea 6).
### SistemaRecursos/repositorio/repositorio_persona_sql.py

- `RepositorioPersonaSQL.buscar_personas` (línea 73).
- `RepositorioPersonaSQL.consultar_cuentas_bloqueadas` (línea 67).
- `RepositorioPersonaSQL.guardar_persona` (línea 43).
### SistemaRecursos/repositorio/repositorio_politica_prestamo_sql.py

- `RepositorioPoliticaPrestamoSQL.consultar_configuracion_general` (línea 19).
- `RepositorioPoliticaPrestamoSQL.consultar_politica_prestamo` (línea 11).
- `RepositorioPoliticaPrestamoSQL.consultar_politicas_prestamo` (línea 6).
- `RepositorioPoliticaPrestamoSQL.desactivar_politica_prestamo` (línea 34).
- `RepositorioPoliticaPrestamoSQL.eliminar_politica_prestamo` (línea 39).
- `RepositorioPoliticaPrestamoSQL.guardar_configuracion_general` (línea 42).
- `RepositorioPoliticaPrestamoSQL.guardar_limite_articulos` (línea 52).
- `RepositorioPoliticaPrestamoSQL.guardar_politica_prestamo` (línea 29).
### SistemaRecursos/repositorio/repositorio_prestamo_sql.py

- `RepositorioPrestamoSQL.actualizar_estado_prestamo` (línea 258).
- `RepositorioPrestamoSQL.consultar_condiciones_prestamo` (línea 20).
- `RepositorioPrestamoSQL.consultar_contexto_entrega_prestamo` (línea 113).
- `RepositorioPrestamoSQL.registrar_devolucion` (línea 231).
- `RepositorioPrestamoSQL.registrar_entrega_prestamo` (línea 178).
- `RepositorioPrestamoSQL.registrar_perdida_bien_material` (línea 266).
- `RepositorioPrestamoSQL.sanciones` (línea 54).
### SistemaRecursos/repositorio/repositorio_recurso_sql.py

- `RepositorioRecursoSQL.guardar_bien_material` (línea 40).
- `RepositorioRecursoSQL.guardar_categoria` (línea 49).
- `RepositorioRecursoSQL.guardar_recurso` (línea 28).
### SistemaRecursos/repositorio/repositorio_reporte_sql.py

- `RepositorioReporteSQL._consultar_integrantes_prestamos` (línea 72).
- `RepositorioReporteSQL.consultar_reportes` (línea 11).
### SistemaRecursos/repositorio/repositorio_reserva_sql.py

- `RepositorioReservaSQL.actualizar_reserva` (línea 103).
- `RepositorioReservaSQL.bloquear_recurso` (línea 118).
- `RepositorioReservaSQL.cambiar_estado_bien_reservado` (línea 145).
- `RepositorioReservaSQL.consultar_bien_disponible` (línea 135).
- `RepositorioReservaSQL.consultar_configuracion_general` (línea 95).
- `RepositorioReservaSQL.consultar_contexto_reserva` (línea 59).
- `RepositorioReservaSQL.consultar_primera_reserva_en_espera` (línea 125).
- `RepositorioReservaSQL.consultar_recursos_para_reserva` (línea 7).
- `RepositorioReservaSQL.consultar_reservas_vencidas` (línea 158).
- `RepositorioReservaSQL.prestamos` (línea 19).
### SistemaRecursos/repositorio/repositorio_rol_sql.py

- `RepositorioRolSQL.consultar_matriz_permisos` (línea 6).
- `RepositorioRolSQL.guardar_matriz_permisos` (línea 13).
### SistemaRecursos/repositorio/repositorio_sancion_sql.py

- `RepositorioSancionSQL.consultar_detalle_prestamo` (línea 76).
- `RepositorioSancionSQL.consultar_detalles_vencidos` (línea 69).
- `RepositorioSancionSQL.consultar_incidencia_retraso` (línea 36).
- `RepositorioSancionSQL.consultar_sancion` (línea 13).
- `RepositorioSancionSQL.consultar_sanciones` (línea 5).
- `RepositorioSancionSQL.existen_sanciones_activas` (línea 20).
- `RepositorioSancionSQL.levantar_sancion` (línea 84).
- `RepositorioSancionSQL.registrar_incidencia` (línea 45).
- `RepositorioSancionSQL.registrar_sancion` (línea 57).
### SistemaRecursos/servicios/servicio_acceso.py

- `ServicioAplicacionAcceso.autenticar_cuenta` (línea 11).
- `ServicioAplicacionAcceso.consultar_cuenta_activa` (línea 31).
### SistemaRecursos/servicios/servicio_ampliacion_prestamo.py

- `ServicioAplicacionAmpliacionPrestamo.ampliar_prestamo` (línea 14).
### SistemaRecursos/servicios/servicio_bien_material.py

- `ServicioAplicacionBienMaterial.consultar_historial_bien_material` (línea 70).
- `ServicioAplicacionBienMaterial.guardar_bien_material` (línea 34).
### SistemaRecursos/servicios/servicio_cuenta.py

- `ServicioAplicacionCuenta._actualizar_cuenta` (línea 42).
- `ServicioAplicacionCuenta.asignar_rol_cuenta` (línea 39).
- `ServicioAplicacionCuenta.buscar_cuentas` (línea 86).
### SistemaRecursos/servicios/servicio_persona.py

- `ServicioAplicacionPersona.buscar_personas` (línea 62).
- `ServicioAplicacionPersona.guardar_persona` (línea 28).
### SistemaRecursos/servicios/servicio_politica_prestamo.py

- `ServicioAplicacionPoliticaPrestamo.consultar_configuracion_general` (línea 26).
- `ServicioAplicacionPoliticaPrestamo.consultar_politica_prestamo` (línea 17).
- `ServicioAplicacionPoliticaPrestamo.consultar_politicas_prestamo` (línea 23).
- `ServicioAplicacionPoliticaPrestamo.eliminar_politica_prestamo` (línea 79).
- `ServicioAplicacionPoliticaPrestamo.guardar_configuracion_general` (línea 46).
- `ServicioAplicacionPoliticaPrestamo.guardar_limite_articulos` (línea 65).
- `ServicioAplicacionPoliticaPrestamo.guardar_politica_prestamo` (línea 32).
### SistemaRecursos/servicios/servicio_prestamo.py

- `ServicioAplicacionPrestamo.consultar_condiciones_prestamo` (línea 18).
- `ServicioAplicacionPrestamo.registrar_perdida_bien_material` (línea 113).
- `ServicioAplicacionPrestamo.registrar_prestamo_en_operacion` (línea 73).
- `ServicioAplicacionPrestamo.registrar_vencimientos_prestamos` (línea 133).
### SistemaRecursos/servicios/servicio_recurso.py

- `ServicioAplicacionRecurso.guardar_categoria` (línea 75).
- `ServicioAplicacionRecurso.guardar_recurso` (línea 29).
### SistemaRecursos/servicios/servicio_reporte.py

- `ServicioAplicacionReporte.consultar_reportes` (línea 17).
- `ServicioAplicacionReporte.exportar_reportes_csv` (línea 29).
### SistemaRecursos/servicios/servicio_reserva.py

- `ServicioAplicacionReserva._consultar_configuracion_reservas` (línea 68).
- `ServicioAplicacionReserva._liberar_bien_reservado` (línea 180).
- `ServicioAplicacionReserva.consultar_recursos_para_reserva` (línea 20).
- `ServicioAplicacionReserva.expirar_reservas_vencidas` (línea 186).
### SistemaRecursos/servicios/servicio_rol.py

- `ServicioAplicacionRol.consultar_matriz_permisos` (línea 10).
- `ServicioAplicacionRol.guardar_matriz_permisos` (línea 14).
### SistemaRecursos/servicios/servicio_sancion.py

- `ServicioAplicacionSancion.aplicar_sanciones_por_vencimiento` (línea 40).
- `ServicioAplicacionSancion.consultar_sanciones` (línea 51).
- `ServicioAplicacionSancion.levantar_sancion` (línea 54).
- `ServicioAplicacionSancion.registrar_sancion_por_retraso` (línea 13).

## Definiciones retiradas

### SistemaRecursos/app.py

- `create_app.cabeceras` (línea 134).
- `create_app.contexto` (línea 127).
- `create_app.descripcion_permiso` (línea 96).
- `create_app.fecha_local` (línea 103).
- `create_app.mostrar_conflicto` (línea 171).
- `create_app.mostrar_error_base_datos` (línea 180).
- `create_app.mostrar_error_formulario` (línea 187).
- `create_app.mostrar_error_permiso` (línea 192).
- `create_app.mostrar_error_validacion` (línea 176).
- `create_app.preparar_peticion` (línea 115).
### SistemaRecursos/dominio/gestion_control/fabrica_politica_prestamo.py

- `FabricaPoliticaPrestamo._entero` (línea 6).
- `FabricaPoliticaPrestamo.construir` (línea 13).
### SistemaRecursos/dominio/gestion_control/horario_atencion.py

- `HorarioAtencion.__post_init__` (línea 29).
- `HorarioAtencion.apertura_texto` (línea 36).
- `HorarioAtencion.cierre_para_entrega` (línea 43).
- `HorarioAtencion.cierre_texto` (línea 40).
- `HorarioAtencion.limitar_prestamo_por_horas` (línea 51).
- `hora_valida` (línea 8).
### SistemaRecursos/dominio/gestion_control/i_repositorio_politica_prestamo.py

- `IRepositorioPoliticaPrestamo.actualizar_horario_atencion` (línea 46).
- `IRepositorioPoliticaPrestamo.actualizar_limites_articulos` (línea 64).
- `IRepositorioPoliticaPrestamo.actualizar_politica` (línea 21).
- `IRepositorioPoliticaPrestamo.actualizar_politica_vencimiento_reserva` (línea 55).
- `IRepositorioPoliticaPrestamo.consultar_horario_atencion` (línea 41).
- `IRepositorioPoliticaPrestamo.consultar_limites_articulos` (línea 59).
- `IRepositorioPoliticaPrestamo.consultar_politica` (línea 16).
- `IRepositorioPoliticaPrestamo.consultar_politica_aplicable` (línea 36).
- `IRepositorioPoliticaPrestamo.consultar_politica_vencimiento_reserva` (línea 51).
- `IRepositorioPoliticaPrestamo.consultar_politicas` (línea 31).
- `IRepositorioPoliticaPrestamo.eliminar_politica` (línea 26).
- `IRepositorioPoliticaPrestamo.registrar_politica` (línea 11).
### SistemaRecursos/dominio/gestion_control/i_repositorio_reporte.py

- `IRepositorioReporte.consultar_prestamos` (línea 7).
### SistemaRecursos/dominio/gestion_control/i_repositorio_sancion.py

- `IRepositorioSancion.aplicar_sanciones_vencidas` (línea 6).
- `IRepositorioSancion.levantar_sancion_vencimiento` (línea 11).
### SistemaRecursos/dominio/gestion_control/politica_prestamo.py

- `LimiteArticulosPrestamo.__post_init__` (línea 62).
- `LimiteArticulosPrestamo.validar_entrega` (línea 69).
- `PoliticaPrestamo.aplica_a` (línea 35).
- `PoliticaPrestamo.fecha_limite` (línea 46).
- `PoliticaPrestamo.plazo_texto` (línea 39).
### SistemaRecursos/dominio/gestion_control/politica_vencimiento_reserva.py

- `PoliticaVencimientoReserva.__post_init__` (línea 12).
- `PoliticaVencimientoReserva._sumar` (línea 32).
- `PoliticaVencimientoReserva._validar_plazo` (línea 17).
- `PoliticaVencimientoReserva.vencimiento_espera` (línea 37).
- `PoliticaVencimientoReserva.vencimiento_retiro` (línea 40).
### SistemaRecursos/dominio/gestion_control/sancion.py

- `Sancion.__post_init__` (línea 24).
- `Sancion.levantar` (línea 27).
### SistemaRecursos/dominio/gestion_personas_usuarios/estudiante.py

- `Estudiante.matricula_vigente` (línea 19).
- `tiene_matricula_vigente` (línea 8).
### SistemaRecursos/dominio/gestion_personas_usuarios/fabrica_persona.py

- `FabricaPersona.construir` (línea 9).
### SistemaRecursos/dominio/gestion_personas_usuarios/i_repositorio_persona.py

- `IRepositorioPersona.actualizar_persona` (línea 30).
- `IRepositorioPersona.consultar_persona` (línea 15).
- `IRepositorioPersona.consultar_personas` (línea 20).
- `IRepositorioPersona.consultar_solicitantes` (línea 25).
- `IRepositorioPersona.desactivar_persona` (línea 35).
- `IRepositorioPersona.registrar_persona` (línea 10).
### SistemaRecursos/dominio/gestion_personas_usuarios/i_repositorio_rol.py

- `IRepositorioRol.actualizar_matriz_permisos` (línea 24).
- `IRepositorioRol.consultar_permisos` (línea 19).
- `IRepositorioRol.consultar_rol` (línea 9).
- `IRepositorioRol.consultar_roles` (línea 14).
### SistemaRecursos/dominio/gestion_personas_usuarios/permiso.py

- `consultar_catalogo_permisos` (línea 25).
### SistemaRecursos/dominio/gestion_personas_usuarios/persona.py

- `Persona.documento_identidad` (línea 29).
- `Persona.esta_activa` (línea 36).
### SistemaRecursos/dominio/gestion_personas_usuarios/rol.py

- `Rol.__post_init__` (línea 14).
- `Rol.tiene_permiso` (línea 17).
- `validar_permisos_administrador` (línea 21).
### SistemaRecursos/dominio/gestion_personas_usuarios/usuario_sistema.py

- `IRepositorioAcceso.consultar_cuenta_por_id` (línea 75).
- `IRepositorioAcceso.consultar_por_nombre_usuario` (línea 71).
- `IRepositorioAcceso.registrar_acceso` (línea 79).
- `IRepositorioCuenta.actualizar_cuenta` (línea 99).
- `IRepositorioCuenta.actualizar_rol_cuenta` (línea 108).
- `IRepositorioCuenta.consultar_cuenta_persona` (línea 87).
- `IRepositorioCuenta.consultar_cuentas_para_roles` (línea 104).
- `IRepositorioCuenta.consultar_resumen_cuentas` (línea 91).
- `IRepositorioCuenta.registrar_cuenta` (línea 95).
- `IdentidadAcceso.esta_activa` (línea 40).
- `IdentidadAcceso.nombre_completo` (línea 37).
- `UsuarioSistema.__post_init__` (línea 53).
- `UsuarioSistema.activo` (línea 57).
- `UsuarioSistema.puede_acceder` (línea 60).
- `es_administrador_activo` (línea 112).
- `validar_baja_persona` (línea 118).
- `validar_conservacion_administrador` (línea 142).
### SistemaRecursos/dominio/gestion_personas_usuarios/validacion_persona.py

- `ValidacionPersonaError.__init__` (línea 20).
- `_validar_texto` (línea 25).
- `validar_datos_persona` (línea 33).
- `validar_dni` (línea 77).
### SistemaRecursos/dominio/gestion_personas_usuarios/version_edicion.py

- `exigir_version` (línea 27).
- `huella` (línea 10).
- `version_matriz` (línea 19).
- `version_persona` (línea 15).
### SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py

- `AmpliacionPrestamo.calcular_fecha` (línea 29).
### SistemaRecursos/dominio/gestion_prestamos/contexto_entrega.py

- `ContextoEntrega.construir_prestamo` (línea 22).
### SistemaRecursos/dominio/gestion_prestamos/detalle_prestamo.py

- `DetallePrestamo.__post_init__` (línea 21).
- `DetallePrestamo.pendiente` (línea 37).
### SistemaRecursos/dominio/gestion_prestamos/fabrica_prestamo.py

- `FabricaPrestamo.construir` (línea 8).
### SistemaRecursos/dominio/gestion_prestamos/i_operacion_prestamo.py

- `IOperacionPrestamo.ahora` (línea 40).
- `IOperacionPrestamo.cargar_cuenta_ampliacion` (línea 44).
- `IOperacionPrestamo.cargar_entrega` (línea 8).
- `IOperacionPrestamo.cargar_politica_ampliacion` (línea 48).
- `IOperacionPrestamo.cargar_recepcion` (línea 16).
- `IOperacionPrestamo.cargar_vencidos` (línea 32).
- `IOperacionPrestamo.guardar_devoluciones` (línea 20).
- `IOperacionPrestamo.guardar_entrega` (línea 12).
- `IOperacionPrestamo.guardar_estado` (línea 36).
- `IOperacionPrestamo.guardar_fecha_limite` (línea 52).
- `IOperacionPrestamo.guardar_perdida` (línea 28).
- `IOperacionPrestamo.registrar_sancion_vencimiento` (línea 24).
### SistemaRecursos/dominio/gestion_prestamos/i_operacion_reserva.py

- `IOperacionEntregaReserva.ahora` (línea 20).
- `IOperacionEntregaReserva.cargar_reserva` (línea 12).
- `IOperacionEntregaReserva.guardar_entrega` (línea 16).
- `IOperacionEntregaReserva.prestamos` (línea 8).
### SistemaRecursos/dominio/gestion_prestamos/i_repositorio_prestamo.py

- `IRepositorioPrestamo.consultar_prestamo` (línea 15).
- `IRepositorioPrestamo.consultar_prestamos` (línea 25).
- `IRepositorioPrestamo.consultar_resumen_prestamos` (línea 20).
- `IRepositorioPrestamo.transaccion` (línea 10).
### SistemaRecursos/dominio/gestion_prestamos/i_repositorio_reserva.py

- `IRepositorioReserva.cancelar_reserva` (línea 38).
- `IRepositorioReserva.consultar_reserva` (línea 17).
- `IRepositorioReserva.consultar_reservas` (línea 22).
- `IRepositorioReserva.expirar_reserva` (línea 50).
- `IRepositorioReserva.expirar_solicitudes_vencidas` (línea 57).
- `IRepositorioReserva.preparar_reserva` (línea 27).
- `IRepositorioReserva.rechazar_reserva` (línea 44).
- `IRepositorioReserva.registrar_reserva` (línea 12).
- `IRepositorioReserva.transaccion_entrega` (línea 33).
### SistemaRecursos/dominio/gestion_prestamos/incidencia.py

- `Incidencia.__init__` (línea 21).
### SistemaRecursos/dominio/gestion_prestamos/participante_prestamo.py

- `ParticipantePrestamo.__post_init__` (línea 13).
### SistemaRecursos/dominio/gestion_prestamos/prestamo.py

- `Prestamo.__post_init__` (línea 32).
- `Prestamo.agregar_detalle` (línea 42).
- `Prestamo.estado_actual` (línea 77).
- `Prestamo.marcar_vencido` (línea 92).
- `Prestamo.registrar_devolucion` (línea 96).
- `Prestamo.validar` (línea 48).
- `Prestamo.validar_perdida` (línea 118).
- `Prestamo.validar_recepcion` (línea 107).
### SistemaRecursos/dominio/gestion_prestamos/reserva.py

- `AccionReserva.desde_valor` (línea 33).
- `AccionReserva.estado_destino` (línea 44).
- `AccionReserva.observacion` (línea 48).
- `AccionReserva.requiere_motivo` (línea 40).
- `AccionReserva.validar_permiso` (línea 51).
- `Reserva.__post_init__` (línea 103).
- `Reserva.cambiar_estado` (línea 118).
- `Reserva.preparar_solicitud_prestamo` (línea 161).
- `Reserva.resolver_reserva` (línea 125).
- `Reserva.validar_fecha_retiro` (línea 151).
- `Reserva.validar_politica` (línea 145).
- `Reserva.validar_solicitante` (línea 136).
- `Reserva.validar_turno` (línea 155).
- `autorizar_resolucion` (línea 84).
### SistemaRecursos/dominio/gestion_prestamos/solicitud_prestamo.py

- `SolicitudPrestamo.__post_init__` (línea 21).
- `SolicitudPrestamo.construir_prestamo` (línea 32).
### SistemaRecursos/dominio/gestion_prestamos/validacion_prestamo.py

- `lista_dnis` (línea 32).
- `lista_ids` (línea 23).
- `validar_persona` (línea 10).
### SistemaRecursos/dominio/gestion_recursos/bien_material.py

- `BienMaterial.cambiar_estado` (línea 99).
- `BienMaterial.esta_disponible` (línea 92).
- `BienMaterial.validar_disponible` (línea 95).
### SistemaRecursos/dominio/gestion_recursos/categoria_recurso.py

- `CategoriaRecurso.__post_init__` (línea 11).
### SistemaRecursos/dominio/gestion_recursos/fabrica_bien_material.py

- `FabricaBienMaterial.construir` (línea 6).
### SistemaRecursos/dominio/gestion_recursos/fabrica_recurso.py

- `FabricaRecurso.construir` (línea 6).
### SistemaRecursos/dominio/gestion_recursos/i_repositorio_bien_material.py

- `IRepositorioBienMaterial.actualizar_bien_material` (línea 25).
- `IRepositorioBienMaterial.cambiar_estado_bien_material` (línea 55).
- `IRepositorioBienMaterial.consultar_bien_material` (línea 20).
- `IRepositorioBienMaterial.consultar_bienes_disponibles` (línea 50).
- `IRepositorioBienMaterial.consultar_bienes_materiales` (línea 45).
- `IRepositorioBienMaterial.consultar_bienes_por_recurso` (línea 40).
- `IRepositorioBienMaterial.consultar_historial_bien_material` (línea 72).
- `IRepositorioBienMaterial.consultar_prestamo_pendiente` (línea 67).
- `IRepositorioBienMaterial.contar_disponibles` (línea 35).
- `IRepositorioBienMaterial.eliminar_bien_material` (línea 30).
- `IRepositorioBienMaterial.existen_por_recurso` (línea 15).
- `IRepositorioBienMaterial.registrar_bien_material` (línea 10).
### SistemaRecursos/dominio/gestion_recursos/i_repositorio_recurso.py

- `IRepositorioRecurso.actualizar_categoria` (línea 55).
- `IRepositorioRecurso.actualizar_recurso` (línea 25).
- `IRepositorioRecurso.consultar_categoria` (línea 45).
- `IRepositorioRecurso.consultar_categorias` (línea 40).
- `IRepositorioRecurso.consultar_recurso` (línea 20).
- `IRepositorioRecurso.consultar_recursos` (línea 35).
- `IRepositorioRecurso.eliminar_categoria` (línea 60).
- `IRepositorioRecurso.eliminar_recurso` (línea 30).
- `IRepositorioRecurso.registrar_categoria` (línea 50).
- `IRepositorioRecurso.registrar_recurso` (línea 10).
- `IRepositorioRecurso.registrar_recurso_con_bien` (línea 15).
### SistemaRecursos/dominio/gestion_recursos/recurso.py

- `Recurso.clasificar` (línea 21).
### SistemaRecursos/dominio/gestion_recursos/validacion_recurso.py

- `entero` (línea 21).
- `fecha` (línea 33).
- `instante_utc` (línea 42).
- `texto` (línea 8).
### SistemaRecursos/presentacion/controladores/controlador_acceso.py

- `ControladorAcceso.login` (línea 13).
- `ControladorAcceso.logout` (línea 30).
### SistemaRecursos/presentacion/controladores/controlador_ampliacion_prestamo.py

- `ControladorAmpliacionPrestamo.ampliar_plazo` (línea 16).
### SistemaRecursos/presentacion/controladores/controlador_bien_material.py

- `ControladorBienMaterial._registrar_rutas` (línea 29).
- `ControladorBienMaterial.actualizar_bien_material` (línea 109).
- `ControladorBienMaterial.consultar_detalle_bien_material` (línea 63).
- `ControladorBienMaterial.mostrar_edicion_bien_material` (línea 103).
- `ControladorBienMaterial.mostrar_formulario_bien_material` (línea 77).
- `ControladorBienMaterial.registrar_bien_material` (línea 83).
### SistemaRecursos/presentacion/controladores/controlador_persona.py

- `ControladorPersona._errores_persona` (línea 42).
- `ControladorPersona._ir_al_detalle` (línea 36).
- `ControladorPersona._mostrar_detalle` (línea 102).
- `ControladorPersona.activar_cuenta` (línea 190).
- `ControladorPersona.actualizar_cuenta` (línea 167).
- `ControladorPersona.actualizar_persona` (línea 116).
- `ControladorPersona.desactivar_cuenta` (línea 198).
- `ControladorPersona.mostrar_confirmacion_desactivacion_persona` (línea 131).
- `ControladorPersona.mostrar_edicion_cuenta` (línea 160).
- `ControladorPersona.mostrar_edicion_persona` (línea 111).
- `ControladorPersona.mostrar_formulario_persona` (línea 82).
- `ControladorPersona.registrar_cuenta` (línea 142).
- `ControladorPersona.registrar_persona` (línea 86).
### SistemaRecursos/presentacion/controladores/controlador_politica_prestamo.py

- `ControladorPoliticaPrestamo._mostrar_consulta` (línea 78).
- `ControladorPoliticaPrestamo._mostrar_error_politica` (línea 65).
- `ControladorPoliticaPrestamo.actualizar_horario_atencion` (línea 86).
- `ControladorPoliticaPrestamo.actualizar_limites_articulos` (línea 95).
- `ControladorPoliticaPrestamo.actualizar_politica` (línea 48).
- `ControladorPoliticaPrestamo.actualizar_vencimientos` (línea 70).
- `ControladorPoliticaPrestamo.consultar_politicas` (línea 39).
- `ControladorPoliticaPrestamo.eliminar_politica` (línea 60).
- `ControladorPoliticaPrestamo.mostrar_edicion_politica` (línea 43).
- `ControladorPoliticaPrestamo.registrar_politica` (línea 30).
### SistemaRecursos/presentacion/controladores/controlador_prestamo.py

- `ControladorPrestamo._puede_consultar` (línea 32).
- `ControladorPrestamo.actualizar_prestamos_vencidos` (línea 112).
- `ControladorPrestamo.consultar_bienes_disponibles` (línea 78).
- `ControladorPrestamo.consultar_solicitantes` (línea 73).
- `ControladorPrestamo.levantar_sancion_vencimiento` (línea 118).
- `ControladorPrestamo.mostrar_formulario_prestamo` (línea 51).
- `ControladorPrestamo.reportar_perdida` (línea 101).
### SistemaRecursos/presentacion/controladores/controlador_recurso.py

- `ControladorRecurso._consultar_politicas_por_categoria` (línea 219).
- `ControladorRecurso._mostrar_administracion` (línea 188).
- `ControladorRecurso._mostrar_error_administracion` (línea 169).
- `ControladorRecurso._registrar_rutas` (línea 33).
- `ControladorRecurso.actualizar_categoria` (línea 148).
- `ControladorRecurso.actualizar_recurso` (línea 112).
- `ControladorRecurso.consultar_administracion_recursos` (línea 84).
- `ControladorRecurso.mostrar_edicion_recurso` (línea 105).
- `ControladorRecurso.registrar_categoria` (línea 138).
- `ControladorRecurso.registrar_recurso` (línea 89).
### SistemaRecursos/presentacion/controladores/controlador_reporte.py

- `ControladorReporte._mostrar` (línea 16).
- `ControladorReporte.consultar_prestamos` (línea 25).
- `ControladorReporte.exportar_prestamos` (línea 33).
### SistemaRecursos/presentacion/controladores/controlador_reserva.py

- `ControladorReserva._alcance` (línea 33).
- `ControladorReserva._respuesta_accion_reserva` (línea 107).
- `ControladorReserva.mostrar_formulario_reserva` (línea 47).
### SistemaRecursos/presentacion/controladores/controlador_rol.py

- `ControladorRol._mostrar_consulta` (línea 25).
- `ControladorRol.actualizar_matriz_permisos` (línea 34).
- `ControladorRol.actualizar_rol_cuenta` (línea 41).
### SistemaRecursos/presentacion/formularios.py

- `error_formulario` (línea 4).
### SistemaRecursos/presentacion/seguridad.py

- `redirigir_segun_permiso` (línea 39).
- `token_csrf` (línea 7).
- `validar_csrf` (línea 13).
### SistemaRecursos/presentacion/vistas/vista_bien_material.py

- `VistaBienMaterial.mostrar_consulta` (línea 14).
- `VistaBienMaterial.mostrar_detalle` (línea 33).
- `VistaBienMaterial.mostrar_formulario` (línea 23).
- `VistaBienMaterial.mostrar_mensaje` (línea 50).
- `opciones_estado` (línea 8).
### SistemaRecursos/presentacion/vistas/vista_persona.py

- `VistaPersona.mostrar_alta_cuenta` (línea 29).
- `VistaPersona.mostrar_confirmacion_desactivacion` (línea 40).
- `VistaPersona.mostrar_consulta` (línea 12).
- `VistaPersona.mostrar_detalle` (línea 24).
- `VistaPersona.mostrar_formulario` (línea 6).
- `VistaPersona.mostrar_formulario_cuenta` (línea 32).
- `VistaPersona.mostrar_mensaje` (línea 37).
### SistemaRecursos/presentacion/vistas/vista_politica_prestamo.py

- `VistaPoliticaPrestamo.mostrar_consulta` (línea 6).
- `VistaPoliticaPrestamo.mostrar_mensaje` (línea 25).
### SistemaRecursos/presentacion/vistas/vista_prestamo.py

- `VistaPrestamo.mostrar_consulta` (línea 16).
- `VistaPrestamo.mostrar_detalle` (línea 24).
- `VistaPrestamo.mostrar_formulario` (línea 6).
- `VistaPrestamo.mostrar_mensaje` (línea 30).
### SistemaRecursos/presentacion/vistas/vista_recurso.py

- `VistaRecurso._mostrar` (línea 6).
- `VistaRecurso.mostrar_administracion` (línea 10).
- `VistaRecurso.mostrar_consulta` (línea 39).
- `VistaRecurso.mostrar_detalle` (línea 46).
- `VistaRecurso.mostrar_edicion_recurso` (línea 30).
- `VistaRecurso.mostrar_mensaje` (línea 49).
### SistemaRecursos/presentacion/vistas/vista_rol.py

- `VistaRol.mostrar_consulta` (línea 6).
- `VistaRol.mostrar_mensaje` (línea 12).
### SistemaRecursos/repositorio/conexion_mysql.py

- `MySQLConnection.abrir_conexion` (línea 21).
- `MySQLConnection.cerrar_conexion` (línea 24).
### SistemaRecursos/repositorio/politica_vencimiento_reserva_sql.py

- `consultar_politica_vencimiento_reserva` (línea 4).
### SistemaRecursos/repositorio/repositorio_acceso_sql.py

- `RepositorioAccesoSQL.__init__` (línea 37).
- `RepositorioAccesoSQL._bloquear_cuentas` (línea 41).
- `RepositorioAccesoSQL._construir_cuenta` (línea 50).
- `RepositorioAccesoSQL._consultar` (línea 61).
- `RepositorioAccesoSQL._persistir_cambio_acceso` (línea 129).
- `RepositorioAccesoSQL._validar_cambio_acceso` (línea 116).
- `RepositorioAccesoSQL.actualizar_cuenta` (línea 149).
- `RepositorioAccesoSQL.actualizar_rol_cuenta` (línea 206).
- `RepositorioAccesoSQL.consultar_cuenta_persona` (línea 73).
- `RepositorioAccesoSQL.consultar_cuentas_para_roles` (línea 185).
- `RepositorioAccesoSQL.consultar_por_nombre_usuario` (línea 70).
- `RepositorioAccesoSQL.consultar_resumen_cuentas` (línea 79).
- `RepositorioAccesoSQL.registrar_cuenta` (línea 97).
### SistemaRecursos/repositorio/repositorio_bien_material_sql.py

- `RepositorioBienMaterialSQL.__init__` (línea 27).
- `RepositorioBienMaterialSQL._consultar_registros` (línea 234).
- `RepositorioBienMaterialSQL._filtros_sql` (línea 69).
- `RepositorioBienMaterialSQL.actualizar_bien_material` (línea 143).
- `RepositorioBienMaterialSQL.consultar_bienes_disponibles` (línea 115).
- `RepositorioBienMaterialSQL.consultar_bienes_por_recurso` (línea 56).
- `RepositorioBienMaterialSQL.consultar_historial_bien_material` (línea 239).
- `RepositorioBienMaterialSQL.contar_disponibles` (línea 50).
- `RepositorioBienMaterialSQL.existen_por_recurso` (línea 36).
- `RepositorioBienMaterialSQL.registrar_bien_material` (línea 30).
- `insertar_bien_material` (línea 254).
- `registrar_historial_bien` (línea 272).
### SistemaRecursos/repositorio/repositorio_persona_sql.py

- `RepositorioPersonaSQL.__init__` (línea 67).
- `RepositorioPersonaSQL._bloquear_cuentas` (línea 71).
- `RepositorioPersonaSQL._bloquear_persona_para_cambio` (línea 221).
- `RepositorioPersonaSQL._filtros_sql` (línea 116).
- `RepositorioPersonaSQL._validar_identificadores` (línea 80).
- `RepositorioPersonaSQL.actualizar_persona` (línea 234).
- `RepositorioPersonaSQL.consultar_solicitantes` (línea 175).
- `RepositorioPersonaSQL.registrar_persona` (línea 95).
### SistemaRecursos/repositorio/repositorio_politica_prestamo_sql.py

- `RepositorioPoliticaPrestamoSQL.__init__` (línea 14).
- `RepositorioPoliticaPrestamoSQL._consultar_horario_atencion` (línea 18).
- `RepositorioPoliticaPrestamoSQL.actualizar_horario_atencion` (línea 104).
- `RepositorioPoliticaPrestamoSQL.actualizar_limites_articulos` (línea 130).
- `RepositorioPoliticaPrestamoSQL.actualizar_politica` (línea 62).
- `RepositorioPoliticaPrestamoSQL.actualizar_politica_vencimiento_reserva` (línea 115).
- `RepositorioPoliticaPrestamoSQL.consultar_horario_atencion` (línea 100).
- `RepositorioPoliticaPrestamoSQL.consultar_politica` (línea 42).
- `RepositorioPoliticaPrestamoSQL.consultar_politica_aplicable` (línea 48).
- `RepositorioPoliticaPrestamoSQL.consultar_politica_vencimiento_reserva` (línea 111).
- `RepositorioPoliticaPrestamoSQL.consultar_politicas` (línea 57).
- `RepositorioPoliticaPrestamoSQL.eliminar_politica` (línea 96).
- `RepositorioPoliticaPrestamoSQL.registrar_politica` (línea 26).
### SistemaRecursos/repositorio/repositorio_prestamo_sql.py

- `OperacionPrestamoSQL.__init__` (línea 262).
- `OperacionPrestamoSQL._construir_prestamo` (línea 420).
- `OperacionPrestamoSQL._guardar_detalles` (línea 448).
- `OperacionPrestamoSQL._guardar_historial` (línea 407).
- `OperacionPrestamoSQL._registrar_devolucion_detalle` (línea 476).
- `OperacionPrestamoSQL.ahora` (línea 265).
- `OperacionPrestamoSQL.cargar_cuenta_ampliacion` (línea 269).
- `OperacionPrestamoSQL.cargar_entrega` (línea 297).
- `OperacionPrestamoSQL.cargar_politica_ampliacion` (línea 279).
- `OperacionPrestamoSQL.cargar_recepcion` (línea 356).
- `OperacionPrestamoSQL.cargar_vencidos` (línea 385).
- `OperacionPrestamoSQL.guardar_devoluciones` (línea 372).
- `OperacionPrestamoSQL.guardar_entrega` (línea 341).
- `OperacionPrestamoSQL.guardar_estado` (línea 402).
- `OperacionPrestamoSQL.guardar_fecha_limite` (línea 290).
- `OperacionPrestamoSQL.guardar_perdida` (línea 379).
- `OperacionPrestamoSQL.registrar_sancion_vencimiento` (línea 369).
- `RepositorioPrestamoSQL.__init__` (línea 43).
- `RepositorioPrestamoSQL._consulta_todos` (línea 169).
- `RepositorioPrestamoSQL.consultar_resumen_prestamos` (línea 118).
- `RepositorioPrestamoSQL.transaccion` (línea 47).
- `hay_prestamos_vencidos` (línea 248).
### SistemaRecursos/repositorio/repositorio_recurso_sql.py

- `RepositorioRecursoSQL.__init__` (línea 26).
- `RepositorioRecursoSQL._consulta_todos` (línea 143).
- `RepositorioRecursoSQL._insertar_recurso` (línea 187).
- `RepositorioRecursoSQL.actualizar_categoria` (línea 119).
- `RepositorioRecursoSQL.actualizar_recurso` (línea 63).
- `RepositorioRecursoSQL.consultar_categoria` (línea 100).
- `RepositorioRecursoSQL.registrar_categoria` (línea 109).
- `RepositorioRecursoSQL.registrar_recurso` (línea 46).
- `RepositorioRecursoSQL.registrar_recurso_con_bien` (línea 53).
### SistemaRecursos/repositorio/repositorio_reporte_sql.py

- `RepositorioReporteSQL.__init__` (línea 24).
- `RepositorioReporteSQL._cargar_integrantes` (línea 80).
- `RepositorioReporteSQL._condiciones` (línea 28).
- `RepositorioReporteSQL.consultar_prestamos` (línea 51).
### SistemaRecursos/repositorio/repositorio_reserva_sql.py

- `OperacionEntregaReservaSQL.__init__` (línea 373).
- `OperacionEntregaReservaSQL.ahora` (línea 382).
- `OperacionEntregaReservaSQL.cargar_reserva` (línea 385).
- `OperacionEntregaReservaSQL.guardar_entrega` (línea 388).
- `OperacionEntregaReservaSQL.prestamos` (línea 379).
- `RepositorioReservaSQL.__init__` (línea 38).
- `RepositorioReservaSQL._bloquear_personas` (línea 126).
- `RepositorioReservaSQL._bloquear_reserva` (línea 108).
- `RepositorioReservaSQL._condiciones_de_retiro` (línea 178).
- `RepositorioReservaSQL._consultar_bien_disponible` (línea 225).
- `RepositorioReservaSQL._consultar_politica` (línea 161).
- `RepositorioReservaSQL._consultar_recurso_bloqueado` (línea 136).
- `RepositorioReservaSQL._consultar_solicitante` (línea 144).
- `RepositorioReservaSQL._desde_fila` (línea 94).
- `RepositorioReservaSQL._expirar_vencida` (línea 347).
- `RepositorioReservaSQL._guardar_historial` (línea 283).
- `RepositorioReservaSQL._guardar_resolucion` (línea 274).
- `RepositorioReservaSQL._insertar_reserva` (línea 198).
- `RepositorioReservaSQL._liberar_bien` (línea 256).
- `RepositorioReservaSQL._preparar_bien` (línea 239).
- `RepositorioReservaSQL._primera_solicitud_disponible` (línea 212).
- `RepositorioReservaSQL._resolver_reserva` (línea 70).
- `RepositorioReservaSQL._validar_elegibilidad` (línea 169).
- `RepositorioReservaSQL._verificar_solicitud_duplicada` (línea 186).
- `RepositorioReservaSQL.cancelar_reserva` (línea 61).
- `RepositorioReservaSQL.expirar_reserva` (línea 67).
- `RepositorioReservaSQL.expirar_solicitudes_vencidas` (línea 331).
- `RepositorioReservaSQL.preparar_reserva` (línea 53).
- `RepositorioReservaSQL.rechazar_reserva` (línea 64).
- `RepositorioReservaSQL.transaccion_entrega` (línea 57).
### SistemaRecursos/repositorio/repositorio_rol_sql.py

- `RepositorioRolSQL.__init__` (línea 10).
- `RepositorioRolSQL.actualizar_matriz_permisos` (línea 31).
- `RepositorioRolSQL.consultar_permisos` (línea 28).
- `RepositorioRolSQL.consultar_rol` (línea 13).
- `RepositorioRolSQL.consultar_roles` (línea 22).
- `cargar_permisos_roles` (línea 52).
### SistemaRecursos/repositorio/repositorio_sancion_sql.py

- `RepositorioSancionSQL.__init__` (línea 8).
- `RepositorioSancionSQL.aplicar_sanciones_vencidas` (línea 11).
- `RepositorioSancionSQL.levantar_sancion_vencimiento` (línea 38).
### SistemaRecursos/repositorio/sanciones_vencimiento_sql.py

- `aplicar_sancion_vencimiento` (línea 4).
### SistemaRecursos/servicios/servicio_acceso.py

- `ServicioAplicacionAcceso.autenticar` (línea 22).
- `ServicioAplicacionAcceso.consultar_usuario_activo` (línea 37).
- `ServicioAplicacionAcceso.version_credenciales` (línea 18).
### SistemaRecursos/servicios/servicio_ampliacion_prestamo.py

- `ServicioAplicacionAmpliacionPrestamo.ampliar_plazo` (línea 12).
### SistemaRecursos/servicios/servicio_bien_material.py

- `ServicioAplicacionBienMaterial.actualizar_bien_material` (línea 49).
- `ServicioAplicacionBienMaterial.consultar_detalle_bien_material` (línea 87).
- `ServicioAplicacionBienMaterial.contar_disponibles` (línea 46).
- `ServicioAplicacionBienMaterial.registrar_bien_material` (línea 20).
### SistemaRecursos/servicios/servicio_cuenta.py

- `ServicioAplicacionCuenta._hash_clave` (línea 28).
- `ServicioAplicacionCuenta._nombre_usuario` (línea 22).
- `ServicioAplicacionCuenta.cambiar_estado_cuenta` (línea 71).
- `ServicioAplicacionCuenta.consultar_cuenta_persona` (línea 33).
- `ServicioAplicacionCuenta.consultar_resumen_cuentas` (línea 36).
### SistemaRecursos/servicios/servicio_persona.py

- `ServicioAplicacionPersona.actualizar_persona` (línea 46).
- `ServicioAplicacionPersona.registrar_persona` (línea 14).
### SistemaRecursos/servicios/servicio_politica_prestamo.py

- `ServicioAplicacionPoliticaPrestamo._validar_categoria` (línea 26).
- `ServicioAplicacionPoliticaPrestamo.actualizar_horario_atencion` (línea 36).
- `ServicioAplicacionPoliticaPrestamo.actualizar_limites_articulos` (línea 87).
- `ServicioAplicacionPoliticaPrestamo.actualizar_politica` (línea 59).
- `ServicioAplicacionPoliticaPrestamo.actualizar_politica_vencimiento_reserva` (línea 43).
- `ServicioAplicacionPoliticaPrestamo.consultar_categorias` (línea 30).
- `ServicioAplicacionPoliticaPrestamo.consultar_horario_atencion` (línea 33).
- `ServicioAplicacionPoliticaPrestamo.consultar_politica` (línea 50).
- `ServicioAplicacionPoliticaPrestamo.consultar_politica_vencimiento_reserva` (línea 40).
- `ServicioAplicacionPoliticaPrestamo.consultar_politicas` (línea 56).
- `ServicioAplicacionPoliticaPrestamo.eliminar_politica` (línea 69).
- `ServicioAplicacionPoliticaPrestamo.registrar_politica` (línea 19).
- `ServicioAplicacionPoliticaPrestamo.validar_prestamo` (línea 72).
### SistemaRecursos/servicios/servicio_prestamo.py

- `ServicioAplicacionPrestamo._lista` (línea 34).
- `ServicioAplicacionPrestamo._preparar_participantes` (línea 124).
- `ServicioAplicacionPrestamo._validar_encargado` (línea 238).
- `ServicioAplicacionPrestamo.actualizar_prestamos_vencidos` (línea 184).
- `ServicioAplicacionPrestamo.consultar_bienes_disponibles` (línea 58).
- `ServicioAplicacionPrestamo.consultar_resumen_prestamos` (línea 147).
- `ServicioAplicacionPrestamo.consultar_solicitantes` (línea 39).
- `ServicioAplicacionPrestamo.registrar_en_operacion` (línea 117).
- `ServicioAplicacionPrestamo.registrar_solicitud` (línea 113).
- `ServicioAplicacionPrestamo.reportar_perdida` (línea 227).
- `ServicioAplicacionPrestamo.seleccionar_bien_para_prestamo` (línea 67).
### SistemaRecursos/servicios/servicio_recurso.py

- `ServicioAplicacionRecurso._validar_filtros` (línea 67).
- `ServicioAplicacionRecurso.actualizar_categoria` (línea 122).
- `ServicioAplicacionRecurso.actualizar_recurso` (línea 49).
- `ServicioAplicacionRecurso.consultar_administracion_recursos` (línea 18).
- `ServicioAplicacionRecurso.consultar_categoria` (línea 110).
- `ServicioAplicacionRecurso.consultar_disponibilidad_recurso` (línea 95).
- `ServicioAplicacionRecurso.opciones_catalogo` (línea 85).
- `ServicioAplicacionRecurso.registrar_categoria` (línea 116).
- `ServicioAplicacionRecurso.registrar_recurso` (línea 28).
### SistemaRecursos/servicios/servicio_reporte.py

- `ServicioAplicacionReporte._celda_csv` (línea 57).
- `ServicioAplicacionReporte._fecha` (línea 20).
- `ServicioAplicacionReporte._fecha_csv` (línea 64).
- `ServicioAplicacionReporte._validar_filtros` (línea 31).
- `ServicioAplicacionReporte.consultar_prestamos` (línea 53).
- `ServicioAplicacionReporte.exportar_prestamos` (línea 69).
### SistemaRecursos/servicios/servicio_reserva.py

- `ServicioAplicacionReserva._fecha_requerida` (línea 110).
- `ServicioAplicacionReserva.expirar_solicitudes_vencidas` (línea 40).
### SistemaRecursos/servicios/servicio_rol.py

- `ServicioAplicacionRol._construir_matriz` (línea 25).
- `ServicioAplicacionRol.actualizar_matriz_permisos` (línea 40).
- `ServicioAplicacionRol.actualizar_rol_cuenta` (línea 55).
- `ServicioAplicacionRol.consultar_cuentas_para_roles` (línea 47).
- `ServicioAplicacionRol.consultar_permisos` (línea 21).
- `ServicioAplicacionRol.consultar_roles` (línea 18).
### SistemaRecursos/servicios/servicio_sancion.py

- `ServicioAplicacionSancion.aplicar_sanciones_vencidas` (línea 11).
- `ServicioAplicacionSancion.levantar_sancion_vencimiento` (línea 14).
### SistemaRecursos/servicios/validacion_identificadores.py

- `identificador` (línea 1).

## Definiciones modificadas conservando ruta y nombre

### SistemaRecursos/app.py

- `create_app` (línea 70).
- `create_app.inicio` (línea 122).
### SistemaRecursos/dominio/gestion_control/politica_prestamo.py

- `PoliticaPrestamo.__post_init__` (línea 57).
### SistemaRecursos/dominio/gestion_personas_usuarios/persona.py

- `Persona.__post_init__` (línea 37).
### SistemaRecursos/dominio/gestion_prestamos/ampliacion_prestamo.py

- `AmpliacionPrestamo.__post_init__` (línea 15).
### SistemaRecursos/dominio/gestion_prestamos/devolucion.py

- `Devolucion.__post_init__` (línea 11).
- `Devolucion.estado_bien` (línea 18).
### SistemaRecursos/dominio/gestion_recursos/bien_material.py

- `BienMaterial.__post_init__` (línea 21).
### SistemaRecursos/dominio/gestion_recursos/recurso.py

- `Recurso.__post_init__` (línea 17).
### SistemaRecursos/presentacion/controladores/controlador_acceso.py

- `ControladorAcceso.__init__` (línea 6).
### SistemaRecursos/presentacion/controladores/controlador_ampliacion_prestamo.py

- `ControladorAmpliacionPrestamo.__init__` (línea 6).
### SistemaRecursos/presentacion/controladores/controlador_bien_material.py

- `ControladorBienMaterial.__init__` (línea 7).
- `ControladorBienMaterial.cambiar_estado_bien_material` (línea 85).
- `ControladorBienMaterial.consultar_bienes_materiales` (línea 46).
- `ControladorBienMaterial.eliminar_bien_material` (línea 93).
### SistemaRecursos/presentacion/controladores/controlador_persona.py

- `ControladorPersona.__init__` (línea 7).
- `ControladorPersona.consultar_persona` (línea 40).
- `ControladorPersona.consultar_personas` (línea 31).
- `ControladorPersona.desactivar_persona` (línea 63).
### SistemaRecursos/presentacion/controladores/controlador_politica_prestamo.py

- `ControladorPoliticaPrestamo.__init__` (línea 7).
### SistemaRecursos/presentacion/controladores/controlador_prestamo.py

- `ControladorPrestamo.__init__` (línea 6).
- `ControladorPrestamo.consultar_prestamo` (línea 73).
- `ControladorPrestamo.consultar_prestamos` (línea 38).
- `ControladorPrestamo.registrar_devolucion` (línea 81).
- `ControladorPrestamo.registrar_prestamo` (línea 54).
### SistemaRecursos/presentacion/controladores/controlador_recurso.py

- `ControladorRecurso.__init__` (línea 6).
- `ControladorRecurso.consultar_recurso` (línea 45).
- `ControladorRecurso.consultar_recursos` (línea 36).
- `ControladorRecurso.eliminar_categoria` (línea 90).
- `ControladorRecurso.eliminar_recurso` (línea 70).
### SistemaRecursos/presentacion/controladores/controlador_reporte.py

- `ControladorReporte.__init__` (línea 6).
### SistemaRecursos/presentacion/controladores/controlador_reserva.py

- `ControladorReserva.__init__` (línea 6).
- `ControladorReserva.cancelar_reserva` (línea 73).
- `ControladorReserva.consultar_reserva` (línea 55).
- `ControladorReserva.consultar_reservas` (línea 28).
- `ControladorReserva.entregar_reserva` (línea 69).
- `ControladorReserva.expirar_reserva` (línea 81).
- `ControladorReserva.preparar_reserva` (línea 65).
- `ControladorReserva.rechazar_reserva` (línea 77).
- `ControladorReserva.registrar_reserva` (línea 40).
### SistemaRecursos/presentacion/controladores/controlador_rol.py

- `ControladorRol.__init__` (línea 7).
- `ControladorRol.consultar_roles` (línea 19).
### SistemaRecursos/presentacion/seguridad.py

- `requiere_permiso` (línea 27).
- `requiere_permiso.decorar` (línea 28).
- `requiere_permiso.decorar.protegida` (línea 30).
### SistemaRecursos/repositorio/conexion_mysql.py

- `MySQLConnection.__init__` (línea 9).
- `MySQLConnection.sesion` (línea 21).
### SistemaRecursos/repositorio/repositorio_acceso_sql.py

- `RepositorioAccesoSQL.consultar_cuenta_por_id` (línea 25).
- `RepositorioAccesoSQL.registrar_acceso` (línea 28).
### SistemaRecursos/repositorio/repositorio_bien_material_sql.py

- `RepositorioBienMaterialSQL.cambiar_estado_bien_material` (línea 45).
- `RepositorioBienMaterialSQL.consultar_bien_material` (línea 6).
- `RepositorioBienMaterialSQL.consultar_bienes_materiales` (línea 16).
- `RepositorioBienMaterialSQL.consultar_prestamo_pendiente` (línea 51).
- `RepositorioBienMaterialSQL.eliminar_bien_material` (línea 59).
### SistemaRecursos/repositorio/repositorio_persona_sql.py

- `RepositorioPersonaSQL.consultar_persona` (línea 15).
- `RepositorioPersonaSQL.consultar_personas` (línea 22).
- `RepositorioPersonaSQL.desactivar_persona` (línea 70).
### SistemaRecursos/repositorio/repositorio_politica_prestamo_sql.py

- `RepositorioPoliticaPrestamoSQL.consultar_limites_articulos` (línea 26).
### SistemaRecursos/repositorio/repositorio_prestamo_sql.py

- `RepositorioPrestamoSQL.consultar_prestamo` (línea 85).
- `RepositorioPrestamoSQL.consultar_prestamos` (línea 57).
### SistemaRecursos/repositorio/repositorio_recurso_sql.py

- `RepositorioRecursoSQL.consultar_categorias` (línea 46).
- `RepositorioRecursoSQL.consultar_recurso` (línea 23).
- `RepositorioRecursoSQL.consultar_recursos` (línea 7).
- `RepositorioRecursoSQL.eliminar_categoria` (línea 60).
- `RepositorioRecursoSQL.eliminar_recurso` (línea 43).
### SistemaRecursos/repositorio/repositorio_reserva_sql.py

- `RepositorioReservaSQL.consultar_reserva` (línea 47).
- `RepositorioReservaSQL.consultar_reservas` (línea 22).
- `RepositorioReservaSQL.registrar_reserva` (línea 100).
### SistemaRecursos/servicios/procesador_vencimientos.py

- `iniciar_procesador_vencimientos` (línea 8).
- `iniciar_procesador_vencimientos.procesar` (línea 11).
### SistemaRecursos/servicios/servicio_acceso.py

- `ServicioAplicacionAcceso.__init__` (línea 7).
### SistemaRecursos/servicios/servicio_ampliacion_prestamo.py

- `ServicioAplicacionAmpliacionPrestamo.__init__` (línea 11).
### SistemaRecursos/servicios/servicio_bien_material.py

- `ServicioAplicacionBienMaterial.__init__` (línea 13).
- `ServicioAplicacionBienMaterial.cambiar_estado_bien_material` (línea 54).
- `ServicioAplicacionBienMaterial.consultar_bien_material` (línea 16).
- `ServicioAplicacionBienMaterial.consultar_bienes_materiales` (línea 22).
- `ServicioAplicacionBienMaterial.eliminar_bien_material` (línea 73).
### SistemaRecursos/servicios/servicio_cuenta.py

- `ServicioAplicacionCuenta.__init__` (línea 15).
- `ServicioAplicacionCuenta.actualizar_cuenta` (línea 34).
- `ServicioAplicacionCuenta.consultar_cuenta` (línea 18).
- `ServicioAplicacionCuenta.registrar_cuenta` (línea 24).
### SistemaRecursos/servicios/servicio_persona.py

- `ServicioAplicacionPersona.__init__` (línea 9).
- `ServicioAplicacionPersona.consultar_persona` (línea 21).
- `ServicioAplicacionPersona.consultar_personas` (línea 12).
- `ServicioAplicacionPersona.desactivar_persona` (línea 57).
### SistemaRecursos/servicios/servicio_politica_prestamo.py

- `ServicioAplicacionPoliticaPrestamo.__init__` (línea 14).
- `ServicioAplicacionPoliticaPrestamo.consultar_limites_articulos` (línea 29).
### SistemaRecursos/servicios/servicio_prestamo.py

- `ServicioAplicacionPrestamo.__init__` (línea 15).
- `ServicioAplicacionPrestamo.consultar_prestamo` (línea 39).
- `ServicioAplicacionPrestamo.consultar_prestamos` (línea 24).
- `ServicioAplicacionPrestamo.registrar_devolucion` (línea 78).
- `ServicioAplicacionPrestamo.registrar_prestamo` (línea 54).
### SistemaRecursos/servicios/servicio_recurso.py

- `ServicioAplicacionRecurso.__init__` (línea 9).
- `ServicioAplicacionRecurso.consultar_categorias` (línea 72).
- `ServicioAplicacionRecurso.consultar_recurso` (línea 23).
- `ServicioAplicacionRecurso.consultar_recursos` (línea 12).
- `ServicioAplicacionRecurso.eliminar_categoria` (línea 84).
- `ServicioAplicacionRecurso.eliminar_recurso` (línea 67).
### SistemaRecursos/servicios/servicio_reserva.py

- `ServicioAplicacionReserva.__init__` (línea 17).
- `ServicioAplicacionReserva._resolver_reserva` (línea 91).
- `ServicioAplicacionReserva.cancelar_reserva` (línea 82).
- `ServicioAplicacionReserva.consultar_reserva` (línea 33).
- `ServicioAplicacionReserva.consultar_reservas` (línea 23).
- `ServicioAplicacionReserva.entregar_reserva` (línea 79).
- `ServicioAplicacionReserva.expirar_reserva` (línea 88).
- `ServicioAplicacionReserva.preparar_reserva` (línea 76).
- `ServicioAplicacionReserva.rechazar_reserva` (línea 85).
- `ServicioAplicacionReserva.registrar_reserva` (línea 44).
### SistemaRecursos/servicios/servicio_rol.py

- `ServicioAplicacionRol.__init__` (línea 7).
### SistemaRecursos/servicios/servicio_sancion.py

- `ServicioAplicacionSancion.__init__` (línea 9).
