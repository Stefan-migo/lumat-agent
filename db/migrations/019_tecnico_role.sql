-- 019_tecnico_role.sql — additive technician panel role.

ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'tecnico';
