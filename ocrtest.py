import cv, numpy, sys, pickle, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
from util import X,Y,WIDTH,HEIGHT
import pickle, os

class Stuff(object):
	def __init__(self):
		self.mode = 0
		self.corners = []
		self.boxes = []
		self.text = []
		self.transform = None
		self.transformInv = None

def DoOCR(rectified, dict):
	try:
		ocr = ocr2.OCRManager(rectified.width, rectified.height, boxAspectThresh = 0, dilateSteps = 5)
		ocr.ClearOCRTempFiles()
		boxes = ocr.FindTextAreas(rectified, verbose=True)
		for box in boxes:
			file, id = ocr.CreateTempFile(rectified, box)
			uncorrected = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
			corrected = dict.CorrectPhrase(uncorrected)
			box2 = [(box.x,box.y),(box.x+box.width,box.y),(box.x+box.width,box.y+box.height),(box.x,box.y+box.height)]
			util.DrawPolyLine(rectified, box2)
			cv.SaveImage('output/textboxes.png',rectified)
			print '----'
			print 'uncorrected: %s' % uncorrected
			print 'corrected: %s' % corrected
			
	except Exception, err:
		print 'Could not rectify image: %s' % err

stuff = Stuff()
	
def onMouse(event, x, y, flags, param):
	global stuff
	if stuff.mode == 0 and event == cv.CV_EVENT_LBUTTONDOWN:
		if len(stuff.corners) > 3: stuff.corners = []
		stuff.corners.append((x,y))
		print 'Added corner (%d,%d)' % (x,y)
	
def main():
	global stuff
	if os.path.exists('stuff.pickle'): stuff = pickle.load(open('stuff.pickle', 'rb'))
	
	windowTitle = 'ocrTestWindow'
	img = cv.LoadImage(sys.argv[1])
	imgCopy = cv.CreateImage((img.width, img.height), img.depth, img.nChannels)
	imgGray = cv.CreateImage((img.width, img.height), img.depth, 1)
	imgRect = None

	cv.CvtColor(img, imgGray, cv.CV_BGR2GRAY)
	d = dict.DictionaryManager(dictFile, userDictFile, verbose=True)
	# DoOCR(image, d)

	
	cv.NamedWindow(windowTitle, 1) 
	cv.SetMouseCallback(windowTitle, onMouse, None)

	
	while True:
		key = cv.WaitKey(10)
		if key == 27: break
		
		# handle keys
		if key != -1:
			char = chr(key)
			if char == 'r': # find text areas
				if stuff.mode == 0 and len(stuff.corners) == 4:
					stuff.mode = 1
					imgRect, stuff.transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))
					stuff.transformInv = numpy.linalg.inv(stuff.transform)
				else:
					stuff.mode = 0
			elif char == 'a': # find text areas
				ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = BoxAspectThresh, dilateSteps = 3, windowSize = 4, boxMinSize = 15)
				ocr.ClearOCRTempFiles()
		
				# find text areas
				stuff.boxes = ocr.FindTextAreas(imgRect, verbose=True)

				
		# show image
		if stuff.mode == 0:
			cv.Copy(img, imgCopy)	
			#betterCorners = cv.FindCornerSubPix(imgGray, corners, (20,20), (-1,-1), (cv.CV_TERMCRIT_ITER,10,0))
			util.DrawPoints(imgCopy, stuff.corners, color=(255,0,0))
			
			for b in stuff.boxes:
				util.DrawRect(imgRect, b, color=(0,255,0), transform=stuff.transformInv)
			
			cv.ShowImage(windowTitle, imgCopy)
		elif stuff.mode == 1:
			if imgRect is None: imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))			
			boxes = stuff.boxes[:]
			for b in boxes[:]:
				util.DrawRect(imgRect, b, color=(0,255,0))
			cv.ShowImage(windowTitle, imgRect)


	# save for later
	pickle.dump(stuff, open('stuff.pickle', 'wb'))	
	
if __name__ == "__main__": main()