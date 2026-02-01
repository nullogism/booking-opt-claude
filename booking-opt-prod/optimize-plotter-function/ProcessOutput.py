'''
function for plotting results

'''

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import numpy as np
from datetime import date
from BookingOptOutputProcessor.Data.ProblemResult import ProblemResult
import io


def Run(result):
	
	problemResult = ProblemResult(result["ProblemId"], result["Succeeded"])
	problemResult.FillFromJson(result)

	# make the plot and return the buffered image
	buf = PlotWithRestrictions(problemResult, f"{problemResult.ProblemId}: {problemResult.ScheduleStart} - {problemResult.ScheduleEnd}")
	return(buf)



def PlotWithRestrictions(problemResult, figTitle):
		
	assignments = problemResult.OptimizedPlan	
	
	fontSize = 6
	size = (8,6)
	
	numberOfRooms = len(problemResult.Rooms)
	
	startOrdinal = date.toordinal(date.fromisoformat(problemResult.ScheduleStart))
	endOrdinal = date.toordinal(date.fromisoformat(problemResult.ScheduleEnd))
	
	fig, ax = plt.subplots(figsize = size)   
	ax.set_ylim(1,numberOfRooms + 1)
	
	ax.set_xlim(-1, endOrdinal - startOrdinal + 1)
	ax.set_axisbelow(True)
	roomMap = {}
	maxY = 0
	rmSigns = {}
	for i in range(numberOfRooms):
		roomMap[problemResult.Rooms[i].RoomNumber] = i + 1
		rmSigns[problemResult.Rooms[i].RoomNumber] = 1.0
		maxY =i+2

	tcks = np.arange(startOrdinal, endOrdinal +1)
	tcks = [t - startOrdinal for t in tcks]
	rmtcks = [i for i in range(numberOfRooms + 1)]
	
	
	for i in range(len(assignments)):
		rm = roomMap[assignments[i].AssignedRoom]
		stayLength = assignments[i].Length
		color = 'gray'
		groupName = assignments[i].Name
		
		if assignments[i].IsLocked and assignments[i].AdjacencyGroup is not None:
			color = "purple"
		
		elif assignments[i].IsLocked:
			color = 'red'
		elif assignments[i].AdjacencyGroup is not None:
			color = 'blue'
		
		if assignments[i].TestStay:	
			color = 'green'

		# want to change the color of the min stay... 
		# and max stay, I guess... 
	
	
		arrOrd = date.toordinal(date.fromisoformat(assignments[i].Arrival))
		ax.add_patch(Rectangle((arrOrd - startOrdinal + 0.5,rm-0.4), width = stayLength, height=.8, alpha=0.5,
							   edgecolor = 'black', facecolor = color))
		x = arrOrd - startOrdinal + stayLength/2.0 
		y = rm  
		rmSigns[assignments[i].AssignedRoom] = rmSigns[assignments[i].AssignedRoom]  * -1
		plt.text(x,y,str(groupName), fontsize = fontSize)
	
	
	closeDeparture = problemResult.ClosedDepartures
	closeArrival = problemResult.ClosedArrivals
	
	minStays = problemResult.MinStays
	maxStays = problemResult.MaxStays
	
	for d in np.arange(startOrdinal, endOrdinal + 1):
		day = date.fromordinal(d).strftime('%Y-%m-%d')
		cd = ""
		ca = ""
		if day in closeDeparture:
			cd = "cd"
		if day in closeArrival:
			ca = "ca"
			
		mins = ""
		if day in minStays:
			mins = f"{minStays[day]:.0f}"
		maxs = ""
		if day in maxStays:
			maxs = f"{maxStays[day]:.0f}"
		x = d - startOrdinal + 0.25
		y = maxY
		plt.text(x,y,f"{cd}", fontsize = fontSize)
		plt.text(x,y+0.3,f"{ca}", fontsize = fontSize)
		if mins == "":
			plt.text(x,y+0.6,f"{mins}", fontsize = fontSize)
		else:
			plt.text(x,y+0.6,f"{mins}", fontsize = fontSize)
		plt.text(x,y+0.9,f"{maxs}", fontsize = fontSize)

	rmtcks.append(maxY)
	rmtcks.append(maxY+0.3)
	rmtcks.append(maxY+0.6)
	rmtcks.append(maxY+0.9)
	rmtcks.append(maxY+1.2)  

	plt.grid()
	labels = ['']
	for r in problemResult.Rooms:
		labels.append(str(r.RoomNumber))
	labels.append("close dep.")
	labels.append("close arr.")
	labels.append("min stay:")
	labels.append("max stay:")
	labels.append("")
	
	dayLabels = [date.fromordinal(day) for day in np.arange(startOrdinal, endOrdinal+1)]
	
	plt.xticks(ticks = tcks, labels = dayLabels, rotation='vertical', fontsize = 6)
	plt.yticks(ticks = rmtcks,labels = labels, fontsize = 6)

	plt.xlabel("Days")
	plt.ylabel("Room Number")
	plt.title(figTitle)
	
	buf = io.BytesIO()
	plt.savefig(buf, format='png')
	plt.close()
	return(buf)	

