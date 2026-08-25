# CestaSmart 2.3 — PRINCIPIO CENTRAL

## Objetivo
Encontrar siempre la opción más económica posible manteniendo la misma calidad, independientemente de la marca.

## Orden de decisión
1. Restricciones duras del usuario, si existen:
   - EAN/GTIN exacto.
   - Marca protegida.
   - Preferencia obligatoria: ecológico, campero, sin lactosa, AOVE, etc.
2. Categoría correcta.
3. Misma calidad o superior.
4. Variante equivalente.
5. Cantidad/formato equivalente o convertido por unidades.
6. Precio efectivo normalizado más bajo.
7. Ofertas/promociones entran automáticamente si cumplen 2–5.
8. Marca: ignorada por defecto.

## Ejemplo AOVE
Petición: AOVE 1 L.
- Compiten todos los AOVE equivalentes, sin importar marca.
- No se admite aceite de oliva virgen ni aceite de oliva normal.
- Gana el AOVE con menor €/L efectivo.
- Si una marca está de oferta y queda más barata, pasa a ser la recomendación.

## Regla de interfaz
La app debe mostrar primero:
- producto elegido,
- supermercado,
- precio,
- unidad normalizada,
- ahorro frente a la siguiente alternativa,
- nivel de confianza/equivalencia.

La marca se muestra como información, no como criterio de selección.
