# just run the camera, so we can look at it
# 1 parameter. if it's 1, use the large size. otherwise small
# if it's b, show the bg

import cv, util, sys, bg2

windowTitle = 'camtest'
camSmall = (640,480)
camLarge = (2592,1944)
vidDepth = 8
rotate = 0

# bg params
yThreshold = 20
fitThreshold = 16
yccMode = 0
findShadow = 1
trainImages = 10

camSize = camLarge if len(sys.argv) > 1 and sys.argv[1] == '1' else camSmall
print camSize

# create the images we need
imSize = reversed(camSize) if rotate == -90 or rotate == 90 else camSize
imgCopy = cv.CreateImage(imSize, vidDepth, 3) # a rotated copy
imgFG = cv.CreateImage(imSize, vidDepth, 1)

# set up cam
camera = cv.CaptureFromCAM(0)
cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, camSize[0])
cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, camSize[1])
img = cv.QueryFrame(camera)
util.RotateImage(img, imgCopy, rotate)

# bg
bgModel = bg2.BackgroundModel(imSize[0], imSize[1], yThreshold=yThreshold, fitThreshold=fitThreshold, yccMode=yccMode)

cv.NamedWindow('camtest', 1) 

if len(sys.argv) > 1 and sys.argv[1] == 'b':
	for i in range(0, trainImages):
		smFrame = cv.QueryFrame(camera)
		util.RotateImage(smFrame, imgCopy, rotate)
		bg2.FindBackground(imgCopy, imgFG, bgModel)
		cv.ShowImage(windowTitle, imgFG)
		cv.WaitKey(10)

while cv.WaitKey(10) != 27:
	smFrame = cv.QueryFrame(camera)
	util.RotateImage(smFrame, imgCopy, rotate)
	
	if len(sys.argv) > 1 and sys.argv[1] == 'b':
		bg2.FindBackground(imgCopy, imgFG, bgModel, update = 0, findShadow=findShadow)
		cv.ShowImage(windowTitle, imgFG)
	else:
		cv.ShowImage(windowTitle, imgCopy)
