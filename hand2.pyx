cimport numpy
cimport cython
import cv, numpy
import util

class Gesture:
	NONE = "None"
	ONEFINGER = "One finger"
	TWOFINGER = "Two fingers"
	CIRCLE = "Circle"
	UNKNOWN = "Unknown"

class HandClassifier(object):
	def __init__(self, historySize = 10, minHistoryCount = 7):
		self.historySize = historySize
		self.minHistoryCount = minHistoryCount
		self.history = []

	def ClassifyHandGesture(self, skin, bg, cross1 = 20, cross2 = 60, cross3 = 120, useX = False):
		skinCon = util.FindContours(skin, minSize=util.Size(50,50))
		if len(skinCon) == 0:  
			gesture = Gesture.NONE
			cursor = None
		else:
			biggestContour = max(skinCon, key=lambda g: util.BoundingRectArea(g))
			rect = util.BoundingRect(biggestContour)
			gesture = _ClassifyHandGesture(numpy.asarray(cv.GetMat(skin)), numpy.asarray(cv.GetMat(bg)), skin.width, skin.height, rect, cross1, cross2, cross3)
			if useX: cursor = min(biggestContour, key=lambda c: c.x)
			else: cursor = min(biggestContour, key=lambda c: c.y)
			
			# find the cursor
			#if gesture in (Gesture.ONEFINGER, Gesture.TWOFINGER, Gesture.UNKNOWN, Gesture.NONE):
				#cursor = min(biggestContour, key=lambda c: c.y)
				# later. if circle, find inner contour and get center
			#else:
				#cursor = None

		if len(self.history) >= self.historySize: self.history = self.history[-(self.historySize-1):]
		self.history.append(gesture)
		
		if self.history.count(gesture) < self.minHistoryCount: gesture = Gesture.UNKNOWN
		return gesture, cursor

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef _ClassifyHandGesture(numpy.ndarray[numpy.uint8_t, ndim=2] skin, numpy.ndarray[numpy.uint8_t, ndim=2] bg, int width, int height, rect, int cross1, int cross2, int cross3, int padding = 5):
	cdef int top, bottom, left, right
	top = rect.y
	bottom = rect.y+rect.height
	left = rect.x - padding
	right = rect.x+rect.width + padding
	
	cdef int x, y, value, i
	cdef int c1, c2, c3
	c1 = 0
	c2 = 0
	c3 = 0
	
	
	with nogil:
		y = top+cross1
		if cross1 == -1 or y >= bottom: c1 = -1
		else:
			value = skin[y,left]
			for left < x < right:
				if skin[y,x] != value:
					value = skin[y,x]
					c1 = c1 + 1
					skin[y,x] = 255
				else: skin[y,x] = 50
		y = top+cross2
		if cross2 == -1 or y >= bottom: c2 = -1
		else:
			value = skin[y,left]
			for left < x < right:
				if skin[y,x] != value:
					value = skin[y,x]
					c2 = c2 + 1
					skin[y,x] = 255
				else: skin[y,x] = 50
		y = top+cross3
		if cross3 == -1 or y >= bottom: c3 = -1
		else:
			value = skin[y,left]
			for left < x < right:
				if skin[y,x] != value:
					value = skin[y,x]
					c3 = c3 + 1
					skin[y,x] = 255
				else: skin[y,x] = 50


	# print 'c1 %d c2 %d c3 %d' % (c1,c2,c3)
	# classify based on crossings
	if c1 == 2 and c2 == 2:
		gesture = Gesture.ONEFINGER
	elif (c1 == 2 or c1 == 4) and c2 == 4 and c3 == 4:
		gesture = Gesture.TWOFINGER
	elif c2 == 2 and c2 == 4:
		gesture = Gesture.CIRCLE
	else:
		gesture = Gesture.UNKNOWN
	return gesture