import util

StopDistance = 10

class Tracker(object):
	def __init__(self, speech):
		self.speech = speech
		self.target = None
		self.targetName = None
	
	def setTarget(self, t, name=None):
		self.target = t
		self.targetName = name
	
	def isTracking(self):
		return self.target is not None
	
	# return direction (as string) and distance
	def updateDirection(self, point, speak=True):
		if not self.isTracking(): return None
		
		dx = self.target.x - point.x
		dy = self.target.y - point.y
		
		# are we there yet?
		dist = util.Distance(point, self.target)

		if dist < StopDistance:
			if self.targetName is not None:
				direction = "Located %s" % self.targetName
			else:
				direction = "Arrived at destination"
			self.target = None # stop tracking
		elif abs(dx) > abs(dy): # left or right
			if dx > 0: direction = "right"
			else: direction = "left"
		else: # up or down
			if dy > 0: direction = "down"
			else: direction = "up"
		
		if speak and ((not self.speech.IsSpeaking()) or direction == "Arrived at destination"):
			self.speech.Say(direction, interrupt=True)
		
		return direction, dist
			