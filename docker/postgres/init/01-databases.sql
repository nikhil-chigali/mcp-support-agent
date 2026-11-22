-- Runs once, as the postgres superuser, when the data volume is first created.
-- Local development credentials only.

-- One role per system, so the boundary rule also holds at the database level:
-- the MCP server's credentials cannot open the store's database, and vice versa.
CREATE ROLE store_app LOGIN PASSWORD 'store_app';
CREATE ROLE cases_app LOGIN PASSWORD 'cases_app';

-- The store ("the customer's system"), plus a throwaway twin for tests and
-- `just migration-check`, which runs `alembic downgrade base`.
CREATE DATABASE store OWNER store_app;
CREATE DATABASE store_test OWNER store_app;

-- The MCP server's case store, plus its throwaway twin.
CREATE DATABASE cases OWNER cases_app;
CREATE DATABASE cases_test OWNER cases_app;

-- New databases let every role connect by default. Take that away, so each
-- database admits only its owner (and the superuser).
REVOKE CONNECT ON DATABASE store, store_test, cases, cases_test FROM PUBLIC;
