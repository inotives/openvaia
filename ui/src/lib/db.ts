import postgres from "postgres";

export const SCHEMA = process.env.PLATFORM_SCHEMA || "openvaia";

export const sql = postgres({
  host: process.env.POSTGRES_HOST || "localhost",
  port: Number(process.env.POSTGRES_PORT) || 5432,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  max: 5,
  idle_timeout: 30,
  connect_timeout: 5,
});

// Warm the connection pool on startup
sql`SELECT 1`.catch(() => {});
