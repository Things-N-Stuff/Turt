
db_file = "sqlite_database"

cursor = None

#For the reaction emojis - Note how each number string relates to index
numbers = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "keycap_ten"] 
numbers_emoji_bytes = [b'1\xef\xb8\x8f\xe2\x83\xa3', #Look at the beginning numbers
                        b'2\xef\xb8\x8f\xe2\x83\xa3',
			b'3\xef\xb8\x8f\xe2\x83\xa3',
			b'4\xef\xb8\x8f\xe2\x83\xa3',
			b'5\xef\xb8\x8f\xe2\x83\xa3',
			b'6\xef\xb8\x8f\xe2\x83\xa3',
			b'7\xef\xb8\x8f\xe2\x83\xa3',
			b'8\xef\xb8\x8f\xe2\x83\xa3',
			b'9\xef\xb8\x8f\xe2\x83\xa3',
			b'\xf0\x9f\x94\x9f'] #ten

bot = None

thumbsup = b'\xf0\x9f\x91\x8d'
thumbsdown = b'\xf0\x9f\x91\x8e'

new_election = "New Election: "
election_over = "Election Concluded: "
