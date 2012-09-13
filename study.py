import cv, numpy, sys, pickle, math
import ocr, ocr2, util, bg2, camera, gui, hand2, dict
from util import X,Y,WIDTH,HEIGHT
import os
import multiprocessing, subprocess
import time
import speechManager
from studyHelper import *
from log import *
import quikBoto
import json
import urllib2
import copy
import multiprocessing

pickleFile = 'temp.pickle'
saveToFile = True
processInput = True # we can turn off handleframe

boto = None
touchLimit = 30 # dwell for tracking

threshold = 30*1
tracking = None
overlayMode = OverlayMode.NONE
drewOverlays = False
handInView = False

useCloudOcr = False
useThimble = True

bigImage = None
mediumImage = None
smallImage = None
newImageToProcess = False

bgModel = None
boxesToRecognize = {}

rectWidth = 0
rectHeight = 0


### what we need goes in here
vidDepth = 8
camSmall = (640,480) # can go up to 1600x1200 without changing view
camLarge = (2592,1944) # really big is 2592x1944
bigClip = (187,140,2218,1664) # for crazy regions, the 2592 rez gives us a different view. so crop it
bigScale = float(camLarge[2])/camSmall[0]
windowTitle = 'ocrTestWindow'
rotate = -90
trainImages = 30

# MGD stuff
boxAspectThresh = 1.5
dilateSteps = 6
windowSize = 4
boxMinSize = 50

# global for OCR results. the key is the box index, since we won't necessarily get these back in order
ocrResults = {}

def main():
	logger.debug('Started')	
	speech = speechManager.SpeechManager()
	
	# create the images we need
	imgCopy = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 3) # a rotated copy
	imgFG = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	imgGray = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	imgEdge = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	imgFinger = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	
	# big images
	imgBigCropped = cv.CreateImage((bigClip[2],bigClip[3]), vidDepth, 3)
	imgBigRotated = cv.CreateImage((bigClip[3],bigClip[2]), vidDepth, 3)
	
	# set up cam
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, camSmall[X])
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, camSmall[Y])
	# SetResolution(camSmall)
	
	img = cv.QueryFrame(camera)
	util.RotateImage(img, imgCopy, rotate)
	
	cv.NamedWindow(windowTitle, 1) 
	counter = 0
	
	# before we do anything, create our background model
	bgModel = bg2.BackgroundModel(camSmall[1], camSmall[0], yThreshold=20, fitThreshold=16, yccMode=0)
		 
	for i in range(0, trainImages):
		smFrame = cv.QueryFrame(camera)
		util.RotateImage(smFrame, imgCopy, rotate)
		bg2.FindBackground(imgCopy, imgFG, bgModel)
		cv.ShowImage(windowTitle, imgFG)
		cv.WaitKey(10)
	
	# keep state here
	documentOnTable = False
	doingOcr = False
	ocrDone = False
	accumulator = 0
	documentCorners = None # corners in small view
	aspectRatio = None
	transform = None
	transformInv = None
	docWidth = None
	docHeight = None
	smallBoxes = []
	overlays = []
	tracking = False
	trackingTarget = None
	finger = None
	lastTouched = None
	colorMode = False
	lastColor = None
	
	# main loop
	while True:
		key = cv.WaitKey(10) # key handler
		if key == 27: break		
		
		# get image
		img = cv.QueryFrame(camera)
		util.RotateImage(img, imgCopy, rotate)
		bg2.FindBackground(imgCopy, imgFG, bgModel, update=0)
		
		### STEP ONE: DETECT DOCUMENT
		# now, start looking for documents
		if not doingOcr and not documentOnTable:
			util.GetGrayscale(imgCopy, imgGray)
			util.GetEdge(frame=imgGray, edge=imgEdge)
			rect = util.FindLargestRectangle(imgEdge, imgGray)
			if len(rect) == 4 and util.BoundingRectArea(rect) > 25000:
				accumulator += 1
				if accumulator == 30:
					accumulator = 0
					speech.Say('Document detected')
					documentOnTable = True
					documentCorners = rect
			else:
				accumulator = 0
		# if we have a document, wait for it to go away
		elif not doingOcr and documentOnTable:
			util.GetGrayscale(imgCopy, imgGray)
			util.GetEdge(frame=imgGray, edge=imgEdge)
			rect = util.FindLargestRectangle(imgEdge, imgGray)
			if len(rect) != 4 or util.BoundingRectArea(rect) < 25000:
				accumulator += 4
				if accumulator == 30:
					speech.Say('Document removed')
					documentOnTable = False
					ocrDone = False
					accumulator = 0
		
		### STEP TWO: IF THE USER PRESSES THE O KEY, DO OCR
		if documentOnTable and not doingOcr and not ocrDone and chr(key) == 'o':
			aspectRatio = GetAspectRatio(documentCorners)
			imgRect, transform, transformInv = CreateTransform(documentCorners, imgCopy, aspectRatio)

			# we'll use this later, for overlays
			docWidth = imgRect.width
			docHeight = imgRect.height

			speech.Say('Starting OCR, please move your hand')
			accumulator = 0
			doingOcr = True
			timestamp = int(time.time()*1000)

			# save small image
			cv.SaveImage('logs/small-%d.png' % timestamp, imgCopy)
			cv.SaveImage('logs/smallrect-%d.png' % timestamp, imgRect)
			
			# get big image
			print 'Getting big image'
			cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, camLarge[X])
			cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, camLarge[Y])
			
			# get a couple frames to warm up
			for i in range(0,10):
				 bigFrame = cv.QueryFrame(camera)
			
			bigFrame = cv.QueryFrame(camera)
			cv.SaveImage('logs/big-%d.png' % timestamp, bigFrame)
			
			# crop big image
			cropRegion = cv.GetSubRect(bigFrame, bigClip)
			cv.Copy(cropRegion, imgBigCropped)
			cv.SaveImage('logs/bigcropped-%d.png' % timestamp, imgBigCropped)
			
			# rotate big image
			util.RotateImage(imgBigCropped, imgBigRotated, rotate)
			cv.SaveImage('logs/bigrotated-%d.png' % timestamp, imgBigRotated)
			
			# rectify big image
			scaledCorners = [(p[0]*bigScale,p[1]*bigScale) for p in documentCorners]
			bigRectified, bigTransform, bigTransformInv = CreateTransform(scaledCorners, imgBigRotated, aspectRatio)
			cv.SaveImage('logs/bigrectified-%d.png' % timestamp, bigRectified)
			
			# get text regions
			print 'Getting text regions'
			bigBoxes = FindTextAreas(bigRectified)
			speech.Say('Found %d text regions' % len(boxes))
			
			# start OCR of text regions
			ocr.ClearOCRTempFiles()
			global ocrResults
			ocrResults.clear()
			# do the OCR for each box
			pool = multiprocessing.Pool(32)
			lock = multiprocessing.Lock()
			for i in range(0, len(bigBoxes)):
				ocrResults[i] = None
				pool.apply_async(ocr.CallOCREngine, args = (bigRectified, bigBoxes[i], i, lock), callback = ocrCallback)
			pool.close()
			pool.join()
			# now we are done with OCR
			speech.Say('Waiting on OCR')
			
		### STEP THREE: WAIT FOR OCR TO HAPPEN
		if doingOcr and not ocrDone:
			# did we recognize everything?
			done = None not in ocrResults.values()
			if done: 
				speech.Say('OCR complete')
				ocrDone = True
				# create overlays
				smallBoxes = [(p[0]*1./bigScale,p[1]*1./bigScale,p[2]*1./bigScale,p[3]*1./bigScale) for p in bigBoxes]
				overlays = CreateOverlays(smallBoxes, docWidth, docHeight)
				speech.Say('Added edge index')
				
				# we can save this state
				state = {}
				state['ocrResults'] = ocrResults
				state['documentCorners'] = documentCorners
				state['aspectRatio'] = aspectRatio
				state['transform'] = transform
				state['transformInv'] = transformInv
				state['smallBoxes'] = smallBoxes
				state['docWidth'] = docWidth
				state['docHeight'] = docHeight
				state['overlays'] = overlays
				
				timestamp = int(time.time())
				pickle.dump(state, open('logs/data-%d.pickle' % timestamp, 'wb'))
				
		### STEP FOUR: IF WE HAVE A DOCUMENT, TRACK TOUCH
		if ocrDone:
			finger = GetFingerPosition(imgFG,imgFinger)
			if finger is None: lastTouched = None
			else:
				fingerTrans = util.Transform(finger, transform)
				
				if not tracking:
					if colorMode:
						color = cv.Get2D(imgCopy, finger[0], finger[1])
						colorName = GetColorName(color)
						if colorName != lastColor:
							speech.Say(colorName)
							lastColor = colorName
					else:
						handledFinger = False
						# first, check to see if we are in an overlay
						for overlay in overlays:
							if not handledFinger and util.PointInsideRect(fingerTrans, overlay):
								index = overlays.index(overlay)
								if lastTouched == overlay:
									accumulator += 1
									if accumulator > 30: # start tracking
										speech.Say('Locating %s' % ocrResults[index])
										trackingTarget = smallBoxes[index]
										accumulator = 0
								else:
									speech.Say('Shortcut to %s' % )
									accumulator = 1
								lastTouched = overlay
								handledFinger = True
						# if that doesn't work, see if we are in the paper
						elif not handledFinger and util.PointInsideRect(fingerTrans, (0,0,docWidth,docHeight)):
							# if so, get the closest box
							closestBox = min(smallBoxes, key=lambda b: util.distance(fingerTrans, (b[0],b[1])))
							index = smallBoxes.index(closestBox)
							box = smallBoxes[index]
							if lastTouched == box:
								pass
							else:
								speech.Say(ocrResults[index])
							lastTouched = box
				else: # tracking
					# are we in are target?
					if util.PointInsideRect(fingerTrans, trackingTarget):
						index = smallBoxes.index(trackingTarget)
						name = ocrResults[index]
						speech.Say('Located %s' % name)
						tracking = False
					else:
						box = trackingTarget
						trackPoint = [box[0]+box[2]/2,box[1]+box[3]/2]
						dx = trackPoint[0] - fingerTrans[0]
						dy = trackPoint[1] - fingerTrans[1]
		
						# get dir
						direction = ''
						if abs(dx) > abs(dy):
							if dx > 0: direction = 'right'
							else: direction = 'left'
						else:
							if dy > 0: direction = 'down'
							else: direction = 'up'
						
						if counter % 10 == 0:
							speech.Say(direction)
				
		### STEP FOUR AND A HALF: CHECK FOR VOICE COMMANDS
		if ocrDone and not tracking and chr(key) == ' ':
			# available voice commands: color mode, text mode, find, rerecognize, cancel
			util.beep()
			input = speech.listen(['color','text','find','recognize','cancel'], 10)
			if input is None: 
				util.beep()
				speech.Say('Canceled')
			elif input == 'color':
				speech.Say('Color mode selected')
				colorMode = True
			elif input == 'text':
				speech.Say('Text mode selected')
				colorMode = False
			elif input == 'recognize':
				if lastTouched is None: speech.Say('No text selected')
				else:
					speech.Say('rerecognizing')
					proc = multiprocessing.Process(target = ocr.CallOCREngine, args = (None, bigBoxes[lastTouched], i, None), callback = ocrCallback)
					proc.start()
					proc.join()
			elif input == 'cancel':
				speech.Say('Canceled')
			elif input == 'find':
				util.beep()
				speech.Say('Say the first word of the section you wish to find')
				# get first words
				firstWords = []
				phrases = []
				for i in range(0, len(ocrResults)):
					phrase = ocrResults[i]
					phrases.append(phrase)
					if phrase is None:
						firstWords.append(None)
					else:
						firstWords.append(phrase.split(' ')[0])

				wordFind = speech.listen(firstWords, 10)
				if wordFind is None: 
					util.beep()
					speech.Say('Not found')
				else:
					match = firstWords.index(wordFind)
					speech.Say('Tracking %s' % ocrResults[match])
					tracking = True
					trackingTarget = smallBoxes[match]
		
		### STEP FIVE: DRAW EVERYTHING
		# doc corners
		util.DrawPoints(imgCopy, documentCorners, color=(255,0,0))
		
		# boxes and overlays
		for i in range(0,len(smallBoxes)):
			b = smallBoxes[i]
			o = overlays[i]
			util.DrawRect(imgCopy, b, color=(0,0,255), transform=transformInv)
			util.DrawRect(imgCopy, o, color=(0,100,255), transform=transformInv)
			if ocrResults[i] is not None:
				pbox = util.Transform((b[X],b[Y]), stransformInv)
				util.DrawText(imgCopy, ocrResults[i], pbox[X], pbox[Y], color=(0,0,255))
				po = util.Transform((o[X],o[Y]), transformInv)
				util.DrawText(imgCopy, text, po[X], po[Y], color=(0,100,255))

		if finger is not None:
			util.DrawPoint(imgCopy, finger, color=(0,0,255))
			
		cv.ShowImage(windowTitle, imgCopy)
		
		### STEP END: INCREMENT THE COUNTER
		counter += 1
		### END OF MAIN LOOP

	logger.debug('Ended')

####################
# utility functions
####################

def GetAspectRatio(points, options=((8.5,11),(11,8.5),(5,5))):
	ratio = util.GetAspectRatio(points, options)
	logging.debug('Guessed aspect ratio! %f:%f' % ratio)
	return ratio

def CreateTransform(corners, imgCopy, aspectRatio):
	rectified, transform = util.GetRectifiedImage(imgCopy, corners, aspectRatio)
	transformInv = numpy.linalg.inv(transform)
	return rectified, transform, transformInv

def FindTextAreas(imgRect):
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = boxAspectThresh, dilateSteps = dilateSteps, windowSize = windowSize, boxMinSize = boxMinSize)
	ocr.FindTextAreas(imgRect, verbose=True)
	mgd = cv.LoadImage('output/mgd-3.png',cv.CV_LOAD_IMAGE_GRAYSCALE )
	storage = cv.CreateMemStorage(0)
	contour = cv.FindContours(mgd, storage, cv.CV_RETR_EXTERNAL, cv.CV_CHAIN_APPROX_SIMPLE, (0, 0))
	boxes = []
	while contour != None:
		curve = contour[:]
		curve = copy.deepcopy(curve)
		box = util.BoundingRect(curve)
		if box[2] > 20 and box[3] > 20: boxes.append(box)
		contour = contour.h_next()
	return boxes

def ocrCallback(result):
	global ocrResults
	text, id = result
	ocrResults[id] = text
	print 'Recognized %s, %d of %d remaining' % (text, len(ocrResults), len([v for v in ocrResults.values() if v is None]))

# now we just have the edge overlay, not the search button
def CreateOverlays(boxes, docWidth, docHeight):
	overlayWidth = docWidth*.2
	overlayHeight = float(docHeight) / len(stuff.text.keys())
	overlayX = docWidth + overlayWidth/4
	
	# our overlays are a tuple: (x,y,w,h)
	overlays = []
	for i in range(0, len(boxes)):
		overlays.append((overlayX, overlayHeight*i, overlayWidth, overlayHeight))
	return overlays	

# no thimble anymore. pass imgFG
def GetFingerPosition(imgFG,imgFinger):
	cv.Copy(imgFG,imgFinger)

	contours = util.FindContours(imgFinger,minSize=(20,20))
	contours.sort(key=lambda c: -1*util.BoundingRectArea(c)) # contours[0] is the biggest
	
	if len(contours) > 0:
		bigContour = contours[0]
		top = min(bigContour, key=lambda p:p[1])
		return top
	
	else: return None # nothing

# get a friendly color name for a BGR value
def GetColorName(color):
	r,g,b = color[2],color[1],color[0]
	
	colorNames = ['red','orange','yellow''green','blue','purple','brown','gray','white','black','pink']
	colorPairs = [(255,0,0),(255,165,0),(255,255,0),(0,255,0),(0,0,255),(128,0,128),(165,42,42),(100,100,100),(255,255,255),(0,0,0),(255,0,255)]
	
	bestMatch = min(colorPairs, key=lambda c: (c[0]-r)**2+(c[1]-g)**2+(c[2]-b)**2 )
	bestName = colorNames[colorPairs.index(bestMatch)]
	return bestName
	
if __name__ == "__main__": main()