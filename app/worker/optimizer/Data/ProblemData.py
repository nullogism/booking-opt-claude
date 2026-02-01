'''
Problem Input Data object, with method to serialize to 
a Json string (for accepting a problem specification from 
the problem builder step).  

Need to load this to a dictionary if want to write it in 
the nice format (i.e. 
jsonString = pr.JsonSerialize()
dict = json.load(jsonString)
write to filePath ( json.dump(dict, filePath, indent = 4))
) 
'''
from .Room import Room
from .Reservation import Reservation
import json


class ProblemData:
	def __init__(self):

		self.ProblemId = ""
		self.MinimumStayByDay = {} # alternative min stays for different days
		self.NewReservations = [] # of reservation objects, to check feasibility
		self.Reservations = [] # of reservation objects
		self.Rooms = [] # of room objects
		self.MinStay = 5
		
		self.Days = ["M","T","W","TH","F","SA","SU"]
		
	
	def FillFromJson(self, jsonDict):
		
		try:
			self.ProblemId = jsonDict["ProblemId"]
		except:
			raise KeyError("Input data requires a problem ID")
		
		try:
			self.LoadReservationData(jsonDict["Reservations"])
		except KeyError:
			raise KeyError("Input data does not contain reservations")
		except: 
			raise 
		
		try:
			self.LoadRoomData(jsonDict["Rooms"])
		except KeyError:
			raise KeyError("Input data must contain room information")
		except:
			raise Exception("Room data is incorrectly formatted")
		
		try:
			self.MinStay = int(jsonDict["MinStay"])
		except KeyError:
			self.MinStay = 5
		except ValueError:
			raise ValueError("min stay must be an integer")
			
		try:
			self.LoadNewReservations(jsonDict["NewReservations"])
		except KeyError:
			self.NewReservations = []
		except:
			raise Exception("New reservation info is inorrectly formatted")
	
		try:
			self.LoadMinStaysByDay(jsonDict["MinimumStayByDay"])
		except:
			raise Exception("There's a problem with the min stays per day")
	
	def LoadReservationData(self, reservations):
		
		for r in  reservations:
			res = Reservation()
			for e in r:
				if e not in res.__dict__.keys():
					raise KeyError(f"Key {e} is not valid for reservations")
				setattr(res, e, r[e])
			self.Reservations.append(res)

	def LoadRoomData(self, rooms):
		for r in  rooms:
			rm = Room()
			for e in r:
				if e not in rm.__dict__.keys():
					raise KeyError(f"Key {e} is not valid for rooms")
				setattr(rm, e, r[e])
			self.Rooms.append(rm)
			
	def LoadNewReservations(self, reservations):
		
		for r in  reservations:
			res = Reservation()
			for e in r:
				if e not in res.__dict__.keys():
					raise KeyError(f"Key {e} is not valid for reservations")
				setattr(res, e, r[e])
			self.NewReservations.append(res)
		
	def LoadMinStaysByDay(self,minStayByDay):
		for m in minStayByDay:
			# this is supposed to be a dict of day of week, to int
			if m not in self.Days:
				raise Exception(f"{m} is not a supported weekday")
			if m in self.MinimumStayByDay:
				raise Exception(f"{m} has two entries")
			self.MinimumStayByDay[m] = int(minStayByDay[m])
	
	def JsonSerialize(self):
		return(json.dumps(self, default=lambda x: x.__dict__))
			
	
		
		


