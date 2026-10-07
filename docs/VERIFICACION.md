# Verificación del login — 6 de octubre de 2026

26 pruebas aprobadas: 15 unitarias y 11 de integración HTTP con MySQL real. Se emplearon bases temporales con nombres aleatorios, eliminadas al finalizar. No se utilizaron los registros de la base del usuario para las pruebas.

Cobertura: registro de recursos y personas, duplicados y rollback, validación, persistencia, hash y salt de contraseñas, expiración de sesión, acceso denegado sin sesión, cierre de sesión, rechazo de reutilización de la cookie y límite de intentos fallidos.

Navegador Edge: login erróneo y correcto, atributos HttpOnly/SameSite de cookie, navegación a personas, cierre de sesión, bloqueo posterior de API y páginas. Vista revisada en escritorio y móvil sin errores JavaScript. Captura login.png sin credenciales reales.

Revisión de fuentes: sin emojis ni pictogramas Unicode decorativos. Se mantiene el servidor local HTTP. Roles, recuperación de cuentas y despliegue público no están incluidos.
