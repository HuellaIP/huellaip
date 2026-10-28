# Ejemplos del formato de huella v0

Los valores son ficticios. Los dominios usan el TLD reservado `.example` ([RFC 2606](https://www.rfc-editor.org/info/rfc2606)), los ASN salen del rango de documentación ([RFC 5398](https://www.rfc-editor.org/info/rfc5398)) y el OUI `00:00:5E` es el de la IANA, que se usa en documentación ([RFC 7042](https://www.rfc-editor.org/info/rfc7042)).

## Válidos

| Archivo | Qué muestra |
|---|---|
| [`validos/camara-benigna.json`](validos/camara-benigna.json) | Una cámara con los cuatro estados, confianza `media`, perfiles TLS en las ACL y un destino con comodín |
| [`validos/tv-box-maliciosa.json`](validos/tv-box-maliciosa.json) | Un TV box genérico `malicioso`, con confianza `baja`, dos estados omitidos por estar en cuarentena, TLS 1.0 observado y reglas `drop` para los indicadores de compromiso |

## Inválidos

Cada uno parte de un ejemplo válido y tiene un único error.

| Archivo | Error esperado |
|---|---|
| [`invalidos/mac-completa.json`](invalidos/mac-completa.json) | `identificacion.oui` tiene una MAC completa en lugar del OUI |
| [`invalidos/malicioso-sin-fuente.json`](invalidos/malicioso-sin-fuente.json) | La etiqueta es `malicioso` y falta `fuentes-ioc` |
