package db

import (
	"log"
	"os"
	"time"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
)

var DB *sqlx.DB

func Connect() error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return nil
	}

	conn, err := sqlx.Connect("postgres", dsn)
	if err != nil {
		return err
	}
	conn.SetMaxOpenConns(10)
	conn.SetMaxIdleConns(5)
	conn.SetConnMaxLifetime(time.Hour)
	DB = conn

	schema := `
CREATE TABLE IF NOT EXISTS users (
    chat_id BIGINT PRIMARY KEY,
    username TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);`
	_, err = DB.Exec(schema)
	if err != nil {
		return err
	}

	log.Println("✅ Connected to PostgreSQL and ensured schema.")
	return nil
}

func Close() {
	if DB != nil {
		DB.Close()
	}
}
