# Colector IPFIX: plan de implementación

> **Para agentes:** sub-skill requerido: superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans, tarea por tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** construir la imagen `ghcr.io/huellaip/colector` v0.1.0. La imagen recibe IPFIX por UDP 2055 y deja un archivo JSON por hora, comprimido al cerrarse, en un volumen local.

**Arquitectura:**
- Un supervisor en Python, solo con la biblioteca estándar, arranca GoFlow2 v2.2.7 como proceso hijo y lee su stdout línea por línea.
- El supervisor es el único que escribe archivos: rota por hora en UTC, comprime con gzip, aplica la retención y el piso de espacio libre, y publica un latido que usa el healthcheck.
- La imagen se construye en el CI de forma nativa para amd64 y arm64, y se publica en GHCR al crear una etiqueta `colector-v*`.

**Tecnologías:** Python 3 (biblioteca estándar), GoFlow2 v2.2.7, Docker y Compose, pytest, ruff, GitHub Actions.

**Diseño:** [`docs/disenos/2026-11-12-colector-ipfix.md`](2026-11-12-colector-ipfix.md)

## Restricciones globales

Valen para todas las tareas:
- En el host solo se usa Docker. No se instala nada más.
- Arquitecturas: `linux/arm64` y `linux/amd64`.
- Código, comentarios, nombres y mensajes de commit en inglés. Documentación en castellano.
- GoFlow2 v2.2.7, fijado por digest. Imagen base oficial de Python 3 slim, versión estable vigente, fijada por digest. Nunca `latest`.
- Variables de entorno y sus valores por defecto:

  | Variable | Por defecto |
  |---|---|
  | `LISTEN_PORT` | `2055` |
  | `RETENTION_DAYS` | `90` |
  | `MIN_FREE_GB` | `5` |
  | `FLUSH_SECONDS` | `5` |
  | `GOFLOW2_EXTRA_ARGS` | vacío |

- Ruta de los archivos: `/datos/flujos/AAAA/MM/DD/AAAA-MM-DDTHH.jsonl`, en UTC. El archivo cerrado termina en `.jsonl.gz`.
- Contenedor:
  - UID fijo 10001, sin privilegios;
  - sistema de archivos raíz de solo lectura y `/tmp` en memoria;
  - `cap_drop: ALL` y `no-new-privileges`;
  - solo el puerto 2055/udp publicado;
  - volumen con nombre `huellaip-flujos` montado en `/datos`.
- Cinco caídas seguidas de GoFlow2 hacen que el supervisor salga con código 1.
- Commits firmados con `git commit -s`. PR con la plantilla del repo.

## Fallas a vigilar en la revisión

Cada una tiene su prueba en la tarea que es dueña del código.

1. **Cambio de hora sin tráfico.** Si no llega ninguna línea, el archivo de la hora anterior igual se cierra y se comprime: el lazo principal despierta al menos una vez por segundo (tarea 2).
2. **Reinicio a mitad de hora.** Al arrancar se comprimen los `.jsonl` de horas pasadas. El de la hora en curso se sigue escribiendo a continuación, sin truncarlo (tarea 2).
3. **El reloj vuelve atrás (corrección de NTP).** Si el `.gz` de destino ya existe, se escribe uno con sufijo (`…THH.1.jsonl.gz`) y nunca se pisa el anterior (tarea 2).
4. **Líneas que no son JSON** (un mensaje de GoFlow2 por stdout, o una línea cortada cuando el proceso muere). Se descartan, se cuentan y se registran como máximo una vez por minuto (tarea 4).
5. **Disco lleno.** Se borran primero los archivos vencidos y después los más viejos. Si aun así no alcanza, se pausa la escritura y el healthcheck da `unhealthy`. El archivo de la hora en curso nunca se borra (tareas 3 y 5).

---

## Estructura de archivos

```text
laboratorio/colector/
├── Dockerfile
├── compose.yaml
├── .env.example
├── mapping.yaml
├── pyproject.toml            configuración de ruff y pytest; paquete colector
├── README.md
├── colector/
│   ├── __init__.py
│   ├── __main__.py           punto de entrada: python -m colector
│   ├── config.py             Config y load_config
│   ├── writer.py             HourlyWriter, hour_path, compress
│   ├── retention.py          prune
│   ├── process.py            Backoff, build_goflow2_command, run
│   └── health.py             beat, check y python -m colector.health
└── tests/
    ├── test_config.py
    ├── test_writer.py
    ├── test_retention.py
    ├── test_process.py
    ├── test_health.py
    ├── fake_goflow2.py       proceso falso para las pruebas de process
    └── integration/
        ├── ipfix_synth.py    arma mensajes IPFIX sintéticos (plantilla y datos)
        └── test_container.py
.github/workflows/colector.yml
.github/dependabot.yml
```

---

### Task 1: configuración

**Archivos:**
- Crear: `laboratorio/colector/pyproject.toml`
- Crear: `laboratorio/colector/colector/__init__.py`
- Crear: `laboratorio/colector/colector/config.py`
- Prueba: `laboratorio/colector/tests/test_config.py`

**Interfaces:**
- Produce:
  - `class ConfigError(ValueError)`;
  - `@dataclass(frozen=True) class Config`, con los campos:

    | Campo | Tipo | Por defecto |
    |---|---|---|
    | `listen_port` | `int` | `2055` |
    | `retention_days` | `int` | `90` |
    | `min_free_bytes` | `int` | `5 * 1024**3` |
    | `flush_seconds` | `float` | `5.0` |
    | `goflow2_extra_args` | `tuple[str, ...]` | `()` |
    | `data_dir` | `Path` | `Path("/datos/flujos")` |
    | `heartbeat_path` | `Path` | `Path("/tmp/colector-heartbeat.json")` |
    | `goflow2_path` | `Path` | `Path("/usr/local/bin/goflow2")` |
    | `mapping_path` | `Path` | `Path("/etc/colector/mapping.yaml")` |

  - `def load_config(env: Mapping[str, str]) -> Config`.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
def test_defaults():
    cfg = load_config({})
    assert cfg.listen_port == 2055
    assert cfg.retention_days == 90
    assert cfg.min_free_bytes == 5 * 1024**3
    assert cfg.flush_seconds == 5.0
    assert cfg.goflow2_extra_args == ()

def test_overrides():
    cfg = load_config({"LISTEN_PORT": "4739", "RETENTION_DAYS": "30", "MIN_FREE_GB": "2.5",
                       "FLUSH_SECONDS": "1", "GOFLOW2_EXTRA_ARGS": "-loglevel debug"})
    assert (cfg.listen_port, cfg.retention_days) == (4739, 30)
    assert cfg.min_free_bytes == int(2.5 * 1024**3)
    assert cfg.goflow2_extra_args == ("-loglevel", "debug")

@pytest.mark.parametrize("key,value", [("LISTEN_PORT", "0"), ("LISTEN_PORT", "70000"),
    ("RETENTION_DAYS", "0"), ("MIN_FREE_GB", "-1"), ("FLUSH_SECONDS", "abc")])
def test_invalid_values_raise(key, value):
    with pytest.raises(ConfigError, match=key):
        load_config({key: value})
```

- [ ] **Paso 2: correr las pruebas y ver que fallan.** `cd laboratorio/colector && python -m pytest tests/test_config.py -v`. Resultado esperado: FAIL por `ImportError`.
- [ ] **Paso 3: implementar `load_config`.** `GOFLOW2_EXTRA_ARGS` se divide con `shlex.split`. El mensaje de `ConfigError` nombra la variable. En `pyproject.toml`: el paquete `colector`, `requires-python` igual a la versión de la imagen base, ruff con la regla por defecto y el marcador de pytest `integration`.
- [ ] **Paso 4: correr las pruebas y ver que pasan.** El mismo comando. Resultado esperado: PASS.
- [ ] **Paso 5: commit.** `git add laboratorio/colector && git commit -s -m "Add collector configuration loading"`

---

### Task 2: archivos por hora

**Archivos:**
- Crear: `laboratorio/colector/colector/writer.py`
- Prueba: `laboratorio/colector/tests/test_writer.py`

**Interfaces:**
- Consume: nada de tareas anteriores.
- Produce:
  - `def hour_path(root: Path, ts: datetime) -> Path`. Devuelve `root/AAAA/MM/DD/AAAA-MM-DDTHH.jsonl`. Si `ts` no trae zona horaria, lanza `ValueError`.
  - `def compress(path: Path) -> Path`. Comprime a `.jsonl.gz` pasando por un archivo temporal y un rename atómico, y después borra el original. Si el destino ya existe, usa el sufijo `.1`, `.2`, etcétera.
  - `class HourlyWriter`, con:
    - `__init__(self, root: Path, clock: Callable[[], datetime], flush_seconds: float, monotonic: Callable[[], float] = time.monotonic)`;
    - `recover(self) -> list[Path]`: comprime los `.jsonl` de horas pasadas;
    - `write(self, line: bytes) -> None`;
    - `tick(self) -> None`: rota si cambió la hora y baja a disco si pasaron `flush_seconds`;
    - `close(self) -> None`: baja a disco y cierra, sin comprimir;
    - `paused: bool`: si es verdadero, `write` descarta la línea;
    - `dropped_lines: int`.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
UTC = timezone.utc

def test_hour_path_layout(tmp_path):
    ts = datetime(2026, 11, 13, 22, 5, tzinfo=UTC)
    assert hour_path(tmp_path, ts) == tmp_path / "2026/11/13/2026-11-13T22.jsonl"

def test_hour_path_rejects_naive(tmp_path):
    with pytest.raises(ValueError):
        hour_path(tmp_path, datetime(2026, 11, 13, 22))

def test_rotation_on_tick_without_traffic(tmp_path):
    clock = FakeClock(datetime(2026, 11, 13, 22, 59, 59, tzinfo=UTC))
    w = HourlyWriter(tmp_path, clock, flush_seconds=5)
    w.write(b'{"a":1}')
    clock.advance(seconds=2)          # 23:00:01, sin líneas nuevas
    w.tick()
    gz = tmp_path / "2026/11/13/2026-11-13T22.jsonl.gz"
    assert gz.exists() and gzip.decompress(gz.read_bytes()) == b'{"a":1}\n'
    assert not (tmp_path / "2026/11/13/2026-11-13T22.jsonl").exists()

def test_recover_compresses_past_hours_and_appends_current(tmp_path):
    past = tmp_path / "2026/11/13/2026-11-13T20.jsonl"
    cur = tmp_path / "2026/11/13/2026-11-13T22.jsonl"
    for p in (past, cur):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'{"x":0}\n')
    w = HourlyWriter(tmp_path, FakeClock(datetime(2026, 11, 13, 22, 30, tzinfo=UTC)), 5)
    assert w.recover() == [past.with_suffix(".jsonl.gz")]
    w.write(b'{"x":1}'); w.close()
    assert cur.read_bytes() == b'{"x":0}\n{"x":1}\n'

def test_compress_never_overwrites(tmp_path):
    src = tmp_path / "2026-11-13T22.jsonl"; src.write_bytes(b"new\n")
    (tmp_path / "2026-11-13T22.jsonl.gz").write_bytes(gzip.compress(b"old\n"))
    out = compress(src)
    assert out.name == "2026-11-13T22.1.jsonl.gz"
    assert gzip.decompress((tmp_path / "2026-11-13T22.jsonl.gz").read_bytes()) == b"old\n"

def test_paused_writer_drops_and_counts(tmp_path):
    w = HourlyWriter(tmp_path, FakeClock(datetime(2026, 11, 13, 22, tzinfo=UTC)), 5)
    w.paused = True
    w.write(b'{"a":1}')
    assert w.dropped_lines == 1
```

`FakeClock` es un helper en la prueba: devuelve un `datetime` fijo y tiene `advance(seconds=...)`.

- [ ] **Paso 2: correr las pruebas y ver que fallan.** `python -m pytest tests/test_writer.py -v`. Resultado esperado: FAIL.
- [ ] **Paso 3: implementar `writer.py`.** El archivo se abre en modo append binario. `write` agrega el `\n` si falta. `recover` no toca el archivo de la hora en curso.
- [ ] **Paso 4: correr las pruebas y ver que pasan.** Resultado esperado: PASS.
- [ ] **Paso 5: commit.** `git commit -s -m "Add hourly writer with compression and crash recovery"`

---

### Task 3: retención y piso de espacio

**Archivos:**
- Crear: `laboratorio/colector/colector/retention.py`
- Prueba: `laboratorio/colector/tests/test_retention.py`

**Interfaces:**
- Consume: la convención de nombres de `hour_path` (tarea 2).
- Produce:
  - `@dataclass(frozen=True) class PruneResult`, con `deleted: list[Path]` y `low_space: bool`;
  - `def prune(root: Path, now: datetime, retention_days: int, min_free_bytes: int, free_bytes: Callable[[Path], int]) -> PruneResult`.
- Reglas:
  - solo se borran archivos `*.jsonl.gz`;
  - la edad se calcula por la hora del nombre del archivo;
  - primero se borran los vencidos;
  - después, mientras `free_bytes(root) < min_free_bytes`, se borra el más viejo;
  - `low_space` es verdadero si al terminar sigue faltando espacio.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
def test_deletes_only_expired(tmp_path):
    old = make_gz(tmp_path, "2026-08-01T10"); keep = make_gz(tmp_path, "2026-11-01T10")
    r = prune(tmp_path, datetime(2026, 11, 13, tzinfo=UTC), 90, 0, lambda _: 10**12)
    assert r.deleted == [old] and keep.exists() and r.low_space is False

def test_frees_space_oldest_first_and_spares_current(tmp_path):
    a = make_gz(tmp_path, "2026-11-10T01"); b = make_gz(tmp_path, "2026-11-11T01")
    cur = make_jsonl(tmp_path, "2026-11-13T22")
    free = iter([0, 0, 0, 0])
    r = prune(tmp_path, datetime(2026, 11, 13, 22, tzinfo=UTC), 90, 1, lambda _: next(free))
    assert r.deleted == [a, b] and cur.exists() and r.low_space is True
```

`make_gz` y `make_jsonl` son helpers de la prueba que crean el archivo en la ruta de `hour_path`.

- [ ] **Paso 2: correr las pruebas y ver que fallan.** Resultado esperado: FAIL.
- [ ] **Paso 3: implementar `prune`.** En producción, `free_bytes` es `lambda p: shutil.disk_usage(p).free`.
- [ ] **Paso 4: correr las pruebas y ver que pasan.** Resultado esperado: PASS.
- [ ] **Paso 5: commit.** `git commit -s -m "Add retention and minimum free space guard"`

---

### Task 4: supervisión de GoFlow2

**Archivos:**
- Crear: `laboratorio/colector/colector/process.py`
- Crear: `laboratorio/colector/colector/__main__.py`
- Crear: `laboratorio/colector/tests/fake_goflow2.py`
- Prueba: `laboratorio/colector/tests/test_process.py`

**Interfaces:**
- Consume:
  - `Config` y `load_config` (tarea 1);
  - `HourlyWriter` (tarea 2);
  - `prune` y `PruneResult` (tarea 3);
  - `beat` (tarea 5). Hasta que exista, se inyecta un stub.
- Produce:
  - `class Backoff`, con `__init__(self, base: float = 1.0, cap: float = 60.0, max_failures: int = 5)`, `next_delay(self) -> float`, `reset(self) -> None` y la propiedad `exhausted -> bool`.
  - `def build_goflow2_command(cfg: Config) -> list[str]`. Devuelve `[str(cfg.goflow2_path), "-listen", f"netflow://:{cfg.listen_port}", "-format", "json", "-mapping", str(cfg.mapping_path), *cfg.goflow2_extra_args]`.
  - `def run(cfg: Config, writer: HourlyWriter, stop: threading.Event, popen=subprocess.Popen, sleep=time.sleep, prune_fn=prune, beat_fn=beat, prune_every: float = 60.0) -> int`. Devuelve 0 si para por `stop` y 1 si se agota el backoff.
- Comportamiento:
  - un hilo lee el stdout del hijo y lo pasa a una cola;
  - el lazo principal toma de la cola con un timeout de 1 s y llama a `writer.tick()` en cada vuelta;
  - cada `prune_every` segundos llama a `prune_fn`, pone `writer.paused = result.low_space` y llama a `beat_fn`;
  - solo pasan las líneas que `json.loads` acepta como objeto; las demás se cuentan y se registran como máximo una vez por minuto;
  - el stderr del hijo se reenvía al stderr del supervisor;
  - con `stop`, manda SIGTERM al hijo, espera 10 s, llama a `writer.close()` y devuelve 0.
- `__main__.py` maneja SIGTERM y SIGINT activando `stop`, llama a `writer.recover()` y después a `run`, y termina con `sys.exit` del resultado.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
def test_command_uses_config():
    cfg = load_config({"LISTEN_PORT": "4739", "GOFLOW2_EXTRA_ARGS": "-loglevel debug"})
    assert build_goflow2_command(cfg) == ["/usr/local/bin/goflow2", "-listen", "netflow://:4739",
        "-format", "json", "-mapping", "/etc/colector/mapping.yaml", "-loglevel", "debug"]

def test_backoff_exhausts_after_five_failures():
    b = Backoff(base=1, cap=60, max_failures=5)
    delays = [b.next_delay() for _ in range(5)]
    assert delays == [1, 2, 4, 8, 16] and b.exhausted

def test_run_writes_json_and_drops_garbage(tmp_path):
    # fake_goflow2.py imprime dos JSON y una línea basura, y queda vivo hasta SIGTERM
    writer, stop = make_writer(tmp_path), threading.Event()
    t = threading.Thread(target=lambda: results.append(run(cfg_with_fake(tmp_path, "ok"), writer, stop,
                                                           sleep=lambda _: None)))
    t.start(); wait_until(lambda: count_lines(tmp_path) == 2); stop.set(); t.join(15)
    assert results == [0] and count_lines(tmp_path) == 2

def test_run_returns_1_after_crash_loop(tmp_path):
    # fake_goflow2.py sale enseguida con código 2
    assert run(cfg_with_fake(tmp_path, "crash"), make_writer(tmp_path), threading.Event(),
               sleep=lambda _: None) == 1

def test_low_space_pauses_writer(tmp_path):
    writer = make_writer(tmp_path)
    run_briefly(tmp_path, writer, prune_fn=lambda *a, **k: PruneResult([], True), prune_every=0)
    assert writer.paused is True
```

`cfg_with_fake(tmp_path, mode)` arma un `Config` cuyo `goflow2_path` es un script que ejecuta `fake_goflow2.py` con ese modo. `make_writer`, `count_lines`, `wait_until` y `run_briefly` son helpers de la prueba.

- [ ] **Paso 2: correr las pruebas y ver que fallan.** Resultado esperado: FAIL.
- [ ] **Paso 3: implementar `process.py` y `__main__.py`.** El backoff se reinicia cuando el hijo dura más de 60 s vivo.
- [ ] **Paso 4: correr las pruebas y ver que pasan.** `python -m pytest tests -m "not integration" -v`. Resultado esperado: PASS.
- [ ] **Paso 5: commit.** `git commit -s -m "Supervise GoFlow2 and stream its output to hourly files"`

---

### Task 5: latido y healthcheck

**Archivos:**
- Crear: `laboratorio/colector/colector/health.py`
- Prueba: `laboratorio/colector/tests/test_health.py`

**Interfaces:**
- Produce:
  - `def beat(path: Path, now: float, child_alive: bool, low_space: bool, dropped_lines: int) -> None`. Escribe JSON de forma atómica (temporal y rename).
  - `def check(path: Path, now: float, max_age: float = 120.0) -> int`. Devuelve 0 si está sano y 1 si no.
  - `python -m colector.health`, que termina con `check(...)` usando `Config.heartbeat_path`.
- Está sano si el latido existe, tiene menos de `max_age` segundos, `child_alive` es verdadero y `low_space` es falso.

- [ ] **Paso 1: escribir las pruebas que fallan**

```python
@pytest.mark.parametrize("age,alive,low,expected", [
    (10, True, False, 0), (500, True, False, 1), (10, False, False, 1), (10, True, True, 1)])
def test_check(tmp_path, age, alive, low, expected):
    hb = tmp_path / "hb.json"
    beat(hb, now=1000.0, child_alive=alive, low_space=low, dropped_lines=0)
    assert check(hb, now=1000.0 + age) == expected

def test_missing_heartbeat_is_unhealthy(tmp_path):
    assert check(tmp_path / "nope.json", now=0.0) == 1
```

- [ ] **Paso 2: correr las pruebas y ver que fallan.** Resultado esperado: FAIL.
- [ ] **Paso 3: implementar `health.py`** y conectar `beat` en `run`, reemplazando el stub de la tarea 4.
- [ ] **Paso 4: correr todas las pruebas unitarias.** `python -m pytest tests -m "not integration" -v`. Resultado esperado: PASS.
- [ ] **Paso 5: commit.** `git commit -s -m "Add heartbeat and container healthcheck"`

---

### Task 6: imagen, mapeo y compose

**Archivos:**
- Crear: `laboratorio/colector/Dockerfile`
- Crear: `laboratorio/colector/mapping.yaml`
- Crear: `laboratorio/colector/compose.yaml`
- Crear: `laboratorio/colector/.env.example`
- Crear: `laboratorio/colector/tests/integration/ipfix_synth.py`
- Prueba: `laboratorio/colector/tests/integration/test_container.py`

**Interfaces:**
- Consume: `python -m colector` y `python -m colector.health` (tareas 4 y 5).
- Produce: la imagen local `huellaip/colector:dev`, que usan las pruebas y el CI.
- `def build_message(template_id: int = 256, observation_domain: int = 0) -> bytes` en `ipfix_synth.py`. Arma un mensaje IPFIX v10 con un conjunto de plantilla y uno de datos. La plantilla lleva los campos:
  - 8 y 12, direcciones IPv4 de origen y destino;
  - 7 y 11, puertos de origen y destino;
  - 4, protocolo;
  - 1 y 2, bytes y paquetes;
  - 152 y 153, inicio y fin del flujo en milisegundos;
  - 56 y 80, MAC de origen y destino;
  - 225 a 228, los campos de NAT.

  Valores ficticios: origen `10.77.10.11:40000`, destino `192.0.2.10:443`, TCP, 1234 bytes, 10 paquetes, MAC `02:00:00:00:00:11` y `02:00:00:00:00:01`, y NAT de origen `198.51.100.7:50000`.

**Requisitos de la imagen:**
- **Etapa 1:** `FROM netsampler/goflow2:v2.2.7@sha256:<digest del índice multiarquitectura>`, de donde se copia `/goflow2`.
- **Etapa final:** `python:<versión>-slim@sha256:<digest>`.
  - `COPY --from=… /goflow2 /usr/local/bin/goflow2`, y un `RUN /usr/local/bin/goflow2 -v` que prueba que el binario corre sobre la base de Python.
  - Usuario 10001 y `/datos/flujos` con ese dueño.
  - `VOLUME /datos`, `EXPOSE 2055/udp`, `HEALTHCHECK CMD ["python","-m","colector.health"]` y `ENTRYPOINT ["python","-m","colector"]`.
  - Etiquetas OCI: `source=https://github.com/huellaip/huellaip`, `licenses=Apache-2.0` y `version`.
- **`mapping.yaml`:** agrega 225 → `post_nat_src_addr`, 226 → `post_nat_dst_addr`, 227 → `post_napt_src_port`, 228 → `post_napt_dst_port`, y 80 → `dst_mac` si GoFlow2 no lo toma por defecto. La sintaxis se verifica contra `docs/protocols.md` de GoFlow2 v2.2.7.
- **`compose.yaml`:**
  - `image: ghcr.io/huellaip/colector:0.1.0` con `build: .`;
  - `restart: unless-stopped` y `ports: ["2055:2055/udp"]`;
  - `volumes: [huellaip-flujos:/datos]`;
  - `read_only: true`, `tmpfs: [/tmp]`, `cap_drop: [ALL]` y `security_opt: [no-new-privileges:true]`;
  - `env_file` con `.env` y `required: false`;
  - `logging` con el driver `json-file`, `max-size: 10m` y `max-file: 3`.
- **`.env.example`:** las cinco variables con su valor por defecto, comentadas.

- [ ] **Paso 1: escribir la prueba de integración que falla**

```python
pytestmark = pytest.mark.integration

def test_container_writes_flow_and_is_healthy(container):
    send_udp(build_message(), port=container.host_port)
    line = wait_for_first_line(container, timeout=30)
    flow = json.loads(line)
    assert flow["src_addr"] == "10.77.10.11" and flow["dst_addr"] == "192.0.2.10"
    assert flow["bytes"] == 1234 and flow["packets"] == 10 and flow["dst_port"] == 443
    assert flow["src_mac"] == "02:00:00:00:00:11" and flow["dst_mac"] == "02:00:00:00:00:01"
    assert flow["post_nat_src_addr"] == "198.51.100.7" and flow["post_napt_src_port"] == 50000
    assert flow["sampler_address"]          # la IP desde la que llegó el paquete
    assert wait_for_health(container, "healthy", timeout=150)
```

El fixture `container`:
- construye `huellaip/colector:dev` con `docker build`;
- lo levanta con las mismas opciones de seguridad que `compose.yaml`, un volumen temporal y el puerto 2055/udp en un puerto libre del host;
- al terminar, lo borra junto con el volumen.

`wait_for_first_line` lee con `docker exec … cat` los `.jsonl` de `/datos/flujos`.

En esta prueba, `sampler_address` es el gateway de Docker, porque el paquete sale del mismo host. Que traiga la IP real del router se verifica en staging, con el router de verdad (sección 5.4 del diseño).

- [ ] **Paso 2: correr la prueba y ver que falla.** `python -m pytest tests/integration -m integration -v`. Resultado esperado: FAIL, porque no existe el Dockerfile.
- [ ] **Paso 3: crear el Dockerfile, `mapping.yaml`, `compose.yaml` y `.env.example`.** Si GoFlow2 v2.2.7 no puede sacar los campos de NAT en el JSON, se saca esa aserción y se documenta la limitación en el README y en el PR, porque cambia el diseño.
- [ ] **Paso 4: correr la prueba y ver que pasa.** El mismo comando. Resultado esperado: PASS. Además, `docker compose -f laboratorio/colector/compose.yaml config` tiene que validar sin errores.
- [ ] **Paso 5: commit.** `git commit -s -m "Add collector image, field mapping and compose file"`

---

### Task 7: CI, Dependabot y README

**Archivos:**
- Crear: `.github/workflows/colector.yml`
- Crear: `.github/dependabot.yml`
- Crear: `laboratorio/colector/README.md`

**Interfaces:**
- Consume: las pruebas unitarias (tareas 1 a 5) y la prueba de integración (tarea 6).

**`colector.yml`:**
- Se dispara con `pull_request` y `push` a `main`, filtrados por `laboratorio/colector/**` y el propio workflow, y con `push` de etiquetas `colector-v*`.
- Permisos por defecto: `contents: read`.
- **Job `test`** (`ubuntu-24.04`): `ruff check`, `ruff format --check` y `pytest -m "not integration"`.
- **Job `build`** (matriz de `ubuntu-24.04` y `ubuntu-24.04-arm`): `docker build` y `pytest -m integration`, nativo en cada arquitectura.
- **Job `publish`:**
  - corre solo con etiquetas `colector-v*`, después de `test` y `build`;
  - permisos `contents: read` y `packages: write`;
  - construye por arquitectura en los mismos runners y publica por digest;
  - un job final arma el manifiesto con `docker buildx imagetools create` y las etiquetas `X.Y.Z` y `X.Y`, sacadas de la etiqueta de git;
  - genera la procedencia y el SBOM con las opciones de `docker/build-push-action`.
- Todas las acciones se fijan por SHA de commit, con la versión en un comentario.

**`dependabot.yml`:** el ecosistema `github-actions` en `/` y `docker` en `/laboratorio/colector`, los dos semanales.

**`README.md` del colector (castellano):**
- qué hace y qué requiere el host (solo Docker);
- cómo levantarlo, con `docker compose up -d`, o `--build` antes de la primera versión publicada;
- las variables de entorno;
- dónde quedan los datos y cómo leerlos con DuckDB (`read_json_auto('/datos/flujos/**/*.jsonl*')`);
- una línea JSON de ejemplo con valores ficticios;
- cómo verificar que llega el IPFIX;
- privacidad: el volumen tiene MAC completas e IP privadas y nunca se sube.

- [ ] **Paso 1: escribir el workflow y validarlo localmente.** `actionlint .github/workflows/colector.yml`, corrido en Docker con `rhysd/actionlint`. Resultado esperado: sin errores.
- [ ] **Paso 2: escribir `dependabot.yml` y el README.**
- [ ] **Paso 3: abrir el PR y ver que el CI pasa.** Los jobs `test` y `build`, en las dos arquitecturas, tienen que quedar en verde.
- [ ] **Paso 4: commit.** `git commit -s -m "Build and publish the collector image from CI"`

---

## Después del PR (fuera de este plan)

- El mantenedor crea la etiqueta `colector-v0.1.0` sobre `main` y hace pública la imagen en GHCR.
- La primera prueba en vivo se hace en el equipo de staging, con el procedimiento que se defina aparte.
