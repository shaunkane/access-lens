import cv, numpy, itertools, math, subprocess, sys, collections
import bg2

def beep():
	print '\a'

# enum code taken from http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python/1695250#1695250
def Enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

# constants for named tuples
X = 0
Y = 1
WIDTH = 2
HEIGHT = 3

# image conversion
def GetYCC(img, dest=None):
	if dest == None: dest = cv.CreateImage((img.width,img.height),img.depth,img.nChannels)
	cv.CvtColor(img, dest, cv.CV_BGR2YCrCb)
	return dest
def GetGrayscale(img, dest=None):
	if dest == None: dest = cv.CreateImage((img.width,img.height),img.depth,1)
	cv.CvtColor(img, dest, cv.CV_BGR2GRAY)
	return dest
def GetColor(img, dest=None):
	if dest == None: dest = cv.CreateImage((img.width,img.height),img.depth,3)
	cv.CvtColor(img, dest, cv.CV_GRAY2BGR)
	return dest
	
def GetEdge(frame, edge=None):
	if frame.nChannels > 1: 
		gray = GetGrayscale(frame)
	else: 
		gray = frame
	#mean = numpy.median(gray[:])
	mean = 110
	if edge == None: edge = cv.CreateImage((gray.width,gray.height),gray.depth,1)
	cv.Canny(gray, edge, .5*mean, 1.33*mean, 3)
	return edge
# end image conversion

# drawing
FONT = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1, 1, 0, 1, 8)
def DrawRect(img, rect, color=(0,255,0), thickness=1, transform=None):
	points = [(rect[X],rect[Y]),(rect[X]+rect[WIDTH],rect[Y]),(rect[X]+rect[WIDTH],rect[Y]+rect[HEIGHT]),(rect[X],rect[Y]+rect[HEIGHT])]
	DrawPolyLine(img, points, color, thickness, transform)
def DrawPolyLine(img, points, color=(0,255,0), thickness=1, transform=None):
	#ints = [(int(p[X]),int(p[Y])) for p in points]
	ints = points[:]
	if transform is not None:
		ints = [(int(Transform(p[X], transform)),int(Transform(p[Y], transform))) for p in ints]
	cv.PolyLine(img, [ints], thickness, color)
def DrawPoints(img, points, color=(0,255,0), thickness=1, border=5, colors = None):
	for i in xrange(0, len(points)):
		if colors is not None: color = colors[i % len(colors)]
		DrawPoint(img, points[i], border=border, thickness=thickness, color=color)

def Centroid(points):
	sumX = float(sum([p[0] for p in points]))
	sumY = float(sum([p[1] for p in points]))
	
	return (sumX/len(points),sumY/len(points))

def DrawText(img, text, x, y, color=(0,255,0), offset=10): # draw labeled boxes on image. good for showing OCR results eh
	cv.PutText(img, text, (x, int(y+offset)), FONT, color)
def DrawPoint(img, point, border=5, thickness=1, color=(255,0,255)):
	rect = [(point[X]-border, point[Y]-border), (point[X]+border, point[Y]-border),
			(point[X]+border, point[Y]+border), (point[X]-border, point[Y]+border)]
	DrawPolyLine(img, rect, color, thickness)
# end drawing

# image processing
def FindContours(img, imgCopy=None, minLength=2, storage=None, minSize=(100,100)):
	if storage == None: storage = cv.CreateMemStorage(0)
	if imgCopy == None: imgCopy = cv.CloneImage(img) # find contours is destructive to the image, so clone it
	blobs = []
	currentContour = cv.FindContours(imgCopy, storage, cv.CV_RETR_EXTERNAL, cv.CV_CHAIN_APPROX_SIMPLE, (0, 0))
	while currentContour != None and len(currentContour) > 0:
		blob = currentContour[:]
		if len(blob) > minLength:
			bbox = BoundingRect(blob)
			if bbox[WIDTH] > minSize[WIDTH] and bbox[HEIGHT] > minSize[HEIGHT]:
				blobs.append([b for b in blob])
		currentContour = currentContour.h_next()
	return blobs	
def RotateImage(img, dest=None, angle=90): # angle in degrees
	assert angle in (90,-90,180,-180), "Angle not supported"
	if dest is None:
		if angle in (90,-90):
			dest = cv.CreateImage((img.height, img.width), img.depth, img.nChannels)
		else:
			dest = cv.CreateImage((img.width, img.height), img.depth, img.nChannels)
	if angle == 90: # CW
		cv.Transpose(img,dest)
		cv.Flip(dest,dest,flipMode=1)
	elif angle == -90: # CCW
		cv.Transpose(img,dest)
		cv.Flip(dest,dest,flipMode=0)
	else: # 180
		cv.Copy(img,dest)
		cv.Flip(dest,dest,flipMode=-1)
	return dest
# end image processing

# homography and perspective transform
def FindHomography(srcs, dests, homographyMatrix=None, useNumpy=False):
	if useNumpy:
		a = srcs if type(srcs) == numpy.ndarray and srcs.shape[1] == 3 else numpy.array([(x,y,1) for x,y in srcs],dtype=numpy.float32)
		b = dests if type(dests) == numpy.ndarray and dests.shape[1] == 3 else numpy.array([(x,y,1) for x,y in dests],dtype=numpy.float32)
		homographyMatrix = numpy.linalg.lstsq(a,b)[0].T		
	else: # use opencv
		a = srcs if type(srcs) == numpy.ndarray else numpy.array(srcs, dtype=numpy.float32)
		b = dests if type(dests) == numpy.ndarray else numpy.array(dests, dtype=numpy.float32)
		if homographyMatrix is None:
			homographyMatrix = numpy.zeros((3,3), dtype=numpy.float32) # set up homography matrix
		cv.FindHomography(cv.fromarray(a),cv.fromarray(b),cv.fromarray(homographyMatrix),0) # find homography
	return homographyMatrix
def Transform(point, homography):
	a = point if type(point) == numpy.ndarray and len(a) == 3 else numpy.array((point[0],point[1],1),dtype=numpy.float32)
	result = numpy.dot(homography,a)
	return numpy.array((result[0]/result[2],result[1]/result[2]),dtype=numpy.float32)

def GetRectifiedImage(img, points, aspectRatio, padding=0): # return a NEW, perfectly sized rectified image
	srcs = numpy.array(ReordersClockwise(points), dtype=numpy.float32) # reorder points: topleft, topright, bottomleft, bottomright
	longestDim = LongestEdge(points) # figure out dimensions of image
	height = int(longestDim) if aspectRatio[Y] > aspectRatio[X] else int(longestDim*(aspectRatio[Y]/aspectRatio[X]))
	width = int(longestDim) if aspectRatio[X] > aspectRatio[Y] else int(longestDim*(aspectRatio[X]/aspectRatio[Y]))

	if padding == 0:
		dests = numpy.array([[0,0],[width,0],[width,height],[0,height]], dtype=numpy.float32)
		destImage = cv.CreateImage((width, height),img.depth,img.nChannels) # create dest image
	else:
		hp = height*padding
		wp = width*padding
		h2 = int(height + hp*2)
		w2 = int(width + wp*2)
		dests = numpy.array([[wp,hp],[w2-wp,hp],[w2-wp,h2-hp],[wp,h2-hp]], dtype=numpy.float32)
		destImage = cv.CreateImage((w2, h2),img.depth,img.nChannels) # create dest image
	
	homographyMatrix = FindHomography(srcs, dests)
	WarpImage(img, homographyMatrix, destImage) # apply homography
	return destImage, homographyMatrix # return image and transform

def WarpImage(frame, transform, dest=None, width=None, height=None):
	assert dest is not None or (width is not None and height is not None), "Must provide either a width/height or a dest image"
	if dest is None:
		dest = cv.CreateImage((width, height),frame.depth,frame.nChannels)
	transform = cv.fromarray(transform.copy())
	cv.WarpPerspective(frame, dest, transform)
	return dest

def MaskAndCopy(img, points, copy=None, background=(0,0,0), crop=True): # copy only inside the mask. useful if image is not too distorted
	mask = cv.CreateImage((img.width,img.height),img.depth,1)
	if copy == None: copy = cv.CloneImage(img)
	cv.Set(copy, background)
	tuples = [tuple(p) for p in points]
	cv.FillPoly(mask, [tuples], 255)
	cv.Copy(img, copy, mask)
	if crop: cv.SetImageROI(copy, BoundingRect(points))
	return copy, mask

def FindLargestRectangle(bg, frame=None, refineCorners = True, refineSearch = 5):
	contours = FindContours(bg) 
	if len(contours) > 0:
		biggestContour = max(contours, key=lambda c: BoundingRectArea(c))
		biggestContour = cv.ApproxPoly(biggestContour, cv.CreateMemStorage(0), cv.CV_POLY_APPROX_DP, 1)
		bbox = BoundingRect(biggestContour)
		# get corners
		tl = min(biggestContour, key = lambda p: Distance(p, (bbox[X],bbox[Y])))
		tr = min(biggestContour, key = lambda p: Distance(p, (bbox[X]+bbox[WIDTH],bbox[Y])))
		br = min(biggestContour, key = lambda p: Distance(p, (bbox[X]+bbox[WIDTH],bbox[Y]+bbox[HEIGHT])))
		bl = min(biggestContour, key = lambda p: Distance(p, (bbox[X],bbox[Y]+bbox[HEIGHT])))
		corners = [tl, tr, br, bl]
		if not refineCorners or frame is None:
			return [p for p in corners]
		elif refineCorners and frame is not None:
			if frame.nChannels > 1: 
				gray = GetGrayscale(frame)
			else: 
				gray = frame
			betterCorners = cv.FindCornerSubPix(gray, corners, (refineSearch,refineSearch), (-1,-1), (cv.CV_TERMCRIT_ITER, 10, 0) )
			return [p for p in betterCorners]
		else: return []
	else: return []
def GuessAspectRatio(width, height, options=((8.5,11.),(5.,5.))):
	ratio = float(width)/height
	return (min(options, key=lambda p: abs(ratio-p[X]/p[Y])))
# end homography and perspective transform

# geometry
def GetSize(points):
	points = ReordersClockwise(points)
	x = points[0][X]
	y = points[0][Y]
	width = (Distance(points[0],points[1])+Distance(points[2],points[3]))/2
	height = (Distance(points[0],points[3])+Distance(points[1],points[2]))/2
	return Rect(x,y,width,height)
def Boundings(img): # in clockwise order
	return [(0,0), (img.width-1,0), (img.width-1,img.height-1), (0,img.height-1)]
def BoundingRect(points): # in correct format (x,y,w,h)
	points = [p for p in points]
	minX = min(p[X] for p in points)
	maxX = max(p[X] for p in points)
	minY = min(p[Y] for p in points)
	maxY = max(p[Y] for p in points)
	return Rect(minX, minY, maxX-minX, maxY-minY)
def BoundingRectArea(points):
	rect = BoundingRect(points)
	return rect[WIDTH]*rect[HEIGHT]
def LongestEdge(points):
	pShift = points[1:]+[points[0]] # shift by 1
	return max(Distance(a,b) for a,b in zip(points,pShift))
def ReordersClockwise(points): # top left, top right, bottom right, bottom left
	assert len(points) == 4, "Array should have 4 points, but has %d" % len(points)
	points = [p for p in points]
	
	topbot = sorted(points, key=lambda p: p[Y])
	tl, tr = sorted(topbot[0:2], key=lambda p:p[X])
	bl, br = sorted(topbot[2:4], key=lambda p:p[X])
	
	return [tl, tr, br, bl]
	
def Resamples(points, N):
	p2 = [p for p in points] # point array may change, so act on a copy
	intervalLength = PathLength(points) / (N - 1.0)
	distanceTraveled = 0.0
	news = [points[0]]
	i = 1
	while i < len(p2):
		distanceThisStep = Distance(p2[i - 1], p2[i])
		if (distanceTraveled + distanceThisStep) >= intervalLength:
			qx = p2[i-1][X] + ((intervalLength - distanceTraveled) / distanceThisStep) * (p2[i][X] - p2[i-1][X])
			qy = p2[i-1][Y] + ((intervalLength - distanceTraveled) / distanceThisStep) * (p2[i][X] - p2[i-1][Y])
			q = (qx, qy)
			news.append(q) # append new point 'q'
			p2.insert(i, q) # insert 'q' at position i in points s.t. 'q' will be the next i
			distanceTraveled = 0.0
		else: 
			distanceTraveled += distanceThisStep
		i += 1

	if len(news) == N - 1: # somtimes we fall a rounding-error short of adding the last point, so add it if so
		news.append(p2[-1])
	return news
def PathLength(points):
	pShift = points[1:]+[points[0]] # shift by 1
	return sum(Distance(a,b) for a,b in zip(points,pShift)) #pairwise sum
def Distance(p1, p2):
	return math.sqrt((p2[Y]-p1[Y])**2+(p2[X]-p1[X])**2)
def InsideBoundingBox(point, shape):
	p = point
	bbox = BoundingRect(shape)
	return p[X] > bbox[X] and p[X] < bbox[X]+bbox[WIDTH] and p[Y] > bbox[Y] and p[Y] < bbox[Y]+bbox[HEIGHT]
# end geometry