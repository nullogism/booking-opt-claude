
import numpy as np

class FinalRestrictions:

	def __init__(self, initialRestrictions):
	
		self.MinStayStartingOnDay = initialRestrictions.MinStayStartingOnDay
		self.FixedMaxStayStartingOnDay = initialRestrictions.FixedMaxStayStartingOnDay
		self.AbsoluteMaxStaysStartingOnDay = initialRestrictions.AbsoluteMaxStaysStartingOnDay
	
		
		self.OccupancyPerDay = initialRestrictions.OccupancyPerDay
		self.FullyBookedDays = initialRestrictions.FullyBookedDays
		self.DayRoomsFirstFilled = initialRestrictions.DayRoomsFirstFilled
		self.FirstDepartureDay = initialRestrictions.FirstDepartureDay
		# number of exact gaps observed that are less than desired Min Stay
		# used for setting availability, and feasibility
		self.NumberOfSmallGapsPerDay = initialRestrictions.NumberOfSmallGapsPerDay #{(startDate, gap): number}
		
		# compute ca/cd for fixed plan min stay. 
		# these are adjusted to not duplicate the 
		# limitations placed by min stays and 
		# 0 availability (fully booked) days
		self.ClosedArrival = initialRestrictions.ClosedArrival
		self.ClosedDeparture = initialRestrictions.ClosedDeparture
		
		
		# these will be recomputed by checking feasibility
		self.ComputedMaxStaysStarting = self.FixedMaxStayStartingOnDay
	
		#might do it for min as well... 
		self.ComputedMinStaysStartingOnDay = self.MinStayStartingOnDay
		
		# need to parse the min/max stay starting on a day
		# to give the min/max stay that can be in the hotel that day
		# if the inn is full then do make this min stay 0 (or do not add)
		self.MinStayCoveringDay = {}
		self.MaxStayCoveringDay = {}
		
		
	
	def ClearComputedStays(self):
		# Clear these if recomputing:
		self.ComputedMaxStaysStarting = {}
		self.ComputedMinStaysStartingOnDay = {}	
	
	def Fill(self, data):
		self.FillMinStaysCoveringDay(data.MaxEnd)
		self.FillMaxStaysCoveringDay(data)
		self.UpdateCaCdRestrictions()
		self.RemoveRedundantRestrictions(data)
	
			
	def UpdateCaCdRestrictions(self):
		'''
		idea is to loop through and remove the ca/cd from the days on which calculated
		max or min stays can arrive/depart.
		'''
		

	def FillMinStaysCoveringDay(self, maxEnd):
		
		for day in self.MinStayStartingOnDay:
			currentMin = self.MinStayStartingOnDay[day]
			for d in range(0,int(self.MinStayStartingOnDay[day])):
				
				if day + d in self.MinStayCoveringDay:
					
					self.MinStayCoveringDay[day+d] = min(currentMin, self.MinStayCoveringDay[day+d])
				elif day + d < maxEnd:
					self.MinStayCoveringDay[day+d] = currentMin
					
					
	def FillMaxStaysCoveringDay(self, data):
		for d in range(data.ScheduleStart, self.DayRoomsFirstFilled + 1):
			self.MaxStayCoveringDay[d] = data.ScheduleEnd - data.ScheduleStart
		
		
		for day in self.ComputedMaxStaysStarting:
			currentMax = self.ComputedMaxStaysStarting[day]
			for d in range(0, int(self.ComputedMaxStaysStarting[day])):
				
				if day + d in self.MaxStayCoveringDay:
					if currentMax > self.MaxStayCoveringDay[day+d]:
					
						self.MaxStayCoveringDay[day+d] = currentMax
				
				elif day + d < data.ScheduleEnd:
					self.MaxStayCoveringDay[day+d] = currentMax
		
		dates = list(self.MaxStayCoveringDay.keys())
		dates.sort()
		daysToKeep = []
		for i in range(0,len(dates)):
			day = dates[i]
			maxStayStartingThisDay = self.FixedMaxStayStartingOnDay[day]
			if day in self.ComputedMaxStaysStarting:
				maxStayStartingThisDay = self.ComputedMaxStaysStarting[day]
			
			if day + maxStayStartingThisDay >= data.ScheduleEnd:
				continue
			
			if day <= data.ScheduleStart:
				continue
			
			newMaxStay = self.MaxStayCoveringDay[day] == maxStayStartingThisDay
			changeInMaxStay = self.MaxStayCoveringDay[day] != self.MaxStayCoveringDay[dates[i-1]]
			
			if newMaxStay or changeInMaxStay:
				daysToKeep.append(day)
			
		
		for day in dates:
			if day not in daysToKeep:
				del(self.MaxStayCoveringDay[day])
		
		
	def RemoveRedundantRestrictions(self, data):
		# remove cd and ca from days that are fully booked, 
		# and remove cd from days that are less than min stay from a fully booked day
		days = list(self.ClosedArrival.keys())
		for day in days:
			if day in self.MinStayCoveringDay:
				if day + self.MinStayCoveringDay[day] > day + self.AbsoluteMaxStaysStartingOnDay[day]:
					del(self.ClosedArrival[day])
		
		
		for day in self.FullyBookedDays:
			if day > data.MaxEnd:
				continue
			if day in self.ClosedArrival:
				del(self.ClosedArrival[day])
		
			
			if day in self.ClosedDeparture:
				del(self.ClosedDeparture[day])
			if day + 1 not in self.MinStayStartingOnDay:
				continue
			for d in range(int(self.MinStayStartingOnDay[day+1])):
				if day + 1 + d in self.ClosedDeparture:
					del(self.ClosedDeparture[day+1+d])

				
		
		