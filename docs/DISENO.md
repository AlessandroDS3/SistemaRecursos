# Identidad visual de la escuela - UNSA

Paleta inspirada en la captura proporcionada por el usuario: granate principal #87002e, granate oscuro #500019, panel de acceso #700023, gris y blanco. Son aproximaciones visuales de la referencia, no una especificación oficial de marca.

El archivo static/img/logo-escuela.png es la imagen original proporcionada, sin recortes ni cambios de color. Se muestra completa sobre blanco en el acceso, catálogo y personas. El azul y verde del logo se conservan.

| Antes | Después | Motivo |
|---|---|---|
| Marca Recurso y símbolo r. | Logo de Ciencia de la Computación UNSA | Identificar la escuela |
| Azul y verde en la interfaz | Granate, gris y blanco | Seguir la referencia de la universidad |
| Marca tipográfica compacta | Imagen proporcional adaptable | Conservar legibilidad y composición |

Se mantienen las interacciones de emil-design-eng, navegación con teclado y movimiento reducido. Sin emojis en el código.

Verificado en Edge con MySQL real y datos ficticios en una base temporal: login correcto e incorrecto, consultas, búsqueda, filtros, alta de recursos y ejemplares, rechazo de duplicados, registro de personas, fichas, cierre de sesión y protección de API. Logo accesible desde el login. Vistas de escritorio y móvil sin desbordamiento horizontal. Sin errores JavaScript. La base temporal fue eliminada al terminar.

Para ver los cambios: cerrar el servidor anterior, ejecutar iniciar.cmd y recargar con Ctrl+F5. Se necesita reiniciar porque server.py incorpora la ruta pública del logo. La configuración MySQL, cuentas y datos existentes se conservan. El ZIP no incluye contraseñas ni config.ini personal; incluye config.example.ini y las instrucciones del proyecto.
