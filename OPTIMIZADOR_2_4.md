# CestaSmart 2.9 — Optimizador de cesta

Objetivo central:
**obtener la cesta más económica posible manteniendo la misma calidad, independientemente de la marca.**

## Variables aplicadas

### 1. Calidad
- Misma calidad exacta.
- Calidad mínima aceptable: permite igual o superior, nunca inferior.

### 2. Marca
- Ignorada por defecto.
- Solo se protege si el usuario lo indica expresamente.

### 3. Formato flexible
- Permite equivalencias por peso, volumen, unidades, lavados, rollos, hojas, etc.
- Ejemplo: 12 rollos = 2 packs de 6 si hace falta.

### 4. Ofertas
- Entran automáticamente si mantienen la calidad y abaratan el coste normalizado.

### 5. Tienda única vs cesta dividida
El optimizador calcula:
- mejor cesta comprando todo en una sola tienda;
- mejor cesta repartida entre varias tiendas.

### 6. Umbral de ahorro
La cesta dividida solo se recomienda si el ahorro adicional supera el mínimo definido.
Valor inicial: 3 €.

### 7. Máximo de tiendas
Por defecto, hasta 2 supermercados.
Puede configurarse a 1, 2 o 3.

### 8. Coste real
El motor ya acepta:
- coste de desplazamiento por tienda para compra física;
- coste de envío/preparación para compra online.

Estos importes se suman al precio de productos antes de recomendar una opción.

## Resultado
CestaSmart devuelve:
- mejor tienda única;
- mejor cesta dividida;
- ahorro entre ambas;
- recomendación final;
- motivo de la recomendación.
