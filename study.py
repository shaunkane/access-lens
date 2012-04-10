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

windowTitle = 'ocrTestWindow'
pickleFile = 'temp.pickle'
saveToFile = False
smallRez = (640,480)
bigRez = (1280,960)
reallyBigRez = (2592,1944)
vidDepth = 8
rotate = -90
processInput = False # we can turn off handleframe

img = cv.CreateImage(smallRez, vidDepth, 3)
imgCopy = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgGray = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgB = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgG = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgR = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgEdge = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgHSV = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgFinger = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgRect = None

threshold = 30*1
tracking = None
touched = None
overlayMode = OverlayMode.NONE
drewOverlays = False
handInView = False

speech = speechManager.SpeechManager()
useCloudOcr = False
aspectRatio = (11,8.5)

useFakeOcr = False
FakeOcrFile = 'seattle.txt'
useThimble = True

# ocr stuff
boxAspectThresh = 1.5
dilateSteps = 3
windowSize = 4
boxMinSize = 50

bigImage = None
mediumImage = None
smallImage = None
newImageToProcess = False

stuff = Stuff()

# capture big, medium, small images
def CaptureImages():
	global bigImage, mediumImage, smallImage, newImageToProcess
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
	
	newImageToProcess = True

# get text areas and start OCR
def ProcessImage():
	global bigImage, mediumImage, smallImage
	if bigImage is None: CaptureImages()
	# find rectangle
	
	# do everything with the medium document, then scale down
	scaleFactor = float(smallImage.width) / mediumImage.width
	
	gray = util.GetGrayscale(mediumImage)
	edge = util.GetEdge(frame=gray)
	bigCorners = util.FindLargestRectangle(edge, gray)
	
	speech.Say('Locating document')
	#util.GetGrayscale(imgCopy, imgGray)
	#util.GetEdge(frame=imgGray, edge=imgEdge)
	#rect = util.FindLargestRectangle(imgEdge, imgGray)
	if len(bigCorners) == 4 and util.BoundingRectArea(bigCorners) > 400:
		# squish corners down
	
		stuff.corners = []
		for p in bigCorners: stuff.corners.append([p[0]*scaleFactor,p[1]*scaleFactor])
		
		speech.Say("Document detected. Starting OCR")
		mediumRect, bigTrans, bigInv = CreateTransform(bigCorners, mediumImage, aspectRatio)
		# now do it with the small one
		imgRect, stuff.transform, stuff.transformInv = CreateTransform(stuff.corners, imgCopy, aspectRatio)
		
		#speech.Say('Locating text')
		bigBoxes = FindTextAreas(mediumImage, mediumRect, bigCorners, aspectRatio)
		stuff.boxes = []
		try:
			for p in bigBoxes:
				stuff.boxes.append([p[0]*scaleFactor,p[1]*scaleFactor,p[2]*scaleFactor,p[3]*scaleFactor])
		except Exception as e:
			logger.debug('It broke! %s' % e)	
		finally:
			speech.Say('Located %d potential text items' % len(stuff.boxes)) 
		
		#speech.Say('Starting OCR')
			DoOCR(mediumImage, mediumRect, bigCorners, bigBoxes)
			
			#while len(stuff.text.keys()) != len(stuff.boxes):
			#	speech.Say('Waiting for %d OCR items' % (len(stuff.boxes) - len(stuff.text.keys())))
			#	time.sleep(5)
			#speech.Say('OCR complete')
			
			# add overlays
			print len(stuff.text.keys())
			global processInput
			processInput = True

accumulator = 0	
documentOnTable = False
def HandleFrame(img, imgCopy, imgGray, imgEdge, imgRect, imgHSV, imgFinger, counter, stuff, aspectRatio):
	global drewOverlays
	global accumulator
	global bigImage, mediumImage, smallImage 
	global documentOnTable
	
	if not documentOnTable:
		util.GetGrayscale(imgCopy, imgGray)
		util.GetEdge(frame=imgGray, edge=imgEdge)
		rect = util.FindLargestRectangle(imgEdge, imgGray)
		if len(rect) == 4 and util.BoundingRectArea(rect) > 25000:
			accumulator += 1
			if accumulator == 60:
				accumulator = 0
				speech.Say('Document detected')
				documentOnTable = True
				stuff.corners = rect
		else:
			accumulator = 0
	elif documentOnTable:
		util.GetGrayscale(imgCopy, imgGray)
		util.GetEdge(frame=imgGray, edge=imgEdge)
		rect = util.FindLargestRectangle(imgEdge, imgGray)
		if len(rect) != 4 or util.BoundingRectArea(rect) < 25000:
			accumulator += 4
			if accumulator == 60:
				speech.Say('Document removed')
				documentOnTable = False
				stuff.corners = []
				accumulator = 0
		#else:
		#	accumulator -= 2		
	
	if processInput and len(stuff.text.keys()) > 0 and  len(stuff.text.keys()) == len(stuff.boxes) and not drewOverlays:
		# draw our overlays here
		drewOverlays = True
		
		if overlayMode == OverlayMode.NONE: pass
		elif overlayMode == OverlayMode.EDGE: pass
		elif overlayMode == OverlayMode.SEARCH: pass
		elif overlayMode == OverlayMode.EDGE_PLUS_SEARCH: pass
	
	elif len(stuff.text.keys()) > 0 and tracking is None:  # finger tracking, tracing 
		global touched
		if useThimble == False: return
		# use thimble
		stuff.finger = GetGreenCursor(imgCopy, imgHSV, imgFinger)
		global handInView
		if not handInView and stuff.finger != (-1,-1): #hello hand!
			speech.Say('hand detected')
			handInView = True
		elif handInView and stuff.finger == (-1,-1):
			speech.Say('hand removed')
			handInView = False
		touchedAreas = [area for area in stuff.boxes if util.PointInsideRect(util.Transform(stuff.finger, stuff.transform), area)]
		if len(touchedAreas) > 0:
			oldTouched = touched
			touched = stuff.boxes.index(touchedAreas[0])
			if (oldTouched is None or oldTouched != touched) and len(stuff.text.keys()) > touched and stuff.text[touched] is not None and len(stuff.text[touched]) > 5: speech.Say(stuff.text[touched]) # say it 
		else: touched = None
	
	
# modified from http://www.davidhampgonsalves.com/2011/05/OpenCV-Python-Color-Based-Object-Tracking
def GetGreenCursor(frame, imgHSV, imgFinger):
	cv.Copy(frame, imgHSV)
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
	moments = cv.Moments(cv.GetMat(imgFinger,1), 0)
	area = cv.GetCentralMoment(moments, 0, 0) 
	
	#there can be noise in the video so ignore objects with small areas 
	if(area > 100000): 
		#determine the x and y coordinates of the center of the object 
		#we are tracking by dividing the 1, 0 and 0, 1 moments by the area 
		x = cv.GetSpatialMoment(moments, 1, 0)/area 
		y = cv.GetSpatialMoment(moments, 0, 1)/area 
		return (x,y)
	else: return (-1,-1)
		
def DoOCR(imgCopy, imgRect, corners, boxes):
	imgRect, transform = util.GetRectifiedImage(imgCopy, corners, aspectRatio)
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)
	ocr.ClearOCRTempFiles()
	filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(boxes))]

	pool = multiprocessing.Pool()
	
	for boxIndex in range(0, len(boxes)):
		box = boxes[boxIndex]
		fname = ocr.CreateTempFile(imgRect, box, boxIndex)
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
		
def DoCloudOCR():
	sessionID = int(time.time())
	# re-rectify to clear drawn lines
	cv.Copy(img, imgCopy)
	imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio)
	if stuff.mode == 0: cv.ShowImage(windowTitle, imgCopy)
	elif stuff.mode == 1: cv.ShowImage(windowTitle, imgRect)
	
	cv.WaitKey(10)
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)

	# clear out text
	stuff.text = {}

	filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(stuff.boxes))]

	for boxIndex in range(0, len(stuff.boxes)):
		print imgRect
		box = stuff.boxes[boxIndex]
		print box
		fname = ocr.CreateTempFile(imgRect, box, boxIndex)

		#pool.apply_async(CallOCREngine, (id, ocr2.DefaultWorkingDirectory, ocr2.DefaultRecognizer, i), callback=setText)
		
		#text = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
		#text = ''
		# text = self.dict.CorrectPhrase(text, verbose=True)
		#if text is not None: 
		#	print 'Recognized %s' % text
		#	setText(i, text)
	
	print 'uploading images'
	cloudKeys = CloudUpload(sessionID, filenames)
	print 'images uploaded'

	stuff.ocrItemsRemaining = len(stuff.boxes)
	
	cloudKeys = cloudKeys.split(',')
	# setting up pool
	pool = multiprocessing.Pool(50)
	
	ResetCloudOCR()
	print 'sending images to mturk'
	for boxIndex in range(0, len(stuff.boxes)):
		pool.apply_async(CloudOCR,(boxIndex, cloudKeys[boxIndex]), callback=setText)
	print 'done. %d items to recognize' % stuff.ocrItemsRemaining		
	pool.close()
	#pool.join()
	
def DrawWindow(img, imgCopy, imgRect, imgHSV, imgFinger, stuff, windowTitle):
	# show image
	if stuff.mode == Mode.NORMAL:
		#cv.Copy(img, imgCopy)	
		util.DrawPoints(imgCopy, stuff.corners, color=(255,0,0))
			
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgCopy, b, color=(0,0,255), transform=stuff.transformInv)
			if len(stuff.text.keys()) > i and stuff.text.has_key(i):
				t = stuff.text[i]
				p = util.Transform((b[X],b[Y]), stuff.transformInv)
				util.DrawText(imgCopy, t, p[X], p[Y], color=(0,0,255))
	
		if stuff.finger is not None and stuff.finger != (-1,-1):
			util.DrawPoint(imgCopy, stuff.finger, color=(0,0,255))
			#cv.ShowImage(windowTitle, imgFinger)
		cv.ShowImage(windowTitle, imgCopy)
	elif stuff.mode == Mode.RECTIFIED:
		imgRect, transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)			
		
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgRect, b, color=(0,0,255))
			if len(stuff.text.keys()) > i and stuff.text[i] is not None:
				t = stuff.text[i]	
				if t != '': util.DrawText(imgRect, t, b[X], b[Y], color=(0,255,0))	
		cv.ShowImage(windowTitle, imgRect)


def CreateTransform(corners, imgCopy, aspectRatio, guessAspectRatio = False):
	ratio = util.GuessAspectRatio(util.GetSize(corners)) if guessAspectRatio else aspectRatio
	rectified, transform = util.GetRectifiedImage(imgCopy, corners, ratio)
	transformInv = numpy.linalg.inv(transform)
	return rectified, transform, transformInv

import copy
	
def FindTextAreas(imgCopy, imgRect, corners, aspectRatio, guessAspectRatio = False):
	ratio = util.GuessAspectRatio(util.GetSize(stuff.corners)) if guessAspectRatio else aspectRatio
	speech.Say('Finding text areas')
	imgRect, transform = util.GetRectifiedImage(imgCopy, corners, ratio)	
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
	print 'WOOOO'
	global stuff
	text, index = result
	if text is not None:
		text = text.strip()
		print 'recognized %s (%d/%d)' % (text, len(stuff.boxes)-len(stuff.text.keys()), len(stuff.text.keys()))

		if text == '*' or text == '': 
			#stuff.text[index] = None
			stuff.boxes[index] = [0,0,0,0]
		else:
			# print 'async recoed %s' % text
			stuff.text[index] = text
		#stuff.ocrItemsRemaining -= 1
		#if stuff.ocrItemsRemaining == 0:
		#	print 'BOOM! Recognized all text'	
	
usingBigRez = False
def ToggleResolution():
	global usingBigRez, imgCopy, imgGray, imgEdge, imgHSV, imgFinger, camera
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
	global camera
	newWidth = rez[0]
	newHeight = rez[1]
	
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, newWidth)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, newHeight)
	
	frame = cv.QueryFrame(camera)
	while frame.width != newWidth:
		print frame.width
		frame = cv.QueryFrame(camera)
	
	imgCopy = cv.CreateImage((newHeight, newWidth), vidDepth, 3)
	imgGray = cv.CreateImage((newHeight, newWidth), vidDepth, 1)
	imgEdge = cv.CreateImage((newHeight, newWidth), vidDepth, 1)
	imgHSV = cv.CreateImage((newHeight, newWidth), vidDepth, 3)
	imgFinger = cv.CreateImage((newHeight, newWidth), vidDepth, 1)
		
def HandleKey(key):
	global imgRect, stuff
	char = chr(key)
	if char == 'r': # toggle between rectified view
		if stuff.mode == 0 and len(stuff.corners) == 4: 
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
	elif char == 'p':
		ProcessImage()
		
camera = None
		
def main():
	logger.debug('Started')
	global camera, stuff, FakeOcrFile, useFakeOcr
	if len(sys.argv) > 1:
		useFakeOcr = True
		cheatFile = sys.argv[1]
		if os.path.exists(cheatFile): stuff = pickle.load(open(cheatFile, 'rb'))
	
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, smallRez[X])
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, smallRez[Y])
	
	cv.NamedWindow(windowTitle, 1) 
	counter = 0
	
	while True:
		key = cv.WaitKey(10)
		if key == 27: break		
		if key != -1: HandleKey(key)
				
		img = cv.QueryFrame(camera)
		util.RotateImage(img, imgCopy, rotate)
		HandleFrame(img, imgCopy, imgGray, imgEdge, imgRect, imgHSV, imgFinger, counter, stuff, aspectRatio)
		DrawWindow(img, imgCopy, imgRect, imgHSV, imgFinger, stuff, windowTitle)
		counter += 1

	# save for later
	timestamp = int(time.time()*1000)
	outputFile = 'logs/%d-data.pickle' % timestamp
	if saveToFile: pickle.dump(stuff, open(outputFile, 'wb'))
	print 'Saving file: %s' % outputFile
	logger.debug('Ended')

if __name__ == "__main__": main()