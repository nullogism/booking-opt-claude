'''
Solver runner
'''

from .Data.ProblemData import ProblemData
from .Data.ProblemResult import ProblemResult
from .Data.Assignment import Assignment
from .Data.ReOptimizedPlan import ReOptimizedPlan

from datetime import date


from . import InitialPlanSolverRunner as sr
from .FixedPlanRestrictions import InitialRestrictions as ir
from . import RestrictionSolverRunner as rsr
from .FixedPlanRestrictions import FinalRestrictions as fr
import json
import time

def ConvertOrdinalToString(dateDict):
	output = {date.fromordinal(d).strftime('%Y-%m-%d'): dateDict[d] for d in dateDict}
	return(output)

def Run(problemJson, returnDict = True):
	
	startTime = time.time()
	result = ProblemResult(problemJson["ProblemId"], False)
	
	problemData = ProblemData()
	problemData.FillFromJson(problemJson)
	
	initialRunner = sr.InitialPlanSolverRunner(problemData)
	succeeded, initAssignment = initialRunner.Run()
	
	if not succeeded:
		failureOutput = {
		"ProblemId" : result.ProblemId,
		"ProvenInfeasible" : initialRunner.Infeasible
		}
		
		return( succeeded, failureOutput)
	
	result.InitialOptimizationTime = time.time() - startTime
	result.Succeeded = succeeded
		
	initRestrictions = ir.InitialRestrictions(initAssignment, initialRunner.SolverData)
	
	finalRestrictions = fr.FinalRestrictions(initRestrictions)
	#print(finalRestrictions.MinStayStartingOnDay)
	restrictionSolverRunner = rsr.RestrictionSolverRunner(initialRunner.SolverData, finalRestrictions)
	# eventually could break this up into smaller sets of days to be parallelized
	
	if result.InitialOptimizationTime < 5.0:
		# i.e. if the individual optimizations take a long time, then 
		# do NOT want to go through this, just use the straight fixed plan
		# for now
		finalRestrictions = restrictionSolverRunner.Run()
	
	restrSolverData = restrictionSolverRunner.SolverData

	finalRestrictions.Fill(initialRunner.SolverData)
	
	labeledAssignments = []
	labeledDummyAssignments = []
	
	# have to prevent this breaking due to duplicate group names for adjacent
	for s in initialRunner.SolverData.StayDict: 
		stay = initialRunner.SolverData.StayDict[s]
		
		arr = date.fromordinal(stay[0])
		adjGrp = None
		if s in initialRunner.SolverData.StayToAdjGroupDict:
			adjGrp = initialRunner.SolverData.StayToAdjGroupDict[s]
		
		
		labeledAssignments.append(Assignment(
								initialRunner.SolverData.GroupDict[s],
								s in initialRunner.SolverData.FixedRooms,
								initAssignment[s],
								arr.strftime('%Y-%m-%d'), 
								stay[1] - stay[0], adjGrp
								)
							)
			
	for dl in restrictionSolverRunner.DummyOptimalAssignments:
		
		
		reOpt = ReOptimizedPlan(date.fromordinal(dl[0]).strftime('%Y-%m-%d'), dl[1])

		for a in restrictionSolverRunner.DummyOptimalAssignments[dl]:
			grpName = "Test_Max"
			arr = dl[0]
			dep = dl[0] + dl[1]
			test = True
			
			if a in initialRunner.SolverData.GroupDict:
				grpName = initialRunner.SolverData.GroupDict[a]
				arr = initialRunner.SolverData.StayDict[s][0]
				dep = initialRunner.SolverData.StayDict[s][1]
				test = False
			
			adjGrp = None
			if a in initialRunner.SolverData.StayToAdjGroupDict:
				adjGrp = initialRunner.SolverData.StayToAdjGroupDict[a]
			
			reOpt.OptimizedPlan.append(Assignment(
								grpName,
								a in initialRunner.SolverData.FixedRooms,
								restrictionSolverRunner.DummyOptimalAssignments[dl][a],
								date.fromordinal(arr).strftime('%Y-%m-%d'), 
								arr - dep, adjGrp,
								test = test
								)
							)	
		labeledDummyAssignments.append(reOpt)

	
	result.OptimizedPlan = labeledAssignments
	result.ReOptimizedPlans = labeledDummyAssignments
	result.ClosedArrivals = ConvertOrdinalToString(finalRestrictions.ClosedArrival)
	result.ClosedDepartures  = ConvertOrdinalToString(finalRestrictions.ClosedDeparture)
	result.MinStays  = ConvertOrdinalToString(finalRestrictions.MinStayCoveringDay)
	result.MaxStays  = ConvertOrdinalToString(finalRestrictions.MaxStayCoveringDay)
	result.ScheduleStart = date.fromordinal(initialRunner.SolverData.ScheduleStart).strftime('%Y-%m-%d')
	result.ScheduleEnd = date.fromordinal(initialRunner.SolverData.ScheduleEnd).strftime('%Y-%m-%d')
	result.Rooms = problemData.Rooms
	result.TotalTime = time.time() - startTime
	
	
	if not returnDict:
		return(succeeded, result)
	
	resultDict = json.loads(result.JsonSerialize())	

	return(succeeded, resultDict)
	

	
	
	

