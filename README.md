# Sistema de recursos: copia simplificada

Esta carpeta contiene la versión reorganizada en la rama local `sistema-simplificado`.
La versión de trabajo anterior permanece en `D:\TI_sistema_recursos\SistemaRecursos_local`.

La copia usa una carpeta y un entorno virtual propios. Ambas ramas pertenecen al mismo repositorio Git; no se publicó nada en GitHub.

## Abrir y ejecutar

Abre esta carpeta como proyecto en tu editor. La aplicación está en **`SistemaRecursos/`**.
Las instrucciones de base de datos y arranque están en [SistemaRecursos/README.md](SistemaRecursos/README.md).

La aplicación nueva utiliza por defecto el puerto **5001** y el nombre de base **`prestamos_escuela_rehecho`**, para distinguirla de la anterior. Configura sus credenciales antes de iniciar. No se copiaron contraseñas ni bases de datos privadas.

## Qué cambió

- El dominio se agrupa en ocho módulos reconocibles: personas, cuentas, recursos, préstamos, reservas, control, reportes y validaciones.
- Las clases, estados, contratos y resultados de consulta de cada área se encuentran juntos.
- Los controladores renderizan directamente las plantillas; se retiraron seis clases intermedias `Vista`.
- Las conversiones simples de recurso y bien están en su módulo de dominio, sin fábricas separadas.
- El inicio y recuperación de sesión están en `presentacion/seguridad.py`.
- Préstamos y reservas comparten la consulta de sanciones activas y mantienen la transacción de sus operaciones.
- Los servicios reciben diccionarios y listas normales; las particularidades de formularios HTTP se resuelven en presentación.
- Los errores de validación, ausencia y base de datos tienen códigos distintos. Los de MySQL quedan registrados internamente.

Se conservan las funciones existentes: acceso, cuentas y roles, personas, catálogo e inventario, políticas, préstamos individuales y grupales, reservas, devoluciones, ampliación directa, sanciones de retraso y reportes CSV.

## Comparación y verificación

Comparación con los archivos actuales de `SistemaRecursos_local`, incluida la reorganización de acceso que estaba pendiente de commit allí:

| Medida | Anterior | Copia simplificada |
| --- | ---: | ---: |
| Módulos Python de producción, incluidos los inicializadores de paquetes | 104 | 53 |
| Líneas Python de producción, incluidos comentarios y blancos | 7135 | 7133 |
| Pruebas | 79 | 83 |
| Rutas y métodos HTTP | 68 | 68 |
| Tablas | 19 | 19 |

La reducción principal es de fragmentación y de archivos intermediarios; se conserva prácticamente el mismo volumen de reglas y comportamiento.

La verificación completa terminó con **83 pruebas correctas en 148,533 segundos, sin omisiones**, usando el entorno virtual nuevo y bases MySQL temporales. Se comprobaron también las 12 plantillas HTML, la sintaxis de JavaScript, la igualdad de los dos SQL y las dependencias entre capas. No se ejecutaron modificaciones sobre la base habitual del proyecto anterior.

## Documentación de referencia

Los MDJ, el XML/PNG y `AUDITORIA_MANTENIBILIDAD.md` heredados son referencias de la versión anterior: no representan la nueva distribución de archivos. La guía vigente de esta copia es el README de la aplicación. El esquema de 19 tablas conserva sus definiciones y limitaciones anteriores.
