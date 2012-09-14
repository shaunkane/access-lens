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

### what we need goes in here
vidDepth = 8
camSmall = (640,480) # can go up to 1600x1200 without changing view
camLarge = (2592,1944) # really big is 2592x1944
bigClip = (187,140,2218,1664) # for crazy regions, the 2592 rez gives us a different view. so crop it
bigScale = float(bigClip[2])/camSmall[0]
windowTitle = 'ocrTestWindow'
rotate = -90
trainImages = 30

# bg stuff
findShadow = 0
shadowColorDiff=30.0
shadowMaxDarken=0.3
fitThreshold=16
erodeIterations=2

# MGD stuff
boxAspectThresh = 2.5
dilateSteps = 4
windowSize = 4
boxMinSize = 50

# global for OCR results. the key is the box index, since we won't necessarily get these back in order
ocrResults = {}

# 1, 2, or 4
overlayNumSides = 1

saveFile = 'savestate.pickle'

def main():
	global ocrResults
	logger.debug('Started')	
	speech = speechManager.SpeechManager()
	
	# create the images we need
	imgCopy = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 3) # a rotated copy
	imgFG = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	imgHSV = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 3)
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
	bgModel = bg2.BackgroundModel(camSmall[1], camSmall[0], fitThreshold=fitThreshold, shadowColorDiff=shadowColorDiff, shadowMaxDarken=shadowMaxDarken)
		 
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
	documentCorners = [] # corners in small view
	aspectRatio = None
	transform = None
	transformInv = None
	docWidth = None
	docHeight = None
	bigBoxes = []
	smallBoxes = []
	overlays = []
	overlayIndex = [] # map overlay to box index
	tracking = False
	trackingTarget = None
	finger = None
	lastTouched = None
	colorMode = False
	lastColor = None
	tableMode = False
	topRow = []
	leftRow = []
	showBG = False
	
	# main loop
	while True:
		key = cv.WaitKey(10) # key handler
		if key == 27: break
		char = None if key == -1 else chr(key)
		
		# mini key handler
		if char == 'b':
			showBG = not showBG
			print 'Show bg? %s' % showBG
		elif char == 'c':
			colorMode = not colorMode
			print 'Color mode? %s' % colorMode
		elif char == 'u':
			print 'Updating bg'
			for i in range(0, trainImages):
				smFrame = cv.QueryFrame(camera)
				util.RotateImage(smFrame, imgCopy, rotate)
				bg2.FindBackground(imgCopy, imgFG, bgModel)
				cv.ShowImage(windowTitle, imgFG)
				cv.WaitKey(10)			
		
		# get image
		img = cv.QueryFrame(camera)
		util.RotateImage(img, imgCopy, rotate)
		bg2.FindBackground(imgCopy, imgFG, bgModel, update=0,findShadow=(findShadow and documentOnTable))
		if ocrDone: cv.Erode(imgFG,imgFG,iterations=erodeIterations)
		
		### STEP ONE: DETECT DOCUMENT
		# now, start looking for documents
		if not doingOcr and not documentOnTable:
			if len(sys.argv) > 1 and sys.argv[1].startswith('r'):
				smallBoxes, documentCorners, aspectRatio, ocrResults, docWidth, docHeight, transform, transformInv = LoadState()
				doingOcr = True
				ocrDone = True
				documentOnTable = True
				print 'Loaded'
			
			util.GetGrayscale(imgCopy, imgGray)
			util.GetEdge(frame=imgGray, edge=imgEdge)
			rect = util.FindLargestRectangle(imgFG, imgGray)
			if len(rect) == 4 and util.BoundingRectArea(rect) > 25000:
				accumulator += 1
				if accumulator >= 60:
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
			rect = util.FindLargestRectangle(imgFG, imgGray)
			if len(rect) != 4 or util.BoundingRectArea(rect) < 25000:
				accumulator += 1
				if accumulator >= 30:
					speech.Say('Document removed')
					documentOnTable = False
					documentCorners = []
					ocrDone = False
					accumulator = 0
		
		### STEP TWO: IF THE USER PRESSES THE O KEY, DO OCR
		if documentOnTable and not doingOcr and not ocrDone and char == ' ':
			speech.Say('Starting OCR')
			char = -1
			
			aspectRatio = GetAspectRatio(documentCorners)
			imgRect, transform, transformInv = CreateTransform(documentCorners, imgCopy, aspectRatio)

			# we'll use this later, for overlays
			docWidth = imgRect.width
			docHeight = imgRect.height
						
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
				 cv.WaitKey(10)
			
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
			ocr.ClearOCRTempFiles()
			bigBoxes = FindTextAreas(bigRectified)
			smallBoxes = [(p[0]*1./bigScale,p[1]*1./bigScale,p[2]*1./bigScale,p[3]*1./bigScale) for p in bigBoxes]
									
			# start OCR of text regions
			ocrResults.clear()
			
			bigGray = util.GetGrayscale(bigRectified)
			
			# do the OCR for each box
			for i in range(0, len(bigBoxes)):
				ocr.CreateTempFile(bigGray,bigBoxes[i],i)

			pool = multiprocessing.Pool(4)
			for i in range(0, len(bigBoxes)):
				ocrResults[i] = None
				pool.apply_async(ocr.CallOCREngine, args = (i,), callback = ocrCallback)
			pool.close()
			pool.join()
			
			# now we are done with OCR
			# restore small image
			cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, camSmall[X])
			cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, camSmall[Y])
			
			# get a couple frames to warm up
			for i in range(0,3):
				 smFrame = cv.QueryFrame(camera)
				 cv.WaitKey(10)
				 
			# retrain bg to hide the document
			for i in range(0, trainImages):
				smFrame = cv.QueryFrame(camera)
				util.RotateImage(smFrame, imgCopy, rotate)
				bg2.FindBackground(imgCopy, imgFG, bgModel)
				cv.ShowImage(windowTitle, imgFG)
				cv.WaitKey(10)
			
		### STEP THREE: WAIT FOR OCR TO HAPPEN
		if doingOcr and not ocrDone:
			# did we recognize everything?
			done = None not in ocrResults.values()
			if done: 
				speech.Say('OCR complete. Found %d items' %len([v for v in ocrResults.values() if v is not None and v != '']))
				ocrDone = True
				
				SaveState(smallBoxes, documentCorners, aspectRatio, ocrResults, docWidth, docHeight, transform, transformInv)
				print 'Saved state'
				
				# auto add overlay
				overlays, overlayIndex = CreateOverlays(smallBoxes, docWidth, docHeight, sides=overlayNumSides)
				
				# # we can save this state
				# state = {}
				# state['ocrResults'] = ocrResults
				# state['documentCorners'] = documentCorners
				# state['aspectRatio'] = aspectRatio
				# state['transform'] = transform
				# state['transformInv'] = transformInv
				# state['smallBoxes'] = smallBoxes
				# state['docWidth'] = docWidth
				# state['docHeight'] = docHeight
				# state['overlays'] = overlays
				# timestamp = int(time.time())
				# pickle.dump(state, open('logs/data-%d.pickle' % timestamp, 'wb'))
				
		### STEP FOUR: IF WE HAVE A DOCUMENT, TRACK TOUCH
		if ocrDone:
			finger = GetFingerPosition(imgFG,imgFinger)
			if finger is None: lastTouched = None
			else:
				fingerTrans = util.Transform(finger, transform)
				
				if not tracking:
					if colorMode:
						cv.CvtColor(imgCopy,imgHSV,cv.CV_BGR2HSV)
						color = cv.Get2D(imgHSV, finger[1], finger[0])
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
									if not tableMode: accumulator += 1
									if accumulator > 30: # start tracking
										speech.Say('Locating %s' % ocrResults[index])
										trackingTarget = smallBoxes[index]
										accumulator = 0
								else:
									speech.Say('Shortcut to %s' % ocrResults[index])
									accumulator = 1
								lastTouched = overlay
								handledFinger = True
						# if that doesn't work, see if we are in the paper
						if not handledFinger and util.PointInsideRect(fingerTrans, (0,0,docWidth,docHeight)) and len(smallBoxes) > 0:
							nonEmptyBoxes = [smallBoxes[i] for i in range(0, len(smallBoxes)) if ocrResults[i] is not None and ocrResults[i] != '']
							# if so, get the closest box
							closestBox = min(nonEmptyBoxes, key=lambda b: util.distance(fingerTrans, (b[0]+b[2]/2,b[1]+b[3]/2)))
							index = smallBoxes.index(closestBox)
							box = smallBoxes[index]
							if lastTouched == box:
								pass
							else: # we are in a box
								if not tableMode: speech.Say(ocrResults[index])
								else: # get the row and column
									row, col = GetTableHeaders(box,leftRow,topRow)
									speech.Say('%s, row %s, column %s' % (ocrResults[index],row,col))
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
		if ocrDone and not tracking and char == ' ':
			# available voice commands: color mode, text mode, find, rerecognize, cancel
			util.beep()
			print 'Waiting for voice command'
			commands = ['color','text','find','recognize','cancel', 'all','help']
			input = speech.listen(commands, 5)
			if input is None: 
				util.beep()
				speech.Say('Canceled')
			elif input == 'help':
				speech.Say('You can say ' + ', '.join(commands)
				colorMode = True
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
					proc = multiprocessing.Process(target = ocr.CallOCREngine, args = (i, './ocrtemp/', 'abbyy'), callback = ocrCallback)
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
			elif input == 'overlay':
				overlays, overlayIndex = CreateOverlays(smallBoxes, docWidth, docHeight, sides=overlayNumSides)
				speech.Say('Added overlays')
			elif input == 'table':
				speech.Say('Set table mode')
				overlays, overlayIndex = CreateTableOverlays(smallBoxes, docWidth, docHeight)
			elif input == 'all':
				# get all results
				items = [ocrResults[i] for i in range(0, len(smallBoxes)) if ocrResults[i] is not None and ocrResults[i] != '']
				whatToSay = '%d items. ' % len(items)
				for i in items:
					whatToSay += 'Item %s. ' %i
				speech.Say(whatToSay)
		
		### STEP FIVE: DRAW EVERYTHING
		# doc corners
		util.DrawPoints(imgCopy, documentCorners, color=(255,0,0))
		nonEmptyBoxes = [smallBoxes[i] for i in range(0, len(smallBoxes)) if ocrResults[i] is not None and ocrResults[i] != '']
		
		# boxes and overlays
		for i in range(0,len(smallBoxes)):
			b = smallBoxes[i]
			if b in nonEmptyBoxes:
				util.DrawRect(imgCopy, b, color=(0,0,255), transform=transformInv)
				if ocrResults[i] is not None:
					pbox = util.Transform((b[X],b[Y]), transformInv)
					util.DrawText(imgCopy, ocrResults[i], pbox[X], pbox[Y], color=(0,0,255))
				

		for i in range(0, len(overlays)):
			o = overlays[i]
			# get relevant box index
			box = overlayIndex[i]
			util.DrawRect(imgCopy, o, color=(0,100,255), transform=transformInv)
			if ocrResults[box] is not None:
				po = util.Transform((o[X],o[Y]), transformInv)
				util.DrawText(imgCopy, ocrResults[box], po[X], po[Y], color=(0,100,255))
				
		if finger is not None:
			util.DrawPoint(imgCopy, finger, color=(0,0,255))
			
		cv.ShowImage(windowTitle, imgFG if showBG else imgCopy)
		
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
	ocrm = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = boxAspectThresh, dilateSteps = dilateSteps, windowSize = windowSize, boxMinSize = boxMinSize)
	ocrm.FindTextAreas(imgRect, verbose=True)
	mgd = cv.LoadImage('ocrtemp/mgd-3.png',cv.CV_LOAD_IMAGE_GRAYSCALE )
	storage = cv.CreateMemStorage(0)
	contour = cv.FindContours(mgd, storage, cv.CV_RETR_EXTERNAL, cv.CV_CHAIN_APPROX_SIMPLE, (0, 0))
	boxes = []
	while contour != None:
		curve = contour[:]
		curve = copy.deepcopy(curve)
		box = util.BoundingRect(curve)
		boxes.append(box) # used to be: if box[2] > 20 and box[3] > 20:
		contour = contour.h_next()
	return boxes

def ocrCallback(result):
	global ocrResults
	text, id = result
	ocrResults[id] = text
	print 'Recognized %s, %d of %d remaining' % (text, len([v for v in ocrResults.values() if v is None]), len(ocrResults))

# now we just have the edge overlay, not the search button
def CreateOverlays(boxes, docWidth, docHeight, sides):
	top, right, bottom, left = False, False, False, False
	if sides == 1: # if portrait, right side. otherwise, bottom
		portrait = docHeight > docWidth
		if portrait: right = True
		else: bottom = True
	elif sides == 2: # right and bottom
		right, bottom = True, True
	elif sides == 4: # you guessed it
		top, right, bottom, left = True, True, True, True
	
	# we have multiple sides now
	overlayVWidth = docWidth*.2
	overlayVHeight = float(docHeight) / len(boxes)
	overlayHWidth = float(docHeight) / len(boxes)
	overlayHHeight = docHeight*.2
		
	# our overlays are a tuple: (x,y,w,h)
	overlays = []
	overlayIndex = [] # indicate box index
	
	if right:
		for i in range(0, len(boxes)):
			over = (docWidth, overlayVHeight*i, overlayVWidth, overlayVHeight)
			overlays.append(over)
			overlayIndex.append(i)
	if left:
		for i in range(0, len(boxes)):
			over = (-overlayVWidth, overlayVHeight*i, overlayVWidth, overlayVHeight)
			overlays.append(over)
			overlayIndex.append(i)
	if top:
		for i in range(0, len(boxes)):
			over = (overlayHWidth*i, -overlayHHeight, overlayHWidth, overlayHHeight)
			overlays.append(over)
			overlayIndex.append(i)
	if bottom:
		for i in range(0, len(boxes)):
			over = (overlayHWidth*i, docHeight, overlayHWidth, overlayHHeight)
			overlays.append(over)
			overlayIndex.append(i)

	return overlays, overlayIndex



# we'll add overlays to the top and left
# based on the first row of data
def CreateTableOverlays(boxes, docWidth, docHeight):
	# we have multiple sides now
	overlayVWidth = docWidth*.2
	overlayVHeight = float(docHeight) / len(boxes)
	overlayHWidth = float(docHeight) / len(boxes)
	overlayHHeight = docHeight*.2
		
	# our overlays are a tuple: (x,y,w,h)
	overlays = []
	overlayIndex = [] # indicate box index
	
	# we need to find the top row, and the left row
	topBox = min(boxes, key=lambda b: b[1])
	leftBox = min(boxes, key=lambda b: b[0])
	
	# the top row is items that have a top above the middle of topBox
	topRow = [b for b in boxes if b[1] < topBox[1]+topBox[3]/2.]
	leftRow = [b for b in boxes if b[0] < topBox[0]+topBox[2]/2.]
	
	# left
	for i in range(0, len(leftRow)):
		over = (-overlayVWidth, overlayVHeight*i, overlayVWidth, overlayVHeight)
		overlays.append(over)
		overlayIndex.append(i)

	# top
	for i in range(0, len(topRow)):
		over = (overlayHWidth*i, -overlayHHeight, overlayHWidth, overlayHHeight)
		overlays.append(over)
		overlayIndex.append(i)

	return overlays, overlayIndex, topRow, leftRow

def GetTableHeaders(box,leftRow,topRow):
	leftHeader = min(leftRow, key=lambda b: abs(b[1]-box[1]))
	topHeader = min(topRow, key=lambda b: abs(b[0]-box[0]))
	return leftHeader, topHeader

# no thimble anymore. pass imgFG
def GetFingerPosition(imgFG,imgFinger):
	cv.Copy(imgFG,imgFinger)

	contours = util.FindContours(imgFinger,minSize=(20,20))
	contours.sort(key=lambda c: -1*util.BoundingRectArea(c)) # contours[0] is the biggest
	
	if len(contours) > 0:
		bigContour = contours[0]
		top = min(bigContour, key=lambda p:p[1])
		return top[:]
	
	else: return None # nothing

# get a friendly color name for a BGR value
def GetColorName(color):
	h,s,v = color[0],color[1],color[2]
	
	if v > 240 and s < 100: return 'white'
	elif v < 20: return 'black'
	elif s < 40: return 'gray'
	elif h < 30: return 'red'
	elif h < 60: return 'yellow'
	elif h < 120: return 'blue'
	else: return 'purple'

def SaveState(smallBoxes, documentCorners, aspectRatio, ocrResults, docWidth, docHeight, transform, transformInv):
	state = {}
	state["smallBoxes"] = smallBoxes
	state["documentCorners"] = documentCorners
	state["aspectRatio"] = aspectRatio
	state["ocrResults"] = ocrResults
	state["docWidth"] = docWidth
	state["docHeight"] = docHeight
	state["transform"] = transform
	state["transformInv"] = transformInv
	pickle.dump(state, open(saveFile,'wb'))

def LoadState():
	state = pickle.load(open(saveFile,'rb'))
	return state["smallBoxes"], state["documentCorners"], state["aspectRatio"], state["ocrResults"], state["docWidth"], state["docHeight"], state["transform"], state["transformInv"]
	
if __name__ == "__main__": main()