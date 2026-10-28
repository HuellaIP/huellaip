# Formato de huella, versión 0.1.0

> **Estado: borrador.** Esta versión todavía no está publicada. Puede cambiar hasta que se publique la 0.1.0, prevista para el cierre del prototipo. Los cambios quedan en el [registro de cambios](CHANGELOG.md).

Una **huella** describe el comportamiento de red normal de un dispositivo, con un modelo y un firmware concretos: con quién habla, cuántas sesiones abre, cuánto tráfico mueve y a qué ritmo, en cada estado de uso.

| Archivo | Qué es |
|---|---|
| Este documento | La especificación en prosa |
| [`esquema/huella-v0.schema.json`](esquema/huella-v0.schema.json) | El esquema JSON (draft 2020-12), que valida la estructura |
| [`ejemplos/`](ejemplos/) | Dos ejemplos válidos y dos inválidos |

Si este documento y el esquema dicen cosas distintas en algo estructural, manda el esquema, y la diferencia se corrige como un error.

## 1. Principios

- **Un archivo MUD válido.** Cada huella es un archivo MUD ([RFC 8520](https://www.rfc-editor.org/info/rfc8520)), así que cualquier herramienta que entienda MUD puede leer los destinos permitidos.
- **Estándares antes que formato propio.** Lo que MUD o sus extensiones publicadas pueden expresar se expresa ahí. La extensión propia, `huellaip-perfil`, lleva solo lo que el estándar no cubre: las métricas por estado de uso.
- **Solo metadatos.** Destinos, puertos, sesiones, volúmenes, tiempos, nombres DNS y parámetros de TLS. Nunca contenido ni identificadores personales.
- **Observado, no declarado.** MUD nació para que el fabricante declare lo que su equipo debería hacer. Una huella, en cambio, registra lo que se midió. Por eso cada huella dice quién la midió, cuándo y con qué confianza.

## 2. Estructura del archivo

Una huella es un objeto JSON codificado según el [RFC 7951](https://www.rfc-editor.org/info/rfc7951), con dos miembros:

```text
{
  "ietf-mud:mud": {                         ← contenedor MUD (RFC 8520)
    mud-version, mud-url, last-update, …    ← cabecera MUD (sección 3)
    from-device-policy, to-device-policy    ← nombres de las ACL
    "huellaip-perfil:perfil": { … }         ← extensión propia (sección 5)
  },
  "ietf-access-control-list:acls": {        ← listas de acceso (sección 4)
    "acl": [ "desde-dispositivo", "hacia-dispositivo" ]
  }
}
```

La extensión va **dentro** del contenedor `ietf-mud:mud`. Así define el RFC 8520 las extensiones: como un `augment` del modelo MUD. En JSON, eso se escribe con el prefijo del módulo, `huellaip-perfil:perfil`, igual que en el ejemplo `ietf-mud-detext-example` del propio RFC.

Las claves de la extensión van en castellano, sin tildes y con guiones (`sesiones-concurrentes`), que es la convención de los modelos YANG y de MUD.

## 3. Cabecera MUD

| Campo | Obligatorio | Valor en una huella |
|---|---|---|
| `mud-version` | Sí | `1` |
| `mud-url` | Sí | `https://huellaip.github.io/huellas/<categoria>/<fabricante>/<modelo>/<firmware>.json`, con la misma normalización que la ruta del archivo en `huellaip/huellas` (ver [R3](#7-reglas-que-verifica-el-validador)) |
| `last-update` | Sí | Fecha y hora de la última modificación de la huella, con zona horaria |
| `cache-validity` | No | Horas, de 1 a 168. Recomendado: `48`, el valor por defecto de MUD |
| `is-supported` | Sí | `true`, salvo que se sepa que el fabricante dejó de dar soporte o que el equipo es genérico sin soporte: en esos casos, `false` |
| `systeminfo` | Sí | Descripción breve para personas |
| `mfg-name`, `model-name`, `firmware-rev` | Sí | Fabricante, modelo y firmware, como los informa el equipo. Para equipos sin marca clara, `mfg-name` es `Genérico` |
| `documentation` | No | Enlace a la huella o al repositorio |
| `extensions` | Sí | Incluye `huellaip-perfil`. Si alguna ACL tiene perfiles TLS (sección 4.3), incluye también `ietf-mud-tls` |
| `ietf-mud-tls:is-tls-dtls-profile-supported` | No | `true` si alguna ACL tiene perfiles TLS |
| `from-device-policy`, `to-device-policy` | Sí | Apuntan a las ACL `desde-dispositivo` y `hacia-dispositivo` |
| `mud-signature` | No | En v0 las huellas no se firman |

**La `mud-url` en v0.** Es una dirección estable, reservada en las páginas de GitHub de la organización. Todavía no se sirve: la publicación de las huellas en esa dirección llega con la versión 0.1.0.

## 4. Listas de acceso (ACL)

### 4.1 Dos listas por huella

- **`desde-dispositivo`**: el tráfico que sale del equipo. Los destinos van en `ietf-acldns:dst-dnsname`.
- **`hacia-dispositivo`**: el tráfico que entra al equipo. Los orígenes van en `ietf-acldns:src-dnsname`.

En v0, las dos son de tipo `ipv4-acl-type`, porque el laboratorio mide solo IPv4.

### 4.2 Cada regla (ACE)

- **Coincidencia:** `ipv4` con el protocolo (`6` para TCP, `17` para UDP) y el nombre DNS, más `tcp` o `udp` con el puerto. En TCP se indica quién inicia la conexión con `ietf-mud:direction-initiated`.
- **Acción:** `accept` para el tráfico normal. En huellas `sospechoso` o `malicioso`, el tráfico ligado al indicador de compromiso va con **`drop`**. Ejemplos: un dominio de comando y control, o conexiones salientes a los puertos 22 y 23. Así la misma huella sirve para alertar.
- **Nombres DNS exactos.** El tipo `inet:host` de MUD no admite comodines. Los destinos con comodín (sección 5.4) van solo en la extensión y no tienen regla en la ACL.
- **Sin redes privadas.** Si una regla usa una red IP en lugar de un nombre, no puede ser privada, compartida, de loopback ni de enlace local.

### 4.3 Versión de TLS en las ACL

Cuando el tráfico a un destino usa TLS, la regla puede llevar el perfil del [RFC 9761](https://www.rfc-editor.org/info/rfc9761), en `ietf-acl-tls:client-profiles`, con las versiones observadas en `supported-tls-version`:

```json
"ietf-acl-tls:client-profiles": {
  "tls-dtls-profile": [{ "name": "observado", "supported-tls-version": ["tls12"] }]
}
```

El RFC 9761 solo admite `tls12` y `tls13`. Si un equipo usa TLS 1.0 o 1.1, eso queda registrado en la extensión (`versiones-tls`), donde además es una señal en sí misma.

## 5. Extensión `huellaip-perfil:perfil`

### 5.1 Campos generales

| Campo | Obligatorio | Contenido |
|---|---|---|
| `version-formato` | Sí | Versión de esta especificación contra la que se validó la huella, por ejemplo `0.1.0` |
| `categoria` | Sí | `televisor`, `streaming`, `tv-box`, `camara`, `impresora`, `router`, `asistente`, `enchufe` o `electrodomestico` |
| `etiqueta` | Sí | `benigno`, `sospechoso` o `malicioso` (sección 6) |
| `fuentes-ioc` | Si la etiqueta es `malicioso` | Enlaces HTTPS a los informes que documentan el indicador de compromiso |
| `observaciones` | Si la etiqueta es `sospechoso` | Texto breve con lo observado, solo con metadatos agregados |
| `identificacion.oui` | No | Los tres primeros bytes de la MAC, en mayúsculas (`00:00:5E`). **Nunca la MAC completa** |
| `captura` | Sí | Ver 5.2 |
| `estados` | Sí | Al menos un estado (5.3) |
| `estados-omitidos` | Si falta algún estado | Lista de `{ "estado", "motivo" }` |
| `licencia` | Sí | `CC-BY-4.0` |

### 5.2 Captura

| Campo | Obligatorio | Contenido |
|---|---|---|
| `pais` | Sí | Código ISO 3166-1 de dos letras del lugar de la captura |
| `fecha-inicio`, `fecha-fin` | Sí | Fechas de la captura (`AAAA-MM-DD`) |
| `aportante` | Sí | Quién aporta la huella: una organización o una persona, como quiere que se la atribuya |
| `confianza` | Sí | `baja`, `media` o `alta` (sección 6) |
| `fuente-asn` | No | La base IP a ASN que se usó, con su fecha |

### 5.3 Estados de uso

| Estado | Definición | Captura mínima para confianza `media` |
|---|---|---|
| `encendido` | Desde que el equipo se energiza hasta que se estabiliza | 5 ciclos de 15 minutos |
| `reposo` | Encendido, sin interacción humana | 72 horas continuas (4320 minutos) |
| `activo` | Uso típico: streaming, impresión, video de una cámara | 3 sesiones de 30 a 60 minutos |
| `interaccion` | Control desde la app del fabricante | 3 sesiones de 10 minutos |

Cada estado capturado se describe por separado. Si un estado no se capturó, va en `estados-omitidos` con el motivo. Por ejemplo, un equipo sin app no tiene `interaccion`, y un equipo en cuarentena no se usa.

### 5.4 Métricas de cada estado

| Campo | Obligatorio | Unidad | Cómo se calcula |
|---|---|---|---|
| `muestra.sesiones` | Sí | Cantidad | Sesiones de captura de ese estado |
| `muestra.minutos` | Sí | Minutos | Duración total capturada del estado |
| `sesiones-concurrentes.p50`, `.p95`, `.max` | Sí | Sesiones | Conexiones abiertas al mismo tiempo, muestreadas cada 30 segundos a partir del inicio y la duración de cada conexión. Percentiles sobre las muestras del estado; `max` es el máximo observado |
| `bytes-subida-hora-p95`, `bytes-bajada-hora-p95` | Sí | Bytes por hora | Bytes por ventana de una hora, percentil 95 sobre las ventanas del estado. En estados de menos de una hora, tasa por hora de cada sesión (bytes ÷ duración × 3600) y percentil 95 sobre las sesiones |
| `conexiones-nuevas-min-p95` | Sí | Conexiones por minuto | Inicios de conexión por minuto, percentil 95 sobre los minutos del estado |
| `keepalive-segundos` | No | Segundos | Intervalo dominante entre conexiones repetidas al mismo destino. Se omite si no hay un patrón |
| `destinos` | Sí | — | Nombres DNS consultados y SNI observados, en minúsculas y sin punto final. Puede estar vacía |
| `asn-esperados` | Sí | — | Sistemas autónomos de las IP de destino, según `captura.fuente-asn`. Puede estar vacía |
| `versiones-tls` | No | — | Versiones de TLS observadas: `tls10`, `tls11`, `tls12` o `tls13` |

**Destinos con comodín.** Algunos servicios usan un subdominio distinto por equipo, por ejemplo `a1b2c3.dispositivos.fabricante.com`. Ese subdominio identifica al equipo, así que no se publica tal cual: se reemplaza por un comodín en la etiqueta de más a la izquierda, `*.dispositivos.fabricante.com`. El comodín se admite solo en `destinos` de la extensión.

Los métodos de cálculo vienen de la sección 6.3 del plan del prototipo. Los va a fijar la metodología de captura (`docs/metodologia-captura.md`). Si difieren, manda la metodología, y esta tabla se actualiza.

## 6. Etiqueta y nivel de confianza

| Etiqueta | Significado | Requisito |
|---|---|---|
| `benigno` | No se observó nada que su categoría no haga normalmente | — |
| `sospechoso` | Comportamiento anómalo para su categoría, sin un IOC confirmado | `observaciones` |
| `malicioso` | El comportamiento coincide con un indicador de compromiso documentado | `fuentes-ioc` |

La etiqueta describe lo observado en ese modelo con ese firmware. No es un juicio sobre la marca.

| Confianza | Criterio |
|---|---|
| `baja` | Al menos una sesión por estado capturado, en un solo laboratorio |
| `media` | Las capturas mínimas de la tabla 5.3 para cada estado capturado |
| `alta` | Nivel `media` más una réplica en un segundo laboratorio o con datos de un ISP. La réplica no se ve en el archivo: la verifica la revisión |

## 7. Reglas que verifica el validador

El esquema JSON valida la estructura. Estas reglas cruzan campos y las verifica el validador del proyecto:

| Regla | Qué verifica |
|---|---|
| **R1** | En cada estado, `p50 ≤ p95 ≤ max` |
| **R2** | Cada uno de los cuatro estados aparece una sola vez, en `estados` o en `estados-omitidos` |
| **R3** | La `mud-url` termina en `<categoria>/<fabricante>/<modelo>/<firmware>.json`, normalizados como en `huellaip/huellas`: minúsculas, sin tildes, y cualquier carácter que no sea letra, número, punto o guion reemplazado por un guion. En `huellaip/huellas`, la ruta del archivo es `huellas/` más ese mismo camino |
| **R4** | Los destinos exactos de todos los estados coinciden con los nombres DNS de las ACL: cada destino tiene al menos una regla, y cada regla con nombre DNS corresponde a un destino observado |
| **R5** | Las ACL no usan redes privadas (10/8, 172.16/12, 192.168/16), compartidas (100.64/10), de loopback (127/8) ni de enlace local (169.254/16) |
| **R6** | `fecha-inicio ≤ fecha-fin ≤` la fecha de `last-update` |
| **R7** | La muestra de cada estado alcanza el mínimo de su nivel de confianza (sección 6) |
| **R8** | Las versiones de TLS de las ACL figuran entre las `versiones-tls` observadas |
| **R9** | `from-device-policy` y `to-device-policy` apuntan a ACL que existen, y no hay ACL sin usar |
| **R10** | Si alguna ACL tiene perfiles TLS, `extensions` incluye `ietf-mud-tls` |

## 8. Privacidad

Una huella nunca tiene:

- contenido de las comunicaciones (URLs completas, cuerpos, consultas);
- direcciones MAC completas: como mucho, el OUI;
- números de serie, IMEI ni identificadores únicos del equipo, tampoco dentro de un nombre DNS (para eso está el comodín);
- cuentas, correos ni otros identificadores personales;
- direcciones IP privadas, ni la IP pública del laboratorio o de quien aporta.

El esquema bloquea algunos casos: MAC completas en `oui`, direcciones IP en `destinos` y campos desconocidos. El resto lo controlan el validador y la revisión.

## 9. Versionado y compatibilidad

- `version-formato` sigue el [versionado semántico](https://semver.org/lang/es/). Mientras el formato esté en 0.x, un cambio incompatible sube el número menor y uno compatible, el de parche.
- La extensión no admite campos desconocidos. Un campo nuevo es un cambio de formato y sigue el [proceso de cambios a la especificación](../CONTRIBUTING.md#cambios-a-la-especificación).

## 10. Diferencias con MUD y puntos abiertos

- **Registro de la extensión.** El RFC 8520 pide que cada nombre de extensión esté registrado en la IANA y descripto en un RFC. `huellaip-perfil` no lo está: es parte del trabajo previo a llevar la extensión a la IETF, junto con un módulo YANG formal.
- **Huellas de terceros.** MUD supone que el archivo lo publica el fabricante. Las huellas las mide y publica la comunidad.
- **`ietf-mud-tls`.** El uso de `ietf-mud-tls` y de `is-tls-dtls-profile-supported` sigue los módulos YANG del RFC 9761. Falta contrastarlo con el texto del RFC antes de publicar la 0.1.0.
- **IPv6, firma de huellas (`mud-signature`) y publicación en la `mud-url`.** Quedan para versiones posteriores.

## 11. Cambios respecto del borrador del pitch

| Borrador (Anexo B del pitch) | v0 |
|---|---|
| `huellaip-perfil` en la raíz del JSON | `huellaip-perfil:perfil` dentro de `ietf-mud:mud` |
| Claves con guiones bajos (`sesiones_concurrentes`) | Claves con guiones (`sesiones-concurrentes`) |
| `captura.contribuyente` | `captura.aportante` |
| `captura.fecha` | `captura.fecha-inicio` y `captura.fecha-fin` |
| `tls_version` por estado | `versiones-tls` por estado, más los perfiles TLS del RFC 9761 en las ACL |
| — | `categoria`, `muestra`, `estados-omitidos`, `fuentes-ioc`, `observaciones`, `identificacion.oui`, `captura.fuente-asn` |
| Destinos solo exactos | Comodín en la etiqueta de más a la izquierda, solo en la extensión |
