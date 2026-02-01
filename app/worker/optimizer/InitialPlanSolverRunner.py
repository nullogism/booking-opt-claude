
from .Models.InitialPlanSolver import InitialPlanSolver

from .SolverData import InitialPlanSolverData as initData 

class InitialPlanSolverRunner:
	def __init__(self, problemData, maxDummy = 2):
		self.SolverData = initData.InitialPlanSolverData(maxDummy = maxDummy)
		self.SolverData.Initialize(problemData)
		self.Assignment = {}
		self.Infeasible = False

	def Run(self):		
		
		self.FillDummyStays()	
	
		solver = InitialPlanSolver(self.SolverData)
		
		solver.OptimizeSchedule()
		solver.GetInitialPlan()
		self.SolverData.OptimalSolution = solver.Solution
		
		self.SolverData.ClearDummyStays()
		
		if not solver.Succeeded:
			self.Infeasible = solver.ProvedInfeasible
		
		return(solver.Succeeded, solver.OptimizationAssignments)
	
	
	def FillDummyStays(self):
		self.SolverData.DummyStays = {}
		j = len(self.SolverData.StayDict)
			
		# need to make sure that the dummy stays go right up to the end 
		# of the schedule! Otherwise the clique constraints may cause problems... 
		for days in range(1 ,int(self.SolverData.MinStay * self.SolverData.MaxDummyMultiple + 1)):
			self.SolverData.DummyStays[days] = []
			
			for i in range(self.SolverData.MaxEnd - self.SolverData.MinStart): 
				if self.CheckInFeasibility(days, i + self.SolverData.MinStart):
					# do not add gaps that are less than the mns for this day
					# or greater than possible
					# 
					continue
					
				elif self.SolverData.MinStart + i + days <= self.SolverData.MaxEnd + 1:			
					# maybe add a few extra beyond the real end??
					# probably doesn't matter though...
					# then remember to just add clique sum to 1 constraints
					# up to the MaxEnd!!!! 
					self.SolverData.GroupDict[j] = -1
					self.SolverData.StayDict[j] = [self.SolverData.MinStart + i, self.SolverData.MinStart + i + days]
					self.SolverData.StartDict[j] =  self.SolverData.MinStart + i
					self.SolverData.LengthDict[j] = days
					self.SolverData.DummyStays[days].append(j)
					j += 1
		
	
	def CheckInFeasibility(self, length, day):
		# always leave the dummy stays at the ends and beginning for feasibility's sake
		# But do not need to add short dummies before/after the real bookings
		if day < self.SolverData.MinStart and length < self.SolverData.MinStart - day:
			return(False)
		if day + length > self.SolverData.ScheduleEnd:
			return(False)
		if day >= self.SolverData.MaxEnd - 1 and length < self.SolverData.ScheduleEnd - day:
			# do not need to add short stays at the end of the schedule
			return(False)

		