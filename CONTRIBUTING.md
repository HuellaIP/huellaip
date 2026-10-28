# Cómo contribuir a HuellaIP

Gracias por querer sumarte. HuellaIP solo funciona si lo sostiene una comunidad: SPIN, el proyecto más parecido que existió, se archivó por falta de manos, no de ideas.

Esta guía es para el repositorio `huellaip/huellaip`: especificación del formato, laboratorio, herramientas y exportadores. **Para proponer o revisar una huella**, la guía está en [`huellaip/huellas`](https://github.com/huellaip/huellas/blob/main/CONTRIBUTING.md).

> [!TIP]
> ¿Primera vez en un proyecto abierto? Buscá issues con la etiqueta `good first issue`. Están pensados para resolverse sin conocer todo el proyecto, y alguien del equipo te acompaña en la revisión.

## Antes de empezar

Tres cosas, en este orden:

1. Leé el [código de conducta](CODE_OF_CONDUCT.md). Rige en issues, PRs, Discussions y cualquier espacio del proyecto.
2. Leé las [líneas rojas](#líneas-rojas). No son preferencias de estilo: un aporte que cruza una se cierra, aunque el resto sea bueno.
3. Configurá Git para [firmar tus commits](#firmar-los-commits-dco). Sin firma, el CI no deja integrar el PR.

## Líneas rojas

**Solo metadatos.** HuellaIP trabaja con destinos, puertos, sesiones, volúmenes, tiempos, consultas DNS y parámetros de TLS. Nunca con el contenido de las comunicaciones. Si una herramienta necesita algo fuera de esa lista, primero se discute como [cambio de especificación](#cambios-a-la-especificación).

**Solo defensa.** No se aceptan malware, exploits, escáneres ofensivos, herramientas de fuerza bruta, infraestructura de comando y control, técnicas de evasión ni código que reproduzca la propagación de un malware real, aunque se presente "para pruebas". Las anomalías de prueba son sintéticas (un destino nuevo, una ráfaga de conexiones, una subida de volumen) y van siempre contra servidores propios, declarados en la configuración de la prueba.

**Contención primero.** Un equipo que puede estar comprometido solo se conecta al segmento de cuarentena, y solo después de que los filtros de salida pasaron la [prueba de contención](#laboratorio-y-capturas). Esto incluye a cualquier TV box genérico, aunque venga sellado de fábrica, y vale igual para quien replica la maqueta en otro lugar.

**Privacidad por diseño**, conforme a la Ley 25.326 de Protección de Datos Personales. Nunca se suben al repositorio:

- capturas (pcap) ni logs crudos;
- direcciones MAC completas (en las huellas va solo el OUI, los tres primeros bytes, que identifican al fabricante);
- números de serie;
- cuentas, correos ni ningún otro identificador personal;
- la IP pública de un laboratorio;
- credenciales, llaves ni tokens.

**Seguridad, no antipiratería.** HuellaIP no evalúa qué contenido se consume. En esta etapa, en el laboratorio no se instalan apps no oficiales ni se consume contenido no autorizado. Si algún día se estudia ese caso, va a ser con revisión legal previa y en cuarentena.

## Formas de aportar

| Si querés... | Dónde | Cómo |
|---|---|---|
| Preguntar, presentarte o proponer una idea | [Discussions](https://github.com/huellaip/huellaip/discussions) | Abrí un hilo en la categoría que corresponda |
| Proponer o revisar una huella | [`huellaip/huellas`](https://github.com/huellaip/huellas) | Seguí la guía de ese repositorio |
| Reportar un comportamiento raro de un dispositivo | Issues | Plantilla *Reportar un comportamiento* (ver [abajo](#comportamientos-sospechosos)) |
| Proponer un cambio al formato | Issues | Plantilla *Proponer un cambio de formato* (ver [el proceso](#cambios-a-la-especificación)) |
| Escribir código | Issues con `good first issue`, `exportador` o `laboratorio` | Comentá que tomás el issue y abrí un PR |
| Mejorar la documentación o la metodología | `docs/` y `especificacion/` | PR directo para correcciones; issue antes para cambios de fondo |
| Replicar la maqueta en tu laboratorio | `laboratorio/` y Discussions | Contanos dónde y con qué equipos; la guía de réplica llega con la versión 0.1.0 |
| Reportar una vulnerabilidad | Canal privado | Seguí [SECURITY.md](SECURITY.md) |

## Flujo de trabajo

1. **Primero el issue.** Para cualquier cosa más grande que una corrección chica, abrí un issue o tomá uno existente y comentá que lo estás trabajando. Así evitamos que dos personas hagan lo mismo.
2. **Fork y rama.** Trabajá en una rama con nombre descriptivo, por ejemplo `exportador-address-lists`.
3. **Commits chicos y firmados** (`git commit -s`).
4. **Chequeos locales** antes de abrir el PR:

   ```bash
   ruff check .
   ruff format --check .
   pytest
   ```

   El comando del validador de huellas se documenta acá cuando la herramienta esté lista.
5. **PR con la plantilla:** qué cambia, por qué, cómo lo probaste e issue relacionado. Si toca el laboratorio o datos de dispositivos, completá el chequeo de privacidad.
6. **Integración continua.** El CI valida el esquema, el estilo, los tests y la firma DCO, y busca secretos. Tiene que pasar todo.
7. **Revisión.** Cualquiera puede revisar. Para integrar hace falta la aprobación de un mantenedor del área, según `CODEOWNERS`. Los cambios a la especificación necesitan además la decisión del comité técnico.
8. **Ajustes.** Respondé los comentarios con commits nuevos. Si tenés que reescribir la rama, usá `git push --force-with-lease`.

## Firmar los commits (DCO)

HuellaIP usa el [Developer Certificate of Origin 1.1](https://developercertificate.org/) (DCO). Al firmar un commit certificás que el aporte es tuyo, o que tenés derecho a aportarlo, bajo la licencia del repositorio (Apache-2.0).

No cedés tus derechos: seguís siendo autor o autora, y el proyecto usa tu aporte según esa licencia. Es más liviano que un acuerdo de cesión de derechos (CLA), que muchos proyectos piden y nosotros no.

Dos condiciones:

- **Identidad.** Firmá con un nombre con el que se te pueda identificar. No aceptamos aportes anónimos.
- **Empleador.** Si aportás como parte de tu trabajo, asegurate de que tu empleador te autoriza. En muchas empresas, lo que escribís en horario laboral le pertenece a la empresa.

Para firmar:

```bash
git config --global user.name "Nombre Apellido"
git config --global user.email "vos@ejemplo.com"
git commit -s -m "Add address-list export for RouterOS"
```

El commit queda con esta línea al final del mensaje:

```text
Signed-off-by: Nombre Apellido <vos@ejemplo.com>
```

Si te olvidaste de firmar:

```bash
# Solo el último commit
git commit --amend --no-edit -s

# Todos los commits de tu rama (main = la rama contra la que abriste el PR)
git rebase --signoff main

git push --force-with-lease
```

## Convenciones

### Idioma

- Documentación: castellano, en cualquiera de sus variantes.
- Issues, PRs y Discussions: castellano o inglés.
- Código, identificadores, comentarios y mensajes de commit: inglés.
- Claves del formato de huella: castellano, sin tildes y con guiones, como en la especificación (`sesiones-concurrentes`, `interaccion`).

### Python

- Python 3.11 o posterior.
- Estilo y lint con [ruff](https://docs.astral.sh/ruff/); tests con [pytest](https://docs.pytest.org/).
- Anotaciones de tipo en las funciones públicas.
- Pocas dependencias, y justificadas en el PR: las herramientas corren en una Raspberry Pi 5.
- Los análisis de flujos van en DuckDB.

### RouterOS

- RouterOS v7, que es lo que corre el hEX de la maqueta.
- Scripts en `.rsc`, comentados bloque por bloque.
- Cada script o regla nueva trae en el PR qué hace cada bloque, cómo probarlo en la maqueta y cómo revertirlo.
- Las MAC de ejemplo son ficticias, del rango administrado localmente (`02:00:00:00:00:xx`).
- La configuración que se versiona sale de `/export` y se revisa a mano antes de subirla. `/export` oculta por defecto contraseñas y llaves, salvo que se pida `show-sensitive` ([Configuration Management](https://help.mikrotik.com/docs/spaces/ROS/pages/328155/Configuration+Management)). Pero sí incluye las MAC de las reservas DHCP y la IP de la WAN si es fija: reemplazalas por valores ficticios antes de subir el archivo.

### JSON y especificación

- Toda huella y todo ejemplo valida contra el esquema de `especificacion/esquema/`.
- Un cambio al esquema trae ejemplos válidos e inválidos que lo ejerciten.

### Documentación y diagramas

- Markdown, con diagramas en Mermaid para que GitHub los muestre.
- Cuando afirmes algo del mundo (un RFC, un comando, un dataset, una amenaza), enlazá la fuente.

### Commits

- Mensajes en inglés, en imperativo y con una primera línea de hasta 72 caracteres, por ejemplo `Add address-list export for RouterOS`.
- El cuerpo explica el porqué, no el qué.
- Un commit, un cambio lógico.

## Cambios a la especificación

El formato de huella es el contrato entre quienes capturan, quienes revisan y los routers que consumen las huellas. Por eso se cambia con más cuidado que el código.

1. **Propuesta.** Abrí un issue con la plantilla *Proponer un cambio de formato*. Incluí el problema, la propuesta, por qué no alcanza con lo que ya permite MUD, el impacto sobre las huellas publicadas y los exportadores, y si el cambio es compatible.
2. **Discusión.** Queda abierta al menos 14 días.
3. **Decisión.** La toma el comité técnico según [GOVERNANCE.md](GOVERNANCE.md) y queda registrada en el issue.
4. **Implementación.** Un único PR actualiza juntos la especificación, el esquema, los ejemplos y el registro de cambios (`especificacion/CHANGELOG.md`).
5. **Versión.** Versionado semántico. Mientras el formato esté en 0.x, un cambio incompatible sube el número menor (0.1 → 0.2) y uno compatible, el de parche (0.1.0 → 0.1.1).

**Estándares antes que software propio:** lo que se pueda expresar con los campos de MUD (RFC 8520) o de sus extensiones publicadas, como el RFC 9761, se expresa ahí y no en `huellaip-perfil`.

## Laboratorio y capturas

- Seguí la metodología de captura (`docs/metodologia-captura.md`) y el plan de contención (`docs/contencion.md`).
- **Prueba de contención.** Antes de conectar cualquier equipo dudoso, conectá un equipo de prueba a la cuarentena y generá, contra un servidor propio, intentos a los puertos 22 y 23, una ráfaga de conexiones nuevas y un intento de acceso a la gestión. Los tres tienen que quedar cortados y registrados en el log. Hasta que eso pase, el equipo dudoso no se enchufa.
- Usá un uplink con IP propia y avisale antes al equipo de abuse de tu proveedor.
- Configurá los dispositivos con cuentas de laboratorio, nunca personales.
- Registrá el firmware antes y después de cada captura. Si cambia, corresponde una huella nueva.
- Las capturas crudas no salen del equipo de captura del laboratorio.

## Comportamientos sospechosos

Si un dispositivo hace algo que su categoría no hace nunca, abrí un issue con la plantilla *Reportar un comportamiento*. Incluí marca, modelo y firmware, y metadatos agregados: puertos, cantidad de destinos, conexiones nuevas por segundo, horarios y ASN.

No subas muestras, binarios, APKs ni capturas. El acceso a muestras maliciosas es controlado y el canal se está definiendo; mientras tanto, mencioná en el issue que tenés material y te contactamos.

Si el equipo puede estar atacando a terceros, aislalo primero y reportá después.

## Si subiste algo que no debías

1. No lo borres con un commit nuevo: queda en el historial.
2. Avisá enseguida por el canal privado de [SECURITY.md](SECURITY.md).
3. Si es una credencial, revocala o cambiala ya, sin esperar a que se limpie el repositorio.
4. Los mantenedores reescriben el historial y, si hace falta, le piden a GitHub que borre las copias en caché.

## Reportar una vulnerabilidad

No abras un issue público. Seguí [SECURITY.md](SECURITY.md).

## Reconocimiento

Tu nombre queda en el historial de Git y en las notas de cada versión. Las huellas se publican bajo CC-BY-4.0, con atribución a quien las aporta.

¿Dudas? Preguntá en [Discussions](https://github.com/huellaip/huellaip/discussions). Ninguna pregunta es demasiado básica.
