from datetime import date
import json

class InitialPlanSolverData:

	def __init__(self, maxDummy = 3):

		self.Rooms = [] 
		
		self.NumberOfRooms = 0
		self.FullyBookedDays = []
		
		self.AdjacentRooms = []
		self.RoomAdjacencyLists = {} # dictionary of lists rm: [rooms adj to rm]
		self.StayAdjacencyLists = {} # dictionary by adj group name, grp:[stays in grp]
		self.StayToAdjGroupDict = {}
		
		self.NumberOfRealReservations = 0
		
		self.MaxDummyMultiple = maxDummy
		
		self.MinStay = 5
		self.MinStayByDay = {}
		
		self.GroupDict = {}
		self.IdDict = {}
		self.StayDict = {}
		
		
		self.ReservationRoomTypes = {} # dict of int res index to list of allowable room types
		self.TypeToRooms = {} # dict of room types to list of room numbers
		self.RoomsToTypes = {} # dict of room number to type
		
		self.TestDict = {}
		self.SplitGroups = {}
		
		self.StartDict = {}
		self.LengthDict = {}
		self.FixedRooms = {}
		self.FixedForSolver = {}
		
		self.DummyStays = {}
		
		self.MinStart = -1
		self.MaxStart = -1
		self.MaxEnd = -1
		
		self.ScheduleStart = -1
		self.ScheduleEnd = -1
		
		self.OptimalSolution = {}
		
		self.RequestStart = -1
		self.RequestEnd = float("inf")
		
		self.NonAdjacentAssignmentsPerGroup = {} # group labels for groups 
					# that can't be assigned adjacent rooms. 
					# return this in the result AND use for determining
					# whether to relax the adjacency criterion in the 
					# restriction part. 
											
		
		self.HeuristicEmphasis = None
		self.RelGapTol = 0.01
		
		self.InitialPlan = {}
		self.CurrentReservationsWithoutAssignedRoom = 0
		
		self.Exceptions = ""
		
	def Initialize(self, problemData, withAdditionalRoomTypes = False, fitNewReservationInInitialPlan = False):
		self.CurrentReservationsWithoutAssignedRoom = 0
		if problemData.RequestStartDate is not None:		
			self.RequestStart = date.toordinal(date.fromisoformat(problemData.RequestStartDate))
	
		if problemData.RequestEndDate is not None:
			self.RequestEnd = date.toordinal(date.fromisoformat(problemData.RequestEndDate))
			
		self.Rooms = [rm.RoomNumber for rm in problemData.Rooms]
		self.NumberOfRooms = len(self.Rooms)

		self.TypeToRooms = {} # dict of room types to list of room numbers
		self.RoomsToTypes = {} #
		
		for i in range(self.NumberOfRooms):
			room = problemData.Rooms[i]	
			if room.RoomType is None:
				room.RoomType = "Default"
			
			if room.RoomType not in self.TypeToRooms:
				self.TypeToRooms[room.RoomType] = []
			self.TypeToRooms[room.RoomType].append(room.RoomNumber)
			self.RoomsToTypes[room.RoomNumber] = room.RoomType
			
			allowableAdjacentRooms = [r for r in room.AdjacentRooms if r in self.Rooms]
			
			if len(allowableAdjacentRooms) > 0:
				self.RoomAdjacencyLists[room.RoomNumber] = allowableAdjacentRooms
				self.AdjacentRooms.append(room.RoomNumber)
		
		availableRoomTypes = list(self.TypeToRooms.keys())
		
		adjacentStayDict = {}
		
		self.NumberOfRealReservations = len(problemData.Reservations) + len(problemData.NewReservations)
		
		startDates = []
		endDates = []
		
		incoming_reservations = [r for r in problemData.Reservations] 
		
		for r in problemData.NewReservations: 
			r.Test = True
			incoming_reservations.append(r)
			if r.SplitGroup == None:
				continue
			if r.SplitGroup not in self.SplitGroups:
				self.SplitGroups[r.SplitGroup] = []
		
		exceptions = ""
		for i in range(self.NumberOfRealReservations):
			
			res = incoming_reservations[i]
		
			arrOrd = date.toordinal(date.fromisoformat(res.Arrival))
			self.GroupDict[i] = res.Name
			self.IdDict[i] = res.Id
			self.InitialPlan[i] = res.AssignedRoom if res.AssignedRoom != "" else None
			
			depOrd = arrOrd + res.Length
			startDates.append(arrOrd)
			endDates.append(depOrd)
			self.LengthDict[i] = depOrd - arrOrd
			
			self.StayDict[i] = [arrOrd,depOrd]
			self.TestDict[i] = res.Test
			self.StartDict[i] = arrOrd
			
			allowableTypes = availableRoomTypes
			
			if (res.RoomType is not None and res.RoomType != "Default") or len(res.AllowableRoomTypes)>0:		
				allowableTypes = [res.RoomType]	
				if withAdditionalRoomTypes:
					allowableTypes += res.AllowableRoomTypes

				
			allowableTypes = list(set(allowableTypes))
			if len(res.TypeOrder) > 0:
				order = {res.TypeOrder[i]:i for i in range(len(res.TypeOrder))}
				allowableTypes = sorted(allowableTypes, key = lambda k: order[k] if k in order else 0) 
				
			self.ReservationRoomTypes[i] = allowableTypes # dict of int res index to list of allowable room types
				
			if res.IsLocked :
				self.FixedRooms[i] = res.AssignedRoom
			
			if fitNewReservationInInitialPlan and not res.Test:
				self.FixedForSolver[i] = res.AssignedRoom
				if res.AssignedRoom == None or res.AssignedRoom not in self.Rooms:
					exceptions += f"{res.Name}\n"
					self.CurrentReservationsWithoutAssignedRoom += 1
			
			if arrOrd < self.RequestStart or depOrd > self.RequestEnd:
				if res.AssignedRoom == None or res.AssignedRoom not in self.Rooms:
					self.CurrentReservationsWithoutAssignedRoom += 1
					exceptions += f"{res.Name}\n"
				self.FixedForSolver[i] = res.AssignedRoom
			if depOrd > self.RequestEnd:
				self.FixedForSolver[i] = res.AssignedRoom
			
			if res.AssignedRoom not in self.Rooms and problemData.RestrictionsForInitialPlan:
				self.CurrentReservationsWithoutAssignedRoom += 1
				newBooking = " (New booking)" if res.Test else "" 
				exceptions += f"{res.Name}{newBooking}\n"
			
			if res.SplitGroup in self.SplitGroups:
				self.SplitGroups[res.SplitGroup].append(i)
			
			if res.AdjacencyGroup == "None" or res.AdjacencyGroup == "" or res.AdjacencyGroup == None:
				continue
			
			if res.AdjacencyGroup not in adjacentStayDict:
				adjacentStayDict[res.AdjacencyGroup] = []
			
			self.StayToAdjGroupDict[i] = res.AdjacencyGroup
			adjacentStayDict[res.AdjacencyGroup].append(i)
		
		if len(exceptions) > 1:
			self.Exceptions = f"Reservations:\n{exceptions}Must be assigned rooms externally, or the optimization must be adjusted to include them."
			
		self.StayAdjacencyLists = adjacentStayDict
		self.MinStart = int(min(startDates))
		self.MaxEnd = int(max(endDates))
		self.MaxStart = int(max(startDates))

		self.ScheduleEnd = self.MaxEnd
		if problemData.RequestEndDate is not None:
			self.ScheduleEnd = int(max(self.RequestEnd, max(endDates)))
		self.ScheduleStart = self.MinStart
		if problemData.RequestStartDate is not None:
			self.ScheduleStart = int(min(self.RequestStart, min(startDates)))
		
		self.MinStay = problemData.MinStay
		
		for d in range(self.ScheduleStart,self.ScheduleEnd + 1):
			dayOfWeekLwrCase = date.fromordinal(d).strftime("%a")
			dateString = date.fromordinal(d).strftime('%Y-%m-%d')
			if dayOfWeekLwrCase in problemData.MinimumStayByDay:
				self.MinStayByDay[d] = int(problemData.MinimumStayByDay[dayOfWeekLwrCase])
			else:
				self.MinStayByDay[d] = self.MinStay
		
		for entry in problemData.MinimumStayByDate:
			startOrd = date.toordinal(date.fromisoformat(entry["Start"]))
			endOrd = date.toordinal(date.fromisoformat(entry["End"]))
			minStayPerDate = int(entry["MinimumStay"])
			for d in range(startOrd,endOrd + 1):
				self.MinStayByDay[d] = minStayPerDate					
		
		
	def ClearDummyStays(self):
	
		for l in self.DummyStays:
			for d in self.DummyStays[l]:
				del(self.GroupDict[d])
				del(self.StayDict[d])
				del(self.StartDict[d])
				del(self.LengthDict[d])
			
		self.DummyStays = {}



