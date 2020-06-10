#!/usr/bin/env python3

#import sqlite
import sqlite3

# Setup sqlite

db_file = "sqlite_database"

def setup_sqlite_db(db):
	'''Create the database'''
	conn = None

	try:
		conn = sqlite3.connect(db)
		print("Sqlite3 version: " + sqlite3.version)
		cursor = conn.cursor()
		cursor.execute("CREATE TABLE users(UserID int DEFAULT -1, ElectionsVotedIn TEXT)")
		cursor.execute("CREATE TABLE elections(ElectionID int DEFAULT -1, MessageID int DEFAULT -1, ServerID int DEFAULT -1, UserToStart int DEFAULT -1, Name str DEFAULT election, Desc str DEFAULT description, EndTime int DEFAULT 0, Thumbnail str)")
		cursor.execute("CREATE TABLE servers(ServerID int DEFAULT -1, ElectionChannelID int DEFAULT -1)")
		conn.commit()
		print("Database file successfully created: " + db_file)
	except Error as e:
		print(e)
	finally:
		if conn:
			conn.close()

if __name__ == '__main__':
    setup_sqlite_db(db_file)
