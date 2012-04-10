class Stuff(object):
	def __init__(self):
		self.mode = 0
		self.corners = []
		self.boxes = []
		self.overlays = []
		self.text = {}
		self.transform = None
		self.transformInv = None
		self.ocrItemsRemaining = 0
		self.finger = None	

class OverlayMode:
	NONE = 0
	EDGE = 1
	SEARCH = 2
	EDGE_PLUS_SEARCH = 3

class Mode:
	NORMAL = 0
	RECTIFIED = 1