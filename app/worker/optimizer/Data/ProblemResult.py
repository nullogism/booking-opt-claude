'''
Problem result object, with method to serialize to 
a Json string (for returning the result to the 
result processing step).  

Need to load this to a dictionary if want to write it in 
the nice format (i.e. 
jsonString = pr.JsonSerialize()
dict = json.load(jsonString)
write to filePath ( json.dump(dict, filePath, indent = 4))
) 
'''

import json
import datetime
from .Assignment import Assignment
from .ReOptimizedPlan import ReOptimizedPlan
from .Room import Room

class ProblemResult:

	def __init__(self, problemId, succeeded):
	
		self.ProcessingDate = datetime.datetime.now().strftime("%Y-%m-%d")
		self.InitialOptimizationTime = 0.0
		self.TotalTime = 0.0
		
		self.ProblemId = problemId
		
		self.Succeeded = succeeded
		self.ClosedArrivals = {} # these have the string date as the key
		self.ClosedDepartures = {}
		
		self.MinStays = {}
		self.MaxStays = {}
		
		self.OptimizedPlan = [] # array of assignment objects
		
		self.ReOptimizedPlans = [] # dictionary of arrays
								# these are the plans that resulted in 
								# different restrictions or min/max	 
		
		self.ScheduleStart = "" #date as YYYY-MM-DD string
		self.ScheduleEnd = ""
		self.Rooms = []


	def FillFromJson(self, jsonDict):
		
		try: 
			self.ProcessingDate = jsonDict["ProcessingDate"]
		except:
			self.ProcessingDate = datetime.datetime.now().strftime("%Y-%m-%d")
		
		try:
			self.ScheduleStart = jsonDict["ScheduleStart"]
			self.ScheduleEnd = jsonDict["ScheduleEnd"]
		except:
			raise KeyError("Result does not contain either start or end.")
		
		
		try:
			self.LoadOptimizedPlan(jsonDict["OptimizedPlan"])
		except KeyError:
			raise KeyError("Input data does not contain optimized plan")
		except: 
			raise 
		
		try:
			self.LoadReOptimizedPlans(jsonDict["ReOptimizedPlans"])
		except KeyError:
			self.ReOptimizedPlans = []
		except:
			raise Exception("Reoptimized plan data is incorrectly formatted")
		
		try: 
			self.LoadRoomData(jsonDict["Rooms"])
		except KeyError:
			raise KeyError("Result does not contain room information")
		
		try:
			self.MinStays = jsonDict["MinStays"]
			self.MaxStays = jsonDict["MaxStays"]
			self.ClosedArrivals = jsonDict["ClosedArrivals"]
			self.ClosedDepartures = jsonDict["ClosedDepartures"]
			
		except KeyError:
			raise KeyError("Result is missing a restriction entry")
		except:
			raise
	
	def LoadReOptimizedPlans(self, reOptAssignments):
		
		for reOpt in reOptAssignments:
			day = reOpt["Day"]
			length = reOpt["Length"]
			reOptPlan = ReOptimizedPlan(day, length)
			
			for a in  reOpt["OptimizedPlan"]:
				assgmnt = Assignment()
				for e in a:
					if e not in assgmnt.__dict__.keys():
						raise KeyError(f"Key {e} is not valid for assignments")
					setattr(assgmnt, e, a[e])
				reOptPlan.OptimizedPlan.append(assgmnt)
			self.ReOptimizedPlans.append(reOptPlan)	

	def LoadOptimizedPlan(self, optAssignments):
		for a in  optAssignments:
			assgmnt = Assignment()
			for e in a:
				if e not in assgmnt.__dict__.keys():
					raise KeyError(f"Key {e} is not valid for assignments")
				setattr(assgmnt, e, a[e])
			self.OptimizedPlan.append(assgmnt)
	
	def LoadRoomData(self, rooms):
		for r in  rooms:
			rm = Room()
			for e in r:
				if e not in rm.__dict__.keys():
					raise KeyError(f"Key {e} is not valid for rooms")
				setattr(rm, e, r[e])
			self.Rooms.append(rm)
	
	def JsonSerialize(self):
		return(json.dumps(self, default=lambda x: x.__dict__))

		


