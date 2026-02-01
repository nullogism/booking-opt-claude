'''
Class for storing Reservation Data
'''

class ReOptimizedPlan:
	def __init__(self, day, length):
		
		self.Day = day # arrival of the added stay
		self.TestLength = length # length of the stay being checked
		
		self.OptimizedPlan = [] # array of assignments
		
		