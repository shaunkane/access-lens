# now finding text only
import numpy, os, cv, uuid, subprocess
cimport numpy, cython

from util import X,Y,WIDTH,HEIGHT

class Recognizer: 
	OCROPUS = 1
	TESSERACT = 2
	CLOUD = 3

tesseractPath = '/usr/local/bin/tesseract' # Name of executable to be called at command line
ocropusPath = '/usr/local/bin/ocropus'
DefaultTesseractArgs = '-l eng' # or 'letters'
DefaultWorkingDirectory = './ocrtemp/'
DefaultRecognizer = Recognizer.TESSERACT
DefaultFileType = 'png'


# cloud ocr
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
cloudURL = 'http://umbc-cloud.appspot.com/upload'
register_openers()


class OCRManager(object): # manage OCR for a single set of images
	def __init__(self, width, height, boxAspectThresh = 0, boxMinSize = 30, windowSize = 12, expand = .01, foregroundWeight = 0.3, dilateSteps = 5, laplaceLevel = 3, useCloud = False):
		self.width = width
		self.height = height
		
		# other params that might matter or maybe who cares
		self.boxAspectThresh = boxAspectThresh
		self.boxMinSize = boxMinSize
		self.windowSize = windowSize
		self.expand = expand
		self.foregroundWeight = foregroundWeight
		self.dilateSteps = dilateSteps
		self.laplaceLevel = laplaceLevel
		
		# scratch images
		self.gray = cv.CreateImage((width,height),cv.IPL_DEPTH_8U,1) 
		self.laplace = cv.CreateImage((width,height),cv.IPL_DEPTH_16S,1)
		self.tempMGD = numpy.zeros((height,width), dtype=numpy.int16)
		self.mgdValues = cv.CreateImage((width,height),cv.IPL_DEPTH_8U,1)
		
	def FindTextAreas(self, frame, verbose=False):
		cv.Zero(self.mgdValues)
		cv.CvtColor(frame, self.gray, cv.CV_BGR2GRAY)
		cv.Laplace(self.gray, self.laplace, self.laplaceLevel)
		boxes = _FindTextAreas(numpy.asarray(cv.GetMat(self.laplace)), self.tempMGD, numpy.asarray(cv.GetMat(self.mgdValues)), self.width, self.height, self.boxAspectThresh, self.boxMinSize, self.windowSize, self.expand, self.foregroundWeight, self.dilateSteps, (1 if verbose else 0))
		return boxes
		boxes2 = []
		for box in boxes:
			ratio = float(box[WIDTH]) / box[HEIGHT]
			if ratio > self.boxAspectThresh and box[HEIGHT] > self.boxMinSize and box[HEIGHT] > self.boxMinSize and box[WIDTH]*box[HEIGHT] > self.boxMinSize*3:
				boxes2.append(box)
		return boxes2

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef _FindTextAreas(numpy.ndarray[numpy.int16_t, ndim=2] laplace, numpy.ndarray[numpy.int16_t, ndim=2] temp, numpy.ndarray[numpy.uint8_t, ndim=2] mgdValues, int videoWidth, int videoHeight, float boxAspectThresh, int boxMinSize, int windowSize, float expand, float foregroundWeight, int dilateSteps, int verbose):
	cdef int start, end, maxVal, minVal, globalMax, globalMin, i, j, k
	globalMax = -1000000 # hacky but should be fine
	globalMin = 1000000
	for 0 <= i < videoWidth:
		for 0 <= j < videoHeight:
			start = i - windowSize
			if start < 0: start = 0
			end = i + windowSize
			if end >= videoWidth: end = videoWidth-1
			maxVal = minVal = laplace[j,start]
			
			for start+1 <= k <= end:
				if laplace[j,k] < minVal: minVal = laplace[j,k]
				if laplace[j,k] > maxVal: maxVal = laplace[j,k]					

			temp[j,i] = maxVal-minVal
			if temp[j,i] > globalMax: globalMax = temp[j,i]
			if temp[j,i] < globalMin: globalMin = temp[j,i]

	# if verbose == 1: cv.SaveImage('output/mgd-1.png', mgdValues)
	for 0 <= i < videoWidth:
		for 0 <= j < videoHeight:
			if (globalMax-temp[j,i])*foregroundWeight < temp[j,i]-globalMin:
				mgdValues[j,i] = 255
			else:
				mgdValues[j,i] = 0

	if verbose == 1: cv.SaveImage('ocrtemp/mgd-2.png', cv.fromarray(mgdValues))
	cv.Dilate(cv.fromarray(mgdValues),cv.fromarray(mgdValues),None,dilateSteps)
	if verbose == 1: cv.SaveImage('ocrtemp/mgd-3.png', cv.fromarray(mgdValues))
	storage = cv.CreateMemStorage(0)
	contour = cv.FindContours(cv.fromarray(mgdValues), storage, cv.CV_RETR_EXTERNAL, cv.CV_CHAIN_APPROX_SIMPLE, (0, 0))
	boxes = []
	while contour != None:
		box = cv.BoundingRect(contour)
		boxes.append(box)
		contour = contour.h_next()
	return boxes