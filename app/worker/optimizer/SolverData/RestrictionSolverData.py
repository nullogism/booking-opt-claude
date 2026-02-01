
import numpy as np



class RestrictionSolverData:
	
	def __init__(self, initPlanSolverData):
		
		self.InitialSolution = initPlanSolverData.OptimalSolution
		
		self.Rooms = initPlanSolverData.Rooms
		
		self.NumberOfRooms = initPlanSolverData.NumberOfRooms
		
		self.AdjacentRooms = initPlanSolverData.AdjacentRooms
		self.RoomAdjacencyLists = initPlanSolverData.RoomAdjacencyLists
		self.StayAdjacencyLists = initPlanSolverData.StayAdjacencyLists
		
		self.NumberOfRealReservations = initPlanSolverData.NumberOfRealReservations
		
		self.MaxDummyMultiple = 2 # this needs to be 2x min stay, 
		# otherwise things longer than min stay will be unfairly penalized 
		# due to the added short stays to extend the gap... 
		
		self.MinStay = initPlanSolverData.MinStay
		self.MinStayByDay = initPlanSolverData.MinStayByDay
		
		self.ReservationRoomTypes = initPlanSolverData.ReservationRoomTypes # dict of int res index to list of allowable room types
		self.TypeToRooms = initPlanSolverData.TypeToRooms # dict of room types to list of room numbers
		self.RoomsToTypes = initPlanSolverData.RoomsToTypes # dict of room number to type
		
		self.GroupDict = initPlanSolverData.GroupDict
		self.StayDict = initPlanSolverData.StayDict
		self.StartDict = initPlanSolverData.StartDict
		self.LengthDict = initPlanSolverData.LengthDict
		self.FixedRooms = initPlanSolverData.FixedRooms
		
		self.FullyBookedDays = initPlanSolverData.FullyBookedDays
		
		self.DummyStays = {} # these get filled separately 
		
		self.MinStart = initPlanSolverData.MinStart
		self.MaxStart = initPlanSolverData.MaxStart
		self.MaxEnd = initPlanSolverData.MaxEnd
		

		self.ScheduleStart = initPlanSolverData.ScheduleStart
		self.ScheduleEnd = initPlanSolverData.ScheduleEnd
		
		self.TestName = "test_min_max"

		
		self.DummyOptimizedAssignments = {}# {(day,length): {}}
		
		self.NonAdjacentAssignmentsPerGroup = initPlanSolverData.NonAdjacentAssignmentsPerGroup
	
	
	def ClearDummyStays(self):
	
		for l in self.DummyStays:
			for d in self.DummyStays[l]:
				del(self.GroupDict[d])
				del(self.StayDict[d])
				del(self.StartDict[d])
				del(self.LengthDict[d])
			
		self.DummyStays = {}

	def AddNewReservation(self, startDate, length):
		self.ClearDummyStays()
		key = len(self.StayDict)
		
		self.GroupDict[key] = self.TestName
		
		self.StayDict[key] = [startDate, startDate + length]
		self.StartDict[key] = startDate
		self.LengthDict[key] = length
		
		return(key)
	
	
	def RemoveNewReservation(self, key):
		del(self.GroupDict[key])
		del(self.StayDict[key])
		del(self.StartDict[key])
		del(self.LengthDict[key])
		return()
	
	
	def FillDummyStays(self, minNightStays ={}, absoluteMaxStays={}):
		
		j = len(self.StayDict)
			
		lastArrival = sorted([d[0] for d in self.StayDict.values()],reverse = True)[0]
		departuresAfterLastArrival = [s[1] for s in self.StayDict.values() if s[1] >= lastArrival]
		departuresAfterLastArrival.append(lastArrival)
		departuresAfterLastArrival = sorted(list(set(departuresAfterLastArrival)))
		
		firstDeparture = sorted([d[1] for d in self.StayDict.values()])[0]
		
		arrivalsBeforeAnyDep = [s[0] for s in self.StayDict.values() if s[0] <= firstDeparture]
		arrivalsBeforeAnyDep.append(firstDeparture)
		arrivalsBeforeAnyDep = sorted(list(set(arrivalsBeforeAnyDep)))
		
		
		for i in range(len(arrivalsBeforeAnyDep)-1):
			
			start = int(arrivalsBeforeAnyDep[i])
			end = int(arrivalsBeforeAnyDep[i+1])
			length = end - start			
			
			if length not in self.DummyStays:
				self.DummyStays[length] = []
			
			self.GroupDict[j] = -1
			
			self.StayDict[j] = [start, end]
			self.StartDict[j] =  start
			self.LengthDict[j] = length
			self.DummyStays[length].append(j)
			j += 1
	
		for i in range(len(departuresAfterLastArrival)):
			
			start = int(departuresAfterLastArrival[i])
			end = int(self.MaxEnd + 1)
			length = int(end - start)			
			
			if length not in self.DummyStays:
				self.DummyStays[length] = []
			
			self.GroupDict[j] = -1
			
			self.StayDict[j] = [start, end]
			self.StartDict[j] =  start
			self.LengthDict[j] = length
			self.DummyStays[length].append(j)
			j += 1
			
		# need to make sure that the dummy stays go right up to the end 
		# of the schedule! Otherwise the clique constraints may cause problems... 
		for i in range(self.MaxEnd - self.MinStart):
			done = False
			minStay = self.MinStayByDay[self.MinStart + i]
			for days in range(1 ,int(minStay * self.MaxDummyMultiple + 1)):
				if done:
					continue
				if days not in self.DummyStays:
					self.DummyStays[days] = []
				if self.CheckInFeasibility(days, i + self.MinStart, minNightStays, absoluteMaxStays):
					# do not add gaps that are less than the mns for this day
					# or greater than possible
					# 
					continue
				
				elif i + self.MinStart < firstDeparture or i + self.MinStart > lastArrival :
					continue
				
				elif i + self.MinStart in self.FullyBookedDays:
					continue
				
				elif self.MinStart + i + days <= self.MaxEnd + 1:			
	
					self.GroupDict[j] = -1
					self.StayDict[j] = [self.MinStart + i, self.MinStart + i + days]
					self.StartDict[j] =  self.MinStart + i
					self.LengthDict[j] = days
					self.DummyStays[days].append(j)
					j += 1
				
				if self.MinStart + i + days in self.FullyBookedDays:
					done = True
		
	
	def CheckInFeasibility(self, length, day, minStays= {}, maxNightStays = {}):
		# always leave the dummy stays at the ends and beginning for feasibility's sake
		# But do not need to add short dummies before/after the real bookings
		if day < self.MinStart and length < self.MinStart - day:
			return(False)
		if day + length > self.ScheduleEnd:
			return(False)
		if day >= self.MaxEnd - 1 and length < self.ScheduleEnd - day:
			# do not need to add short stays at the end of the schedule
			return(False)
			
		minStayInFeas = False
		if day in minStays:
			if length < minStays[day]:

				minStayInFeas = True
		
		maxStayInFeas = False
		if day in maxNightStays:
			if length > maxNightStays[day]:
				maxStayInFeas = True
				
		return(minStayInFeas or maxStayInFeas)
		
		
	

			
