
from .Models.RestrictionSolver import RestrictionSolver
from .SolverData import RestrictionSolverData as rd 



class RestrictionSolverRunner:
	def __init__(self, initialPlanSolverData, restrictions):
		
		self.SolverData = rd.RestrictionSolverData(initialPlanSolverData)
		self.Restrictions = restrictions
		self.Solutions = []
		self.DummyOptimalAssignments = {}
	
	def Run(self, reOptimize = True):
			
		r = self.Restrictions
		
		r.ClearComputedStays()
		
		m = RestrictionSolver(self.SolverData)
		
		r.ComputedMaxStaysStarting[m.Inputs.ScheduleStart] = r.FixedMaxStayStartingOnDay[m.Inputs.ScheduleStart]
		
		for day in range(m.Inputs.MinStart, m.Inputs.MaxEnd):
			
			if day < r.FirstDepartureDay:
				continue
			
			stopChecking = False		
			
			if r.FixedMaxStayStartingOnDay[day] == 0:
				# don't need to check this if the day is full
				continue
			
			if day in r.ClosedArrival or r.FixedMaxStayStartingOnDay[day] == 0:
				# don't need to check this if the day is CA
				#dayRange = range(int(r.FixedMaxStayStartingOnDay[day]), int(r.FixedMaxStayStartingOnDay[day]+1))
				continue
				#just check if the fixed max stay starting that day can be made feasible... 
				# if so, then open for arrval
		
			
			r.ComputedMaxStaysStarting[day] = r.FixedMaxStayStartingOnDay[day]
			
			if not reOptimize:
				# can use this to skip long running cases and just use the fixed plan solution
				continue
			
			lastFeas = r.FixedMaxStayStartingOnDay[day]
			
			if r.FixedMaxStayStartingOnDay[day] == r.AbsoluteMaxStaysStartingOnDay[day]:
			
				r.ComputedMaxStaysStarting[day] = lastFeas
				stopChecking = True
		
			dayRange = range(int(r.FixedMaxStayStartingOnDay[day]+1), int(r.AbsoluteMaxStaysStartingOnDay[day])+1)
			
			for nextLength in dayRange:
				if stopChecking:
					continue
				
				if day + nextLength in r.ClosedDeparture:
					# don't need to worry about 
					continue
				
				if day + nextLength > m.Inputs.ScheduleEnd:
					# don't need to worry about the end of the scheduele, I think
					continue 
				
				feas = m.CheckFeasibility(day, nextLength, r)
	
				if feas:
					maxCoversEnd = day + nextLength > m.Inputs.MaxEnd
					lastFeas = nextLength
				   
					if maxCoversEnd:
						r.ComputedMaxStaysStarting[day] = r.AbsoluteMaxStaysStartingOnDay[day]
						stopChecking = True
					else:
						# normal case, where we record the computed max stay for future use. 
						r.ComputedMaxStaysStarting[day] = lastFeas
					
				if not feas:
					#r.ComputedMaxStaysStarting[day] = nextLength - 1
					# Depends on how you want to report it. above gives a longer max, the longest one that's blocked
					# by other stuff.
					# below gives the shortest feasible max
					# so it's the SMALLEST infeasible one against the LONGEST feasible one
					r.ComputedMaxStaysStarting[day] = lastFeas
					stopChecking = True
		
		self.DummyOptimalAssignments = m.DummyOptimizedAssignments
		self.SolverData.ClearDummyStays()
		return(r)

