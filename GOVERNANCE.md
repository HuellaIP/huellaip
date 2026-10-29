# Gobernanza de HuellaIP

> Versión 0.2 · octubre de 2026 · Rige para toda la organización HuellaIP en GitHub, incluido `huellaip/huellas`.

Este documento explica quién decide qué en HuellaIP y cómo. Busca dos cosas: que el proyecto pueda avanzar rápido mientras es chico, y que ninguna organización, tampoco la de quien lo impulsa, pueda apropiárselo cuando crezca.

## Principios

Todo lo demás de este documento está al servicio de estos principios. Cambiarlos requiere una [decisión reforzada](#decisiones-reforzadas).

1. **Neutralidad.** Ningún ISP, fabricante ni empresa es dueño del proyecto, y aportar no da derechos especiales.
2. **Solo metadatos.** Destinos, puertos, sesiones, volúmenes, tiempos, DNS y parámetros de TLS. Nunca contenido.
3. **Solo defensa.** No se escribe, mejora ni distribuye malware, exploits ni herramientas de ataque. El tráfico anómalo de prueba es sintético y va contra destinos propios.
4. **Seguridad, no antipiratería.** HuellaIP no evalúa qué contenido se consume.
5. **Privacidad por diseño**, conforme a la Ley 25.326 de Protección de Datos Personales.
6. **Contención primero.** Un equipo que puede estar comprometido solo se conecta a un segmento de cuarentena con filtros probados.
7. **Estándares antes que software propio.** Lo que se pueda expresar en MUD (RFC 8520), se expresa en MUD.
8. **Apertura.** Código bajo Apache-2.0, huellas bajo CC-BY-4.0 y decisiones en público.

## Roles

| Rol | Quién | Qué hace | Cómo se llega |
|---|---|---|---|
| **Colaborador/a** | Toda persona con al menos un aporte aceptado: código, documentación, una huella, una captura o una revisión | Propone, opina, revisa y vota en la elección del comité | Con el primer aporte aceptado |
| **Mantenedor/a** | Personas con permiso de escritura en un repositorio o en un área, según `CODEOWNERS` | Revisa e integra PRs, ordena issues y acompaña a quienes empiezan | Lo propone un mantenedor o el comité después de aportes sostenidos, y se aprueba por consenso perezoso del comité |
| **Comité técnico** | Tres integrantes en el período provisorio; cinco cuando sea elegido | Decide sobre la especificación, la hoja de ruta y los conflictos; aprueba huellas; designa mantenedores; aplica este documento | Ver [Comité técnico](#comité-técnico) |
| **Administración de la organización** | Al menos dos personas, de organizaciones distintas | Gestiona permisos, configuración y seguridad de la organización en GitHub. Ejecuta decisiones, no las toma | La designa el comité |

Cualquiera puede revisar un PR o una huella. Para integrar, cuentan las aprobaciones de mantenedores y del comité.

**El impulsor.** Uriel Rozenbaum inició el proyecto. Durante el período provisorio coordina el trabajo y representa al proyecto ante sus aliados. No tiene más atribuciones que su lugar en el comité y el desempate que se describe abajo.

## Cómo se decide

### Consenso perezoso

La mayoría de las decisiones se toman por consenso perezoso: una propuesta se publica en un issue, un PR o una discusión, con la etiqueta `decision`, y se aprueba si nadie objeta en 7 días.

Una objeción tiene que estar fundamentada y, si se puede, proponer una alternativa. El silencio cuenta como acuerdo: por eso se llama perezoso.

Los cambios de rutina (correcciones, arreglos de errores, mejoras de documentación) siguen el flujo normal de revisión de [CONTRIBUTING.md](CONTRIBUTING.md) y no esperan los 7 días.

### Votación del comité

Si una objeción no se resuelve en la discusión, vota el comité técnico. Se cuentan los votos sobre el total de integrantes, no sobre los presentes.

- **Comité provisorio (tres integrantes).** La propuesta se aprueba con dos votos a favor. Si por una abstención la votación queda uno a uno, desempata el impulsor, salvo que la abstención sea suya o que tenga un conflicto de interés en el tema. En esos casos la propuesta no pasa.
- **Comité elegido (cinco integrantes).** La propuesta se aprueba con tres votos a favor. No hay desempate: si no se llega a tres, la propuesta no pasa.

### Decisiones reforzadas

Algunas decisiones cambian la naturaleza del proyecto y piden más que una mayoría:

- cambiar un principio;
- cambiar una licencia;
- modificar este documento;
- remover a un integrante del comité o a un mantenedor, salvo las medidas urgentes que prevé el código de conducta;
- registrar, ceder o transferir activos del proyecto: nombre, logo, dominio u organización de GitHub;
- recibir fondos o crear una entidad legal.

Requieren 30 días de discusión pública y, además, unanimidad en el comité provisorio o cuatro votos de cinco en el comité elegido. Si la decisión afecta a un integrante, esa persona no vota y el umbral se calcula sobre el resto.

**Sobre las licencias.** El comité puede decidir bajo qué licencia se reciben los aportes de acá en adelante, pero no puede cambiar por sí solo los términos de lo ya aportado. Con el DCO, cada persona conserva los derechos sobre su aporte y lo entrega bajo la licencia vigente en ese momento. Cambiar la licencia de lo existente requiere el consentimiento de sus autores o reescribir esas partes.

## Comité técnico

### Comité provisorio

Lo integran el impulsor y dos personas que él elige entre quienes respondieron a la convocatoria. Las tres tienen que tener organizaciones principales distintas. La organización principal de alguien es su empleador o la organización a la que representa en el proyecto.

| Integrante | Organización principal | Otras afiliaciones declaradas |
|---|---|---|
| Uriel Rozenbaum (impulsor) | Metrotel (Gerente de Operaciones) | Cerrando la Brecha (tesorero) · ITBA (profesor adjunto) |
| [a designar] | [a declarar] | [a declarar] |
| [a designar] | [a declarar] | [a declarar] |

**Hasta cuándo.** El comité provisorio se reemplaza por uno elegido apenas se cumpla la primera de estas dos condiciones:

- HuellaIP llega a **diez participantes** con aportes aceptados;
- llega el **31 de octubre de 2027**, doce meses después del inicio del proyecto.

Cómo se cuentan los participantes:

- Cuenta como participante cada organización con al menos un aporte aceptado hecho en su nombre, confirmado por alguien de esa organización. Puede ser un ISP, una universidad, una empresa, una organización civil o un organismo público.
- También cuenta como participante cada persona independiente con al menos un aporte aceptado. Quien aporta en nombre de una organización suma para esa organización, no por separado.
- El comité provisorio publica cada trimestre, en una discusión fijada, quiénes cuentan y cuántos faltan.
- Dentro de los 30 días de cumplirse cualquiera de las dos condiciones, convoca la primera elección.

### Comité elegido

- **Composición:** cinco integrantes, con un máximo de uno por organización principal. Las personas independientes pueden postularse.
- **Mandato:** un año, con reelección permitida.
- **Quién vota:** quienes tengan al menos un aporte aceptado en los 12 meses anteriores a la convocatoria. Una persona, un voto.
- **Calendario:** 14 días de postulaciones en Discussions, cada una con sus afiliaciones declaradas, y después 7 días de votación.
- **Cómo se vota:** con una herramienta de voto secreto que el comité saliente anuncia al convocar. Cada persona marca hasta cinco candidaturas. Se eligen las cinco más votadas, salteando a quien sea de una organización que ya tiene lugar. Los empates se resuelven por sorteo público.
- **Coordinación:** el comité elige entre sus integrantes a una persona que coordina el trabajo y lo representa durante el año.
- **Vacantes:** asume la siguiente candidatura más votada que respete la regla de una por organización. Si no hay, el comité designa a alguien por mayoría hasta la próxima elección.
- **Pocas candidaturas:** si hay menos de cinco, el comité se integra con las que haya, con un mínimo de tres. Si no se llega a tres, el comité provisorio sigue en funciones y convoca una nueva elección dentro de los seis meses.

## Neutralidad y conflictos de interés

- **Afiliaciones declaradas.** Integrantes del comité y mantenedores declaran su organización principal y cualquier vínculo relevante: empleo, cargos en organizaciones civiles, docencia, consultoría o relación comercial con fabricantes o proveedores. Lo actualizan si cambia.
- **Abstención.** Quien tenga un vínculo con una organización se abstiene en las decisiones que la beneficien o perjudiquen de forma específica.
- **Revisión de huellas.** La revisión del comité sobre una huella no puede hacerla alguien de la organización que la aporta, ni de una que fabrique o venda ese dispositivo.
- **Sin derechos por aportar.** Prestar dispositivos, compartir datos u ofrecer pilotos no da derechos sobre la hoja de ruta, la especificación ni la publicación de huellas.
- **Sin recomendaciones de marcas.** Una huella describe el comportamiento observado de un dispositivo. No lo recomienda ni lo desaconseja.
- **Aliados.** Una organización figura como aliada en los repositorios solo después de confirmarlo por escrito.

## Activos del proyecto

- **Organización de GitHub.** Al menos dos personas administradoras, de organizaciones distintas, con autenticación en dos pasos obligatoria para toda la organización.
- **Nombre, logo, dominio y cuentas en redes.** Se gestionan en nombre del proyecto, no de quien los administra. Los administran al menos dos personas de organizaciones distintas, y ninguna organización puede registrarlos a su nombre. Cualquier registro o transferencia es una decisión reforzada.
- **Fondos.** Hoy HuellaIP no recibe ni administra dinero. Antes del primer ingreso, este documento se actualiza para definir cómo se manejan.

## Transparencia

- Las decisiones se discuten en público y su resultado queda registrado en el hilo, con fecha.
- Las reuniones del comité tienen minuta pública en Discussions dentro de los 7 días.
- Solo se tratan en privado los reportes de vulnerabilidades, los reportes de conducta, los datos personales y el acceso a muestras maliciosas.

## Inactividad y salida

- **Mantenedores.** Después de 6 meses sin actividad, se les consulta. Si no responden en 30 días, pasan a la categoría de emérito: pierden los permisos y conservan el reconocimiento. Pueden volver pidiéndolo.
- **Comité.** Quien no participe en las decisiones durante 3 meses deja su lugar vacante.
- **Renuncia.** Se avisa en público, salvo que haya motivos personales para no hacerlo.
- **Conducta.** Las sanciones por violar el código de conducta siguen [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Si un reporte involucra a un integrante del comité, esa persona no participa de su tratamiento.

## Cambios a este documento

Este documento se cambia con una decisión reforzada, mediante un PR que explique el motivo. El historial de Git es el registro de cambios.
