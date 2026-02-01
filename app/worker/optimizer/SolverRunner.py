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
from . import InitialSolGenerator as rsg
from .FixedPlanRestrictions.RestrictionImpact import RestrictionImpact

import json
import time

def ConvertOrdinalToString(dateDict):
	output = {date.fromordinal(d).strftime('%Y-%m-%d'): dateDict[d] for d in dateDict}
	return(output)

def Run(problemJson, ReturnDict = True):
	
	startTime = time.time()
	result = ProblemResult(problemJson["ProblemId"], False)
	succeeded = False
	provenInfeasible = False
	
	problemData = ProblemData()
	problemData.FillFromJson(problemJson)
	
	initialRunner = sr.InitialPlanSolverRunner(problemData)
	if initialRunner.SolverData.CurrentReservationsWithoutAssignedRoom < 1:
		succeeded, initAssignment = initialRunner.Run()
	
		fullyBookedDays = initialRunner.SolverData.FullyBookedDays
		minStart = initialRunner.SolverData.MinStart
	
	if not succeeded:
		result.Message += f"\nfailed,\nproven infeasible: {initialRunner.Infeasible},\n"
		result.Message += initialRunner.SolverData.Exceptions
		result.Succeeded = succeeded
		result.CurrentScheduleInfeasible = initialRunner.Infeasible
		resultDict = json.loads(result.JsonSerialize())	
		if ReturnDict:
			return(succeeded, resultDict)
		return( succeeded, result)

	
	result.InitialOptimizationTime = time.time() - startTime
	result.Succeeded = succeeded
	
	initialPlan, initialPlanGaps = rsg.Run(initialRunner.SolverData)
		
	initRestrictions = ir.InitialRestrictions(initAssignment, initialRunner.SolverData)
	
	finalRestrictions = fr.FinalRestrictions(initRestrictions)

	restrictionSolverRunner = rsr.RestrictionSolverRunner(initialRunner.SolverData, finalRestrictions)
	# eventually could break this up into smaller sets of days to be parallelized
	
	if result.InitialOptimizationTime < 0.1 and not problemData.RestrictionsForInitialPlan:
		# Do not run if just calculating restrictions for initial plan
		# i.e. if the individual optimizations take a long time, then 
		# do NOT want to go through this, just use the straight fixed plan
		# for now, eventually will allow longer run times and implement
		# some parallelization
		print(time.time() - startTime)
		finalRestrictions = restrictionSolverRunner.Run()
	
	restrSolverData = restrictionSolverRunner.SolverData

	finalRestrictions.Fill(initialRunner.SolverData)
	
	avdCa, avdCd, avdMax = RestrictionImpact().GetAvoidedStays(finalRestrictions, initialRunner.SolverData)
	
	result.StaysAvoidedByCa = avdCa
	result.StaysAvoidedByCd = avdCd
	result.StaysAvoidedByMax = avdMax
	
	labeledAssignments = []
	labeledDummyAssignments = []
	
	for s in initialRunner.SolverData.StayDict: 
		stay = initialRunner.SolverData.StayDict[s]
		
		arr = date.fromordinal(stay[0])
		adjGrp = None
		if s in initialRunner.SolverData.StayToAdjGroupDict:
			adjGrp = initialRunner.SolverData.StayToAdjGroupDict[s]
		
		if problemData.RestrictionsOnly and initAssignment[s] == None:
			result.Message += "Cannot calculate restrictions when missing initial assignments."
			succeeded = False
			
		labeledAssignments.append(Assignment(
								initialRunner.SolverData.GroupDict[s],
								s in initialRunner.SolverData.FixedRooms,
								initAssignment[s],
								arr.strftime('%Y-%m-%d'), 
								stay[1] - stay[0], 
								adjGrp,
								grpId = initialRunner.SolverData.IdDict[s]
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
				arr = initialRunner.SolverData.StayDict[a][0]
				dep = initialRunner.SolverData.StayDict[a][1]
				test = False
			
			adjGrp = None
			if a in initialRunner.SolverData.StayToAdjGroupDict:
				adjGrp = initialRunner.SolverData.StayToAdjGroupDict[a]
			
			reOpt.OptimizedPlan.append(Assignment(
								grpName,
								a in initialRunner.SolverData.FixedRooms,
								restrictionSolverRunner.DummyOptimalAssignments[dl][a],
								date.fromordinal(arr).strftime('%Y-%m-%d'), 
								dep - arr, adjGrp,
								test = test
								)
							)	
		labeledDummyAssignments.append(reOpt)

	result.NonAdjacentAssignments = initialRunner.SolverData.NonAdjacentAssignmentsPerGroup
	result.OptimizedPlan = labeledAssignments
	result.ReOptimizedPlans = labeledDummyAssignments
	result.ClosedArrivals = ConvertOrdinalToString(finalRestrictions.ClosedArrival)
	result.ClosedDepartures  = ConvertOrdinalToString(finalRestrictions.ClosedDeparture)
	result.MinStays  = ConvertOrdinalToString(finalRestrictions.MinStayCoveringDay)
	result.MaxStays  = ConvertOrdinalToString(finalRestrictions.MaxStayCoveringDay)
	
	# could update this to compare with the initial plan
	
	if initialPlan is not None:
		result.InitialPlan = initialPlan
		result.InitialMinStays = initialPlanGaps
		result.QualityComparison = {d : {"Initial":0, "Optimized":0} for d in range(1,problemData.MinStay + 1)}
		
		for d in result.InitialMinStays:
			if date.toordinal(date.fromisoformat(d)) in fullyBookedDays:
				continue
			if int(result.MinStays[d]) not in result.QualityComparison:
				result.QualityComparison[int(result.MinStays[d])] = {"Initial":0, "Optimized":0}
			if int(result.InitialMinStays[d]) not in result.QualityComparison:
				result.QualityComparison[int(result.InitialMinStays[d])] = {"Initial":0, "Optimized":0}
			result.QualityComparison[int(result.MinStays[d])]["Optimized"] += 1
			result.QualityComparison[int(result.InitialMinStays[d])]["Initial"] += 1

	
	result.ScheduleStart = date.fromordinal(initialRunner.SolverData.ScheduleStart).strftime('%Y-%m-%d')
	result.ScheduleEnd = date.fromordinal(initialRunner.SolverData.ScheduleEnd).strftime('%Y-%m-%d')
	result.Rooms = problemData.Rooms
	result.TotalTime = time.time() - startTime
	
	
	if not ReturnDict:
		return(succeeded, result)
	
	resultDict = json.loads(result.JsonSerialize())	

	return(succeeded, resultDict)
	

	
	
	

