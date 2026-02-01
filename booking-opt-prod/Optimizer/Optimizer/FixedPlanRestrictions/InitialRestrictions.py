import numpy as np

class InitialRestrictions:

	def __init__(self, optimizationAssignment, data):
		self.MinStayStartingOnDay = {}
		self.FixedMaxStayStartingOnDay = {}
		self.AbsoluteMaxStaysStartingOnDay ={}
		
		self.OccupancyPerDay = {}
		self.FullyBookedDays = []
		self.FirstDepartureDay = data.MaxEnd

		
		self.DayRoomsFirstFilled = -1
		
		# number of exact gaps observed that are less than desired Min Stay
		# used for setting availability, and feasibility
		self.NumberOfSmallGapsPerDay = {} #{(startDate, gap): number}
		
		self.ClosedArrival = {}
		self.ClosedDeparture ={}
		
		self.Generate(optimizationAssignment, data)
			
	def Generate(self, optimizationAssignment, data):
		
		roomArrivals = {}
		roomDepartures = {}
		for r in data.Rooms: 
			roomArrivals[r] = []
			roomDepartures[r] = []
	
		daysWithArrivals = []
		daysWithDepartures = []
		
		for s in optimizationAssignment:
			roomArrivals[optimizationAssignment[s]].append(data.StayDict[s][0])
			roomDepartures[optimizationAssignment[s]].append(data.StayDict[s][1])

			if data.StayDict[s][1] < self.FirstDepartureDay:
				self.FirstDepartureDay = data.StayDict[s][1] 
		
		endOfSchedule = data.ScheduleEnd
		
		endOfSchedule += data.MinStay + 1
		
		
		for r in data.Rooms: 
			# sort the arrivals and departures in increasing order for each room
			roomArrivals[r].append(endOfSchedule)
			roomDepartures[r].append(endOfSchedule)
			
	
			roomArrivals[r] = np.sort(roomArrivals[r])
			roomDepartures[r] = np.sort(roomDepartures[r])
			
		fullOcc = data.NumberOfRooms

		for i in range(data.ScheduleEnd - data.ScheduleStart):
			occ = 0
			for s in optimizationAssignment:
				max1 = data.StayDict[s][1]
				min1 = data.StayDict[s][0]
				if min1 <= data.ScheduleStart + i and max1 > data.ScheduleStart+i:
					occ += 1
			self.OccupancyPerDay[data.ScheduleStart + i] = occ
			if occ == fullOcc:
				self.FullyBookedDays.append(data.ScheduleStart + i)
		
		# put a fully booked day at the end of the schedule
		self.FullyBookedDays.append(endOfSchedule)

		
		nextFullIndex = 0
		
		for day in self.OccupancyPerDay:
			
			if day < self.FullyBookedDays[nextFullIndex]:
				self.AbsoluteMaxStaysStartingOnDay[day] = self.FullyBookedDays[nextFullIndex] - day
			else:
				self.AbsoluteMaxStaysStartingOnDay[day] = 0
				nextFullIndex += 1
		
		self.FillMinMaxStays(data, roomArrivals, roomDepartures)

		self.GenerateClosures(data, roomArrivals, roomDepartures)
		#self.RemoveRedundantRestrictions(data)
		
			
	def FillMinMaxStays(self, data, roomArrivals, roomDepartures):
	
		nextArrivalIndex = np.zeros(data.NumberOfRooms,dtype = int)
		nextDepartureIndex = np.zeros(data.NumberOfRooms,dtype = int)

		naiveMaxStays = {}

		minGaps = np.ones(len(self.OccupancyPerDay)) * (data.MaxEnd-data.MinStart)

		days = list(self.OccupancyPerDay.keys())
		

		roomsFilledForFirstTime = np.zeros(data.NumberOfRooms)
		roomsAfterLastDeparture = np.zeros(data.NumberOfRooms)
		
		for i in range(len(days)):
			day = days[i]
			naiveMaxStays[day] = 0.0
			gapsObserved = {}
			
			
			for j in range(data.NumberOfRooms):
				r = data.Rooms[j]
				max_r = 0
				min_r = 0 

				if day < roomArrivals[r][nextArrivalIndex[j]]:
					max_r = roomArrivals[r][nextArrivalIndex[j]] - day
					min_r = np.min([max_r,data.MinStay])
					naiveMaxStays[day] = np.max([naiveMaxStays[day],max_r]) 
		
				if day >= data.MaxEnd:
					naiveMaxStays[day] = data.ScheduleEnd - day
				
				if day >= roomArrivals[r][0]:
					roomsFilledForFirstTime[j] = 1
				lastDepartureIndex = min(2,len(roomDepartures[r]))
				if day >= roomDepartures[r][-lastDepartureIndex]:
					roomsAfterLastDeparture[j] = 1
		
				if day == roomDepartures[r][nextDepartureIndex[j]]:
					nextArrivalIndex[j] += 1
					nextDepartureIndex[j] += 1
					if nextArrivalIndex[j] == len(roomArrivals[r]):
						max_r = 0
						min_r = 0
					else: 
						
						max_r = roomArrivals[r][nextArrivalIndex[j]] - day
						min_r = np.min([max_r, data.MinStay])
			
					if min_r > 0:
						if min_r < data.MinStay:
							# record the number of gaps smaller than MinStay observed each day
							# will use this for re-optimizing the max stays
							if int(min_r) in gapsObserved:
								gapsObserved[int(min_r)] += 1
							else:
								gapsObserved[int(min_r)] = 1
						
						minGaps[i] = np.min([minGaps[i],min_r])
					
					naiveMaxStays[day] = np.max([naiveMaxStays[day],max_r])
			
			
			for g in gapsObserved:
				self.NumberOfSmallGapsPerDay[(day,g)] = gapsObserved[g]
			
			if sum(roomsAfterLastDeparture) > 0:
				naiveMaxStays[day] = min([naiveMaxStays[day],len(days)-i])
			if sum(roomsFilledForFirstTime) < data.NumberOfRooms:
				self.DayRoomsFirstFilled = day
				
		self.FixedMaxStayStartingOnDay = naiveMaxStays
	
		for d in range(len(self.OccupancyPerDay)):
			day = days[d]
			self.MinStayStartingOnDay[day] = min([minGaps[d],data.MinStay])
			#if day == data.ScheduleStart:
			#	self.MinStayStartingOnDay[day] = min(self.MinStayStartingOnDay[day], self.FixedMaxStayStartingOnDay[day])
			if day < self.FirstDepartureDay:
				self.MinStayStartingOnDay[day] = data.MinStay
		
				
	def GenerateClosures(self, data, roomArrivals, roomDepartures):
		
		#sketch of restrictions...
		# get min/max stay and restrictions with locked rooms
		
		nextArrivalIndex = np.zeros(data.NumberOfRooms,dtype = int)
		nextDepartureIndex = np.zeros(data.NumberOfRooms,dtype = int)
		
		closeDeparture = {}
		closeArrival = {}
		
		cd = {}
		ca = {}
		
		days = list(self.OccupancyPerDay.keys())
		emptyRooms = True
		
		roomsFilled = np.zeros(data.NumberOfRooms)
		
		startingDeparture = data.MinStart - data.MinStay
		
		for i in range(len(days)):
			day = days[i]
			roomClosedArrival = np.ones(data.NumberOfRooms)
			roomClosedDeparture = np.ones(data.NumberOfRooms)

			for j in range(data.NumberOfRooms):
				r = data.Rooms[j]
				
				if day == roomDepartures[r][nextDepartureIndex[j]]:
					if nextDepartureIndex[j] < len(roomDepartures[r]) - 1:
						nextArrivalIndex[j] += 1
						nextDepartureIndex[j] += 1
		
				#restrictions
				
				previousDeparture = startingDeparture
				if nextDepartureIndex[j] > 0:
					previousDeparture = roomDepartures[r][nextDepartureIndex[j]-1]
				
				
				nextArrival = roomArrivals[r][min(nextArrivalIndex[j],len(roomArrivals[r]) - 1)]
		
				if nextArrival - day == 0 and day - previousDeparture > 0:
					roomClosedDeparture[j] = 0
				if day == days[len(days)-1]:
					roomClosedDeparture[j] = 0
					
				
				if day - previousDeparture >= data.MinStay and nextArrival - day >= data.MinStay:
					roomClosedDeparture[j] = 0
					roomClosedArrival[j] = 0
		 		
				if day - previousDeparture == 0 and nextArrival - day > 0:
					roomClosedArrival[j] = 0
		
			if np.sum(roomClosedArrival) == data.NumberOfRooms:
			
				self.ClosedArrival[day] = 1
				if day > data.MaxEnd and day < data.ScheduleEnd:
					self.ClosedArrival[day] = 1

			if np.sum(roomClosedDeparture) == data.NumberOfRooms:
			
				self.ClosedDeparture[day] = 1
				
	

		
		
				
				
				
				
				
				
				
				
				
				
				
				
				
 