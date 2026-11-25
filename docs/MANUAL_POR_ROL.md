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
nueva o se restableció tu clave, el sistema te pedirá cambiarla antes de continuar.

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

### Reservas

**Reservas → Atender reservas:** prepara un ejemplar para cada reserva en espera, entrégalo
cuando la persona llegue, o recházala con un motivo. Las reservas no retiradas a tiempo vencen
solas y liberan el bien.

### Devoluciones

Abre el préstamo (**Préstamos → Devolver**), marca los bienes que recibes, indica su condición
(**bueno** o **dañado**) y una observación. Puedes recibir solo una parte: el resto queda pendiente.
Si el bien llega tarde, la sanción leve se genera sola.

### Ampliaciones

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
- **Roles y permisos:** asignar a cada cuenta uno de los tres roles. Los permisos de cada rol
  son fijos y se muestran como consulta.

### Inventario

- **Administrar recursos:** categorías, recursos del catálogo y sus bienes físicos.
- Al registrar un bien, el sistema genera su **identificador del sistema** (por ejemplo
  `SR-2026-7F3K9Q`) y su **fecha de registro**. No se escriben a mano y no cambian al editar.
  La **serie del fabricante** y la **fecha de adquisición** son opcionales; la adquisición no
  puede ser una fecha futura.

### Mantenimiento de bienes

En la ficha de un bien (**Administrar recursos → bien**):

1. **Abrir mantenimiento:** tipo (preventivo o correctivo), motivo y fin estimado opcional.
   El bien pasa a *En mantenimiento* y **no se puede prestar ni reservar**.
2. **Cerrar mantenimiento:** indica si queda **disponible** o sigue **dañado**, con una observación.

El registro de mantenimientos (inicio, fin estimado, fin real, responsables) queda en la ficha
del bien. Un bien solo vuelve a estar disponible cerrando su mantenimiento.

### Reglas del servicio

- **Políticas de préstamo:** plazo por tipo de persona y categoría (en horas o días) y permiso de salida.
- **Máximo de artículos** por tipo de persona y **horario de atención**.
- **Sanciones → Configurar plazos:** días de la leve, de la grave y espera para revisar pérdidas.
  Cambiarlos no modifica sanciones ya aplicadas.
- Solo el administrador aplica y levanta sanciones **muy graves**.

### Revisión automática

Si la revisión automática de vencimientos deja de ejecutarse más de 5 minutos, **Inicio** muestra
un aviso con la última ejecución correcta y el último error. Reinicia el sistema con `run.ps1`
(ver la [guía de instalación](GUIA_INSTALACION.md)).
