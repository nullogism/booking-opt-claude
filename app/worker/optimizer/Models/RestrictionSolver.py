import numpy as np
import math
import csv
from pyscipopt import Model, quicksum
import time
		

class RestrictionSolver:
	
	def __init__(self, inputs):
		
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
		self.DummyIncentiveCoefficients = {}
		self.DummyStays = []
		
		# list of adjacent reservations:
		self.AdjacentReservations = []
		
		self.Succeeded = False
		self.ProvedInfeasible = False
		self.OptimizationAssignments = {}
		
		self.DummyOptimizedAssignments = {}# {(day,length): {}}
		

		
	
	def AddDummyPlan(self, day, length):
		self.DummyOptimizedAssignments[(day,length)] = {}
		
		for i in self.Inputs.StayDict:
			
			if i in self.DummyStays:	
				continue
				
			for j in self.Inputs.Rooms:
				if self.Model.getVal(self.AssignmentVars[i,j]) > 0.99:
					self.DummyOptimizedAssignments[(day,length)][i] = j
						
		return()

	def GenerateCliques(self):	
		self.Cliques = []
		stayDict = self.Inputs.StayDict
		for i in range(self.Inputs.MaxEnd - self.Inputs.MinStart):
			cliq = []
			for s in stayDict:
				max1 = stayDict[s][1]
				min1 = stayDict[s][0]
				if min1 <= self.Inputs.MinStart + i and max1 > self.Inputs.MinStart+i:
					cliq.append(s)
			self.Cliques.append(cliq)
			

	def CheckFeasibility(self, startDay, length, restrictions = None):
		
		if (startDay, length) in self.DummyOptimizedAssignments:
			# if there from a previous run, get rid of it
			del(self.DummyOptimizedAssignments[(startDay, length)])
		
		self.Model = Model()
		
		start = time.time()
		
		# reset the variables and coefficients
		self.ObjectiveCoefficients = {}
		self.AssignmentVars = {}
		self.DummyIncentiveVars = {}
		self.DummyStays = []
		
		newIndex = self.Inputs.AddNewReservation(startDay, length)		
		
		minStay = {}
		absMaxStays = {}
		if restrictions is not None:
			minStays = restrictions.MinStayStartingOnDay
			absMaxStays = restrictions.AbsoluteMaxStaysStartingOnDay
		
		self.Inputs.FillDummyStays(minStays, absMaxStays)
		
		succeeded = True
		self.GenerateCliques()
		self.AddAssignmentModel(startDay, length)
		self.AddAdjacentStaysModel()
		self.AddCliqueConstraints()
		
		obj = quicksum(self.ObjectiveCoefficients[s]*self.AssignmentVars[s,r] for s in self.ObjectiveCoefficients for r in self.Inputs.Rooms) + 10*quicksum(self.SlackOddGroups[s,r] for s in self.AdjacentReservations for r in self.Inputs.AdjacentRooms)
		#obj = quicksum(objCoeffs[s]*x[s,r] for s in objCoeffs for r in rooms) - 100*quicksum(cvar[k] for k in cvar.keys())

		self.Model.setObjective(obj,"minimize")


		'''
		probably need to silence the output, and write it to a log
		or something... 
		'''	
		self.Model.setRealParam('limits/gap', 0.01) # stop at 99% of optimality
		self.Model.setParam('limits/time', 60) # stop after 2 minutes
		self.Model.hideOutput(True)
		self.Model.optimize()
		
		end = time.time()
		
		if self.Model.getStatus() == "infeasible": 
			
			succeeded = False
		
		self.MaxStayTime += (end-start)
		
		if succeeded:
			self.AddDummyPlan(startDay, length)
			
		self.Inputs.RemoveNewReservation(newIndex)
	
		# if Not Succeeded, then update the max stay for that day to be 
		# the previous feasible one ( not necessarily length -1, look at 
		# sample 4, start thinking about the split stay I guess...)
		return(succeeded)

	
	def AddAssignmentModel(self, day, newLength):
		for s in self.Inputs.StayDict:
			for r in self.Inputs.Rooms:
				name = str(s)+ ", " + str(r)
				self.AssignmentVars[s,r] = self.Model.addVar(name,vtype= 'B')


		for s in self.Inputs.StayDict:
			
			if s in self.Inputs.FixedRooms:
				self.Model.addCons(self.AssignmentVars[s,self.Inputs.FixedRooms[s]] == 1)
				
			if self.Inputs.GroupDict[s] == -1: # i.e. if it's a dummy stay
				
				length = self.Inputs.LengthDict[s]
				self.DummyStays.append(s)
				
				maxGaps = self.Inputs.NumberOfRooms
				
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) <= maxGaps)
				# this incentivizes gaps longer than min stay length
				# also should not penalize if it goes up to/ over the end of the schedule.
				
				eextra = 0
				if length < self.Inputs.MinStay:
					extra = 1

				if length + self.Inputs.StayDict[s][0] >= self.Inputs.ScheduleEnd:
					self.ObjectiveCoefficients[s] = 0
				
				elif self.Inputs.StayDict[s][0] <= self.Inputs.ScheduleStart:
					self.ObjectiveCoefficients[s] = 0
				
				elif length <= self.Inputs.MinStay:
					self.ObjectiveCoefficients[s] = np.power(2.0, self.Inputs.MinStay - length + extra)
				
				else:
					self.ObjectiveCoefficients[s] = 0
	
			else:
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) == 1)
		
		return()
	
	
	def AddAdjacentStaysModel(self):

		slackOddGroups = {}
		adjacentReservations = []
		
		for a in self.Inputs.StayAdjacencyLists:
			aStays = self.Inputs.StayAdjacencyLists[a]
			size = len(aStays)
			# if the group has odd number, then will
			# allow one to be apart
			oddUb = 1.0
			if size <= 2:
				oddUb = 0.0
			elif size % 2 == 0:
				oddUb = 0.0

			for s in aStays:
				adjacentReservations.append(s)
				connectedStays = [cnctdStay for cnctdStay in aStays if cnctdStay != s] 
				for r in self.Inputs.RoomAdjacencyLists:
					Oname = str(s)+ ", " + str(r) + '_SlackOdd'
					slackOddGroups[s,r] = self.Model.addVar(Oname,vtype= 'B',lb = 0,ub = oddUb)
					self.Model.addCons(self.AssignmentVars[s,r] <= quicksum(self.AssignmentVars[cs,ar] for cs in connectedStays for ar in self.Inputs.RoomAdjacencyLists[r]) + slackOddGroups[s,r])
		
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.AdjacentRooms) >= 1 - quicksum(slackOddGroups[s,r] for r in self.Inputs.AdjacentRooms))
	
			# sum of all odd slacks <= 1     
			self.Model.addCons(quicksum(slackOddGroups[s,r] for s in aStays for r in self.Inputs.AdjacentRooms) <= 1)
	
		self.SlackOddGroups = slackOddGroups
		self.AdjacentReservations = adjacentReservations
		return()
		
		
	def AddCliqueConstraints(self):
		for r in self.Inputs.Rooms:
			#k = 0
			for c in self.Cliques:
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for s in c) == 1)
				#m.addCons(quicksum(x[s,r] for s in c) >= cvar[k])
				#k += 1
	
		return()
	


	