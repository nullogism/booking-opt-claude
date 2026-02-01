'''
Solver Result

This will store all the final results. 

'''

class SolverResult:

	def __init__(self, problemId, succeeded):
	
		self.ProblemId = "ProblemId"
		self.Succeeded = "Succeeded"
		self.ClosedArrivals = "ClosedArrivals"
		self.ClosedDepartures = "ClosedDepartures"
		
		self.MinStays = "MinStays"
		self.MaxStays = "MaxStays"
		
		self.OptimizedPlan = "OptimizedPlan"
		
		self.ReOptimizedPlans = "ReOptimizedPlans" # the plans that resulted in 
								# different restrictions or min/max	 
		
		self.Outputs = {
			self.ProblemId : problemId,
			self.Succeeded : succeeded,
			self.ClosedArrivals : {},
			self.ClosedDepartures: {},
			self.MinStays: {},
			self.MaxStays: {},
			self.OptimizedPlan: {},
			self.ReOptimizedPlans: {}
		} 
