-- Розмежування доступу. Групові ролі (NOLOGIN) несуть права, облікові записи (LOGIN) лише входять у групи.
-- Паролі передаються змінними psql (-v), у репозиторій не потрапляють.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'loader')      THEN CREATE ROLE loader      NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'transformer') THEN CREATE ROLE transformer NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analyst')     THEN CREATE ROLE analyst     NOLOGIN; END IF;
END $$;
DROP ROLE IF EXISTS etl_user;     CREATE ROLE etl_user     LOGIN PASSWORD :'etl_pw'     IN ROLE loader;
DROP ROLE IF EXISTS dbt_user;     CREATE ROLE dbt_user     LOGIN PASSWORD :'dbt_pw'     IN ROLE transformer;
DROP ROLE IF EXISTS analyst_user; CREATE ROLE analyst_user LOGIN PASSWORD :'analyst_pw' IN ROLE analyst;

-- ніхто, крім явно дозволених, не підключається і не створює об'єктів
REVOKE ALL ON DATABASE ednet FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE ednet TO loader, transformer, analyst;

-- loader: пише сирий і оперативний рівні
GRANT USAGE ON SCHEMA raw, core TO loader;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA raw, core TO loader;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA core TO loader;

-- transformer: читає core, будує вітрини в marts
GRANT USAGE ON SCHEMA core TO transformer;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO transformer;
GRANT USAGE, CREATE ON SCHEMA marts TO transformer;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA marts TO transformer;

-- analyst: лише читання вітрин і довідника частин; обмеження часу запиту захищає від випадкових важких запитів
GRANT USAGE ON SCHEMA marts, core TO analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO analyst;
GRANT SELECT ON core.part TO analyst;
ALTER ROLE analyst_user SET statement_timeout = '60s';
ALTER DEFAULT PRIVILEGES FOR ROLE dbt_user IN SCHEMA marts GRANT SELECT ON TABLES TO analyst;
