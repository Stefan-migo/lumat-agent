# Atribución — extracto del callejero oficial de Chile

`maestro.json.gz` no es un dato inventado ni scrapeado de un tercero: es un
extracto del **Maestro de Calles** publicado por el **Instituto Nacional de
Estadísticas (INE) de Chile**, la misma capa que IDE Chile distribuye como
shapefile de *Ejes Viales*.

| Campo | Valor |
|---|---|
| Obra | Maestro de Calles — Ejes Viales Censo 2017 |
| Autor / institución | Instituto Nacional de Estadísticas (INE) de Chile |
| Fuente | <https://www.ine.gob.cl/herramientas/portal-de-mapas/geodatos-abiertos> |
| Servicio consultado | `services5.arcgis.com/hUyD8u3TeZLKPe4T/arcgis/rest/services/Maestro_Calles/FeatureServer/0` |
| Licencia | Creative Commons Atribución 4.0 Internacional (CC BY 4.0) |
| Extracto generado por | `scripts/build_callejero.py` |

## Qué se conservó y qué se descartó

Se conservó lo que el validador necesita: por comuna, el nombre de la calle y
los rangos de numeración que cada cuadra declara (`INI_IZQ`–`TER_IZQ` y
`INI_DER`–`TER_DER`, un rango por lado). Se descartó la geometría: validar una
dirección requiere el rango, no el trazado, y guardar las polilíneas
multiplicaría el tamaño del archivo sin mejorar la respuesta.

## Cobertura real, medida el 2026-11-16

- 6 de las 7 comunas de `coverage.communes`: Las Condes, Ñuñoa, Lo Barnechea,
  La Reina, Peñalolén y Huechuraba.
- **Colina no está en esta capa.** El maestro cubre la Provincia de Santiago; el
  extracto lo reporta en `communes_without_reference` y el validador devuelve
  `sin_referencia`, nunca `no_encontrada`: no se puede afirmar que una calle no
  existe en una comuna de la que no se tiene dato.
- **51 % de las calles del extracto traen numeración.** El resto existe en el
  maestro sin rangos, y para esas el validador devuelve `sin_numeracion`: la
  calle se verificó, el número no.

Regenerar tras agregar una comuna a `coverage.communes`:

```bash
.venv/bin/python scripts/build_callejero.py
```

El script toma comunas del maestro por su propia grafía (`ÑUÑOA`,
`PEÑALOLÉN`), informa las que no cubre y nunca inventa una.
