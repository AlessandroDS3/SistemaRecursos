# Manual de uso por rol

Sistema de Recursos · Escuela Profesional de Ciencia de la Computación · UNSA

El sistema tiene tres roles fijos. El menú lateral muestra solo las opciones de cada rol;
si una acción no aparece, tu cuenta no tiene ese permiso.

- [Para todos](#para-todos)
- [Usuario](#usuario-estudiante-docente-o-administrativo)
- [Encargado de préstamos](#encargado-de-préstamos)
- [Administrador](#administrador)

---

## Para todos

**Iniciar sesión.** Escribe tu usuario y contraseña en la pantalla de acceso. Si tu cuenta es
nueva o se restableció tu acceso, usa **Activar cuenta** en la pantalla de inicio de
sesión. Ingresa el usuario y el código de un solo uso, válido durante 24 horas, y elige
tu contraseña. Con una sesión activa puedes usar **Cambiar mi contraseña** en el menú lateral.

- Tras **5 intentos fallidos** seguidos, la cuenta espera **15 minutos** antes de volver a intentar.
- La sesión se cierra sola tras **30 minutos sin actividad** o **8 horas** desde el ingreso.
- **Cerrar sesión** (al pie del menú) invalida la sesión en el servidor: aunque alguien copie
  la cookie, ya no sirve.

**Cambiar mi contraseña:** al pie del menú. Cambiarla cierra las demás sesiones abiertas.

**Tema claro u oscuro:** botón redondo arriba a la derecha. La elección se recuerda en ese navegador.

**Imprimir:** cualquier listado o ficha se imprime con Ctrl + P; el menú, los filtros y los
botones no salen en el papel.

---

## Usuario (estudiante, docente o administrativo)

| Quiero… | Dónde | Cómo |
|---|---|---|
| Buscar un recurso | **Catálogo** | Filtra por nombre, categoría o disponibilidad y abre **Ver detalle** para ver las condiciones del préstamo. |
| Reservar | Ficha del recurso | Elige la fecha en que lo necesitas y confirma. La reserva queda **en espera** hasta que el encargado prepare un ejemplar. |
| Ver o cancelar mis reservas | **Mis reservas** | Puedes cancelar mientras no se haya entregado. |
| Recibir el préstamo | En el mostrador | El encargado registra la entrega. Los estudiantes necesitan matrícula vigente. |
| Ver mis préstamos | **Mis préstamos** | Cada bien tiene su propia fecha límite. |
| **Pedir más plazo** | **Mis préstamos** → abrir el préstamo → **Solicitar más plazo** | Indica el tiempo adicional y el motivo. El encargado lo aprueba o rechaza; mientras tanto, el plazo actual sigue vigente. Solo la persona responsable del préstamo puede pedirlo, y solo antes del vencimiento. |
| Ver o descargar mi historial | **Mis préstamos** → **Mi historial completo** | Se descarga en CSV o PDF. |

**Bloqueos:** si tienes una sanción activa o un bien vencido sin devolver, no podrás reservar
ni recibir nuevos préstamos. Sí puedes devolver lo que tienes.

Cada reserva activa ocupa un cupo del mismo máximo de artículos que los préstamos pendientes.
Al retirar el bien, el préstamo ocupa el cupo de la reserva. Puedes reservar con hasta siete
días de anticipación y cancelar antes de retirar el bien sin penalización.

---

## Encargado de préstamos

Además de lo anterior:

### Entregas

1. **Préstamos → + Nuevo préstamo.**
2. Busca a la persona por apellido, DNI o CUI. El sistema indica si está habilitada.
3. Elige si es **individual** o **grupal** (en grupal agrega a los integrantes) y si el uso es
   **dentro** o **fuera** de la escuela.
4. Agrega los bienes por código de inventario o nombre. Cada bien muestra su plazo según la política.
5. Marca que comunicaste el plazo y las condiciones, y pulsa **Registrar préstamo**.

Las entregas solo se registran dentro del horario de atención. Los bienes en mantenimiento,
dañados, perdidos o reservados para otra persona no aparecen como disponibles.
Si una reserva en turno necesita el último ejemplar disponible, atiéndela primero.
En un préstamo grupal, todos los bienes pendientes cuentan para el cupo de cada integrante.
Al devolver o regularizar un bien, se libera ese cupo para todos los integrantes.
Para registrar una entrega o recepción de un préstamo propio o de un grupo al que perteneces,
ingresa el número de autorización emitido por otro administrador.
Si estás afectado por una sanción como titular o integrante, otro responsable autorizado
debe evaluar, levantar o anular el caso.

### Reservas

**Reservas → Atender reservas:** prepara un ejemplar para cada reserva en espera, entrégalo
cuando la persona llegue, o recházala con un motivo. Si la persona pierde su habilitación,
la reserva queda pendiente de atención hasta que se cierre o venza. Cuando vence el retiro
de un bien preparado, el sistema registra que la persona no se presentó y libera el ejemplar.

### Devoluciones

Abre el préstamo (**Préstamos → Devolver**), marca los bienes que recibes e ingresa el código
de inventario leído en cada bien y su condición. Puedes recibir una parte y dejar el resto
pendiente. Si el código no coincide, registra la discrepancia en la ficha del préstamo.
Si el bien llega tarde, la sanción leve se genera sola.

### Ampliaciones

Cada bien admite una ampliación por préstamo. Se bloquea si hay una sanción activa aplicable
o si las reservas pendientes del mismo recurso requieren un ejemplar que no está disponible.

- **Directa:** en la ficha del préstamo, **Ampliar plazo**. El sistema muestra la nueva fecha antes
  de confirmar.
- **Solicitudes de usuarios:** **Préstamos → Solicitudes de ampliación** (o el aviso en **Inicio**).
  **Aprobar** revisa de nuevo la política y el horario y actualiza el plazo una sola vez.
  Si el bien ya se devolvió o el plazo venció mientras se revisaba, la aprobación se rechaza
  y debes **Rechazar** la solicitud con un motivo. También se pueden resolver desde la ficha
  del préstamo.

### Pérdidas, faltas y sanciones

- **Reportar pérdida:** desde la ficha del préstamo; aplica una sanción grave y deja el bien
  pendiente de recuperación o reposición.
- **Evaluar una falta:** daño, salida no autorizada o falta de custodia.
- **Sanciones:** puedes levantar una **leve** con justificación después de recibir el bien.
  Las graves exigen cumplir el plazo y regularizar el bien. Las muy graves son exclusivas del
  administrador.
- **Regularizar:** desde la ficha de la sanción (devolución, recuperación, reparación,
  reposición con un código de inventario nuevo, o verificación).

### Consultas

**Reportes** con filtros y descarga en CSV o PDF, e historiales por persona o por bien.

---

## Administrador

Además de todo lo anterior:

### Personas, cuentas y roles

- **Personas:** registrar, editar y desactivar estudiantes, docentes y administrativos.
  Desactivar una persona o su cuenta la expulsa del sistema al instante.
- **Personas → Editar:** cambiar el tipo de persona con un motivo. Se conserva el DNI y la
  ficha muestra el historial de cambios.
- **Personas → Editar cuenta y rol:** asignar a la cuenta uno de los tres roles. En el mismo
  formulario puedes consultar los permisos fijos de cada rol.
- **Personas → Editar cuenta y rol → Restablecer acceso:** verifica la solicitud de la persona,
  registra el motivo y entrega el código por un canal privado. Esta acción está disponible
  para cuentas activas de usuario y encargado y cierra sus sesiones abiertas.

### Inventario

- **Administrar recursos:** categorías, recursos del catálogo y sus bienes físicos.
- Al registrar un bien, el sistema genera su **identificador del sistema** (por ejemplo
  `SR-2026-7F3K9Q`) y su **fecha de registro**. No se escriben a mano y no cambian al editar.
  La **serie del fabricante** es opcional y debe ser única para una misma marca y modelo.
  La **fecha de adquisición** es opcional y debe ser igual o anterior a la fecha actual.
- El código de inventario queda bloqueado mientras el ejemplar esté prestado o reservado.
  La categoría del recurso queda bloqueada mientras tenga un préstamo pendiente.

### Mantenimiento de bienes

En la ficha de un bien (**Administrar recursos → bien**):

1. **Abrir mantenimiento:** tipo (preventivo o correctivo), motivo y fin estimado opcional.
   El bien pasa a *En mantenimiento* y **no se puede prestar ni reservar**.
2. **Cerrar mantenimiento:** indica si queda **disponible** o sigue **dañado**, con una observación.

El registro de mantenimientos (inicio, fin estimado, fin real, responsables) queda en la ficha
del bien. Un bien solo vuelve a estar disponible cerrando su mantenimiento.

### Reglas del servicio

- **Políticas de préstamo:** plazo por tipo de persona y categoría (en horas o días) y permiso de salida.
- **Máximo de artículos** por tipo de persona y **horario de atención**. Elige los días y la
  hora de apertura y cierre en Lima. Por defecto, de lunes a viernes de 08:00 a 16:00.
  Si el plazo de devolución en días cae en un día sin atención, vence el siguiente día de atención.
- **Sanciones → Configurar plazos:** días de la leve, de la grave y espera para revisar pérdidas.
  Cambiarlos no modifica sanciones ya aplicadas.
- Solo el administrador aplica y levanta sanciones **muy graves**.
- **Sanciones → Anular por error:** registra el motivo de la anulación. Si el original de un bien
  perdido aparece después de la reposición, regístralo desde la ficha de la sanción. El original
  pasa a revisión y el reemplazo se conserva.
- **Préstamos → Autorizar operación propia:** registra el motivo y genera un número válido
  durante 24 horas para una entrega o una recepción. Para la recepción indica el número del préstamo.
- **Préstamos → Rectificar devolución:** indica el motivo. Si el bien tuvo movimientos posteriores
  o la devolución está vinculada a una sanción, revisa el caso antes de aplicar una rectificación.

### Revisión automática

Si la revisión automática de vencimientos deja de ejecutarse más de 5 minutos, **Inicio** muestra
un aviso con la última ejecución correcta y el último error. Si operas el procesador por
separado, puedes reiniciarlo con `run.ps1 -SoloProcesador`. Consulta la [guía de instalación](GUIA_INSTALACION.md).
