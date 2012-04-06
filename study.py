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
pickleFile = 'temp.json'
saveToFile = True
vidWidth = 960
vidHeight = 720
vidDepth = 8
rotate = -90
processInput = True # we can turn off handleframe

stuff = studyHelper.Stuff()

img = cv.CreateImage((vidHeight, vidWidth), vidDepth, 3)
imgCopy = cv.CreateImage((vidHeight, vidWidth), vidDepth, 3)
imgGray = cv.CreateImage((vidHeight, vidWidth), vidDepth, 1)
imgEdge = cv.CreateImage((vidHeight, vidWidth), vidDepth, 1)
imgHSV = cv.CreateImage((vidHeight, vidWidth), vidDepth, 1)
imgRect = None

def HandleKey(key):
	char = chr(key)
	if char == 'r': # toggle between rectified view
		if stuff.mode == 0 and len(stuff.corners) == 4: 
			CreateTransform(stuff, imgCopy, imgRect, aspectRatio)
			stuff.mode = 1
		else: stuff.mode = 0
		
def main():
	global stuff
	if os.path.exists(pickleFile): stuff = pickle.load(open(pickleFile, 'rb'))
	camera = cv.CaptureFromCAM(0)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, vidWidth)
	cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, vidHeight)
	
	cv.NamedWindow(windowTitle, 1) 
	
	# let camera warm up
	img = cv.QueryFrame(camera)
	while img.width != vidWidth or img.height != vidHeight:
		img = cv.QueryFrame(camera)
		cv.ShowImage(windowTitle, img)
		cv.WaitKey(10)
	

	counter = 0
	
	while True:
		key = cv.WaitKey(10)
		if key == 27: break		
		if key != -1: HandleKey(key)
				
		img = cv.QueryFrame(camera)
		util.RotateImage(img, imgCopy, rotate)
		if processInput: HandleFrame(img, imgCopy, imgGray, imgEdge, imgHSV, imgRect, counter, stuff, aspectRatio)
		DrawWindow(img, imgCopy, imgRect, stuff, windowTitle)
		counter += 1

	# save for later
	stuff.text = []
	if saveToFile: pickle.dump(stuff, open(pickleFile, 'wb'))	

if __name__ == "__main__": main()