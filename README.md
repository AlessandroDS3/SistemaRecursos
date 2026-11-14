# Sistema de recursos: implementación reescrita

Proyecto de trabajo: **`D:\TI_sistema_recursos\SistemaRecursos_rehecho`**.
Aplicación: **[SistemaRecursos/](SistemaRecursos/README.md)**.
Rama local: **`sistema-simplificado`**.

La aplicación tiene una implementación nueva de dominio, casos de uso, persistencia y presentación. Cada función conserva un nombre reconocible entre capas: `acceso`, `persona`, `cuenta`, `bien_material`, `prestamo`, etc. El dominio está separado en cuatro carpetas de negocio.

Se conservan los dos SQL de 19 tablas y las reglas acordadas: préstamos individuales y grupales, reservas, devoluciones parciales, pérdidas pendientes de recuperación, ampliación presencial por el personal, sanciones por retraso y reportes CSV.

La guía de ejecución y el mapa de archivos están en **[SistemaRecursos/README.md](SistemaRecursos/README.md)**. La copia utiliza el puerto **5001** y propone una base propia **`prestamos_escuela_rehecho`**.

El proyecto anterior permanece en `D:\TI_sistema_recursos\SistemaRecursos_local`, con sus modificaciones pendientes. Ambas carpetas son árboles de trabajo Git con ramas distintas. Esta reescritura se guarda localmente; no se publica en GitHub.

El commit `438ec36` conserva la copia inmediatamente anterior a la reescritura. Los MDJ, XML/PNG y la auditoría heredados de la raíz son documentos de referencia de la versión anterior; el mapa vigente del código está en el README de la aplicación.
