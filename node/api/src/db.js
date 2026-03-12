require("dotenv").config();
const { Pool } = require("pg");

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

pool.on("error", (err) => {
  console.error("[API/DB] Błąd połączenia:", err.message);
});

module.exports = pool;
