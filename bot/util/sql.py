#Modules

#Utility imports
import sys
import sqlite3

class SQLConnector():

    db_file = None

    conn = None
    cursor = None

    def __init__(self, db_file):
	self.db_file = db_file

	def connect(self) -> bool:
		# Create connection with db
		try:
			self.conn = sqlite3.connect(self.db_file)
			self.cursor = self.conn.cursor()
		except Exception as e:
			print(e);
			print("Unable to create a connection with sqlite database `sqlite_database`. It could be corrupted.")
			return False
		return True

	def disconnect(self):
		self.conn.commit() #Make sure everything is saved
		self.conn.close()


	def determine_if_server_exists(self, server_id): #And add the server if not
		self.cursor.execute("SELECT count(*) FROM servers WHERE ServerID = ?", (server_id,))
		if self.cursor.fetchone()[0] == 0:
			self.cursor.execute("INSERT INTO servers VALUES (?, ?, ?)", (server_id, -1, 1))
			self.conn.commit()
			print("\t\tAdded Server")

	def determine_if_user_exists(self, user_id): #And add the user if not
		self.cursor.execute("SELECT count(*) FROM users WHERE UserID = ?", (user_id,))
		if self.cursor.fetchone()[0] == 0:
			self.cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, ""))
			self.conn.commit()
			print("\t\t\tAdded member (" + str(user_id) + ")")

	def setup_database_with_all_users(self, bot):
		for guild in bot.guilds:
			print("\tchecking in server `" + guild.name + "` (" + str(guild.id) + ")")
			self.determine_if_server_exists(guild.id)
			for member in guild.members:
				self.determine_if_user_exists(member.id)
