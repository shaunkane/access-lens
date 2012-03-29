import cv, numpy, sys, json, math, collections, traceback
import ocr2, util, bg2, camera, gui, hand2, dict, speechManager, tracker
from settings import *
from util import Size, Enum

CameraModes = Enum('BG','Skin','Edge','TrainBG','Default', 'Rectified','FindBox')
TextArea = collections.namedtuple('TextArea', 'text box')
OverlayArea = collections.namedtuple('OverlayArea', 'text box link')

class DioptraWindow(gui.GUIWindow):
	def __init__(self, title="Window", scale=1, rotate=rotate, rectifyImage=False):
		super(DioptraWindow,self).__init__(title, scale, rotate)

		# set up scratch images
		self.SetupScratchImages(rotate)

		# mode params
		self.highResMode = False
		self.trackingHand = False
		self.cameraMode = CameraModes.Default
		
		# recognition
		else: self.textAreas = []
		self.rectifyImage = rectifyImage
		
		# load ocr and other stuff
		self.hand = hand2.HandClassifier()
		self.speech = speechManager.SpeechManager()
		self.tracker = tracker.Tracker(self.speech)
		self.dict = dict.DictionaryManager(dictFile, userDictFile)
		
		
		self.overlayAreas = []
		
		# transforms
		self.tCamToDoc = None
		self.tDocToCam = None
		self.docSize = None
		self.largeRect = None
		self.smallRect = None
		
		# overlay
		self.overlaySide = "right"
		
		# gesture tracking
		self.cursor = None
		self.touchedArea = None
		self.lastGesture = None
		
		# say something when we see a big document
		self.seenRectYet = False
		
		# dwell counter for edge overlay
		self.dwellCounter = 0
		self.directionMode = False
		
	# if they exist, load (and show) cached areas from json file (specified in global settings)
	def LoadCachedAreas(self):
		try: # to load cached text areas
			areas = json.load(file(savedAreaFile))
			self.textAreas = []
			for a in areas:
				self.textAreas.append(TextArea._make(a))
			print 'Loaded text areas from %s' % jsonFile
		except Exception, err:
			self.textAreas = []
			traceback.print_exc(file=sys.stdout)
	
	# if the point is inside a text area, return the area
	def PointInsideAreas(self, point, areas):
		if len(areas) == 0: return None
		areasContainingPoint = [area for area in areas if util.PointInsideBoundingBox(point, area.box)]
		return areasContainingPoint[0] if len(areasContainingPoint) > 0 else None

	# set up scratch images
	def SetupScratchImages(self, rotate):
		if rotate in (0,180): 
			small = sizeSmall; half = sizeHalf; large = sizeLarge
		else: 
			small = Size(sizeSmall.height,sizeSmall.width)
			half = Size(sizeHalf.height,sizeHalf.width)
			large = Size(sizeLarge.height,sizeLarge.width)

		# we need 2 BG models here because of weird camera FOV stuff
		self.bgModelSmall = bg2.BackgroundModel(small.width, small.height, yThreshold=20, fitThreshold=16, yccMode=0)
		self.bgModelHalf = bg2.BackgroundModel(half.width, half.height, yThreshold=20, fitThreshold=16, yccMode=0)
		
		# scratch images
		self.bgSmall = cv.CreateImage(small,cv.IPL_DEPTH_8U,1)
		self.skinSmall = cv.CreateImage(small,cv.IPL_DEPTH_8U,1)
		self.edgeSmall = cv.CreateImage(small,cv.IPL_DEPTH_8U,1)
		self.yccSmall = cv.CreateImage(small,cv.IPL_DEPTH_8U,3)
		self.graySmall = cv.CreateImage(small,cv.IPL_DEPTH_8U,1)
		self.skinHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,1)
		self.frameHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,3)
		self.bgHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,1)
		self.yccHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,3)
		self.edgeHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,1)
		self.grayHalf = cv.CreateImage(half,cv.IPL_DEPTH_8U,1)
		self.grayLarge = cv.CreateImage(large,cv.IPL_DEPTH_8U,1)
	
	def FindLargestRectangleCorners(self, frame, gray=None, ycc=None, edge=None, 
									bg=None, bgModel=None, findUsingEdges=True):
		if findUsingEdges:
			gray = util.GetGrayscale(frame, gray)
			edge = util.GetEdge(frame=gray, edge=edge)
			corners = util.FindLargestRectangle(edge, frame=gray)
		else:
			ycc = util.GetYCC(frame, ycc)
			bg2.FindBackground(ycc, bg, bgModel, update=0, doCleanup=True)
			corners = util.FindLargestRectangle(self.bgHalf, color=self.frameHalf)
		return corners
	
	# rectify the largest rect in the image 
	# knownAspectRatio: if passed, use this aspect ratio. otherwise find one
	# findUsingEdges: if true, use edge image to find document. otherwise use trained background
	def RectifyImage(self, knownAspectRatio=None, findUsingEdges=True):
		# get a large camera image, then resize it
		frameBig = self.cam.GetFrame(size=sizeLarge)
		cv.Resize(frameBig, self.frameHalf)
		
		# find corners of the largest rectangle
		if self.largeRect is not None:
			corners = self.largeRect
			print 'yay'
		else:
			corners = self.FindLargestRectangleCorners(self.frameHalf, self.grayHalf, self.yccHalf, 
												   self.edgeHalf, self.bgHalf, self.bgModelHalf, 
												   findUsingEdges)
										
		if len(corners) == 0: 
			print 'No rectangle found'
			return None
		else:
			bigCorners = [(x/bgModelScale,y/bgModelScale) for x,y in corners] # scale box
			util.GetGrayscale(frameBig, self.grayLarge)
			betterCorners = cv.FindCornerSubPix(self.grayLarge, bigCorners, (10,10), (-1,-1), 
												(cv.CV_TERMCRIT_ITER,10,0))
			betterCorners = corners
			print betterCorners
			
			# determine the approximate aspect ratio of the 
			if knownAspectRatio is not None: aspectRatio = knownAspectRatio
			else: 
				rect = util.GetSize(betterCorners)
				aspectRatio = util.GuessAspectRatio(rect.width, rect.height, options=AspectRatios)
				print 'Guessed aspect ratio: (%f,%f)' % (aspectRatio.width, aspectRatio.height)
			
			rectified, transform = util.GetRectifiedImage(frameBig, betterCorners, 
														  aspectRatio=aspectRatio)
			cv.SaveImage('output/rectified.png',rectified)
			return rectified, Size(rectified.width, rectified.height)

	# create the transforms self.tCamToDoc and self.tDocToCam
	def UpdateTransforms(self, imgSize=None, frame=None):
		if frame is None: frame = self.cam.GetFrame()
		camCorners = self.FindLargestRectangleCorners(frame)
		if imgSize is None:
			rect = util.GetSize(camCorners)
			aspectRatio = util.GuessAspectRatio(rect.width, rect.height, options=AspectRatios)
			rectified, transform = util.GetRectifiedImage(frame, camCorners, aspectRatio=aspectRatio)
			imgSize = Size(rectified.width, rectified.height)
			
		docCorners = [(0,0),(imgSize.width,0),(imgSize.width,imgSize.height),(0,imgSize.height)]
		self.tCamToDoc = util.FindHomography(camCorners, docCorners)
		self.tDocToCam = util.FindHomography(docCorners, camCorners)
		self.docSize = imgSize
	
	def CamToDoc(self, point):
		assert self.tCamToDoc is not None, "No transform from camera to document"
		return util.TransformPoint(point, self.tCamToDoc)

	def DocToCam(self, point):
		assert self.tDocToCam is not None, "No transform from document to camera"
		return util.TransformPoint(point, self.tDocToCam)
		
	# perform ocr using the camera. returns the text areas found
	def DoOCR(self):
		waitFrame = cv.CloneImage(self.cam.GetFrame())
		# bg2.FindBackground(waitFrame, bgSmall, bgModelSmall) # train OCR
		if self.rectifyImage:
			# get transform from small image to document
			corners = self.FindLargestRectangleCorners(waitFrame)
			util.DrawPolyLine(waitFrame, corners, color=(0,255,255))
			self.ShowImage(waitFrame)
			
			# rectify
			rectified, imgSize = self.RectifyImage()
			print 'Rectified image'
			#util.DrawPolyLine(waitFrame, corners, color=(0,255,0))
			self.ShowImage(waitFrame)
			cv.WaitKey(10)
			ocrImage = rectified						
			self.UpdateTransforms(imgSize, frame=waitFrame)
		else: 
			ocrImage = self.cam.GetFrame()
		
		ocr = ocr2.OCRManager(ocrImage.width, ocrImage.height, boxAspectThresh = BoxAspectThresh, 
							  dilateSteps = DilateSteps, windowSize = WindowSize, boxMinSize = 15)
		ocr.ClearOCRTempFiles()
		
		# find text areas
		textAreas = []
		boxes = ocr.FindTextAreas(ocrImage, verbose=True)

		# sort by y, then x
		boxes.sort(key=lambda box: (box.y, box.x))

		# highlight boxes as they are found
		rectBoxes = []
		for box in boxes:
			# get transformed box
			rectBox = [(box.x,box.y),(box.x+box.width,box.y),(box.x+box.width,box.y+box.height),(box.x,box.y+box.height)]
			if self.rectifyImage: rectBox = [util.TransformPoint(p, self.tDocToCam) for p in rectBox]
			rectBox = [Point(int(x),int(y)) for x,y in rectBox]
			rectBoxes.append(rectBox)
			util.DrawPolyLine(waitFrame, rectBox, color=(0,255,255))
			self.ShowImage(waitFrame)
			cv.WaitKey(10)
			
		for box,rectBox in zip(boxes,rectBoxes):
			util.DrawPolyLine(waitFrame, rectBox, color=(0,255,0))
			self.ShowImage(waitFrame)
			cv.WaitKey(10)
			
			file, id = ocr.CreateTempFile(ocrImage, box)
			text = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
			#text = ''
			text = self.dict.CorrectPhrase(text, verbose=True)
			if text is not None: 
				textAreas.append(TextArea(text,rectBox))
				self.speech.Say("Recognized %s" % text)
				#util.DrawText(waitFrame, text, rectBox[3][0], rectBox[3][1], color=(0,255,0))
				#util.DrawRect(ocrImage, box, color=(0,255,0))
			else:
				util.DrawPolyLine(waitFrame, rectBox, color=(50,50,50))
				#util.DrawRect(ocrImage, box, color=(0,0,200))
				self.ShowImage(waitFrame)
				cv.WaitKey(10)
			
			cv.SaveImage('output/textareas.png',ocrImage)
			
		# read them out
		#self.speech.Say("found %d items" % (len(textAreas)), interrupt=False)
		
		# save to json file
		jf = open(jsonFile, 'w')
		json.dump(textAreas, jf)
		print 'Saved file %s' % jsonFile
		return textAreas

	# get camera image of the appropriate size, and return pointers to the appropriate temp images
	def GetFrames(self):
		if self.highResMode: 
			frameBig = self.cam.GetFrame(size=sizeLarge)
			cv.Resize(frameBig, self.frameHalf)
			frame = self.frameHalf
			bgModel = self.bgModelHalf
			bg = self.bgHalf
			ycc = self.yccHalf
			skin = self.skinHalf
			edge = self.edgeHalf
			gray = self.grayHalf
		else:
			frame = self.cam.GetFrame()
			bgModel = self.bgModelSmall
			bg = self.bgSmall
			ycc = self.yccSmall
			skin = self.skinSmall
			edge = self.edgeSmall
			gray = self.graySmall
		
		return frame, bgModel, bg, ycc, skin, edge, gray
	
	# track the hand and return the finger point (if it exists) and the current gesture
	def GetGesture(self, frame, skin, bg):
		gesture, cursor = self.hand.ClassifyHandGesture(skin, bg, useX = (not self.rectifyImage))
		return gesture, cursor
	
	# draw textareas and the largest rectangle
	def DrawTextAreas(self, imgToShow, edge):
		textColor = (0,255,0)
		activeColor = (255,255,0)
		overlayColor = (255,100,100)
	
		if imgToShow.nChannels == 1:
			imgToShow = util.GetColor(imgToShow)	
				
		for d in self.overlayAreas:
			util.DrawPolyLine(imgToShow, d.box, color=overlayColor)
			util.DrawText(imgToShow, d.text, d.box[3][0], d.box[3][1], color=overlayColor, offset=-10)
			
		for d in self.textAreas:
			clr = activeColor if (self.touchedArea is not None and d is self.touchedArea) else textColor
			util.DrawPolyLine(imgToShow, d.box, color=clr)
			#util.DrawText(imgToShow, d.text, d.box[3][0], d.box[3][1], color=clr)

		return imgToShow
	
	def FindLargestRect(self, imgToShow, edge):
		util.GetEdge(imgToShow, edge)
		rect = util.FindLargestRectangle(bg=edge, frame=imgToShow)
		if len(rect) > 0:
			if self.highResMode:
				self.largeRect = rect
			else:
				self.smallRect = rect
			#if self.rectifyImage and not self.seenRectYet:
			#	self.seenRectYet = True
			self.speech.Say("Document detected")
			print rect
			return rect
		else: return None
			
	def DrawLargestRect(self, imgToShow):
		rectColors = [(0,0,255), (0,255,0), (255,0,0), (255,0,255)]
		if self.highResMode and self.largeRect is not None:
			util.DrawPoints(imgToShow, self.largeRect, colors=rectColors)
		elif not self.highResMode and self.smallRect is not None:
			util.DrawPoints(imgToShow, self.smallRect, colors=rectColors)

		return imgToShow
	
	def DrawCursor(self, imgToShow):
		if self.cursor is not None:
			util.DrawPoint(imgToShow, self.cursor, color=(255,190,255))
		return imgToShow
	
	# key handler
	def OnKey(self, char, code):
		super(DioptraWindow,self).OnKey(char, code)
		try:
			if char == 'd' or (self.cameraMode != CameraModes.Default and char in ('v','b','t','s','e')):
				self.cameraMode = CameraModes.Default
				print 'Default mode'
			elif char == 'v':
				self.UpdateTransforms()
				self.cameraMode = CameraModes.Rectified
				print 'Rectified mode'
			elif char == 'h':
				self.highResMode = not self.highResMode
				print 'High rez mode? %s' % self.highResMode
			elif char == 'b':
				self.cameraMode = CameraModes.BG
				print 'BG mode'
			elif char == 't':
				self.cameraMode = CameraModes.TrainBG
				print 'Training BG mode'
			elif char == 'g':
				self.trackingHand = not self.trackingHand
				print 'Tracking hand mode? %s' % self.trackingHand
			elif char == 's':
				self.cameraMode = CameraModes.Skin
				print 'Skin mode'
			elif char == 'e':
				self.cameraMode = CameraModes.Edge
				print 'Edge mode'
			elif char == 'f':
				self.cameraMode = CameraModes.FindBox
				print 'Finding box'
			elif char == 'r':
				print 'Reset BG models'
				self.bgModelSmall.Reset()
				self.bgModelHalf.Reset()
				self.largeRect = None
				self.smallRect = None
			elif char == 'a':
				print 'Toggling access overlay'
				self.ToggleOverlay()
			elif char == 'o':
				print 'Do OCR'
				self.speech.Say("Starting OCR")
				self.RectifyImage()
				#self.textAreas = self.DoOCR()
				#print 'OCR complete, found %d text areas' % len(self.textAreas)
					
			elif char == '1':
				print '''
h - switch resolution
b - background mode
t - train background
g - track hand
s - show skin
e - show edges
d - default mode
r - reset BG model
a - toggle access overlays
f - find box
o - start OCR
				'''
		except Exception, err:
			traceback.print_exc(file=sys.stdout)
	
	def ToggleOverlay(self):
		if self.docSize is None: self.UpdateTransforms()
		assert self.overlaySide == "right", "OverlaySide must be 'right'"
		assert self.rectifyImage, "rectifyImage must be True"
		assert self.docSize is not None, "Transforms must be updated"
		if len(self.overlayAreas) > 0:
			self.overlayAreas = []
			self.speech.Say("Removing access overlay")
			return
		
		# otherwise, create them
		# first, get textareas sorted by alpha
		# sortedAreas = sorted(self.textAreas, key=lambda area: area.text.lower())
		sortedAreas = self.textAreas
		
		# get width and height of the addon areas
		width = int(self.docSize.width * .2) # for now, make overlay 20% of doc width
		height = int(1. * self.docSize.height / len(sortedAreas)) # height is the height of the doc by the number of items
		
		startx = self.docSize.width - width/3
		
		# create areas
		for i in range(0, len(sortedAreas)):
			area = sortedAreas[i]
			rect = [Point(startx, height*i),Point(startx+width, height*i),Point(startx+width, height*(i+1)),Point(startx, height*(i+1))]
			tRect = [self.DocToCam(p) for p in rect]
			oArea = OverlayArea(area.text, tRect, area)
			self.overlayAreas.append(oArea)
		
		self.speech.Say("Added access overlay to right edge. %d items" % len(sortedAreas))
		
	def ProcessFrame(self, frameCount): # just focus on what to show here
		frame, bgModel, bg, ycc, skin, edge, gray = self.GetFrames()
		imageRectified = False
		
		if self.cameraMode == CameraModes.TrainBG:
			# util.GetYCC(frame, ycc) 
			bg2.FindBackground(frame, bg, bgModel)
			imgToShow = bg
		elif self.cameraMode == CameraModes.Edge:
			util.GetGrayscale(frame, gray)
			util.GetEdge(frame=gray, edge=edge)
			imgToShow = edge
		elif self.cameraMode == CameraModes.Rectified:
			rect = util.WarpImage(frame, self.tCamToDoc, width=self.docSize.width, height=self.docSize.height)
			imageRectified = True
			imgToShow = rect
		elif self.cameraMode == CameraModes.BG:
			# util.GetYCC(frame, ycc)
			bg2.FindBackground(frame, bg, bgModel, update=0, doCleanup=True)
			imgToShow = bg
		elif self.cameraMode == CameraModes.Skin:
			util.GetYCC(frame, ycc)
			bg2.FindSkin(ycc, skin, doCleanup=True)
			#bg2.FindBackground(frame, bg, bgModel, update=0, doCleanup=True)
			#cv.And(bg,skin,skin)
			util.GetGrayscale(frame, gray)
			util.GetEdge(frame=gray, edge=edge)
			cv.Add(edge,skin,skin)
			imgToShow = skin
		elif self.cameraMode == CameraModes.FindBox:
			util.GetGrayscale(frame, gray)
			util.GetEdge(frame=gray, edge=edge)
			self.FindLargestRect(frame, edge)
			imgToShow = frame
			self.cameraMode = CameraModes.Default
		elif self.cameraMode == CameraModes.Default:
			imgToShow = frame
		
		if self.trackingHand:
			self.TrackHand(frame, ycc, skin, bg, bgModel)

		if not imageRectified:
			self.DrawTextAreas(imgToShow, edge)
			self.DrawLargestRect(imgToShow)
			self.DrawCursor(imgToShow)
		self.ShowImage(imgToShow)

	### this is where the magic happens, when we're tracking
	def TrackHand(self, frame, ycc, skin, bg, bgModel):
		if not self.tracker.isTracking(): self.directionMode = False
		#util.GetYCC(frame, ycc)
		#bg2.FindSkin(ycc, skin, doCleanup=True)
		bg2.FindBackground(frame, bg, bgModel, update=0, doCleanup=True)
		cv.And(bg,skin,skin)	
		cv.MorphologyEx(skin,skin,None,None,cv.CV_MOP_OPEN,2)
		gesture, self.cursor = self.GetGesture(frame, bg, skin)

		if self.lastGesture is None or gesture != self.lastGesture:
			self.lastGesture = gesture
			print 'Gesture: %s' % self.lastGesture	
		
			
		# are we touching a text area?
		elif self.cursor is not None:
			self.tracker.updateDirection(self.cursor)
			
			# are we inside an overlay area?
			area = self.PointInsideAreas(self.cursor, self.overlayAreas)
			if area is not None:
				if (self.touchedArea is None or area is not self.touchedArea):
					self.touchedArea = area
					self.speech.Say('Overlay %s. Hold here for directions.' % area.text)	
					self.dwellCounter = 0
				else:
					self.dwellCounter += 1
					if self.dwellCounter == 60:
						self.directionMode = True
						self.speech.Say('Locating target %s' % area.link.text)
						self.tracker.setTarget(util.Centroid(area.link.box), area.link.text and not self.directionMode)
						
			elif not self.directionMode:
				# otherwise, are we inside a regular area?
				area = self.PointInsideAreas(self.cursor, self.textAreas)

				if area is not None and (self.touchedArea is None or area is not self.touchedArea):
					self.touchedArea = area
					self.speech.Say(area.text)	
			
def main():
	mode = sys.argv[1] if len(sys.argv) > 1 else 't'

	if mode == 't': # table mode
		window = DioptraWindow(windowName + ': Table', rotate=rotate, rectifyImage=True)
	else: # pendant mode
		window = DioptraWindow(windowName + ': Pendant', rotate=0, rectifyImage=False)

	window.StartCameraLoop()
	sys.exit()

if __name__ == "__main__": main()