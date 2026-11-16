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

Después, el router tiene que exportar IPFIX a la IP del equipo, puerto UDP 2055. En RouterOS v7 (ver la sección 4 del plan):

```routeros
# Valores de version: 1, 5, 9 o ipfix
/ip traffic-flow set enabled=yes active-flow-timeout=1m inactive-flow-timeout=15s
/ip traffic-flow target add dst-address=<IP del colector> port=2055 version=ipfix
```

## Configuración

Por variables de entorno, en un `.env` junto al `compose.yaml` (ver [`.env.example`](.env.example)). Todas son opcionales.

| Variable | Por defecto | Qué hace |
|---|---|---|
| `LISTEN_PORT` | `2055` | Puerto UDP de escucha (IPFIX, NetFlow v9 y v5) |
| `RETENTION_DAYS` | `90` | Días que se guardan los archivos cerrados |
| `MIN_FREE_GB` | `5` | Piso de espacio libre. Si se perfora, se borran los archivos más viejos; si aun así no alcanza, se deja de escribir y el contenedor queda `unhealthy` |
| `FLUSH_SECONDS` | `5` | Cada cuánto se bajan los datos a disco: es lo máximo que se pierde ante un corte de luz |
| `GOFLOW2_EXTRA_ARGS` | vacío | Opciones adicionales para GoFlow2, para casos especiales |

## Verificar que funciona

```bash
docker compose ps                 # el estado tiene que pasar a "healthy"
docker compose logs --tail 50     # arranque de GoFlow2 y avisos del supervisor

# Qué plantillas mandó el router y qué campos trae cada una (sin mostrar flujos)
docker compose exec colector python -m colector.templates

# El último flujo guardado
docker compose exec colector sh -c 'tail -n 1 /datos/flujos/*/*/*/*.jsonl'
```

En el diagnóstico de plantillas, revisá dos líneas:
- `NAT elements (225-228)`: si el router manda los campos de NAT, que hacen falta para atribuir los flujos de bajada.
- `Destination MAC element`: si la MAC de destino viene en el campo 80 o en el 57. GoFlow2 toma los dos.

En los flujos, `sampler_address` tiene que traer la IP del router. Si aparece la IP del bridge de Docker, hay que pasar el servicio a `network_mode: host`.

## Los datos

- **Ubicación:** volumen con nombre `huellaip-flujos`, montado en `/datos`.
- **Organización:** `/datos/flujos/AAAA/MM/DD/AAAA-MM-DDTHH.jsonl`, en UTC. Al cambiar la hora, el archivo se cierra y se comprime a `.jsonl.gz`. Si un archivo comprimido ya existe (por ejemplo, después de una corrección de hora), el nuevo lleva un sufijo numérico (`…THH.1.jsonl.gz`) y nunca pisa al anterior.
- **Reinicios:** al arrancar se comprimen los archivos de horas pasadas que hayan quedado abiertos. El de la hora en curso se sigue escribiendo a continuación.
- **Formato:** cada línea es el JSON de GoFlow2 sin cambios, más los campos de NAT que agrega [`mapping.yaml`](mapping.yaml). Una línea recortada, con valores ficticios:

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
  "src_mac": "02:00:00:00:00:11",
  "dst_mac": "02:00:00:00:00:01",
  "post_nat_src_addr": "198.51.100.7",
  "post_nat_dst_addr": "192.0.2.10",
  "post_napt_src_port": 50000,
  "post_napt_dst_port": 443
}
```

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
