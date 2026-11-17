# Consultas reales de los reportes

Abre [reportes_consultas_aplicacion.sql](reportes_consultas_aplicacion.sql).
Contiene las consultas para comprobar los reportes sin filtros y sin paginación,
como al descargar todo un reporte.
Las consultas 01-14 corresponden al SQL actual del repositorio, incluidos los JOIN
del resumen 02. Los parámetros de filtros no están incluidos en estos ejemplos.
Se eliminó `reportes_csv_mysql.sql`: imitaba en SQL pasos que el programa hace en Python.

## Cómo comprobarlo ante el profesor

1. En Reportes, elige el tipo de reporte y pulsa **Limpiar filtros**. Comprueba que
   quedó seleccionado el tipo que quieres comparar y descarga su CSV.
2. En MySQL, ejecuta el `USE` y el `SET NAMES` del principio del archivo.
3. Selecciona y ejecuta únicamente la consulta de **filas** que corresponde al reporte.
   No agregues `LIMIT`: la descarga incluye todas las filas.
4. Compara los identificadores, los bienes, las cantidades y los demás datos con el CSV.
   Para préstamos, devoluciones y sanciones, ejecuta también la consulta 15
   con los `id_prestamo` que salieron para comprobar sus integrantes.

| Reporte | Filas para comparar con el CSV | Indicadores de la pantalla |
| --- | --- | --- |
| Préstamos | 01 | 02 |
| Devoluciones y cumplimiento | 03 | 04 |
| Bienes atrasados | 05 | 06 |
| Inventario | 07 | 08 |
| Solicitudes y reservas | 09 | 10 |
| Sanciones | 11 | 12 |
| Daños y pérdidas | 13 | 14 |

Los indicadores son otro resultado: no son las filas que se exportan. La pantalla
consulta filas y resumen; la descarga consulta solo filas y, si hay préstamos
grupales, sus integrantes. No consulta indicadores.
Las consultas 16-18 documentan la cuenta, sus permisos y las categorías del selector;
no generan las filas del reporte.

## Qué hace Python después del SELECT

La consulta de filas y la tabla del CSV **contienen los mismos registros**, pero no
son idénticas en todas sus columnas ni en su representación:

- Las fechas y horas de la base están en UTC. Python las convierte a Lima (UTC−5).
  Por ejemplo, `2026-11-16 15:00:00` en MySQL corresponde a `2026-11-16 10:00:00` en el CSV.
  La fecha de adquisición del inventario es un día, sin conversión de hora.
- La consulta 15 devuelve una fila por integrante. Python reúne esos nombres como
  `Nombre (DNI); Nombre (DNI)` en la columna `integrantes` de cada préstamo.
- Cada consulta selecciona las columnas de su propio reporte. Préstamos, devoluciones
  y sanciones agregan `integrantes` al final del CSV con el resultado de la consulta 15,
  únicamente para los préstamos grupales; en individuales la celda queda vacía.
  Atrasados devuelve únicamente las ocho columnas de su consulta, sin integrantes.
- Python escribe los `NULL` como celdas vacías y protege los valores que podrían
  interpretarse como fórmulas. También escribe los separadores y las comillas del CSV.

Por eso puedes explicar: **«Esta es la consulta real que obtiene los datos. Python
prepara sus columnas y su formato para escribir el CSV».** Afirmar que un solo
SELECT ya devuelve exactamente todas sus celdas no describiría el programa actual.

## Si comparas un CSV con filtros

Este archivo muestra el caso **sin filtros**. Cuando eliges filtros, el repositorio
construye el `WHERE`, une sus condiciones con `AND` y pasa los valores como parámetros `%s`.
No ejecuta condiciones opcionales con `@variable IS NULL OR ...`.

Ejemplo real: en inventario, al seleccionar únicamente la categoría 1, el final de
la consulta 07 pasa a ser:

```sql
WHERE r.id_categoria=1
ORDER BY r.nombre,b.codigo_inventario,b.id_bien;
```

Para esa misma selección, agrega `WHERE r.id_categoria=1` al resumen 08.
En la aplicación se envía `r.id_categoria=%s` con el parámetro `1`; en MySQL lo
escribes directamente. No cambies sus `JOIN`, sus columnas ni su agrupación.

Las fechas de los filtros se introducen en hora de Lima y se convierten a UTC antes
de llegar al repositorio. Por ejemplo, del 1 al 30 de noviembre de 2026, ambos
incluidos, en préstamos agrega este `WHERE` antes de `ORDER BY`:

```sql
WHERE p.fecha_entrega >= '2026-11-01 05:00:00'
AND p.fecha_entrega <  '2026-12-01 05:00:00'
```

Compara sobre la misma base y sin cambios de datos entre ambas ejecuciones. Los
atrasos usan `UTC_TIMESTAMP()`: sus minutos de retraso avanzan con el tiempo.
Los retrasos de atrasados y devoluciones se expresan en minutos completos. Una
devolución con 30 segundos de demora sigue siendo tardía, aunque muestre 0 minutos.
El promedio de devoluciones tardías puede tener decimales al promediar esos minutos.

El estado del préstamo completo se calcula únicamente si seleccionas ese filtro
en préstamos o devoluciones. El tipo de persona se comprueba únicamente al usar su
filtro; no se calcula ni se añade como columna a cada fila del reporte.
