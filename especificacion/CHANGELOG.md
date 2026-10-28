# Registro de cambios del formato de huella

Acá quedan todos los cambios de la especificación del formato de huella, de su esquema JSON y de sus ejemplos. Las huellas publicadas declaran en `version-formato` la versión contra la que se validaron.

- El formato usa [versionado semántico](https://semver.org/lang/es/). Mientras esté en 0.x, un cambio incompatible sube el número menor (0.1 → 0.2) y uno compatible, el de parche (0.1.0 → 0.1.1).
- Cada cambio llega por el proceso de [cambios a la especificación](../CONTRIBUTING.md#cambios-a-la-especificación): un issue de propuesta, al menos 14 días de discusión y la decisión del comité técnico.
- El PR que implementa un cambio actualiza en un solo paso la especificación, el esquema, los ejemplos y este registro.
- La estructura del registro sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Agregado

- Este registro de cambios.
- Borrador de la especificación del formato 0.1.0 (`formato-huella-v0.md`), con su esquema JSON (`esquema/huella-v0.schema.json`), dos ejemplos válidos y dos inválidos.

### Cambiado respecto del borrador del pitch

- La extensión pasa a `huellaip-perfil:perfil`, dentro de `ietf-mud:mud`, como define el RFC 8520 para las extensiones.
- Las claves de la extensión se escriben con guiones (`sesiones-concurrentes`).
- `captura.contribuyente` pasa a `captura.aportante`.
- `captura.fecha` se divide en `fecha-inicio` y `fecha-fin`.
- `tls_version` pasa a `versiones-tls` por estado, y se suman los perfiles TLS del RFC 9761 en las ACL.
- Se agregan `categoria`, `muestra`, `estados-omitidos`, `fuentes-ioc`, `observaciones`, `identificacion.oui` y `captura.fuente-asn`.
- Se admite un comodín en la etiqueta de más a la izquierda de los destinos, solo en la extensión.

<!--
Plantilla para cada versión:

## [0.1.0] - AAAA-MM-DD

### Agregado
### Cambiado
### Obsoleto
### Eliminado
### Corregido

Cada entrada enlaza el issue de propuesta y el PR que la implementa.
-->
