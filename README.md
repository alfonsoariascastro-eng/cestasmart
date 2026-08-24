# CestaSmart 2.0 Cloud

Versión preparada para desplegar CestaSmart en Internet con **Render + PostgreSQL**.

## Qué incluye

- Flask en producción con Gunicorn.
- Docker reproducible.
- `grocery-cli` compilado dentro de la imagen; no hay que instalar Go en Render.
- ZXing local incluido en la imagen; no hay que instalar Node en Render.
- PostgreSQL mediante `DATABASE_URL`.
- Catálogo maestro que se alimenta con las búsquedas reales.
- Historial de precios.
- Registro de búsquedas y comparaciones.
- Mercadona, Gadis, DIA y Lidl mediante `grocery-cli`.
- Motor semántico, EAN/GTIN, categoría, confianza y equivalencia por unidades heredados del MVP 1.7.
- `/api/health` para comprobación de Render.

> `grocery-cli` es un conector no oficial. Para una explotación comercial a escala hay que validar términos de uso, estabilidad y fuentes autorizadas de cada cadena.

## Despliegue más fácil: Render Blueprint

1. Crea un repositorio nuevo en GitHub, por ejemplo `cestasmart`.
2. Sube **todo el contenido de esta carpeta a la raíz del repositorio**, incluido `Dockerfile` y `render.yaml`.
3. En Render, crea un **Blueprint** y conecta ese repositorio.
4. Render detectará `render.yaml` y propondrá crear:
   - `cestasmart-api` (Web Service Docker)
   - `cestasmart-db` (PostgreSQL)
5. Confirma el despliegue.
6. Cuando termine, abre la URL `https://...onrender.com` que te asigne Render.
7. Comprueba `https://...onrender.com/api/health`.

`DATABASE_URL` se conecta automáticamente desde PostgreSQL al servicio web mediante `render.yaml`.

## Despliegue manual en Render

Si prefieres no usar Blueprint:

- Web Service runtime: Docker
- Health check: `/api/health`
- Variable `DATABASE_URL`: cadena interna de tu Render Postgres
- Variable `GROCERY_CONFIG_DIR`: `/tmp/grocery`

No necesitas configurar manualmente `gunicorn`: el `Dockerfile` ya define el comando de arranque.

## Base de datos

Las tablas se crean automáticamente en el primer arranque:

- `products`: catálogo maestro observado.
- `price_snapshots`: cambios de precio.
- `search_events`: búsquedas realizadas.
- `comparison_events`: comparaciones de cesta.

Cada búsqueda real va enriqueciendo el catálogo.

## Endpoints

- `/` — interfaz CestaSmart.
- `/api/health` — salud de servidor, conector y DB.
- `/api/status` — estado general y estadísticas.
- `/api/catalog/stats` — tamaño del catálogo e historial.
- `/api/search?store=mercadona&q=leche+entera+1+l`
- `/api/compare` — comparación multi-supermercado.

## Seguridad / siguiente fase

Esta versión es apta para un **piloto privado**. Antes de abrirla masivamente al público conviene añadir:

- cuentas de usuario y autenticación;
- límites de peticiones/rate limiting;
- caché y trabajos de actualización programada;
- política de privacidad;
- monitorización y alertas;
- fuentes comerciales/autorizadas para precios cuando proceda.
