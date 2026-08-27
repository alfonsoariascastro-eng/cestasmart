# CestaSmart 3.0

## Objetivo
Obtener la cesta más barata posible manteniendo la misma calidad, independientemente de la marca.

## Reglas consolidadas

1. Producto genérico = producto estándar.
   - Café no implica cápsulas/soluble/sabores.
   - Jamón cocido no implica pavo.
   - Salsa de tomate no implica arrabbiata/albahaca.
   - Variantes especiales solo si el usuario las solicita.

2. Equivalencias por pack/unidad.
   - Si no existe el mismo formato, se calcula cuántos packs hacen falta.
   - Se compara el coste equivalente.

3. Subtipos obligatorios cuando el producto los expresa.
   - Queso manchego debe seguir siendo manchego.
   - Spaghetti debe seguir siendo spaghetti.
   - Café natural/molido no se sustituye por soluble/cápsulas.

4. Falsos positivos bloqueados.
   - Papel húmedo y accesorios de baño no son papel higiénico.
   - Derivados al huevo no son huevos.
   - Detergentes incompatibles se excluyen.

5. Optimizador.
   - Mejor tienda única.
   - Mejor cesta dividida.
   - Umbral mínimo de ahorro.
   - Máximo de tiendas.
   - Coste adicional de desplazamiento/envío.

## Supermercados

### Activos
- Mercadona
- Gadis
- DIA
- Lidl España
- Eroski

### Preparados
- Familia: conector propio pendiente.
- Carrefour: conector separado pendiente.

## Estado de conectores
Nuevo endpoint:
`/api/connectors`

Devuelve qué supermercados están activos y cuáles están preparados pero deshabilitados.
