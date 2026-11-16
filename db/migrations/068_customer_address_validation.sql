-- 068_customer_address_validation.sql — the address is checked before it is trusted.
--
-- `address` has been free text since the first schema: the bot asked and
-- whatever arrived was stored. A fictional address costs a technician a trip,
-- so the capture now checks the street and its numbering against the official
-- street master (INE/IDE Chile Maestro de Calles, CC BY 4.0, shipped offline).
--
-- The outcome travels with the address: `direccion_estado` says how far the
-- check got, `direccion_fuente` says who provided the truth, and the nullable
-- coordinates let the WhatsApp location pin fill them later without a second
-- migration. `direccion_estado` is deliberately `text` with a CHECK and not a
-- new enum type: the panel reads these states and the chat flow writes them,
-- and ALTER TYPE inside the shared migration transaction is a worse trade than
-- a constraint that fails loudly on a typo.

ALTER TABLE customers
    ADD COLUMN direccion_estado text,
    ADD COLUMN direccion_fuente text,
    ADD COLUMN direccion_lat double precision,
    ADD COLUMN direccion_lon double precision,
    ADD COLUMN direccion_validada_at timestamptz,
    ADD CONSTRAINT customers_direccion_estado_check
        CHECK (direccion_estado IS NULL OR direccion_estado IN (
            'validada',
            'sin_numeracion',
            'dudosa',
            'no_encontrada',
            'sin_referencia',
            'cliente'
        )),
    ADD CONSTRAINT customers_direccion_fuente_check
        CHECK (direccion_fuente IS NULL OR direccion_fuente IN (
            'callejero',
            'pin',
            'cliente'
        )),
    ADD CONSTRAINT customers_direccion_lat_check
        CHECK (direccion_lat IS NULL OR direccion_lat BETWEEN -90 AND 90),
    ADD CONSTRAINT customers_direccion_lon_check
        CHECK (direccion_lon IS NULL OR direccion_lon BETWEEN -180 AND 180),
    ADD CONSTRAINT customers_direccion_coords_together_check
        CHECK ((direccion_lat IS NULL) = (direccion_lon IS NULL));

-- The panel filters "addresses the master could not confirm" when an operator
-- reviews a visit; the partial index keeps that query off a full scan without
-- paying for the rows where nothing was recorded.
CREATE INDEX idx_customers_direccion_estado
    ON customers (direccion_estado)
    WHERE direccion_estado IS NOT NULL;

-- Rollback: DROP INDEX idx_customers_direccion_estado; ALTER TABLE customers DROP CONSTRAINT customers_direccion_coords_together_check, DROP CONSTRAINT customers_direccion_lon_check, DROP CONSTRAINT customers_direccion_lat_check, DROP CONSTRAINT customers_direccion_fuente_check, DROP CONSTRAINT customers_direccion_estado_check, DROP COLUMN direccion_validada_at, DROP COLUMN direccion_lon, DROP COLUMN direccion_lat, DROP COLUMN direccion_fuente, DROP COLUMN direccion_estado;
