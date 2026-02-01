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
		self.RestrictionsOnly = False
		self.MinimumStayByDay = {} # alternative min stays for different days
		self.Reservations = []
		self.Rooms = [] # list of room objects
		self.MinimumStayByDate = []
		self.MinStay = 5
		
		self.Days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
		
		# set this to True to return a random solution and the optimal one
		# for comparison.
		#self.EvaluateQuality = False 
		
		# settings for checking whether a reservation fits.
		# if this is all turned on, then will try to optimize, 
		# and if not feasible will check if a broken assignment is feasible, 
		# and try to allocate it across all the allowable types, 
		# need to make sure we have the data to assign all other bookings to their 
		# appropriate room types. 
		self.NewReservations = [] # of reservation objects, to check feasibility
		self.AllowableRoomTypes = [] # room types to consider (if empty will just consider the 
									# the type in the reservation object)
		self.TestNewBooking = False # this will switch off the restriction optimization part
	
		self.RestrictionsForInitialPlan = False
		self.RequestStartDate = None
		self.RequestEndDate = None
	
	def FillFromJson(self, jsonDict):
		
		try:
			self.RestrictionsForInitialPlan = jsonDict["RestrictionsForInitialPlan"]
		except:
			self.RestrictionsOnly = False
		
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
			self.MinStay = int(jsonDict["MinimumStay"])
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
	
		try:
			self.LoadMinStaysByDate(jsonDict["MinimumStayByDate"])
		except KeyError:
			self.MinStayByDate = []
	
		try:
			allowableTypeKey = "AllowableTypesForNewReservation"
			self.AllowableRoomTypes = jsonDict[allowableTypeKey] if allowableTypeKey in jsonDict else []
			testBookingKey = "TestNewBooking"
			self.TestNewBooking =  bool(jsonDict[testBookingKey]) if testBookingKey in jsonDict else False
		except:
			raise ValueError("There is an issue with the allowable room types and/or test booking input.")	
	
		if "RequestStartDate" in jsonDict:
			self.RequestStartDate = jsonDict["RequestStartDate"]
			self.RequestEndDate = jsonDict["RequestEndDate"]
		
			
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
		for m in self.Days:
			if m not in minStayByDay:
				self.MinimumStayByDay[m] = int(self.MinStay)
			else:
				self.MinimumStayByDay[m] = int(minStayByDay[m])
	
	
	
	def LoadMinStaysByDate(self, minStayDict):			
		for entry in minStayDict:
			start = entry["Start"]
			end = entry["End"]
			minStay = float(entry["MinimumStay"])
			self.MinimumStayByDate.append({
				"Start":start,
				"End":end,
				"MinimumStay":minStay})
			
	
	def JsonSerialize(self):
		return(json.dumps(self, default=lambda x: x.__dict__))
			
	
		
		


	
		
		


