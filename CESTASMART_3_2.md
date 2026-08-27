# CestaSmart 3.2

## Eroski
- El dominio principal bloquea peticiones automatizadas desde Render (403).
- El fallback usa el backend Worldline accesible con rutas `/es/supermercado/eroski/...`.
- Mantiene extracción de nombre, formato, precio y promociones del catálogo Eroski.

## Familia
- El dominio público presenta reCAPTCHA a clientes automatizados.
- Para evitar mostrar 0,00 € o reutilizar indebidamente precios de Eroski, Familia queda marcado temporalmente como `CONNECTOR_PENDING`.
- No participa en el ranking hasta disponer de una fuente específica fiable.

Esto prioriza exactitud sobre completar artificialmente todos los supermercados.
