import json
import sys
import os
sys.path.append(os.path.dirname('../BookingOpt/'))

import SolverRunner as Runner
from FeasibilitySolverRunner import FeasibilityRunner

authKey = "!!a6c3z@5123!%@%"

from typing import Union
from fastapi import FastAPI

app = FastAPI()


@app.post("/optimize")
def optimize(input_json: dict, key):
	
	scn = input_json
	try:
		if key.strip() != authKey:
			raise Exception(f"Authentication failed for key: {key}")
		
		restrOnly = scn["RestrictionsForInitialPlan"] if "RestrictionsForInitialPlan" in scn else False
		
		if len(scn["NewReservations"]) > 0 and not restrOnly:
			runner = FeasibilityRunner()
			success, result = runner.Run(scn)
		else:
			success, result = Runner.Run(scn)
		
		return result
	except Exception as e:
		print(e)