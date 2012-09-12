import cv, numpy, sys, pickle, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
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

windowTitle = 'ocrTestWindow'
pickleFile = 'temp.pickle'
saveToFile = True
smallRez = (640,480)
bigRez = (1280,960)
reallyBigRez = (2592,1944)
vidDepth = 8
rotate = -90
processInput = True # we can turn off handleframe

boto = None
touchLimit = 20


img = cv.CreateImage(smallRez, vidDepth, 3)
imgCopy = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgGray = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgB = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgG = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgR = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgFG = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgEdge = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgHSV = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgMasked = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgFinger = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgRect = None

threshold = 30*1
tracking = None
overlayMode = OverlayMode.NONE
drewOverlays = False
handInView = False

speech = speechManager.SpeechManager()
useCloudOcr = False
useThimble = True

# ocr stuff
boxAspectThresh = 1.5
dilateSteps = 6
windowSize = 4
boxMinSize = 50

bigImage = None
mediumImage = None
smallImage = None
newImageToProcess = False

stuff = Stuff()

bgModel = None
boxesToRecognize = {}

rectWidth = 0
rectHeight = 0

# capture big, medium, small images
def CaptureImages():
<<<<<<< HEAD
	global bigImage, mediumImage, smallImage, newImageToProcess, bgModel
	speech.Say('Capturing images')
	
	timestamp = int(time.time()*1000)
	sname = 'logs/small-%d.png' % timestamp
	mname = 'logs/med-%d.png' % timestamp
	lname = 'logs/large-%d.png' % timestamp
	
	# first, large
	SetResolution(reallyBigRez)
	lgFrame = cv.QueryFrame(camera)
	bigImage = util.RotateImage(lgFrame, None, rotate)
	cv.SaveImage(lname, bigImage)
	print 'Saved big image: %s' % lname
	
	# medium
	SetResolution(bigRez)
	mdFrame = cv.QueryFrame(camera)
	mediumImage = util.RotateImage(mdFrame, None, rotate)
	cv.SaveImage(mname, mediumImage)
	print 'Saved medium image: %s' % mname
	
	# small
	SetResolution(smallRez)
	smFrame = cv.QueryFrame(camera)
	smallImage = util.RotateImage(smFrame, None, rotate)
	cv.SaveImage(sname, smallImage)
	print 'Saved small image: %s' % sname
	
	# IF IT BREAKS, HERE IS WHY
	aspectRatio = GetAspectRatio(stuff.corners)
	imgRect, transform, transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
	global rectWidth, rectHeight
	rectWidth = imgRect.width
	rectHeight = imgRect.height
	
	# background
	size = smallRez if rotate == 0 else (smallRez[1],smallRez[0])
	bgModel = bg2.BackgroundModel(size[0], size[1], yThreshold=20, fitThreshold=16, yccMode=0)
	 
	trainImages = 30
	logging.debug('Training background')
	for i in range(0, trainImages):
=======
	if len(stuff.corners) == 4:
		global bigImage, mediumImage, smallImage, newImageToProcess, bgModel
		print 'Capturing images'
		
		timestamp = int(time.time()*1000)
		sname = 'logs/small-%d.png' % timestamp
		mname = 'logs/med-%d.png' % timestamp
		lname = 'logs/large-%d.png' % timestamp
		
		# first, large
		SetResolution(reallyBigRez)
		lgFrame = cv.QueryFrame(camera)
		bigImage = util.RotateImage(lgFrame, None, rotate)
		cv.SaveImage(lname, bigImage)
		print 'Saved big image: %s' % lname
		
		# medium
		SetResolution(bigRez)
		mdFrame = cv.QueryFrame(camera)
		mediumImage = util.RotateImage(mdFrame, None, rotate)
		cv.SaveImage(mname, mediumImage)
		print 'Saved medium image: %s' % mname
		
		# small
		SetResolution(smallRez)
>>>>>>> About to get into things
		smFrame = cv.QueryFrame(camera)
		smallImage = util.RotateImage(smFrame, None, rotate)
		cv.SaveImage(sname, smallImage)
		print 'Saved small image: %s' % sname
		
		# background
		size = smallRez if rotate == 0 else (smallRez[1],smallRez[0])
		bgModel = bg2.BackgroundModel(size[0], size[1], yThreshold=20, fitThreshold=16, yccMode=0)
		 
		trainImages = 30
		logging.debug('Training background')
		for i in range(0, trainImages):
			smFrame = cv.QueryFrame(camera)
			smallImage = util.RotateImage(smFrame, None, rotate)
			bg2.FindBackground(smallImage, imgFG, bgModel)
		logging.debug('Background training complete')
		newImageToProcess = True

# get text areas and start OCR

overlayLookup = {}
mediumImage = None 
mediumRect = None 
bigCorners = None 
bigBoxes = None
def ProcessImage():
	global bigImage, mediumImage, smallImage, overlayLookup
	global mediumImage, mediumRect, bigCorners, bigBoxes
	if bigImage is None: CaptureImages()
	# find rectangle
	
	# do everything with the medium document, then scale down
	scaleFactor = float(smallImage.width) / mediumImage.width
	
	gray = util.GetGrayscale(mediumImage)
	edge = util.GetEdge(frame=gray)
	bigCorners = util.FindLargestRectangle(edge, gray)
	
	#speech.Say('Locating document')
	#util.GetGrayscale(imgCopy, imgGray)
	#util.GetEdge(frame=imgGray, edge=imgEdge)
	#rect = util.FindLargestRectangle(imgEdge, imgGray)
	if len(bigCorners) == 4 and util.BoundingRectArea(bigCorners) > 400:
		# squish corners down
	
		#stuff.corners = []
		#for p in bigCorners: stuff.corners.append([p[0]*scaleFactor,p[1]*scaleFactor])
		
		aspectRatio = GetAspectRatio(bigCorners)
		
		#speech.Say("Document detected. Starting OCR")
		mediumRect, bigTrans, bigInv = CreateTransform(bigCorners, mediumImage, aspectRatio)
		# now do it with the small one
		imgRect, stuff.transform, stuff.transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
		global rectWidth, rectHeight
		rectWidth = imgRect.width
		rectHeight = imgRect.height
		
		#speech.Say('Locating text')
		bigBoxes = FindTextAreas(mediumImage, mediumRect, bigCorners, aspectRatio)
		stuff.boxes = []
		try:
			for p in bigBoxes:
				stuff.boxes.append([p[0]*scaleFactor,p[1]*scaleFactor,p[2]*scaleFactor,p[3]*scaleFactor])
		except Exception as e:
			logger.debug('It broke! %s' % e)	
		finally:
			speech.Say('Located %d potential text items' % len(stuff.boxes), block=True) 

def CreateOverlays():
	stuff.overlays = {}
	if overlayMode == OverlayMode.EDGE or overlayMode == OverlayMode.EDGE_PLUS_SEARCH or overlayMode == OverlayMode.SEARCH and len(stuff.text.keys()) > 0:
		global rectWidth, rectHeight
		aspectRatio = GetAspectRatio(stuff.corners)
		imgRect, stuff.transform, stuff.transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
		rectWidth = imgRect.width
		rectHeight = imgRect.height
		docWidth = rectWidth
		docHeight = rectHeight
		overlayWidth = docWidth*.2
		overlayHeight = float(docHeight) / len(stuff.text.keys())
		# fix - moved this here
		overlayX = docWidth
		overlayLookup = {}
	
		# get reverse overlay lookup
		# this has words as a key and box index as the value
		for boxIndex in stuff.text.keys():
			overlayLookup[stuff.text[boxIndex]] = boxIndex
		
		# set the overlay. key (rect), value (boxIndex)
		overlayTexts = sorted(overlayLookup.keys())
		y = 0 # height of the next rect
		for text in overlayTexts:
			rect = [overlayX, y, overlayWidth, overlayHeight]
			y += overlayHeight
			stuff.overlays[overlayLookup[text]] = rect

	if overlayMode == OverlayMode.SEARCH or overlayMode == OverlayMode.EDGE_PLUS_SEARCH: 
		docWidth = rectWidth
		docHeight = rectHeight
		overlayWidth = docWidth*.2
		overlayX = -overlayWidth/2
		overlayY = docHeight - overlayWidth/2
		
		stuff.searchButton = [overlayX, overlayY, overlayWidth, overlayHeight*4]
				
def StartOcr():
	global boxesToComplete
	boxesToComplete = {}
	for i in range(0, len(stuff.boxes)):
		boxesToComplete[i] = True

	speech.Say('Starting OCR', block=True)
	if not useCloudOcr: DoOCR(mediumImage, mediumRect, bigCorners, bigBoxes)
	else: DoCloudOCR(mediumImage, mediumRect, bigCorners, bigBoxes)
	
	while len(boxesToComplete.keys()) > 0:
		print 'Waiting for %d OCR items' % (len(boxesToComplete.keys()))
		# speech.Say('Waiting for %d OCR items' % (len(stuff.boxes) - len(stuff.text.keys())))
		time.sleep(5)
	speech.Say('OCR complete', block=True)
	
	# add overlays
	CreateOverlays()
	
	# enable gestures
	global processInput
	processInput = True

accumulator = 0	
documentOnTable = False
touched = None
touchCounter = 0
def HandleFrame(img, imgCopy, imgGray, imgEdge, imgRect, imgHSV, imgFinger, counter, stuff):
	global accumulator
	global bigImage, mediumImage, smallImage 
	global documentOnTable
	global tracking
	
	if not documentOnTable:
		util.GetGrayscale(imgCopy, imgGray)
		util.GetEdge(frame=imgGray, edge=imgEdge)
		rect = util.FindLargestRectangle(imgEdge, imgGray)
		if len(rect) == 4 and util.BoundingRectArea(rect) > 25000:
			accumulator += 1
			if accumulator == 120:
				accumulator = 0
				speech.Say('Document detected')
				documentOnTable = True
				stuff.corners = rect
				# get transforms
				aspectRatio = GetAspectRatio(rect)
				
				imgRect, stuff.transform, stuff.transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
		else:
			accumulator = 0
	elif documentOnTable:
		util.GetGrayscale(imgCopy, imgGray)
		util.GetEdge(frame=imgGray, edge=imgEdge)
		rect = util.FindLargestRectangle(imgEdge, imgGray)
		if len(rect) != 4 or util.BoundingRectArea(rect) < 25000:
			accumulator += 4
			if accumulator == 6000:
				speech.Say('Document removed')
				documentOnTable = False
				stuff.corners = []
				accumulator = 0
		#else:
		#	accumulator -= 2		
		
	if processInput and len(stuff.text.keys()) > 0 and tracking is None:  # finger tracking, tracing 
		global touched, touchCounter, touchLimit
		stuff.finger = GetCursor(imgCopy, imgHSV, imgFinger)
		
		doc = [0,0,rectWidth,rectHeight]
		
		fingerTrans = util.Transform(stuff.finger, stuff.transform)
		
		# print doc, fingerTrans
		
		# what are we touching? overlay, search button, in paper, item
		fingerHandled = False
		
		for id in stuff.overlays.keys():
			overlay = stuff.overlays[id]
			if not fingerHandled and util.PointInsideRect(fingerTrans, overlay):
				fingerHandled = True
				if touched is None or touched != overlay:
					# new, say it
					whatToSay = stuff.text[id].split(' ')[0] # first 1 words
					speech.Say('Shortcut %s.' % whatToSay)
					touched = overlay
					touchCounter = 0
				else: # dwell 
					touchCounter += 1
					if touchCounter == touchLimit: # start tracking
						tracking = id
						speech.Say('Finding %s' % stuff.text[id])
		# search button
		if not fingerHandled and util.PointInsideRect(fingerTrans, stuff.searchButton):
			fingerHandled = True
			if touched is None or touched != stuff.searchButton:
				speech.Say('Search')
				touched = stuff.searchButton
				touchCounter = 0
			else: #dwell
				touchCounter += 1
				if touchCounter == touchLimit: # start tracking
					util.beep()
					items = [word.split(' ')[0] for word in stuff.text.values()]
					allWords = [phrase.split(' ') for phrase in items]
<<<<<<< HEAD
					command = speech.listen(phrases=stuff.text.values())
					if command is not None and command != '':
						for key in stuff.text.keys():
							text = stuff.text[key]
							if command in text: # found it
								tracking = key
								speech.Say('Finding %s' % stuff.text[key])
								break
=======
					
					try:
						command = speech.listen(phrases=allWords)
						if command is not None and command != '':
							for key in stuff.text.keys():
								text = stuff.text[key]
								if command in text: # found it
									tracking = key
									speech.Say('Finding %s' % stuff.text[key])
									break

					except KeyboardInterrupt:
						print 'Speech canceled'
>>>>>>> About to get into things
		# inside an item?
		for box in stuff.boxes:
			if not fingerHandled and util.PointInsideRect(fingerTrans, box):
				fingerHandled = True
				touchCounter = 0
				if touched is None or touched != box:
					speech.Say(stuff.text[stuff.boxes.index(box)])
					touched = box
					
		# otherwise, if inside page, find the nearest rect
		if not fingerHandled and util.PointInsideRect(fingerTrans, doc):
			# print 'looking'
			# get the center of each rect, which is the closest?
			validBoxes = []
			for i in range(0, len(stuff.boxes)):
				if stuff.text.has_key(i): validBoxes.append(stuff.boxes[i])
			# print validBoxes
			centers = [(p[0]+p[2]/2,p[1]+p[3]/2) for p in validBoxes]
			closestBox = centers.index(min(centers, key=lambda c: util.Distance(c, fingerTrans)))
			box = validBoxes[closestBox]
			fingerHandled = True
			touchCounter = 0
			if touched is None or touched != box:
				speech.Say(stuff.text[stuff.boxes.index(box)])
				touched = box
		elif not fingerHandled: 
			touchCounter = 0
			touched = None
		if not fingerHandled: 
			touched=None
			touchCounter = 0
	elif tracking is not None: # tracking
		stuff.finger = GetCursor(imgCopy, imgHSV, imgFinger)
		doc = [0,0,rectWidth,rectHeight]
		fingerTrans = util.Transform(stuff.finger, stuff.transform)
	
		# tracking is a box index
		box = stuff.boxes[tracking]
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
	
		inside = util.PointInsideRect(fingerTrans, box)
		if inside:
			speech.Say('Located %s' % stuff.text[tracking])
			tracking = None
		elif counter % 6 == 0:
			speech.Say(direction)
	
# modified from http://www.davidhampgonsalves.com/2011/05/OpenCV-Python-Color-Based-Object-Tracking
def GetCursor(frame, imgHSV, imgFinger):
	if useThimble:
		cv.Copy(imgMasked, imgHSV)
		cv.Smooth(imgHSV, imgHSV, cv.CV_BLUR, 3); 
		
		#convert the image to hsv(Hue, Saturation, Value) so its  
		#easier to determine the color to track(hue) 
		#hsv_img = cv.CreateImage(cv.GetSize(img), 8, 3) 
		cv.CvtColor(imgHSV, imgHSV, cv.CV_BGR2HSV) 
		
		#limit all pixels that don't match our criteria, in this case we are  
		#looking for purple but if you want you can adjust the first value in  
		#both turples which is the hue range(120,140).	OpenCV uses 0-180 as  
		#a hue range for the HSV color model 
		#thresholded_img =  cv.CreateImage(cv.GetSize(hsv_img), 8, 1) 
		cv.Zero(imgFinger)
		cv.InRangeS(imgHSV, (greenLow, 40, 40), (greenHigh, 255, 255), imgFinger) 
		
		#determine the objects moments and check that the area is large	 
		#enough to be our object 
		#moments = cv.Moments(cv.GetMat(imgFinger,1), 0)
		#area = cv.GetCentralMoment(moments, 0, 0) 
		
		#there can be noise in the video so ignore objects with small areas 
		#if(area > 100000): 
			#determine the x and y coordinates of the center of the object 
			#we are tracking by dividing the 1, 0 and 0, 1 moments by the area 
			#x = cv.GetSpatialMoment(moments, 1, 0)/area 
			#y = cv.GetSpatialMoment(moments, 0, 1)/area 
			#return (x,y)
	else:
		cv.Copy(imgFG,imgFinger)

	# get contours
	contours = util.FindContours(imgFinger,minSize=(20,20))
	contours.sort(key=lambda c: -1*util.BoundingRectArea(c)) # contours[0] is the biggest
	
	if len(contours) > 0:
		bigContour = contours[0]
		top = min(bigContour, key=lambda p:p[1])
		return top
	
	else: return (-1,-1)
		
def DoOCR(oimg, orect, corners, boxes):
	ocr = ocr2.OCRManager(orect.width, orect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)
	ocr.ClearOCRTempFiles()
	filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(boxes))]

	pool = multiprocessing.Pool()
	
	for boxIndex in range(0, len(boxes)):
		box = boxes[boxIndex]
		fname = ocr.CreateTempFile(orect, box, boxIndex)
		pool.apply_async(CallOCREngine, (boxIndex, ocr2.DefaultWorkingDirectory, ocr2.DefaultRecognizer), callback=setText)
	pool.close()
	pool.join()

def CallOCREngine(fileID, workingDirectory=ocr2.DefaultWorkingDirectory, recognizer=ocr2.DefaultRecognizer):
	outputName = 'box' + str(fileID)
	print 'tesseract ocrtemp/box%s.png ocrtemp/box%s -l eng' % (fileID, fileID)
	stdout = subprocess.call('tesseract box%s.png box%s -l eng' % (fileID, fileID), cwd='ocrtemp') # 2> redirects stderr to a scratch file
	print 'OCR done. opening ocrtemp/box%s.txt' % fileID
	result = open('ocrtemp/box%s.txt' % fileID).read().strip()
	print 'result ', result
	return (result, fileID)		

# load textareas, ocr stuff, into the current calibration data
def LoadCheat(cheatFile):
	global stuff
	cheat = pickle.load(open(cheatFile, 'rb'))
	if stuff.corners is None or len(stuff.corners) < 4: 
		print 'no corners'
		stuff.corners = cheat.corners
		aspectRatio = GetAspectRatio(stuff.corners)
		rectified, stuff.transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)
		stuff.transformInv = numpy.linalg.inv(stuff.transform)
	stuff.boxes = cheat.boxes
	#stuff.overlays = cheat.overlays
	stuff.text = cheat.text
	#stuff.searchButton = cheat.searchButton
	CreateOverlays()
		
def DoCloudOCR(oimg, orect, corners, boxes):
	sessionID = int(time.time())
	# re-rectify to clear drawn lines
	
	cv.WaitKey(10)
	ocr = ocr2.OCRManager(orect.width, orect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)

	# clear out text
	stuff.text = {}

	filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(stuff.boxes))]

	for boxIndex in range(0, len(boxes)):
		box = boxes[boxIndex]
		print box
		fname  = ocr.CreateTempFile(orect, box, boxIndex)

	logging.debug( 'uploading images')
	cloudKeys = CloudUpload(sessionID, filenames)
	logging.debug('images uploaded')

	cloudKeys = cloudKeys.split(',')

	# run quickBoto
	logging.debug('Starting mturk')
	quikBoto.Run()
	logging.debug('Quitting mturk')
	
	while len(boxesToComplete.keys()) > 0:
		url = 'http://umbc-cloud.appspot.com/status2'
		req = urllib2.Request(url)
		results = json.loads(urllib2.urlopen(req).read())
		logging.debug('Recognized %d of %d' % (len(results), len(boxesToComplete.keys())))
		
		for r in results:
			setText((r['text'],r['index']))
	logging.debug('Finished OCR')
	
	#ResetCloudOCR()
	#print 'sending images to mturk'
	#for boxIndex in range(0, len(boxes)):
	#	pool.apply_async(CloudOCR,(boxIndex, cloudKeys[boxIndex]), callback=setText)
	#print 'done. %d items to recognize' % stuff.ocrItemsRemaining		
	#pool.close()
	#pool.join()
	
def DrawWindow(img, imgCopy, imgRect, imgHSV, imgFinger, stuff, windowTitle):
	# show image
	if stuff.mode == Mode.NORMAL:
		#cv.Copy(img, imgCopy)	
		util.DrawPoints(imgCopy, stuff.corners, color=(255,0,0))
			
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgCopy, b, color=(0,0,255), transform=stuff.transformInv)
			if stuff.text.has_key(i):
				t = stuff.text[i]
				p = util.Transform((b[X],b[Y]), stuff.transformInv)
				util.DrawText(imgCopy, t, p[X], p[Y], color=(0,0,255))
		
		for boxIndex in stuff.overlays.keys():
			rect = stuff.overlays[boxIndex]
			text = stuff.text[boxIndex]
			p = util.Transform((rect[X],rect[Y]), stuff.transformInv)
			util.DrawRect(imgCopy, rect, color=(0,100,255), transform=stuff.transformInv)
			util.DrawText(imgCopy, text, p[X], p[Y], color=(0,100,255))
		
		# draw searchbutton
		if (overlayMode == OverlayMode.SEARCH or overlayMode == OverlayMode.EDGE_PLUS_SEARCH) and stuff.searchButton[2] > 0:
			util.DrawRect(imgCopy, stuff.searchButton, color=(200,0,255), transform=stuff.transformInv)
			p = util.Transform((stuff.searchButton[X],stuff.searchButton[Y]), stuff.transformInv)
			util.DrawText(imgCopy, 'Search', p[X], p[Y], color=(200,0,255))
		
		if stuff.finger != (-1,-1):
			util.DrawPoint(imgCopy, stuff.finger, color=(0,0,255))
			#cv.ShowImage(windowTitle, imgFinger)
		#if bigImage is not None: cv.ShowImage(windowTitle, imgFG)
		#else: cv.ShowImage(windowTitle, imgCopy)
		cv.ShowImage(windowTitle, imgCopy)
	elif stuff.mode == Mode.RECTIFIED:
		aspectRatio = GetAspectRatio(stuff.corners)
		imgRect, transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)			
		
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgRect, b, color=(0,0,255))
			if len(stuff.text.keys()) > i and stuff.text[i] is not None:
				t = stuff.text[i]	
				if t != '': util.DrawText(imgRect, t, b[X], b[Y], color=(0,255,0))	
		cv.ShowImage(windowTitle, imgRect)


def CreateTransform(corners, imgCopy, aspectRatio):
	rectified, transform = util.GetRectifiedImage(imgCopy, corners, aspectRatio)
	transformInv = numpy.linalg.inv(transform)
	return rectified, transform, transformInv

import copy
	
def FindTextAreas(imgCopy, imgRect, corners, aspectRatio):
	speech.Say('Finding text areas')
	imgRect, transform = util.GetRectifiedImage(imgCopy, corners, aspectRatio)	
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = boxAspectThresh, dilateSteps = dilateSteps, windowSize = windowSize, boxMinSize = boxMinSize)
	#ocr.ClearOCRTempFiles()

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

def ResetCloudOCR():
	os.system('pkill -f getCloudOcr.py')
		
def CloudUpload(sessionID, filenames):
	cmd = 'python uploadCloudOcr.py %d %s > ocrtemp/cloudkeys.txt' % (sessionID, ' '.join(filenames))
	#print 'Executing command %s' % cmd
	os.system(cmd)
	#print 'Done'
	result = open('ocrtemp/cloudkeys.txt').read().strip()
	return result
	
def CloudOCR(boxIndex, cloudKey):
	os.system('python getCloudOcr.py %s 1> ocrtemp/box%d.txt 2> ocrtemp/box%derror.txt' % (cloudKey,boxIndex,boxIndex))
	result = open('ocrtemp/box%d.txt' % (boxIndex)).read().strip()
	return (result, boxIndex)

def setText(result):
	global stuff, boxesToComplete
	text, index = result
	if boxesToComplete.has_key(index): del boxesToComplete[index]
	if text is not None: 
		text = text.strip()
		logging.debug( 'recognized %s, %d left' % (text, len(boxesToComplete.keys())))
	
		if text is None or text == '*' or text == '': 
			# stuff.text[index] = None
			stuff.boxes[index] = [0,0,0,0]
		else:
			# print 'async recoed %s' % text
			stuff.text[index] = text
	
usingBigRez = False
def ToggleResolution():
	global usingBigRez, img, imgCopy, imgGray, imgEdge, imgHSV, imgFinger, camera, imgFG, imgMasked
	newWidth = 0
	newHeight = 0
	if usingBigRez:
		usingBigRez = False
		newWidth = smallRez[X]
		newHeight = smallRez[Y]
	else:
		usingBigRez = True
		newWidth = bigRez[X]
		newHeight = bigRez[Y]
	SetResolution((newWidth, newHeight))	

def SetResolution(rez):
	global usingBigRez, img, imgCopy, imgGray, imgEdge, imgHSV, imgFinger, camera, imgFG, imgMasked
	newWidth = rez[0]
	newHeight = rez[1]
	
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, newWidth)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, newHeight)
	
	frame = cv.QueryFrame(camera)
	while frame.width != newWidth:
		print frame.width
		frame = cv.QueryFrame(camera)
	
	size = (newWidth,newHeight) if rotate == 0 else (newHeight, newWidth)
	img = cv.CreateImage((newWidth,newHeight), vidDepth, 3)
	imgCopy = cv.CreateImage(size, vidDepth, 3)
	imgGray = cv.CreateImage(size, vidDepth, 1)
	imgEdge = cv.CreateImage(size, vidDepth, 1)
	imgHSV = cv.CreateImage(size, vidDepth, 3)
	imgMasked = cv.CreateImage(size, vidDepth, 3)
	imgFinger = cv.CreateImage(size, vidDepth, 1)
	imgFG = cv.CreateImage(size, vidDepth, 1)
	
		
def HandleKey(key):
	global imgRect, stuff
	char = -1
	try:
		char = chr(key)
	except Exception as e:
		'Some key junk'
	finally:
		if char == 'r': # toggle between rectified view
			if stuff.mode == 0 and len(stuff.corners) == 4: 
				aspectRatio = GetAspectRatio(stuff.corners)
				imgRect, stuff.transform, stuff.transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
				stuff.mode = 1
			else: stuff.mode = 0
		elif char == 'b':
			ToggleResolution()
		elif char == 't':
			global processInput
			processInput = not processInput
			print 'Processing input? %s' % processInput
		elif char == 'c':
			CaptureImages()
		elif char == 'o':
			StartOcr()
		elif char == 'p':
			ProcessImage()
		elif char == '1':
			LoadCheat('saved/maryland.pickle')
		elif char == '2':
			LoadCheat('saved/mall.pickle')
		elif char == '3':
			LoadCheat('saved/target.pickle')		
		elif char == '4':
			LoadCheat('saved/pyramid.pickle')	
		
		
camera = None

def GetAspectRatio(points, options=((8.5,11),(11,8.5),(5,5))):
	ratio = util.GetAspectRatio(points, options)
	logging.debug('Guessed aspect ratio! %f:%f' % ratio)
	return ratio

# args:rotate=(int)
# args: thimble=(true|false)
# args: cloud=true|false
def main():
	logger.debug('Started')
	global camera, stuff, rotate, useThimble, useCloudOcr, boto
	
	if len(sys.argv) == 2 and sys.argv[1] == '-h':
		print 'python study.py rotate=(rot) thimble=(true|false) cloud=(true|false) overlay =(edge|search|all|none)'
		sys.exit()
	
	for arg in sys.argv[1:]:
		pname, pval = arg.split('=')
		if pname == 'rotate': rotate = int(pval)
		elif pname == 'thimble': useThimble = pval.lower() == 'true'
		elif pname == 'cloud': useCloudOcr = pval.lower() == 'true'	
		elif pname == 'overlay':
			global overlayMode
			if pval.lower() == 'all': overlayMode=OverlayMode.EDGE_PLUS_SEARCH
			elif pval.lower() == 'search': overlayMode=OverlayMode.SEARCH
			elif pval.lower() == 'edge': overlayMode=OverlayMode.EDGE
	
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, smallRez[X])
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, smallRez[Y])
	
	SetResolution(smallRez)
	
	cv.NamedWindow(windowTitle, 1) 
	counter = 0

	while True:
		key = cv.WaitKey(10)
		if key == 27: break		
		if key != -1: HandleKey(key)
				
		img = cv.QueryFrame(camera)
		util.RotateImage(img, imgCopy, rotate)
		if bgModel is not None: bg2.FindBackground(imgCopy, imgFG, bgModel, update=0)
		cv.Zero(imgMasked)
		cv.Copy(imgCopy,imgMasked,imgFG) # now we have a masked image!

		HandleFrame(img, imgCopy, imgGray, imgEdge, imgRect, imgHSV, imgFinger, counter, stuff)
		DrawWindow(img, imgCopy, imgRect, imgHSV, imgFinger, stuff, windowTitle)
		counter += 1
		
		if counter % 300 == 0 and useCloudOcr:
			pass
			#if len(boxesToComplete.keys()) > 0: boto.StartTasks()
			#else: boto.EndTasks()

	# save for later
	timestamp = int(time.time()*1000)
	outputFile = 'logs/data-%d.pickle' % timestamp
	if saveToFile: pickle.dump(stuff, open(outputFile, 'wb'))
	print 'Saving file: %s' % outputFile
	logger.debug('Ended')

if __name__ == "__main__": main()