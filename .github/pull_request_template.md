## Qué cambia

<!-- Resumen del cambio. -->

## Por qué

<!-- Problema que resuelve. Enlazá el issue: Closes #… -->

## Cómo lo probaste

<!-- Comandos, pruebas en la maqueta, resultados. -->

## Checklist

- [ ] Todos los commits están firmados (`git commit -s`).
- [ ] Si hay código: `ruff check .`, `ruff format --check .` y `pytest` pasan.
- [ ] Si cambia la especificación: hay un issue de propuesta aprobado por el comité técnico, y este PR actualiza juntos la especificación, el esquema, los ejemplos y `especificacion/CHANGELOG.md`.
- [ ] Si hay scripts o reglas de RouterOS: el PR explica qué hace cada bloque, cómo probarlo en la maqueta y cómo revertirlo.

## Líneas rojas y privacidad

- [ ] No hay malware, exploits ni herramientas ofensivas. Las anomalías de prueba son sintéticas y van contra destinos propios.
- [ ] No hay capturas, logs crudos, direcciones MAC completas, números de serie, cuentas, la IP pública de un laboratorio ni credenciales.
- [ ] Si hay una exportación de RouterOS (`/export`), la revisé a mano y reemplacé las MAC y la IP de la WAN por valores ficticios.
