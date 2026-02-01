import sys
import os
import unittest

print(os.getcwd())
print(sys.path)

# this works if calling from within the Test Directory, if calling from the booking opt directory
# then need to do BookingOpt/BookingOpt ...

sys.path.append(os.path.dirname('../Optimizer/'))

print(sys.path)

import SolverRunner
from FixedPlanRestrictions import InitialRestrictions
from Data.ProblemData import ProblemData
import json

from Visualize import PlotWithRestrictions


with open("TestCases/json_format/SampleInput_4.json","r") as f:
	scn = json.load(f)


returnDict = False

success, result = SolverRunner.Run(scn, returnDict)

if not success:
	print(result)

elif returnDict:
	with open("TestReWrite.json", "w") as f:
		json.dump(result, f, indent = 4)

else:
	PlotWithRestrictions(result, "test")
