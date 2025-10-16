package db

import (
    "database/sql"
    _ "github.com/lib/pq"
    "log"
)

func Connect() *sql.DB {
    dsn := "postgres://bot:botpass@postgres-service:5432/ludic?sslmode=disable"
    db, err := sql.Open("postgres", dsn)
    if err != nil {
        log.Fatal(err)
    }

    if err := db.Ping(); err != nil {
        log.Fatal(err)
    }

    log.Println("Connected to database")
    return db
}
