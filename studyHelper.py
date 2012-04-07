import cv
import util 
import ocr2
import speechManager
import numpy
import multiprocessing, subprocess
from util import X,Y
from settings import *

speech = speechManager.SpeechManager()
useCloudOcr = False
aspectRatio = (8.5,11)

useFakeOcr = False
FakeOcrFile = 'seattle.txt'
useThimble = True

# ocr stuff
boxAspectThresh = 1.5
dilateSteps = 3
windowSize = 4
boxMinSize = 25

class Stuff(object):
	def __init__(self):
		self.mode = 0
		self.corners = []
		self.boxes = []
		self.text = []
		self.transform = None
		self.transformInv = None
		self.ocrItemsRemaining = 0

class OverlayMode:
	NONE = 0
	EDGE = 1
	SEARCH = 2
	EDGE_PLUS_SEARCH = 3

threshold = 30*1
accumulator = 0
tracking = None
touched = None
overlayMode = OverlayMode.NONE
drewOverlays = False
handInView = False

def HandleFrame(img, imgCopy, imgGray, imgEdge, imgHSV, imgRect, counter, stuff, aspectRatio):
	global drewOverlays
	global accumulator
	# first thing's first. try to find a rectangle
	if len(stuff.corners) < 4:
		accumulator += 1
		if accumulator == threshold:
			accumulator = 0
			util.GetGrayscale(imgCopy, imgGray)
			util.GetEdge(frame=imgGray, edge=imgEdge)
			rect = util.FindLargestRectangle(imgEdge, imgGray)
			if len(rect) == 4 and util.BoundingRectArea(rect) > 200:			
				stuff.corners = rect
				speech.Say("Document detected")
				CreateTransform(stuff, imgCopy, imgRect, aspectRatio)
	elif len(stuff.corners) == 4 and len(stuff.boxes) == 0:
		accumulator += 1
		if accumulator == threshold:
			accumulator = 0
			stuff.boxes = FindTextAreas(imgCopy, imgRect, stuff.corners, aspectRatio)
			
	elif len(stuff.boxes) > 0 and len(stuff.text) == 0: # do ocr here
		accumulator += 1
		if accumulator == threshold:
			# accumulator = 0
			if useFakeOcr:
				speech.Say('Starting OCR')
				fakeWords = open(FakeOcrFile,'r').readlines()
				for i in range(0, min(len(fakeWords), len(stuff.boxes))):
					stuff.text.append(fakeWords[i])
				numWords = min(len(fakeWords), len(stuff.boxes))
				speech.Say('OCR detected %d items' % numWords)
			else:
				if useCloudOcr:
					pass
				else:
					DoOCR(imgCopy, imgRect, stuff)

	elif len(stuff.text) > 0 and len(stuff.text) == len(stuff.boxes) and not drewOverlays:
		# draw our overlays here
		global drewOverlays
		drewOverlays = True
		
		if overlayMode == OverlayMode.NONE: pass
		elif overlayMode == OverlayMode.EDGE: pass
		elif overlayMode == OverlayMode.SEARCH: pass
		elif overlayMode == OverlayMode.EDGE_PLUS_SEARCH: pass
	
	elif len(stuff.text) > 0 and tracking is None:  # finger tracking, tracing 
		global touched
		if useThimble == False: return
		# use thimble
		finger = GetGreenCursor(imgCopy)
		global handInView
		if not handInView and finger != (-1,-1): #hello hand!
			speech.Say('hand detected')
			handInView = True
		elif handInView and finger == (-1,-1):
			speech.Say('hand removed')
			handInView = False
		touchedAreas = [area for area in stuff.boxes if util.PointInsideRect(util.Transform(finger, stuff.transform), area)]
		if len(touchedAreas) > 0:
			oldTouched = touched
			touched = stuff.boxes.index(touchedAreas[0])
			if (oldTouched is None or oldTouched != touched) and len(stuff.text) > touched and stuff.text[touched] is not None and len(stuff.text[touched]) > 5: speech.Say(stuff.text[touched]) # say it 
		else: touched = None
		
		
# modified from http://www.davidhampgonsalves.com/2011/05/OpenCV-Python-Color-Based-Object-Tracking
def GetGreenCursor(frame):
	img = cv.CloneImage(frame)
	cv.Smooth(img, img, cv.CV_BLUR, 3); 
	
	#convert the image to hsv(Hue, Saturation, Value) so its  
	#easier to determine the color to track(hue) 
	hsv_img = cv.CreateImage(cv.GetSize(img), 8, 3) 
	cv.CvtColor(img, hsv_img, cv.CV_BGR2HSV) 
	
	#limit all pixels that don't match our criteria, in this case we are  
	#looking for purple but if you want you can adjust the first value in  
	#both turples which is the hue range(120,140).	OpenCV uses 0-180 as  
	#a hue range for the HSV color model 
	thresholded_img =  cv.CreateImage(cv.GetSize(hsv_img), 8, 1) 
	cv.InRangeS(hsv_img, (greenLow, 40, 40), (greenHigh, 255, 255), thresholded_img) 
	
	#determine the objects moments and check that the area is large	 
	#enough to be our object 
	moments = cv.Moments(cv.GetMat(thresholded_img,1), 0)
	area = cv.GetCentralMoment(moments, 0, 0) 
	
	#there can be noise in the video so ignore objects with small areas 
	if(area > 100000): 
		#determine the x and y coordinates of the center of the object 
		#we are tracking by dividing the 1, 0 and 0, 1 moments by the area 
		x = cv.GetSpatialMoment(moments, 1, 0)/area 
		y = cv.GetSpatialMoment(moments, 0, 1)/area 
		return (x,y)
	else: return (-1,-1)
		
		
def DoOCR(imgCopy, imgRect, stuff):
	imgRect, transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)
	filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(stuff.boxes))]

	pool = multiprocessing.Pool()
	
	for boxIndex in range(0, len(stuff.boxes)):
		box = stuff.boxes[boxIndex]
		fname = ocr.CreateTempFile(imgRect, box, boxIndex)
		stuff.ocrItemsRemaining = len(stuff.boxes)
		pool.apply_async(CallOCREngine, (boxIndex, ocr2.DefaultWorkingDirectory, ocr2.DefaultRecognizer), callback=setText)

def CallOCREngine(fileID, workingDirectory=ocr2.DefaultWorkingDirectory, recognizer=ocr2.DefaultRecognizer):
	outputName = 'box' + str(fileID)
	print 'tesseract ocrtemp/box%s.png ocrtemp/box%s -l eng' % (fileID, fileID)
	stdout = subprocess.call('tesseract box%s.png box%s -l eng' % (fileID, fileID), cwd='ocrtemp') # 2> redirects stderr to a scratch file
	result = open('ocrtemp/box%s.txt' % fileID).readlines().strip()
	print 'result ', result
	return (result, boxIndex)		
		
def DoClOCR():
	sessionID = int(time.time())
	# re-rectify to clear drawn lines
	cv.Copy(img, imgCopy)
	imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio)
	if stuff.mode == 0: cv.ShowImage(windowTitle, imgCopy)
	elif stuff.mode == 1: cv.ShowImage(windowTitle, imgRect)
	
	cv.WaitKey(10)
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = 1, dilateSteps = 3, windowSize = 4, boxMinSize = 30)

	# clear out text
	stuff.text = [''] * len(stuff.boxes)

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
	#pool.close()
	#pool.join()
	
def DrawWindow(img, imgCopy, imgRect, stuff, windowTitle):
	# show image
	if stuff.mode == 0:
		#cv.Copy(img, imgCopy)	
		util.DrawPoints(imgCopy, stuff.corners, color=(255,0,0))
			
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgCopy, b, color=(0,0,255), transform=stuff.transformInv)
			if len(stuff.text) > i and stuff.text[i] is not None:
				t = stuff.text[i]
				p = util.Transform((b[X],b[Y]), stuff.transformInv)
				util.DrawText(imgCopy, t, p[X], p[Y], color=(0,0,255))
	
		cv.ShowImage(windowTitle, imgCopy)
	elif stuff.mode == 1:
		imgRect, transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)			
		
		for i in range(0,len(stuff.boxes)):
			b = stuff.boxes[i]
			util.DrawRect(imgRect, b, color=(0,0,255))
			if len(stuff.text) > i and stuff.text[i] is not None:
				t = stuff.text[i]	
				if t != '': util.DrawText(imgRect, t, b[X], b[Y], color=(0,255,0))	
		cv.ShowImage(windowTitle, imgRect)


def CreateTransform(stuff, imgCopy, imgRect, aspectRatio):
	imgRect, stuff.transform = util.GetRectifiedImage(imgCopy, stuff.corners, aspectRatio)
	stuff.transformInv = numpy.linalg.inv(stuff.transform)



def FindTextAreas(imgCopy, imgRect, corners, aspectRatio):
	speech.Say('Finding text areas')
	imgRect, transform = util.GetRectifiedImage(imgCopy, corners, aspectRatio)	
	ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = boxAspectThresh, dilateSteps = dilateSteps, windowSize = windowSize, boxMinSize = boxMinSize)
	#ocr.ClearOCRTempFiles()

	boxes = ocr.FindTextAreas(imgRect, verbose=True)
	for b in boxes:
		print b
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
	global stuff
	text, index = result
	if text is not None: 
		print 'recognized %s (%d/%d)' % (text, len(stuff.text)-stuff.ocrItemsRemaining+1, len(stuff.text))

		if text == '*': stuff.text[index] = None
		else:
			# print 'async recoed %s' % text
			stuff.text[index] = text
		stuff.ocrItemsRemaining -= 1
		if stuff.ocrItemsRemaining == 0:
			print 'BOOM! Recognized all text'