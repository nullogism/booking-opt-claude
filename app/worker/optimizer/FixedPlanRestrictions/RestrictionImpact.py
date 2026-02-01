from datetime import date
import numpy as np

class RestrictionImpact:
	
	def GetAvoidedStays(self,finalRestrictions, data):
		
		days = np.arange(data.MinStart, data.MaxEnd)
		
		avoidedByCaByDate= {}
		avoidedByCdByDate = {}
		avoidedByMaxByDate = {}
		
		for day in days:
			if day in finalRestrictions.FullyBookedDays:
				continue
			
			dateString = date.fromordinal(day).strftime('%Y-%m-%d')	
			absMax = 0
			try:
				absMax = finalRestrictions.AbsoluteMaxStaysStartingOnDay[day]
			except:
				print(dateString)
			maxStay = absMax
			if day in finalRestrictions.ComputedMaxStaysStarting:
				maxStay = finalRestrictions.ComputedMaxStaysStarting[day]
			minStarting = finalRestrictions.MinStayStartingOnDay[day]
			stays = []
			
			maxStayOnStart = absMax
			if day in finalRestrictions.MaxStayCoveringDay:
				maxStayOnStart = finalRestrictions.MaxStayCoveringDay[day]
			
			
			if day in finalRestrictions.ClosedArrival:
				avoidedByCa =[]
				# Then prevents anything that's not prevented by the min stay or the 
				# CD, or the Max Stay or the Min Stay
				minMaxStayEncountered = maxStayOnStart
				
				for length in range(int(minStarting), int(maxStay) + 1):
					if day + length in finalRestrictions.MaxStayCoveringDay:
						minMaxStayEncountered = min(minMaxStayEncountered, finalRestrictions.MaxStayCoveringDay[day + length])
					
					if length > minMaxStayEncountered:
						continue
					
					if day + length in finalRestrictions.ClosedDeparture:
						continue
					avoidedByCa.append({"Arrival":dateString, "Length":length}) 
				
				if len(avoidedByCa) > 0 :
					avoidedByCaByDate[dateString] = avoidedByCa
				
				continue
			
			avoidedByCd = []
			avoidedByMax = [] 
			minMaxStayEncountered = maxStayOnStart
			#print (dateString,absMax)
			stop = False
			for length in range(int(minStarting), int(absMax) + 1):
				if stop: 
					continue
				
				if length > minMaxStayEncountered:
					avoidedByMax.append({"Arrival":dateString, "Length":length})
					# don't need to track EVERY long stay after, just the first... 
					#break
					stop = True			
				
				if day + length in finalRestrictions.MaxStayCoveringDay:
					minMaxStayEncountered = min(minMaxStayEncountered, finalRestrictions.MaxStayCoveringDay[day + length])
				
				if day + length in finalRestrictions.ClosedDeparture:
					avoidedByCd.append({"Arrival":dateString, "Length":length})
					continue
				
				
			if len(avoidedByCd) > 0 :
				avoidedByCdByDate[dateString] = avoidedByCd
			
			if len(avoidedByMax) > 0 :
				avoidedByMaxByDate[dateString] = avoidedByMax
				
		return (avoidedByCaByDate, avoidedByCdByDate, avoidedByMaxByDate)
	
				
				
				
			
		
				
				
				
				
				
				
				
				
				
				
		