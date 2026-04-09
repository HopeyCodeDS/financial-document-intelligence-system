-- Enforce audit log immutability at the DB level.
-- This trigger fires BEFORE any UPDATE or DELETE on audit_log and raises an exception.
-- Applied after Alembic creates the table (see alembic/versions/001_initial_schema.py).

CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log records are immutable — UPDATE and DELETE are forbidden';
END;
$$ LANGUAGE plpgsql;

-- The trigger itself is created in the Alembic migration after the table exists.
-- This file runs at container init (before migrations) so we only define the function here.
