import cv, numpy, util
from util import X,Y,WIDTH,HEIGHT

class Camera(object):
	def __init__(self, size, camIndex=1, scale=1, rotate=0):
		self.camIndex = camIndex
		self.cam = cv.CaptureFromCAM(camIndex)
		self.SetSize(size)
		self.rotate = rotate
		self.scale = scale
		self.scratchImages = {}
	
	def SetSize(self,size):
		self.width = size[X]
		self.height = size[Y]
		cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_FRAME_WIDTH, self.width)
		cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_FRAME_HEIGHT, self.height)
		# throw these out
		frame = cv.QueryFrame(self.cam)
		while frame.width != self.width or frame.height != self.height:
			frame = cv.QueryFrame(self.cam)
		
	def GetFrame(self,size=None,scale=None,rotate=None):
		if size is None: width = self.width; height = self.height
		else: width = size.width; height = size.height
		if rotate is None: rotate = self.rotate
		if scale is None: scale = self.scale
		
		# first, get the frame
		frame = cv.QueryFrame(self.cam)
		if frame.width != width or frame.height != height:
			cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_FRAME_WIDTH, width)
			cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_FRAME_HEIGHT, height)
			while frame.width != width or frame.height != height:
				frame = cv.QueryFrame(self.cam)
		
		imgToShow = frame
		
		if scale != 1:
			scaledWidth = int(imgToShow.width*scale)
			scaledHeight = int(imgToShow.height*scale)
			if not self.scratchImages.has_key((scaledWidth,scaledHeight)):
				self.scratchImages[(scaledWidth,scaledHeight)] = cv.CreateImage((scaledWidth,scaledHeight),frame.depth,frame.nChannels)
			cv.Resize(imgToShow, self.scratchImages[(scaledWidth,scaledHeight)])
			imgToShow = self.scratchImages[(scaledWidth,scaledHeight)]
		if rotate != 0:
			rotatedWidth = imgToShow.width if rotate == 180 else imgToShow.height
			rotatedHeight = imgToShow.height if rotate == 180 else imgToShow.width
			if not self.scratchImages.has_key((rotatedWidth,rotatedHeight)):
				self.scratchImages[(rotatedWidth,rotatedHeight)] = cv.CreateImage((rotatedWidth,rotatedHeight),frame.depth,frame.nChannels)
			util.RotateImage(imgToShow, self.scratchImages[(rotatedWidth,rotatedHeight)], rotate)
			imgToShow = self.scratchImages[(rotatedWidth,rotatedHeight)]

		return imgToShow