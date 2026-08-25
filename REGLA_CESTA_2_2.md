# CestaSmart 2.3 — Cesta más barata con la misma calidad

Objetivo principal:
**obtener la cesta más barata posible, indistintamente de la marca, manteniendo la misma calidad.**

Orden de decisión:
1. EAN/GTIN exacto, si el usuario pide un producto concreto.
2. Categoría correcta.
3. Misma calidad o superior.
4. Misma variante relevante.
5. Formato/cantidad equivalente o convertido por unidades.
6. Precio normalizado efectivo más bajo.
7. Si existe oferta/promoción válida, usar el precio promocional.
8. Marca: no influye en la selección, salvo que el usuario la proteja expresamente.

Ejemplo AOVE:
- Si se pide AOVE, solo compiten AOVE de cualquier marca.
- No se admite aceite de oliva normal ni virgen como sustituto.
- Gana el AOVE con menor €/l efectivo, incluyendo ofertas.

Ejemplo papel:
- Si se piden 12 rollos y hay packs de 6, se comparan 2 packs.
- Gana el coste total equivalente más bajo.

Ejemplo yogur:
- 4×125 g puede compararse con 4×120 g si la diferencia es pequeña.
- Gana el coste normalizado por kg, manteniendo la misma clase de producto.
