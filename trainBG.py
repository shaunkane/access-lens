# create a background model, then pickle it

import pickle, cv, bg2, util, sys

camSmall = (640,480)
trainImages = 30
vidDepth = 8
rotate = -90

# create the images we need
imgCopy = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 3) # a rotated copy
imgFG = cv.CreateImage((camSmall[1],camSmall[0]), vidDepth, 1)
	
# set up cam
camera = cv.CaptureFromCAM(0)
cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_WIDTH, camSmall[0])
cv.SetCaptureProperty(camera, cv.CV_CAP_PROP_FRAME_HEIGHT, camSmall[1])

# background model
bgModel = bg2.BackgroundModel(camSmall[1], camSmall[0], yThreshold=20, fitThreshold=16, yccMode=0)
		 
for i in range(0, trainImages):
	smFrame = cv.QueryFrame(camera)
	util.RotateImage(smFrame, imgCopy, rotate)
	bg2.FindBackground(imgCopy, imgFG, bgModel)

# save it
pickle.dump(bgModel, open('bgmodel.pickle', 'wb'))

if name == '__main__':
	