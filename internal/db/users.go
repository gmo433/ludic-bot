package db

import "log"

type User struct {
	ChatID    int64  `db:"chat_id"`
	Username  string `db:"username"`
	CreatedAt string `db:"created_at"`
}

func AddUser(chatID int64, username string) error {
	if DB == nil {
		return nil
	}
	_, err := DB.Exec(`INSERT INTO users (chat_id, username)
		VALUES ($1, $2)
		ON CONFLICT (chat_id) DO NOTHING;`, chatID, username)
	if err != nil {
		log.Printf("DB AddUser error: %v", err)
	}
	return err
}

func RemoveUser(chatID int64) error {
	if DB == nil {
		return nil
	}
	_, err := DB.Exec(`DELETE FROM users WHERE chat_id=$1;`, chatID)
	if err != nil {
		log.Printf("DB RemoveUser error: %v", err)
	}
	return err
}

func GetAllUsers() ([]User, error) {
	if DB == nil {
		return nil, nil
	}
	var users []User
	err := DB.Select(&users, `SELECT chat_id, username, created_at FROM users;`)
	if err != nil {
		log.Printf("DB GetAllUsers error: %v", err)
	}
	return users, err
}
