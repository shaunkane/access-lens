import cv, numpy, itertools, math, subprocess, sys, collections
import bg2

def beep():
	print '\a'

# enum code taken from http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python/1695250#1695250
def Enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

# shapes and named tuples
Point = collections.namedtuple('Point', 'x y')
Size = collections.namedtuple('Size', 'width height')
Rect = collections.namedtuple('Rect', 'x y width height')
# end shapes and named tuples

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
def DrawRect(img, rect, color=(0,255,0), thickness=1):
	rect = Rect._make(rect)
	points = [Point(rect.x,rect.y),Point(rect.x+rect.width,rect.y),Point(rect.x+rect.width,rect.y+rect.height),Point(rect.x,rect.y+rect.height)]
	DrawPolyLine(img, points, color, thickness)
def DrawPolyLine(img, points, color=(0,255,0), thickness=1):
	intPoints = [(int(p[0]),int(p[1])) for p in points]
	cv.PolyLine(img, [intPoints], thickness, color)
def DrawPoints(img, points, color=(0,255,0), thickness=1, border=5, colors = None):
	for i in xrange(0, len(points)):
		if colors is not None: color = colors[i % len(colors)]
		DrawPoint(img, points[i], border=border, thickness=thickness, color=color)

def Centroid(points):
	sumX = float(sum([p[0] for p in points]))
	sumY = float(sum([p[1] for p in points]))
	
	return Point(sumX/len(points),sumY/len(points))

def DrawText(img, text, x, y, color=(0,255,0), offset=10): # draw labeled boxes on image. good for showing OCR results eh
	cv.PutText(img, text, (x, int(y+offset)), FONT, color)
def DrawPoint(img, point, border=5, thickness=1, color=(255,0,255)):
	rect = [Point(point.x-border, point.y-border), Point(point.x+border, point.y-border),
			Point(point.x+border, point.y+border), Point(point.x-border, point.y+border)]
	DrawPolyLine(img, rect, color, thickness)
# end drawing

# image processing
def FindContours(img, imgCopy=None, minLength=2, storage=None, minSize=Size(100,100)):
	if storage == None: storage = cv.CreateMemStorage(0)
	if imgCopy == None: imgCopy = cv.CloneImage(img) # find contours is destructive to the image, so clone it
	blobs = []
	currentContour = cv.FindContours(imgCopy, storage, cv.CV_RETR_EXTERNAL, cv.CV_CHAIN_APPROX_SIMPLE, (0, 0))
	while currentContour != None and len(currentContour) > 0:
		blob = currentContour[:]
		if len(blob) > minLength:
			bbox = BoundingRect(blob)
			if bbox.width > minSize.width and bbox.height > minSize.height:
				blobs.append([Point._make(b) for b in blob])
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
def FindHomography(srcPoints, destPoints, homographyMatrix=None, useNumpy=False):
	if useNumpy:
		a = srcPoints if type(srcPoints) == numpy.ndarray and srcPoints.shape[1] == 3 else numpy.array([(x,y,1) for x,y in srcPoints],dtype=numpy.float32)
		b = destPoints if type(destPoints) == numpy.ndarray and destPoints.shape[1] == 3 else numpy.array([(x,y,1) for x,y in destPoints],dtype=numpy.float32)
		homographyMatrix = numpy.linalg.lstsq(a,b)[0].T		
	else: # use opencv
		a = srcPoints if type(srcPoints) == numpy.ndarray else numpy.array(srcPoints, dtype=numpy.float32)
		b = destPoints if type(destPoints) == numpy.ndarray else numpy.array(destPoints, dtype=numpy.float32)
		if homographyMatrix is None:
			homographyMatrix = numpy.zeros((3,3), dtype=numpy.float32) # set up homography matrix
		print a
		print b
		cv.FindHomography(cv.fromarray(a),cv.fromarray(b),cv.fromarray(homographyMatrix),0) # find homography
	return homographyMatrix
def TransformPoint(point, homography):
	a = point if type(point) == numpy.ndarray and len(a) == 3 else numpy.array((point[0],point[1],1),dtype=numpy.float32)
	result = numpy.dot(homography,a)
	return numpy.array((result[0]/result[2],result[1]/result[2]),dtype=numpy.float32)

def GetRectifiedImage(img, points, aspectRatio, padding=0): # return a NEW, perfectly sized rectified image
	srcPoints = numpy.array(ReorderPointsClockwise(points), dtype=numpy.float32) # reorder points: topleft, topright, bottomleft, bottomright
	longestDim = LongestEdge(points) # figure out dimensions of image
	height = int(longestDim) if aspectRatio.height > aspectRatio.width else int(longestDim*(aspectRatio.height/aspectRatio.width))
	width = int(longestDim) if aspectRatio.width > aspectRatio.height else int(longestDim*(aspectRatio.width/aspectRatio.height))

	if padding == 0:
		destPoints = numpy.array([[0,0],[width,0],[width,height],[0,height]], dtype=numpy.float32)
		destImage = cv.CreateImage((width, height),img.depth,img.nChannels) # create dest image
	else:
		hp = height*padding
		wp = width*padding
		h2 = int(height + hp*2)
		w2 = int(width + wp*2)
		destPoints = numpy.array([[wp,hp],[w2-wp,hp],[w2-wp,h2-hp],[wp,h2-hp]], dtype=numpy.float32)
		destImage = cv.CreateImage((w2, h2),img.depth,img.nChannels) # create dest image
	
	print 'src ', srcPoints
	print 'dest ', destPoints
	
	homographyMatrix = FindHomography(srcPoints, destPoints)
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
		tl = min(biggestContour, key = lambda p: Distance(p, Point(bbox.x,bbox.y)))
		tr = min(biggestContour, key = lambda p: Distance(p, Point(bbox.x+bbox.width,bbox.y)))
		br = min(biggestContour, key = lambda p: Distance(p, Point(bbox.x+bbox.width,bbox.y+bbox.height)))
		bl = min(biggestContour, key = lambda p: Distance(p, Point(bbox.x,bbox.y+bbox.height)))
		corners = [tl, tr, br, bl]
		if not refineCorners or frame is None:
			return [Point._make(p) for p in corners]
		elif refineCorners and frame is not None:
			if frame.nChannels > 1: 
				gray = GetGrayscale(frame)
			else: 
				gray = frame
			betterCorners = cv.FindCornerSubPix(gray, corners, (refineSearch,refineSearch), (-1,-1), (cv.CV_TERMCRIT_ITER, 10, 0) )
			return [Point._make(p) for p in betterCorners]
		else: return []
	else: return []
def GuessAspectRatio(width, height, options=(Point(8.5,11.),Point(5.,5.))):
	ratio = float(width)/height
	return Size._make(min(options, key=lambda p: abs(ratio-p.x/p.y)))
# end homography and perspective transform

# geometry
def GetSize(points):
	points = ReorderPointsClockwise(points)
	x = points[0].x
	y = points[0].y
	width = (Distance(points[0],points[1])+Distance(points[2],points[3]))/2
	height = (Distance(points[0],points[3])+Distance(points[1],points[2]))/2
	return Rect(x,y,width,height)
def BoundingPoints(img): # in clockwise order
	return [Point(0,0), Point(img.width-1,0), Point(img.width-1,img.height-1), Point(0,img.height-1)]
def BoundingRect(points): # in correct format (x,y,w,h)
	points = [Point._make(p) for p in points]
	minX = min(p.x for p in points)
	maxX = max(p.x for p in points)
	minY = min(p.y for p in points)
	maxY = max(p.y for p in points)
	return Rect(minX, minY, maxX-minX, maxY-minY)
def BoundingRectArea(points):
	rect = BoundingRect(points)
	return rect.width*rect.height
def LongestEdge(points):
	pShift = points[1:]+[points[0]] # shift by 1
	return max(Distance(a,b) for a,b in zip(points,pShift))
def ReorderPointsClockwise(points): # top left, top right, bottom right, bottom left
	assert len(points) == 4, "Array should have 4 points, but has %d" % len(points)
	points = [Point._make(p) for p in points]
	
	topbot = sorted(points, key=lambda p: p.y)
	tl, tr = sorted(topbot[0:2], key=lambda p:p.x)
	bl, br = sorted(topbot[2:4], key=lambda p:p.x)
	
	return [tl, tr, br, bl]
	
def ResamplePoints(points, N):
	p2 = [Point._make(p) for p in points] # point array may change, so act on a copy
	intervalLength = PathLength(points) / (N - 1.0)
	distanceTraveled = 0.0
	newPoints = [points[0]]
	i = 1
	while i < len(p2):
		distanceThisStep = Distance(p2[i - 1], p2[i])
		if (distanceTraveled + distanceThisStep) >= intervalLength:
			qx = p2[i-1].x + ((intervalLength - distanceTraveled) / distanceThisStep) * (p2[i].x - p2[i-1].x)
			qy = p2[i-1].y + ((intervalLength - distanceTraveled) / distanceThisStep) * (p2[i].x - p2[i-1].y)
			q = Point(qx, qy)
			newPoints.append(q) # append new point 'q'
			p2.insert(i, q) # insert 'q' at position i in points s.t. 'q' will be the next i
			distanceTraveled = 0.0
		else: 
			distanceTraveled += distanceThisStep
		i += 1

	if len(newPoints) == N - 1: # somtimes we fall a rounding-error short of adding the last point, so add it if so
		newPoints.append(p2[-1])
	return newPoints
def PathLength(points):
	pShift = points[1:]+[points[0]] # shift by 1
	return sum(Distance(a,b) for a,b in zip(points,pShift)) #pairwise sum
def Distance(p1, p2):
	p1 = Point._make(p1)
	p2 = Point._make(p2)
	return math.sqrt((p2.y-p1.y)**2+(p2.x-p1.x)**2)
def PointInsideBoundingBox(point, shape):
	p = Point._make(point)
	bbox = BoundingRect(shape)
	return p.x > bbox.x and p.x < bbox.x+bbox.width and p.y > bbox.y and p.y < bbox.y+bbox.height
# end geometry