# Colector IPFIX

Recibe los flujos IPFIX que exporta el router del laboratorio y los guarda como JSON, un archivo por hora, en un volumen local. Con esos archivos se calculan las métricas por estado de cada dispositivo (sección 6 del [plan del prototipo](../../docs/plan-prototipo.md)).

Es una imagen de Docker: [GoFlow2](https://github.com/netsampler/goflow2) v2.2.7 más un supervisor en Python que escribe los archivos. El diseño está en [`docs/disenos/2026-11-12-colector-ipfix.md`](../../docs/disenos/2026-11-12-colector-ipfix.md).

## Requisitos

En el host solo hace falta **Docker Engine con el plugin de Compose**. No se instala nada más.

La imagen se publica para `linux/amd64` y `linux/arm64` (Raspberry Pi 5).

## Levantarlo

```bash
cd laboratorio/colector
docker compose up -d            # con la imagen publicada
docker compose up -d --build    # construyéndola en el equipo (antes de la primera versión publicada)
```

Después, el router tiene que exportar IPFIX a la IP del equipo, puerto UDP 2055. **Antes de configurarlo, revisá que la versión del router esté en la [tabla de compatibilidad](#compatibilidad-con-routers):** con algunas versiones se pierde una parte grande de los flujos.

En RouterOS (los mismos comandos en 6.49 y en v7; ver la sección 4 del plan):

```routeros
# Valores de version: 1, 5, 9 o ipfix
/ip traffic-flow set enabled=yes active-flow-timeout=1m inactive-flow-timeout=15s
/ip traffic-flow target add dst-address=<IP del colector> port=2055 version=ipfix
```

## Compatibilidad con routers

El colector depende mucho de cómo cada router arma las plantillas de IPFIX. GoFlow2 descarta el paquete UDP **entero** cuando uno de sus conjuntos de datos usa una plantilla que nunca recibió, y con eso caen también los flujos buenos que viajaban en el mismo paquete. Por eso cada combinación de router y versión se prueba antes de usarla.

| Router | Versión | Resultado | Fecha | Qué se vio |
|---|---|---|---|---|
| MikroTik hEX RB750Gr3 | RouterOS 6.49.3 (stable) | ❌ **No funciona** | 2026-11-16 | Manda conjuntos de datos con la plantilla 260 (eventos de NAT) y nunca la anuncia, aunque `nat-events=no`. GoFlow2 descartó el 34 % de los paquetes; en la ventana de un diagnóstico aparte, el 41 %. |
| MikroTik hEX RB750Gr3 | RouterOS 6.49.23 (stable) | ✅ **Funciona** | 2026-11-16 | Anuncia las plantillas 258 (IPv4, 37 campos, con NAT 225 a 228 y las cuatro MAC) y 259 (IPv6, 34 campos, con las cuatro MAC y sin NAT), en el dominio de observación 0. Cero `template_not_found` en 300 s, sobre 624 paquetes. |
| MikroTik hEX RB750Gr3 | RouterOS v7 | ⏳ Sin probar | — | Es la versión de la maqueta. Se prueba en la fase 1 del plan. |

Configuración probada en los dos casos: `version=ipfix`, `active-flow-timeout=1m`, `inactive-flow-timeout=15s`, `v9-template-refresh=20`, `v9-template-timeout=30m` y `nat-events=no` (el valor por defecto).

**Versión mínima de RouterOS: 6.49.4 en la rama 6.** El changelog de la 6.49.4 incluye el arreglo: "traffic-flow - do not handle NAT events when nat-events is disabled". Para la rama 7, el hilo del foro de MikroTik indica que el arreglo entró en la 7.2; no lo verificamos en el changelog, y la v7 se valida en la maqueta. Actualizar a la última 6.49 también cierra la CVE-2023-30799, corregida en la 6.49.7.

Fuentes: [changelog de RouterOS 6.49.x](https://mikrotik.wiki/wiki/MikroTik_RouterOS_6.49.x_(Stable)), [hilo del foro sobre `nat-events`](https://forum.mikrotik.com/t/what-does-nat-events-yes-do-in-ip-traffic-flow-ipfix/155568), [aviso de MikroTik sobre la CVE-2023-30799](https://mikrotik.com/supportsec/cve-2023-30799).

### Probar un router nuevo

1. Levantá el colector y apuntá el router al puerto 2055.
2. Esperá al menos dos minutos y corré `docker compose exec colector python -m colector.templates`. La última línea dice cuántos paquetes recibió GoFlow2 y cuántos descartó por falta de plantilla desde que arrancó.
3. Dejalo andar una hora. El contenedor tiene que seguir `healthy` y en los logs no tiene que aparecer `goflow2 dropped … data sets whose template the exporter never sent`.
4. Revisá en el diagnóstico de plantillas que vengan los campos de NAT y de MAC (ver más abajo).
5. Abrí un PR que sume una fila a esta tabla con el modelo, la versión, la fecha, la configuración y lo que viste, funcione o no. Una versión que no funciona también es un dato útil.

### Pérdida esperable al arrancar

Cuando el colector arranca o se reinicia, GoFlow2 no tiene plantillas hasta que el router las vuelve a mandar. En RouterOS eso pasa cada `v9-template-refresh` paquetes o cada `v9-template-timeout`, lo que ocurra primero. Los datos que llegan antes se descartan. Un diagnóstico contra el hEX, que también arranca sin plantillas, perdió 7 conjuntos, todos de los primeros 10 s más o menos; falta medirlo reiniciando el colector. El supervisor no da alarma en el primer intervalo después de arrancar GoFlow2; solo lo registra en el log.

## Configuración

Por variables de entorno, en un `.env` junto al `compose.yaml` (ver [`.env.example`](.env.example)). Todas son opcionales.

| Variable | Por defecto | Qué hace |
|---|---|---|
| `LISTEN_PORT` | `2055` | Puerto UDP de escucha (IPFIX, NetFlow v9 y v5) |
| `RETENTION_DAYS` | `90` | Días que se guardan los archivos cerrados |
| `MIN_FREE_GB` | `5` | Piso de espacio libre. Si se perfora, se borran los archivos más viejos; si aun así no alcanza, se deja de escribir y el contenedor queda `unhealthy` |
| `FLUSH_SECONDS` | `5` | Cada cuánto se bajan los datos a disco: es lo máximo que se pierde ante un corte de luz |
| `MAX_DROP_PERCENT` | `1` | Porcentaje máximo de paquetes que GoFlow2 puede descartar por falta de plantilla entre dos chequeos (cada 60 s). Si se supera, el contenedor queda `unhealthy` |
| `GOFLOW2_EXTRA_ARGS` | vacío | Opciones adicionales para GoFlow2, para casos especiales |

## Verificar que funciona

```bash
docker compose ps                 # el estado tiene que pasar a "healthy"
docker compose logs --tail 50     # arranque de GoFlow2 y avisos del supervisor

# Qué plantillas mandó el router, qué campos trae cada una y cuántos paquetes se
# descartaron (sin mostrar flujos)
docker compose exec colector python -m colector.templates

# El último flujo guardado
docker compose exec colector sh -c 'tail -n 1 /datos/flujos/*/*/*/*.jsonl'
```

El contenedor queda `unhealthy` si pasa cualquiera de estas cosas:
- el supervisor dejó de dar señales de vida hace más de 2 minutos;
- GoFlow2 no está corriendo;
- no hay espacio libre suficiente, o falló la escritura en el volumen;
- GoFlow2 descartó más de `MAX_DROP_PERCENT` de los paquetes en el último intervalo.

El aviso `dropped N non-JSON lines from goflow2` no deja el contenedor `unhealthy`, pero son flujos que no se guardaron. Desde la 0.1.1 no debería aparecer; si aparece, ver "Un solo worker de GoFlow2" en [Mantenimiento](#mantenimiento).

En el diagnóstico de plantillas, revisá tres líneas:
- `NAT elements (225-228)`: si el router manda los campos de NAT, que hacen falta para atribuir los flujos de bajada.
- `MAC elements (56, 80, 81, 57)`: qué campos de MAC manda el router. Ver [Las MAC](#las-mac).
- La última, `GoFlow2: N packets received, M dropped for a missing template`: los totales desde que arrancó GoFlow2. Si M crece después de los primeros minutos, el router manda datos con una plantilla que no anuncia (ver la [tabla de compatibilidad](#compatibilidad-con-routers)).

Las métricas de GoFlow2 llevan el prefijo `goflow2_`. Las que usa el supervisor son `goflow2_flow_traffic_packets_total` y `goflow2_flow_process_nf_errors_total{error="template_not_found"}`. Para verlas:

```bash
docker compose exec colector python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/metrics').read().decode())" | grep -E '^goflow2_flow_(traffic_packets|process_nf_errors)_total'
```

En los flujos, `sampler_address` tiene que traer la IP del router. Si aparece la IP del bridge de Docker, hay que pasar el servicio a `network_mode: host`.

## Los datos

- **Ubicación:** volumen con nombre `huellaip-flujos`, montado en `/datos`.
- **Organización:** `/datos/flujos/AAAA/MM/DD/AAAA-MM-DDTHH.jsonl`, en UTC. Al cambiar la hora, el archivo se cierra y se comprime a `.jsonl.gz`. Si un archivo comprimido ya existe (por ejemplo, después de una corrección de hora), el nuevo lleva un sufijo numérico (`…THH.1.jsonl.gz`) y nunca pisa al anterior.
- **Reinicios:** al arrancar se comprimen los archivos de horas pasadas que hayan quedado abiertos. El de la hora en curso se sigue escribiendo a continuación.
- **Formato:** cada línea es el JSON de GoFlow2 sin cambios, más los campos de NAT y de MAC que agrega [`mapping.yaml`](mapping.yaml). Una línea recortada de un flujo de subida, con valores ficticios:

```json
{
  "type": "IPFIX",
  "time_received_ns": 1794850616410519881,
  "sampler_address": "10.77.0.1",
  "time_flow_start_ns": 1794850615410000000,
  "time_flow_end_ns": 1794850616410000000,
  "bytes": 1234,
  "packets": 10,
  "src_addr": "10.77.10.11",
  "dst_addr": "192.0.2.10",
  "proto": "TCP",
  "src_port": 40000,
  "dst_port": 443,
  "in_if": 0,
  "out_if": 0,
  "src_mac": "02:00:00:00:00:02",
  "dst_mac": "02:00:00:00:00:12",
  "post_nat_src_addr": "198.51.100.7",
  "post_nat_dst_addr": "192.0.2.10",
  "post_napt_src_port": 50000,
  "post_napt_dst_port": 443,
  "in_src_mac": "02:00:00:00:00:11",
  "in_dst_mac": "02:00:00:00:00:01",
  "out_src_mac": "02:00:00:00:00:02",
  "out_dst_mac": "02:00:00:00:00:12"
}
```

### Las MAC

El hEX manda las cuatro MAC de cada flujo: las de la trama que entra al router y las de la que sale. El colector las guarda por separado:

| Campo | Elemento IPFIX | Qué es, en un flujo de subida |
|---|---|---|
| `in_src_mac` | 56 `sourceMacAddress` | La MAC del dispositivo |
| `in_dst_mac` | 80 `destinationMacAddress` | La MAC del router del lado de la LAN |
| `out_src_mac` | 81 `postSourceMacAddress` | La MAC del router del lado de la WAN |
| `out_dst_mac` | 57 `postDestinationMacAddress` | La MAC del equipo siguiente hacia internet |

En un flujo de bajada se invierte: la MAC del dispositivo queda en `out_dst_mac`, porque es el destino de la trama que sale hacia la LAN. **Para atribuir un flujo a un dispositivo, usá `in_src_mac` en la subida y `out_dst_mac` en la bajada.** La tabla sigue las definiciones de IANA; falta confirmarla con flujos reales del hEX.

GoFlow2 además junta cada par en `src_mac` y `dst_mac`, pero **esos dos campos no sirven para atribuir**. Cuando el router manda los dos elementos de un par, gana el que viene después en la plantilla, que en el hEX es el de salida. En el ejemplo, `src_mac` es la MAC de la WAN del router y no la del dispositivo.

- **Lectura con DuckDB:** DuckDB lee los archivos en curso y los comprimidos con un mismo patrón. La imagen de herramientas con DuckDB llega en un PR posterior.

```sql
SELECT src_addr, sum(bytes) AS bytes
FROM read_json_auto('/datos/flujos/**/*.jsonl*')
GROUP BY src_addr
ORDER BY bytes DESC;
```

## Privacidad

El volumen tiene MAC completas, IP privadas y destinos de los equipos de la red. **Nunca se sube ni se comparte.** El `.gitignore` del repo ignora cualquier carpeta `flujos/` como red de seguridad, pero el volumen vive fuera del repo.

## Seguridad del contenedor

- Corre con el usuario sin privilegios 10001.
- El sistema de archivos raíz es de solo lectura, y `/tmp` vive en memoria.
- Sin capacidades (`cap_drop: ALL`) y con `no-new-privileges`.
- Solo se publica el puerto 2055/udp. El servidor HTTP interno de GoFlow2 (puerto 8080, métricas y plantillas) no se publica.
- Los logs de Docker tienen tope: 3 archivos de 10 MB.
- El colector acepta IPFIX de cualquier origen. Para descartar lo que no venga del router, se filtra por `sampler_address` al analizar.

## Mantenimiento

**Actualizar GoFlow2.** GoFlow2 sale de los binarios del release, fijados por SHA-256. Para cambiar de versión:
1. Cambiar `GOFLOW2_VERSION` y los dos checksums en el `Dockerfile`, y el checksum de amd64 en `.github/workflows/colector.yml`.
2. Revisar la lista de campos de `mapping.yaml` contra lo que la versión nueva imprime por defecto.
3. Revisar si sigue haciendo falta un solo worker (ver abajo).

**Un solo worker de GoFlow2.** El supervisor arranca GoFlow2 con `-listen netflow://:2055?workers=1`. GoFlow2 v2.2.7 escribe cada JSON y su salto de línea en dos escrituras separadas, y con dos workers (su valor por defecto) a veces quedan dos flujos pegados en una línea y una línea vacía. El supervisor las descarta y lo avisa con `dropped N non-JSON lines from goflow2`: en el staging se perdían unos 55 flujos por hora, el 0,08 %. Un worker alcanza para un laboratorio, que exporta decenas de flujos por segundo. La prueba `test_goflow2_writes_one_flow_per_line_under_concurrent_load` manda ráfagas en paralelo y falla si vuelve a pasar; sirve para decidir si una versión nueva de GoFlow2 admite más workers.

Un cambio de versión de GoFlow2 se revisa como un cambio de formato. Dependabot actualiza la imagen base y las acciones del CI, pero no GoFlow2.

**Publicar una versión** (mantenedor):
1. Subir la versión en la etiqueta `org.opencontainers.image.version` del `Dockerfile` y en la imagen de `compose.yaml`.
2. Integrar el PR.
3. Crear la etiqueta `colector-vX.Y.Z` sobre `main`.

El CI construye en amd64 y arm64, publica `ghcr.io/huellaip/colector:X.Y.Z` y `:X.Y`, y adjunta la procedencia y el SBOM. La primera vez, la imagen queda privada en GHCR: hay que hacerla pública desde la organización.

## Desarrollo

```bash
cd laboratorio/colector
python -m pip install ruff==0.16.9 pytest==9.1.1
ruff check . && ruff format --check .
python -m pytest                       # pruebas unitarias
GOFLOW2_BIN=/ruta/a/goflow2 python -m pytest   # suma la prueba con GoFlow2 real
```

La prueba del contenedor (`tests/integration/test_container.py`) corre donde haya un daemon de Docker, como en el CI.
