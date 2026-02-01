import numpy as np
import math
import csv
from pyscipopt import Model, quicksum
from datetime import date
import time
		

class InitialPlanSolver:
	def __init__(self, inputs, randomSol = False):
		
		self.Solution = {} # dict of variable names to 
		
		self.Inputs = inputs
		self.Time = 0.0
		self.MaxStayTime = 0.0
		
		# Cliques are stays that are all there on a given day, 
		# one list for each day. 
		self.Cliques = []
		
		self.Model = Model()
		
		self.ObjectiveCoefficients = {}
		self.AssignmentVars = {}
		
		 # these are for finding small/large gaps, don't always need
		self.DummyIncentiveVars = {}
		self.DummyStays = []
		
		# list of adjacent reservations:
		self.AdjacentReservations = []

		
		self.Succeeded = False
		self.ProvedInfeasible = False
		self.OptimizationAssignments = {}
		self.RandomSolution = randomSol
		
		self.NonAdjacentAssignedGroups = {} # adj group labels, and res names
											# for stays that couldn't be adjacent  
			
		
	def GetInitialPlan(self, checkDummyAssignments = False):
		self.OptimizationAssignments = {}
		
		if not self.Succeeded:
			return()
		# print("Cliques Added:")
# 		for c in self.cvars:
# 			print(c, self.Model.getVal(self.cvars[c]))
		for i in self.Inputs.StayDict:
			
			dummy = i in self.DummyStays
	
			for j in self.Inputs.Rooms:
				
				aVal = self.Model.getVal(self.AssignmentVars[i,j])
				if aVal > 0.9 and not dummy:
					self.OptimizationAssignments[i] = j
					
				self.Solution[i,j] = aVal
		return()
	
	
	def CheckAdjacentAssignments(self):	
		nonAdjacentStays = {}
		
		for grpName in self.Inputs.StayAdjacencyLists:
			aStays = self.Inputs.StayAdjacencyLists[grpName]
			assignedRooms = [self.OptimizationAssignments[a] for a in aStays]
			adjAssigned = []
			
			for i in range(len(assignedRooms) - 1):
			
				rm1 = assignedRooms[i]
				adjRooms = self.Inputs.RoomAdjacencyLists[rm1] if rm1 in self.Inputs.RoomAdjacencyLists else []
				adj  = False
				for j in range(i+1, len(assignedRooms)):
					rm2 = assignedRooms[j]
					if rm2 in adjRooms:
						adj = True
						adjAssigned.append(aStays[j])
				if adj and aStays[i] not in adjAssigned:
					adjAssigned.append(aStays[i])
			
			nonAdjacentStays[grpName] = [a for a in aStays if a not in adjAssigned]
	
		return(nonAdjacentStays)	
			
		
	def GenerateCliques(self):	
		self.Cliques = []
		stayDict = self.Inputs.StayDict
		for i in range(self.Inputs.ScheduleEnd - self.Inputs.ScheduleStart):
			cliq = []
			
			for s in stayDict:
				resTypes = self.Inputs.ReservationRoomTypes[s]
				max1 = stayDict[s][1]
				min1 = stayDict[s][0]
				types = self.Inputs.ReservationRoomTypes[s]
				if min1 > self.Inputs.ScheduleStart + i or max1 <= self.Inputs.ScheduleStart+i:
					continue		
				cliq.append(s)

			self.Cliques.append(cliq)
				
	
	
	def OptimizeSchedule(self):
		
		start = time.time()
		
		self.GenerateCliques()
		
		self.AddAssignmentModel()
		self.AddAdjacentStaysModel()
		self.AddCliqueConstraints()
		
		splitObj = 0
		if len(self.Inputs.SplitGroups) > 0:
			splitObj = self.SplittingObjective()
		
		side = 1
		if self.RandomSolution: 
			side = -1
		
		nonAdjPenalty = 100 * np.power(2.0,self.Inputs.MinStay)
		obj = splitObj + side*quicksum(self.ObjectiveCoefficients[s]*self.AssignmentVars[s,r] for s in self.ObjectiveCoefficients for r in self.Inputs.Rooms) + nonAdjPenalty*quicksum(self.SlackAdjVars[s,r] for s in self.AdjacentReservations for r in self.Inputs.AdjacentRooms)
			
		#obj = quicksum(self.ObjectiveCoefficients[s]*x[s,r] for s in self.ObjectiveCoefficients for r in rooms) - 10000*quicksum(cvar[k] for k in self.cvars.keys())

		self.Model.setObjective(obj,"minimize")

		
		self.Model.setRealParam('limits/gap', 0.01) # stop at 90% of optimality
		self.Model.setParam('limits/time', 60) # stop after 1 minute
		self.Model.hideOutput(True)
		self.Model.optimize()

		end = time.time()
		
		self.Time += (end-start)

		solsFound = len(self.Model.getSols())
		if self.Model.getStatus() == "infeasible" or solsFound < 1: 
	
			self.Succeeded = False
			self.ProvedInfeasible = self.Model.getStatus() == "infeasible"
					
			return()
		

		self.Succeeded = True
		return()
	
	def AddAssignmentModel(self):

		for s in self.Inputs.StayDict:
			resName = self.Inputs.GroupDict[s]
			for r in self.Inputs.Rooms:
				name = str(s)+ ", " + str(r)
				ub = 1
				'''
				Probably need to add something to set the order for the 
				allowable room types. 
				
				How to specify that? 
				'''
				if self.Inputs.RoomsToTypes[r] not in self.Inputs.ReservationRoomTypes[s]:
					ub = 0
				if resName == -1:
					'''
					I think this should be ok, because the objective will force the best one 
					to be 1, and I don't actually care if there's some wonkiness in the
					final allocation of the dummy stays
					'''
					self.AssignmentVars[s,r] = self.Model.addVar(name, ub = ub, vtype= 'C')
				else:
					self.AssignmentVars[s,r] = self.Model.addVar(name, ub = ub, vtype= 'B')
					
					
		multiplier = max(1, self.Inputs.MaxDummyMultiple)
		
		for s in self.Inputs.StayDict:
				
			if s in self.Inputs.FixedRooms:
				self.Model.addCons(self.AssignmentVars[s,self.Inputs.FixedRooms[s]] == 1)
			if s in self.Inputs.FixedForSolver:
				
				self.Model.addCons(self.AssignmentVars[s,self.Inputs.FixedForSolver[s]] == 1)
				
			if self.Inputs.GroupDict[s] == -1: # i.e. if it's a dummy stay
				
				length = self.Inputs.LengthDict[s]
				self.DummyStays.append(s)
		
				maxGaps = self.Inputs.NumberOfRooms
						
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) <= maxGaps)
				# this incentivizes gaps longer than min stay length
				extra = 0
				
				# need to adjust this to get the desired min stay for each START DATE
				startDayOrdinal = self.Inputs.StayDict[s][0]

				minStayForThisDay = self.Inputs.MinStayByDay[startDayOrdinal] 
				if length < minStayForThisDay:
					extra = 1

				if length + startDayOrdinal >= self.Inputs.ScheduleEnd:
					self.ObjectiveCoefficients[s] = 0
				
				elif startDayOrdinal <= self.Inputs.ScheduleStart:
					self.ObjectiveCoefficients[s] = 0
				
				# still use the overall min stay to control the number of copies we want to fit...
				elif length <= minStayForThisDay*multiplier:
					self.ObjectiveCoefficients[s] = np.power(2.0, minStayForThisDay - length + extra)
				
				else:
					self.ObjectiveCoefficients[s] = 0
			
			else:
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) == 1)

		return()
	
	
	
	def AddAdjacentStaysModel(self):
		slackVarsForAdjacency = {}
		adjacentReservations = []
		
		for a in self.Inputs.StayAdjacencyLists:
			aStays = self.Inputs.StayAdjacencyLists[a]
			size = len(aStays)

			for s in aStays:
				adjacentReservations.append(s)
				connectedStays = [cnctdStay for cnctdStay in aStays if cnctdStay != s] 

				for r in self.Inputs.RoomAdjacencyLists:
					Oname = str(s)+ ", " + str(r) + '_SlackOdd'
					slackVarsForAdjacency[s,r] = self.Model.addVar(Oname,vtype= 'C',lb = 0,ub = 1)
					self.Model.addCons(self.AssignmentVars[s,r] <= quicksum(self.AssignmentVars[cs,ar] for cs in connectedStays for ar in self.Inputs.RoomAdjacencyLists[r]) + slackVarsForAdjacency[s,r])

				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.AdjacentRooms) >= 1 - quicksum(slackVarsForAdjacency[s,r] for r in self.Inputs.AdjacentRooms))
	
			# sum of all odd slacks <= size of group, want to make adjacent stays soft
			# and incentivize it in the objective.  If it's feasible, then can enforce it 
			# in subsequent steps.     
			self.Model.addCons(quicksum(slackVarsForAdjacency[s,r] for s in aStays for r in self.Inputs.AdjacentRooms) <= size)
	
		self.SlackAdjVars = slackVarsForAdjacency
		self.AdjacentReservations = adjacentReservations
		return()
		
		
	def AddCliqueConstraints(self):
		# self.cvars = {}
		# addV = True
		
		for r in self.Inputs.Rooms:
			k = 0
			for c in self.Cliques:
				# if addV:
# 					self.cvars[k] = self.Model.addVar(f"clique_{k}",vtype= 'C',lb = 0,ub = 1)
				
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for s in c) == 1)
				# something along these lines was useful for debugging... 
				# making clique constraints soft and looking at which ones fail.
				# self.Model.addCons(quicksum(self.AssignmentVars[s,r] for s in c) >= self.cvars[k])
# 				k += 1
# 			addV = False
		return()	
		
	def SplittingObjective(self):

		connectionVars = []
		downGradeVars = []
		for sg in self.Inputs.SplitGroups:
			# these should be in order? I guess? of arrival? 
			g = self.Inputs.SplitGroups[sg]
			downGradeVar = self.Model.addVar(f"downgrade_split_{sg}",vtype= 'C',lb = 0,ub = 1)
			downGradeVars.append(downGradeVar)
			orderedRoomTypes = self.Inputs.ReservationRoomTypes[g[0]]
			
			#print(orderedRoomTypes)
			'''
			so something like for stay and next stay... 
			if this stay assigned to a higher room, then want to penalize
			assigning the next stay to a lower room 
			'''
		
			for i in range(len(g) - 1):
				name = f"splitting_{sg}_{i}"
				connectionVar = self.Model.addVar(name,vtype= 'C',lb = 0,ub = 1)
				connectionVars.append(connectionVar)		
				lowerRooms = []
				for k in range(1,len(orderedRoomTypes)):
					higherRooms = self.Inputs.TypeToRooms[orderedRoomTypes[-(1+k)]]
					#print(higherRooms)
					for r in self.Inputs.TypeToRooms[orderedRoomTypes[-k]]:
						lowerRooms.append(r) 
					self.Model.addCons(quicksum(self.AssignmentVars[g[i+1],lr] for lr in lowerRooms) - downGradeVar <= 1 - quicksum(self.AssignmentVars[g[i],r] for r in higherRooms))
				
			
				for r in self.Inputs.Rooms:
					self.Model.addCons(self.AssignmentVars[g[i],r] - self.AssignmentVars[g[i+1],r] <= connectionVar)
					self.Model.addCons(self.AssignmentVars[g[i+1],r] - self.AssignmentVars[g[i],r] <= connectionVar)
		
		splitObj = 100*quicksum(cv for cv in connectionVars) + 1 * quicksum(dg for dg in downGradeVars)
		return splitObj


	