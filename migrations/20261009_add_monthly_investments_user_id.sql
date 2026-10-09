-- Bring the legacy monthly_investments table in line with the SQLAlchemy model.
-- Existing rows predate multi-user ownership and belong to the default user.

BEGIN;

ALTER TABLE monthly_investments
    ADD COLUMN IF NOT EXISTS user_id INTEGER;

UPDATE monthly_investments
SET user_id = 1
WHERE user_id IS NULL;

ALTER TABLE monthly_investments
    ALTER COLUMN user_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'monthly_investments_user_id_fkey'
          AND conrelid = 'monthly_investments'::regclass
    ) THEN
        ALTER TABLE monthly_investments
            ADD CONSTRAINT monthly_investments_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id);
    END IF;
END
$$;

ALTER TABLE monthly_investments
    DROP CONSTRAINT IF EXISTS unique_year_month_investment;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_user_year_month_investment'
          AND conrelid = 'monthly_investments'::regclass
    ) THEN
        ALTER TABLE monthly_investments
            ADD CONSTRAINT unique_user_year_month_investment
            UNIQUE (user_id, year, month);
    END IF;
END
$$;

COMMIT;
