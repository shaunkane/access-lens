import util, cv, ocr2, copy, time, sys

boxAspectThresh = 1.5
dilateSteps = 6
windowSize = 4
boxMinSize = 50

imgRect = cv.LoadImage(sys.argv[1], 3)
ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = boxAspectThresh, dilateSteps = dilateSteps, windowSize = windowSize, boxMinSize = boxMinSize)
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

print boxes