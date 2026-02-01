from .Data.ProblemData import ProblemData

from datetime import date

from .FixedPlanRestrictions import InitialRestrictions as ir
from .FixedPlanRestrictions import FinalRestrictions as fr

from .Data.Assignment import Assignment

import json
import time

def ConvertOrdinalToString(dateDict):
	output = {date.fromordinal(d).strftime('%Y-%m-%d'): dateDict[d] for d in dateDict}
	return(output)

def Run(solverData):

	initialPlan = solverData.InitialPlan
	for assgnmt in initialPlan.values():
		if assgnmt not in solverData.Rooms:
			return(None,None)
	
	initRestrictions = ir.InitialRestrictions(initialPlan, solverData)
	
	finalRestrictions = fr.FinalRestrictions(initRestrictions)

	finalRestrictions.Fill(solverData)
	
	labeledAssignments = []
	for s in solverData.StayDict: 
		stay = solverData.StayDict[s]
		
		arr = date.fromordinal(stay[0])
		adjGrp = None
		if s in solverData.StayToAdjGroupDict:
			adjGrp = solverData.StayToAdjGroupDict[s]
		
		labeledAssignments.append(Assignment(
								solverData.GroupDict[s],
								s in solverData.FixedRooms,
								initialPlan[s],
								arr.strftime('%Y-%m-%d'), 
								stay[1] - stay[0], adjGrp
								)
							)
	
	return(labeledAssignments,ConvertOrdinalToString(finalRestrictions.MinStayCoveringDay))
	
	
	