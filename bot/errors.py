
class NotInServer(Exception): # The whole point of this is to do nothing
	def __init__(self):
		pass
		
class NotWhitelisted(Exception):
	def __init__(self):
		pass
