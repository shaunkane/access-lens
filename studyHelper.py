class Stuff(object):
	def __init__(self):
		self.mode = 0
		self.corners = []
		self.boxes = []
		self.overlays = {} # rect->boxIndex
		self.text = {} # boxIndex->text
		self.transform = None
		self.transformInv = None
		self.ocrItemsRemaining = 0
		self.finger = (-1,-1)
		self.searchButton = [0,0,0,0]

class OverlayMode:
	NONE = 0
	EDGE = 1
	SEARCH = 2
	EDGE_PLUS_SEARCH = 3

class Mode:
	NORMAL = 0
	RECTIFIED = 1