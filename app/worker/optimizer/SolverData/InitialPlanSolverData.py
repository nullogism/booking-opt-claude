from datetime import date
import json

class InitialPlanSolverData:
	def __init__(self, maxDummy = 3):
		
		self.Rooms = []
		
		self.NumberOfRooms = 0
		
		self.AdjacentRooms = []
		self.RoomAdjacencyLists = {} # dictionary of lists rm: [rooms adj to rm]
		self.StayAdjacencyLists = {} # dictionary by adj group name, grp:[stays in grp]
		self.StayToAdjGroupDict = {}
		
		self.NumberOfRealReservations = 0
		
		self.MaxDummyMultiple = maxDummy
		
		self.MinStay = 5
		
		self.GroupDict = {}
		self.StayDict = {}
		self.StartDict = {}
		self.LengthDict = {}
		self.FixedRooms = {}
		
		self.DummyStays = {}
		
		self.MinStart = -1
		self.MaxStart = -1
		self.MaxEnd = -1
		
		self.ScheduleStart = -1
		self.ScheduleEnd = -1
		self.OptimalSolution = {}
		
		
	def Initialize(self, problemData):
		
		
		self.MinStay = problemData.MinStay
		# probably have to do some error handling
		adjacentStayDict = {}
		
		self.NumberOfRealReservations = len(problemData.Reservations)
		
		startDates = []
		endDates = []
		
		for i in range(self.NumberOfRealReservations):
			res = problemData.Reservations[i]
			
			self.GroupDict[i] = res.Name
			
			arrOrd = date.toordinal(date.fromisoformat(res.Arrival))
			depOrd = arrOrd + res.Length
			startDates.append(arrOrd)
			endDates.append(depOrd)
			self.LengthDict[i] = depOrd - arrOrd
			
			self.StayDict[i] = [arrOrd,depOrd]
			self.StartDict[i] = arrOrd
			
			if res.IsLocked :
				self.FixedRooms[i] = res.AssignedRoom
			
			if res.AdjacencyGroup == "None":
				continue
			
			# the adjacent stay group set up is good because it automatically 
			# handles the case of duplicate group names for adjacent stays
			if res.AdjacencyGroup not in adjacentStayDict:
				adjacentStayDict[res.AdjacencyGroup] = []
			
			self.StayToAdjGroupDict[i] = res.AdjacencyGroup
			adjacentStayDict[res.AdjacencyGroup].append(i)
	
			
		
		self.MinStart = int(min(startDates))
		self.MaxStart = int(max(startDates))
		self.MaxEnd = int(max(endDates))
		self.ScheduleEnd = self.MaxEnd
		self.ScheduleStart = self.MinStart
		
		self.StayAdjacencyLists = adjacentStayDict
		
		self.Rooms = [rm.RoomNumber for rm in problemData.Rooms]
		self.NumberOfRooms = len(self.Rooms)
		for i in range(self.NumberOfRooms):
			room = problemData.Rooms[i]
			if len(room.AdjacentRooms) > 0:
			
				self.RoomAdjacencyLists[room.RoomNumber] = room.AdjacentRooms 
				self.AdjacentRooms.append(room.RoomNumber)
		
	def ClearDummyStays(self):
	
		for l in self.DummyStays:
			for d in self.DummyStays[l]:
				del(self.GroupDict[d])
				del(self.StayDict[d])
				del(self.StartDict[d])
				del(self.LengthDict[d])
			
		self.DummyStays = {}



