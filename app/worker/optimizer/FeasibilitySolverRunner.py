'''
Solver runner for checking feasibility and optimizing 
one version of the broken allocation
'''

from .Data.ProblemData import ProblemData
from .Data.ProblemResult import ProblemResult
from .Data.Assignment import Assignment
from .Data.Reservation import Reservation
from .Data.ReOptimizedPlan import ReOptimizedPlan

from datetime import date

from . import InitialPlanSolverRunner as sr
from .FixedPlanRestrictions import InitialRestrictions as ir
from . import RestrictionSolverRunner as rsr
from .FixedPlanRestrictions import FinalRestrictions as fr
import json
import time


class FeasibilityRunner:
	def __init__(self):
		self.ReturnDict = True
		self.ProblemData = ProblemData()
		self.Message = ""
		self.NewReservationsInOptimizedPlan = {}
		self.NewReservationsInCurrentPlan = {}
	
	def ConvertOrdinalToString(self, dateDict):
		output = {date.fromordinal(d).strftime('%Y-%m-%d'): dateDict[d] for d in dateDict}
		return(output)
	
	def Run(self, problemJson, returnDict = True):
		self.StartTime = time.time()
		self.ProblemData.FillFromJson(problemJson)
		self.Result = ProblemResult(problemJson["ProblemId"], False)
		self.InitialRunner = sr.InitialPlanSolverRunner(self.ProblemData)
	
		if self.InitialRunner.SolverData.CurrentReservationsWithoutAssignedRoom > 0:
			self.Result.Message += self.InitialRunner.SolverData.Exceptions
			self.Result.Succeeded = False
			resultDict = json.loads(self.Result.JsonSerialize())	
			if returnDict:
				return(self.Result.Succeeded, resultDict)
			return( self.Result.Succeeded, self.Result)

	
		absoluteMaxStayCalculator = ir.InitialRestrictions()
		absoluteMaxStayCalculator.GetOccupancyPerDayAndAbsoluteMaxStays(self.InitialRunner.SolverData, ignoreTest = True)
		# now can use the dict of absolute max stays to check the infeasible new stay: 
		absoluteMaxStays = absoluteMaxStayCalculator.AbsoluteMaxStaysStartingOnDay
		
		returnForMaxStay = False
		for new_r in self.ProblemData.NewReservations:
			newStayArrival = date.fromisoformat(new_r.Arrival)
			newStayArrivalOrdinal = date.toordinal(newStayArrival)
			newStayLength = new_r.Length
			if newStayLength > absoluteMaxStays[newStayArrivalOrdinal]:
				self.Succeeded = False
				returnForMaxStay = True
				self.Result.Succeeded = self.Succeeded
				self.Result.NewReservationInfeasible = True
				self.Message += f"Stay length {newStayLength} on date {newStayArrival} conflicts with fully booked days.\n"
		
		if returnForMaxStay:
			if returnDict:
				resultDict = json.loads(self.Result.JsonSerialize())
				return(self.Succeeded, resultDict)
			return(self.Succeeded, self.Result)
		
		self.OriginalNewReservations = self.ProblemData.NewReservations
		splitReservations = self.SplitReservations(self.ProblemData.NewReservations)
		
		self.ProblemData.NewReservations = splitReservations
		
		self.InitialRunner = sr.InitialPlanSolverRunner(self.ProblemData,allowAdditionalRoomTypes = True, newBookingInInitialPlan = True)
		
		if self.InitialRunner.SolverData.CurrentReservationsWithoutAssignedRoom < 1:
			# then can't do the initial part, because some are missing assignments... 
			self.Succeeded, self.NewReservationsInCurrentPlan = self.InitialRunner.Run()
			self.Result.InitialOptimizationTime = time.time() - self.StartTime
		
		if not self.InitialRunner.Infeasible:
			self.InitialRunner = sr.InitialPlanSolverRunner(self.ProblemData,allowAdditionalRoomTypes = True, newBookingInInitialPlan = False)
			self.Succeeded, self.NewReservationsInOptimizedPlan = self.InitialRunner.Run()	
			self.Result.Succeeded = self.Succeeded	
					
		if not self.Result.Succeeded:		
			self.Result.Message += self.Message
			self.Result.Message += f"Schedule infeasible without new booking: {self.InitialRunner.Infeasible}"
			if returnDict:
				resultDict = json.loads(self.Result.JsonSerialize())
				return(self.Succeeded, resultDict)
			return(self.Succeeded, self.Result)

	
		self.FillResult()
		if not returnDict:
			return(self.Succeeded, self.Result)	
		resultDict = json.loads(self.Result.JsonSerialize())	
		return(self.Succeeded, resultDict)
		
		
		
	def SplitReservations(self, originalReservations):
		newNewRes = []
		splitGroup = 1
		for r in originalReservations:
			startOrdinal = date.toordinal(date.fromisoformat(r.Arrival))
			for d in range(int(r.Length)):
				nr = Reservation()
				nr.Name = r.Name
				nr.RoomType = r.RoomType
				nr.AllowableRoomTypes = r.AllowableRoomTypes
				nr.TypeOrder = r.TypeOrder 
				nr.Arrival = date.fromordinal(startOrdinal).strftime('%Y-%m-%d')
				nr.Length = 1 # int number of days
				nr.AdjacencyGroup = r.AdjacencyGroup 
				nr.SplitGroup = splitGroup
				nr.Test = True
				nr.Id = r.Id
				newNewRes.append(nr)
				startOrdinal += 1
			splitGroup += 1
		return newNewRes
			
		
	def FillResult(self):
		self.InitialRestrictions = ir.InitialRestrictions(self.NewReservationsInOptimizedPlan, self.InitialRunner.SolverData)
		finalRestrictions = fr.FinalRestrictions(self.InitialRestrictions)
		finalRestrictions.Fill(self.InitialRunner.SolverData)
			
			
		self.Result.NonAdjacentAssignments = self.InitialRunner.SolverData.NonAdjacentAssignmentsPerGroup
		self.Result.OptimizedPlan = self.FillLabeledAssignments(self.NewReservationsInOptimizedPlan) #labeledAssignments
		self.Result.InitialPlanWithNewReservations = self.FillLabeledAssignments(self.NewReservationsInCurrentPlan)
		self.Result.ClosedArrivals = self.ConvertOrdinalToString(finalRestrictions.ClosedArrival)
		self.Result.ClosedDepartures  = self.ConvertOrdinalToString(finalRestrictions.ClosedDeparture)
		self.Result.MinStays  = self.ConvertOrdinalToString(finalRestrictions.MinStayCoveringDay)
		self.Result.MaxStays  = self.ConvertOrdinalToString(finalRestrictions.MaxStayCoveringDay)
		self.Result.ScheduleStart = date.fromordinal(self.InitialRunner.SolverData.ScheduleStart).strftime('%Y-%m-%d')
		self.Result.ScheduleEnd = date.fromordinal(self.InitialRunner.SolverData.ScheduleEnd).strftime('%Y-%m-%d')
		self.Result.Rooms = self.ProblemData.Rooms
		self.Result.TotalTime = time.time() - self.StartTime
		
		self.FillQualityComparison()
	
	
	def FillLabeledAssignments(self, solverAssignment):
		
		if len(solverAssignment) != len(self.InitialRunner.SolverData.StayDict):
			return(None)
		
		labeledAssignments = []
		labeledDummyAssignments = []
		
		addSplits = len(self.InitialRunner.SolverData.SplitGroups) > 0
		
		for s in self.InitialRunner.SolverData.StayDict: 
			stay = self.InitialRunner.SolverData.StayDict[s]
			
			arr = date.fromordinal(stay[0])
			adjGrp = None
			if s in self.InitialRunner.SolverData.StayToAdjGroupDict:
				adjGrp = self.InitialRunner.SolverData.StayToAdjGroupDict[s]	
			
			if self.InitialRunner.SolverData.TestDict[s] and addSplits:
				continue
			
			labeledAssignments.append(Assignment(
									self.InitialRunner.SolverData.GroupDict[s],
									s in self.InitialRunner.SolverData.FixedRooms,
									solverAssignment[s],
									arr.strftime('%Y-%m-%d'), 
									stay[1] - stay[0], adjGrp,
									test = self.InitialRunner.SolverData.TestDict[s],
									grpId = self.InitialRunner.SolverData.IdDict[s]
									)
								)
		
		for g in self.InitialRunner.SolverData.SplitGroups:
			group = self.InitialRunner.SolverData.SplitGroups[g]
			s = group[0]
			stay = self.InitialRunner.SolverData.StayDict[s]
			arr = date.fromordinal(stay[0])
			
			assignedRoom = solverAssignment[s]
			length = 1
						
			adjGrp = None
			if s in self.InitialRunner.SolverData.StayToAdjGroupDict:
				adjGrp = self.InitialRunner.SolverData.StayToAdjGroupDict[s]
			
			name = f"{self.InitialRunner.SolverData.GroupDict[s]}, split {g}"
			
			assgnmt = Assignment(name,
									s in self.InitialRunner.SolverData.FixedRooms,
									solverAssignment[s],
									arr.strftime('%Y-%m-%d'), 
									length, adjGrp,
									test = self.InitialRunner.SolverData.TestDict[s],
									grpId = self.InitialRunner.SolverData.IdDict[s])
			assgnmt.SplitGroup = g

			for i in range(1, len(group)):
					
				if assignedRoom == solverAssignment[group[i]]:
					assgnmt.Length += 1
				
				else:
					labeledAssignments.append(assgnmt)
					addIt = False
					s = group[i]
					stay = self.InitialRunner.SolverData.StayDict[s]
					arr = date.fromordinal(stay[0])
					assignedRoom = solverAssignment[s]
					assgnmt = Assignment(name,
									s in self.InitialRunner.SolverData.FixedRooms,
									solverAssignment[s],
									arr.strftime('%Y-%m-%d'), 
									length, adjGrp,
									test = self.InitialRunner.SolverData.TestDict[s],
									grpId = self.InitialRunner.SolverData.IdDict[s])
					assgnmt.SplitGroup = g
				if i == len(group) - 1:
					labeledAssignments.append(assgnmt)
		return(labeledAssignments)
		
	def FillQualityComparison(self):
		# compute the gaps for fitting the new reservations in the current schedule, if feasible
		if self.Result.InitialPlanWithNewReservations is None:
			return()
		
		initRestrictions = ir.InitialRestrictions(self.NewReservationsInCurrentPlan, self.InitialRunner.SolverData)
		finalRestrictions = fr.FinalRestrictions(initRestrictions)
		finalRestrictions.Fill(self.InitialRunner.SolverData)
		self.Result.InitialMinStays = self.ConvertOrdinalToString(finalRestrictions.MinStayCoveringDay)
		
		self.Result.QualityComparison = {d : {"Initial":0, "Optimized":0} for d in range(1,self.ProblemData.MinStay + 1)}
		self.Result.RoomChangeComparison = {f"{n.Name}_{n.Id}" : {"Initial":-1, "Optimized":-1} for n in self.OriginalNewReservations}
		
		initSplitGroups = []
		optSplitGroups = []
		
		for assgmt in self.Result.OptimizedPlan:
			if "split" not in assgmt.Name:				
				continue
			keyName = assgmt.Name.split(",")[0]
			key = f"{keyName}_{assgmt.Id}"

			if key in self.Result.RoomChangeComparison:
				self.Result.RoomChangeComparison[key]["Optimized"] += 1
		for assgmt in self.Result.InitialPlanWithNewReservations:
			if "split" not in assgmt.Name:				
				continue
			keyName = assgmt.Name.split(",")[0]
			key = f"{keyName}_{assgmt.Id}"
			if key in self.Result.RoomChangeComparison:
				self.Result.RoomChangeComparison[key]["Initial"] += 1
		
		
		for d in self.Result.InitialMinStays:
			if date.toordinal(date.fromisoformat(d)) in initRestrictions.FullyBookedDays:
				continue
			if int(self.Result.MinStays[d]) not in self.Result.QualityComparison:
				self.Result.QualityComparison[int(self.Result.MinStays[d])] = {"Initial":0, "Optimized":0}
			if int(self.Result.InitialMinStays[d]) not in self.Result.QualityComparison:
				self.Result.QualityComparison[int(self.Result.InitialMinStays[d])] = {"Initial":0, "Optimized":0}
			
			self.Result.QualityComparison[int(self.Result.MinStays[d])]["Optimized"] += 1
			self.Result.QualityComparison[int(self.Result.InitialMinStays[d])]["Initial"] += 1
		

	
	
	

	
	
	

