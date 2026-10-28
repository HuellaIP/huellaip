# Política de seguridad

HuellaIP es un proyecto de seguridad defensiva, así que nos tomamos en serio los problemas de seguridad del propio proyecto. Esta política rige para toda la organización HuellaIP en GitHub, incluido [`huellaip/huellas`](https://github.com/huellaip/huellas).

## Qué reportar por acá

- **Vulnerabilidades en el código del proyecto:** el generador, el validador, los exportadores o las herramientas del laboratorio. Por ejemplo, un exportador que genere reglas que abran accesos en lugar de restringirlos.
- **Fallas de contención en la configuración publicada del laboratorio:** filtros de la cuarentena que dejen salir tráfico que deberían cortar.
- **Datos sensibles publicados por error:** direcciones MAC completas, números de serie, cuentas, la IP pública de un laboratorio, credenciales o cualquier dato personal, en un archivo, un issue, un PR o el historial.

## Qué no va por acá

- **El comportamiento de un dispositivo**, por ejemplo un equipo que escanea la red: usá el formulario [*Reportar un comportamiento*](https://github.com/huellaip/huellaip/issues/new/choose).
- **Una vulnerabilidad en el producto de un fabricante:** reportala al fabricante o a un CSIRT. HuellaIP no publica vulnerabilidades de terceros ni exploits.
- **Un problema de conducta:** seguí el [código de conducta](CODE_OF_CONDUCT.md#reportar-un-incidente).

## Cómo reportar

**No abras un issue público.** Escribí a [huellaip@googlegroups.com](mailto:huellaip@googlegroups.com) con el asunto «Seguridad». Cuando los repositorios sean públicos, también vas a poder usar el reporte privado de GitHub, en la pestaña *Security* del repositorio.

Incluí lo que tengas de esto:

- qué componente está afectado (archivo, versión o commit);
- qué pasa y qué impacto tiene;
- cómo reproducirlo, con la prueba mínima necesaria;
- si querés que te mencionemos al publicar la corrección, y con qué nombre.

Si encontraste un dato sensible publicado, **no lo copies en el reporte**: alcanza con indicar dónde está. Si es una credencial tuya, revocala o cambiala ya, sin esperar nuestra respuesta.

## Qué esperar

HuellaIP lo sostienen personas voluntarias, así que estos plazos son un compromiso de mejor esfuerzo:

| Paso | Plazo |
|---|---|
| Acuse de recibo | Hasta 5 días hábiles |
| Evaluación inicial y plan de corrección | Hasta 30 días |
| Publicación coordinada del aviso de seguridad | Después de la corrección, en acuerdo con quien reportó y como máximo a los 90 días del reporte |

Si se trata de datos sensibles publicados, actuamos lo antes posible: los quitamos del repositorio y del historial y, si hace falta, le pedimos a GitHub que borre las copias en caché.

Coordina la respuesta el comité técnico. Si el reporte involucra a alguien del comité, esa persona no participa de su tratamiento, como establece la [gobernanza](GOVERNANCE.md).

## Versiones cubiertas

El proyecto está en fase 0, sin versiones publicadas. Hasta la versión 0.1.0 solo se corrige la rama `main`.
