import cv, numpy, sys, pickle, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
from util import X,Y,WIDTH,HEIGHT
import pickle, os
import multiprocessing, subprocess
import time
from studyHelper import *

windowTitle = 'ocrTestWindow'
useCloudOcr = True
pickleFile = 'stuff.pickle'
saveToFile = False
useGreenTracking = True
aspectRatio = (11,8.5)
vidWidth = 1024
vidHeight = 768
vidDepth = 8

stuff = Stuff()

img = cv.CreateImage((vidWidth, vidHeight), vidDepth, 3)
imgCopy = cv.CreateImage((vidWidth, vidHeight), vidDepth, 3)
imgGray = cv.CreateImage((vidWidth, vidHeight), vidDepth, 1)
imgEdge = cv.CreateImage((vidWidth, vidHeight), vidDepth, 1)
imgHSV = cv.CreateImage((vidWidth, vidHeight), vidDepth, 1)
imgRect = None

def HandleKey(key):
	char = chr(key)
	if char == 'r': # toggle between rectified view
		if stuff.mode == 0 and len(stuff.corners) == 4: 
			CreateTransform(stuff, img, imgRect, aspectRatio)
			stuff.mode = 1
		else: stuff.mode = 0
		
def main():
	global stuff
	if os.path.exists(pickleFile): stuff = pickle.load(open(pickleFile, 'rb'))
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, vidWidth)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, vidHeight)

	cv.NamedWindow(windowTitle, 1) 
	counter = 0
	
	while True:
		key = cv.WaitKey(10)
		if key == 27: break		
		if key != -1: HandleKey(key)
				
		img = cv.QueryFrame(self.capture)
		
		HandleFrame(img, imgCopy, imgGray, imgEdge, imgHSV, imgRect, counter, stuff)
		DrawWindow(img, imgCopy, imgRect)
		counter += 1

	# save for later
	if saveToFile: pickle.dump(stuff, open(pickleFile, 'wb'))	

if __name__ == "__main__": main()