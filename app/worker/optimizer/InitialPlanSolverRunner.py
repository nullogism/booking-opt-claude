
from .Models.InitialPlanSolver import InitialPlanSolver
from .SolverData import InitialPlanSolverData as initData 
from datetime import date

class InitialPlanSolverRunner:
	def __init__(self, problemData, maxDummy = 2, allowAdditionalRoomTypes = False, newBookingInInitialPlan = False):
		self.SolverData = initData.InitialPlanSolverData(maxDummy = maxDummy)
		self.SolverData.Initialize(problemData, withAdditionalRoomTypes = allowAdditionalRoomTypes, fitNewReservationInInitialPlan = newBookingInInitialPlan)
		
		
		self.Assignment = {}
		self.Infeasible = False
		self.RestrictionsOnly = problemData.RestrictionsForInitialPlan
	
	

	def Run(self):		
		solver = InitialPlanSolver(self.SolverData)
		
		if self.RestrictionsOnly: 
			print("got here")
			solver.OptimizationAssignments = self.SolverData.InitialPlan
			solver.Succeeded = True
			self.SolverData.NonAdjacentAssignmentsPerGroup = solver.CheckAdjacentAssignments()
			return(True, self.SolverData.InitialPlan)
		
		
		self.FillDummyStays()	

		
		solver.OptimizeSchedule()
		if not solver.Succeeded:
			self.Infeasible = solver.ProvedInfeasible
		else:
			solver.GetInitialPlan()
			self.SolverData.OptimalSolution = solver.Solution
			
			self.SolverData.NonAdjacentAssignmentsPerGroup = solver.CheckAdjacentAssignments()
			
		
		self.SolverData.ClearDummyStays()
			
	
		
		return(solver.Succeeded, solver.OptimizationAssignments)
	
	
	def FillDummyStays(self):
		'''
		Need to update this for cases when there aren't enough bookings to make
		the fancy gaps calculations work.
		'''
		self.SolverData.DummyStays = {}
		j = len(self.SolverData.StayDict)
		
		roomTypes = list(self.SolverData.TypeToRooms.keys()) 
		
		# need to make sure that the dummy stays go right up to the end 
		# of the schedule! Otherwise the clique constraints may cause problems... 	
		
		self.SolverData.FullyBookedDays = []
		fullOcc = self.SolverData.NumberOfRooms
		
		for i in range(self.SolverData.ScheduleEnd - self.SolverData.ScheduleStart):
			occ = 0
			for s in self.SolverData.StayDict:
				max1 = self.SolverData.StayDict[s][1]
				min1 = self.SolverData.StayDict[s][0]
				if min1 <= self.SolverData.ScheduleStart + i and max1 > self.SolverData.ScheduleStart +i:
					occ += 1
			if occ == fullOcc:
				self.SolverData.FullyBookedDays.append(self.SolverData.ScheduleStart + i)
		self.SolverData.FullyBookedDays.append(self.SolverData.ScheduleEnd + 1)
		
		
		lastArrival = sorted([d[0] for d in self.SolverData.StayDict.values()],reverse = True)[0]
		departuresAfterLastArrival = [s[1] for s in self.SolverData.StayDict.values() if s[1] >= lastArrival]
		departuresAfterLastArrival.append(lastArrival)
		departuresAfterLastArrival = sorted(list(set(departuresAfterLastArrival)))
		
		firstDeparture = sorted([d[1] for d in self.SolverData.StayDict.values()])[0]
		
		arrivalsBeforeAnyDep = [s[0] for s in self.SolverData.StayDict.values() if s[0] <= firstDeparture]
		if self.SolverData.ScheduleStart < self.SolverData.MinStart:
			arrivalsBeforeAnyDep.append(self.SolverData.ScheduleStart)
		arrivalsBeforeAnyDep.append(firstDeparture)
		arrivalsBeforeAnyDep = sorted(list(set(arrivalsBeforeAnyDep)))
		
		'''
		all the dummy stays need to be eligible for all the 
		room types!!!
		
		that way still only have one set of dummy vars.
		'''
	
		'''
		Try to add something that streamlines the number of 
		dummy stays in periods where the hotel is empty... 
		like in between the last departure and first arrival only need dummies 
		for +/- the min stay 
		
		
		(if get too cute and leave out the +/- min stay it can cause issues 
		with placing real bookings)
		'''

		for i in range(len(arrivalsBeforeAnyDep)-1):
			
			start = int(arrivalsBeforeAnyDep[i])
			end = int(arrivalsBeforeAnyDep[i+1])
			length = end - start			
			
			if length not in self.SolverData.DummyStays:
				self.SolverData.DummyStays[length] = []
			
			self.SolverData.GroupDict[j] = -1
			
			self.SolverData.StayDict[j] = [start, end]
			self.SolverData.StartDict[j] =  start
			self.SolverData.LengthDict[j] = length
			self.SolverData.DummyStays[length].append(j)
			self.SolverData.ReservationRoomTypes[j] = roomTypes
			
			j += 1
		
		
		for i in range(len(departuresAfterLastArrival)):
			start = int(departuresAfterLastArrival[i])
			end = int(self.SolverData.ScheduleEnd + 1)
			length = int(end - start)			
	
			if length not in self.SolverData.DummyStays:
				self.SolverData.DummyStays[length] = []
			
			self.SolverData.GroupDict[j] = -1
			
			self.SolverData.StayDict[j] = [start, end]
			self.SolverData.StartDict[j] =  start
			self.SolverData.LengthDict[j] = length
			self.SolverData.DummyStays[length].append(j)
			self.SolverData.ReservationRoomTypes[j] = roomTypes
			j += 1
			
		for i in range(self.SolverData.ScheduleEnd - self.SolverData.ScheduleStart): 
			
			done = False
			dayOrdinal = i + self.SolverData.ScheduleStart

			minStayForThisDay = self.SolverData.MinStayByDay[dayOrdinal] 
			for days in range(1 ,int(minStayForThisDay * self.SolverData.MaxDummyMultiple + 1)):
				if done: 
					continue
				
				if days not in self.SolverData.DummyStays:
					self.SolverData.DummyStays[days] = []
			

				if self.CheckInFeasibility(days, dayOrdinal):
					# do not add gaps that are less than the mns for this day
					# or greater than schedule length.
					continue
				
				if dayOrdinal < firstDeparture - minStayForThisDay or dayOrdinal > lastArrival+ minStayForThisDay :
 					continue
			
				if dayOrdinal in self.SolverData.FullyBookedDays:
					continue
				
				if dayOrdinal + days <= self.SolverData.ScheduleEnd + 1:			
					self.SolverData.GroupDict[j] = -1
					self.SolverData.StayDict[j] = [dayOrdinal, dayOrdinal+ days]
					self.SolverData.StartDict[j] =  dayOrdinal
					self.SolverData.LengthDict[j] = days
					self.SolverData.DummyStays[days].append(j)
					self.SolverData.ReservationRoomTypes[j] = roomTypes
					j += 1
				
				if dayOrdinal + days in self.SolverData.FullyBookedDays:
					done = True
	
	def CheckInFeasibility(self, length, day):
		# always leave the dummy stays at the ends and beginning for feasibility's sake
		# But do not need to add short dummies before/after the real bookings
		if day < self.SolverData.ScheduleStart and length < self.SolverData.ScheduleStart - day:
			return(False)
		if day + length > self.SolverData.ScheduleEnd:
			return(False)
		if day >= self.SolverData.ScheduleEnd - 1 and length < self.SolverData.ScheduleEnd - day:
			# do not need to add short stays at the end of the schedule
			return(False)

		