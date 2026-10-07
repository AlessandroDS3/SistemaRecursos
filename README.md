# Sistema de Recursos — Ciencia de la Computación UNSA

## ¿De qué trata?

Este proyecto busca ayudar a la Escuela de Ciencia de la Computación de la UNSA a organizar sus recursos y gestionar sus préstamos.

La idea es tener en un solo lugar los equipos, materiales y personas de la escuela. Por ahora podemos registrar recursos, revisar sus ejemplares y registrar estudiantes, docentes y administrativos.

## ¿Qué necesitamos?

- Python instalado.
- MySQL Server instalado y encendido.
- Un navegador, como Chrome o Edge.
- Internet para instalar las dependencias la primera vez.

Si usas MySQL Workbench, recuerda que sirve para administrar la base de datos: también necesitas que MySQL Server esté funcionando.

## Cómo usarlo

### La primera vez

1. Descarga el proyecto y descomprime la carpeta si viene en ZIP.
2. Enciende MySQL Server.
3. Abre `configurar_mysql.cmd` haciendo doble clic.
4. Escribe los datos de tu conexión. Si MySQL está en tu computadora, normalmente el host es `127.0.0.1` y el puerto es `3306`. Usa tu usuario y contraseña de MySQL. Puedes dejar `prestamos_escuela` como nombre de la base de datos.
5. Espera a que termine la configuración. El programa prepara las dependencias y puede crear la base si tu usuario tiene permisos.
6. Abre `crear_usuario.cmd` y crea tu cuenta para entrar a la página. Elige una contraseña de al menos 10 caracteres.
7. Abre `iniciar.cmd` y deja esa ventana abierta.
8. En tu navegador entra a **http://127.0.0.1:8000** e inicia sesión con la cuenta que acabas de crear.

La cuenta de la página es diferente del usuario y contraseña de MySQL.

### Las siguientes veces

Solo enciende MySQL Server, abre `iniciar.cmd` y entra a **http://127.0.0.1:8000**. No necesitas configurar todo otra vez.

## ¿Qué puedo hacer en la página?

- **Entrar con mi cuenta:** el sistema pide iniciar sesión antes de acceder.
- **Registrar recursos:** agregar los equipos y materiales de la escuela.
- **Agregar ejemplares:** registrar varias unidades de un mismo recurso. Por ejemplo, un modelo de laptop puede tener tres laptops físicas.
- **Buscar y filtrar:** encontrar recursos y consultar su disponibilidad.
- **Ver detalles:** revisar la información y los ejemplares de cada recurso.
- **Registrar personas:** agregar estudiantes, docentes y administrativos, buscar sus registros y consultar sus fichas.
- **Cerrar sesión:** salir de la cuenta al terminar.

Las fechas de registro se colocan automáticamente y los números de serie se generan al guardar. No hay que escribirlos a mano.

## Lo que ya avanzamos

Empezamos con el catálogo de recursos y luego agregamos el registro de personas y el inicio de sesión. También cambiamos la base de datos a **MySQL** para guardar la información del sistema.

Después mejoramos la apariencia con el logo de la escuela y los colores granate, gris y blanco. La página también se adapta a celulares.

Por último, ordenamos el código: los HTML, CSS, JavaScript e imágenes están en carpetas separadas. También agregamos validaciones para detectar datos incorrectos o registros repetidos.

## Lo que sigue

El siguiente paso es agregar el registro de préstamos y devoluciones. Más adelante se podrán incluir reservas y permisos según el tipo de usuario. Estas funciones todavía no están disponibles.

## ¿Con qué está hecho?

- **HTML:** organiza el contenido de las páginas.
- **CSS:** les da colores y diseño.
- **JavaScript:** hace funcionar los botones, formularios y búsquedas.
- **Python:** procesa lo que hacemos en la página.
- **MySQL:** guarda la información.

## Si algo no abre

- Si no conecta con MySQL, comprueba que el servidor esté encendido y que los datos de conexión sean correctos.
- Si la página no carga, revisa que la ventana de `iniciar.cmd` siga abierta.
- Si no ves un cambio de diseño, recarga con **Ctrl + F5**.

El proyecto funciona de forma local en tu computadora. No compartas `config.ini`, porque contiene los datos de tu conexión a MySQL.
