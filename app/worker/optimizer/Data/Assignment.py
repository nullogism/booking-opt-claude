'''
Class for storing optimized assignment data
'''

class Assignment:
	def __init__(self, name = None, isLocked = False, assignedRoom = None, arrival = None, 
	length = None, adjGrp = None, test = False, grpId = None):
		self.Name = name
		self.Id = grpId
		self.IsLocked = isLocked
		self.AssignedRoom = assignedRoom # will keep this if locked, otherwise can use to determine adjacent stays
		self.RoomType = ""
		self.Arrival = arrival # date as YYYY-MM-DD string
		self.Length = length # int number of days
		self.AdjacencyGroup = adjGrp # this format is better because when loading into the 
		self.TestStay = test
		self.SplitGroup = None
		# solver data it automatically handles the case of duplicate reservation names
		