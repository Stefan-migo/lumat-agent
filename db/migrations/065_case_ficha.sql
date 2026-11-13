-- 065_case_ficha.sql — Fase 3 "el caso existe": linaje de casos y quién decide el gasto.
--
-- D5 (`odd/analysis/lumatdata/03-defectos-y-mejoras.md`): `Case` no referenciaba
-- casos previos, así que una postventa — Antonieta al día siguiente de la
-- mantención, Marcelo Aceituno con una garantía de un año declarada, Pabla Leiva
-- reincidiendo tres veces — se guardaba como un caso suelto sin trabajo anterior
-- al que apuntar. `origin_case_id` es el caso nuevo DECLARANDO de dónde viene; el
-- caso anterior no se reabre ni se modifica.
--
-- D7: la capacidad mínima no es conocer el rol del cliente, es no confirmar
-- precio ni autorizar trabajo a quien no decide. Ese hecho se guarda por persona
-- con default `si`, y sólo se baja cuando la conversación lo demuestra:
--   si   — default: no hay evidencia de lo contrario.
--   duda — hay indicio (nombra a un dueño distinto de quien escribe) sin prueba.
--   no   — la conversación lo demuestra ("soy arrendatario", "consulto con el
--          dueño", "no es mi casa", ...). Ver `app/services/case_ficha.py`.
--
-- Aditiva y reversible; ninguna fila se borra ni se reescribe.

ALTER TABLE cases
    ADD COLUMN origin_case_id bigint REFERENCES cases(id);

CREATE INDEX idx_cases_origin_case_id ON cases (origin_case_id);

ALTER TABLE customers
    ADD COLUMN decide_spending varchar(10) NOT NULL DEFAULT 'si';

ALTER TABLE customers
    ADD CONSTRAINT customers_decide_spending_check
        CHECK (decide_spending IN ('si', 'duda', 'no'));

-- Rollback: ALTER TABLE customers DROP CONSTRAINT customers_decide_spending_check, DROP COLUMN decide_spending; DROP INDEX idx_cases_origin_case_id; ALTER TABLE cases DROP COLUMN origin_case_id;
