'''
Class for storing Reservation Data
'''

class Reservation:
	def __init__(self):
		self.Name = ""
		self.IsLocked = False
		self.AssignedRoom = "" # will keep this if locked, otherwise can use to determine adjacent stays
		self.RoomType = ""
		self.Arrival = "" # date as YYYY-MM-DD string
		self.Length = 0 # int number of days
		self.AdjacencyGroup = "" # this format is better because when loading into the 
		# solver data it automatically handles the case of duplicate reservation names
		