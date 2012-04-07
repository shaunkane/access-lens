import cv, numpy, sys, pickle, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
from util import X,Y,WIDTH,HEIGHT
import os
import multiprocessing, subprocess
import time
import studyHelper
from studyHelper import *

windowTitle = 'ocrTestWindow'
pickleFile = 'temp.pickle'
saveToFile = False
smallRez = (640,480)
bigRez = (1280,960)
vidDepth = 8
rotate = -90
processInput = False # we can turn off handleframe

stuff = studyHelper.Stuff()

img = cv.CreateImage(smallRez, vidDepth, 3)
imgCopy = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 3)
imgGray = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgEdge = cv.CreateImage((smallRez[1],smallRez[0]), vidDepth, 1)
imgRect = None

usingBigRez = False
def ToggleResolution():
		global usingBigRez, imgCopy, imgGray, imgEdge, camera
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
		
		camera = cv.CaptureFromCAM(0)
		cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, newWidth)
		cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, newHeight)
		
		imgCopy = cv.CreateImage((newHeight, newWidth), vidDepth, 3)
		imgGray = cv.CreateImage((newHeight, newWidth), vidDepth, 1)
		imgEdge = cv.CreateImage((newHeight, newWidth), vidDepth, 1)

def HandleKey(key):
	char = chr(key)
	if char == 'r': # toggle between rectified view
		if stuff.mode == 0 and len(stuff.corners) == 4: 
			CreateTransform(stuff, imgCopy, imgRect, aspectRatio)
			stuff.mode = 1
		else: stuff.mode = 0
	elif char == 'b':
		ToggleResolution()
	elif char == 'p':
		global processInput
		processInput = not processInput
		print 'Processing input? %s' % processInput
		
camera = None
		
def main():
	global camera, stuff
	if os.path.exists(pickleFile): stuff = pickle.load(open(pickleFile, 'rb'))
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
		if processInput: HandleFrame(img, imgCopy, imgGray, imgEdge, imgRect, counter, stuff, aspectRatio)
		DrawWindow(img, imgCopy, imgRect, stuff, windowTitle)
		counter += 1

	# save for later
	stuff.text = []
	if saveToFile: pickle.dump(stuff, open(pickleFile, 'wb'))	

if __name__ == "__main__": main()