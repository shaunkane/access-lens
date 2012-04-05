import cv, numpy, sys, json, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
from util import Point, Size
import cPickle as pickle, os

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

corners = []
mode = 0
	
def onMouse(event, x, y, flags, param):
	global corners
	if mode == 0 and event == cv.CV_EVENT_LBUTTONDOWN:
		if len(corners) > 3: corners = []
		corners.append(Point(x,y))
		print 'Added corner (%d,%d)' % (x,y)
	
def main():
	global mode, corners
	if os.path.exists('area.pickle'): corners = pickle.load(open('area.pickle', 'rb'))
	
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
			if char == 'r':
				if mode == 0 and len(corners) == 4:
					mode = 1
					imgRect, transform = util.GetRectifiedImage(img, corners, aspectRatio=Size(11,8.5))
				else:
					mode = 0
		
		# show image
		if mode == 0:
			cv.Copy(img, imgCopy)	
			betterCorners = cv.FindCornerSubPix(imgGray, corners, (20,20), (-1,-1), (cv.CV_TERMCRIT_ITER,10,0))
			betterCorners = [Point._make(p) for p in betterCorners]
			util.DrawPoints(imgCopy, corners, color=(255,0,0))
			# util.DrawPoints(imgCopy, betterCorners, color=(255,0,255))
			cv.ShowImage(windowTitle, imgCopy)
		elif mode == 1:
			cv.ShowImage(windowTitle, imgRect)

	output = open('area.pickle', 'wb')
	pickle.dump(corners, output)	
	
if __name__ == "__main__": main()