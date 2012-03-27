import sys, cv, subprocess
import util, camera
from settings import *

class GUIWindow(object):
	def __init__(self, title="Window", scale=1, rotate=rotate, camIndex=defaultCamIndex):
		assert rotate in (0,90,-90,180), "Invalid rotation: %d" % rotate
		self.title = title
		self.cam = camera.Camera(camIndex=camIndex,size=sizeSmall, scale=scale, rotate=rotate)
		self.scratchImages = {}
		self.inCameraLoop = False
				
	def BringToFront(self):
		try:
			if sys.platform == "darwin":
				subprocess.Popen("osascript -e 'tell app \"Python\" to activate'",shell=True)
			else:
				print "Can't bring window to front, platform: %s" % sys.platform
		except Exception, err:
			print "Failed to bring Python window to front %s" % str(err)

	def ShowImage(self, frame, scale=1, rotate=0):
		imgToShow = frame
		if scale != 1:
			scaledWidth = int(imgToShow.width*scale)
			scaledHeight = int(imgToShow.height*scale)
			if not self.scratchImages.has_key((scaledWidth,scaledHeight,frame.depth,frame.nChannels)):
				self.scratchImages[(scaledWidth,scaledHeight,frame.depth,frame.nChannels)] = cv.CreateImage((scaledWidth,scaledHeight),frame.depth,frame.nChannels)
			cv.Resize(imgToShow, self.scratchImages[(scaledWidth,scaledHeight,frame.depth,frame.nChannels)])
			imgToShow = self.scratchImages[(scaledWidth,scaledHeight,frame.depth,frame.nChannels)]
		if rotate != 0:
			rotatedWidth = imgToShow.width if rotate == 180 else imgToShow.height
			rotatedHeight = imgToShow.height if rotate == 180 else imgToShow.width
			if not self.scratchImages.has_key((rotatedWidth,rotatedHeight,frame.depth,frame.nChannels)):
				self.scratchImages[(rotatedWidth,rotatedHeight,frame.depth,frame.nChannels)] = cv.CreateImage((rotatedWidth,rotatedHeight),frame.depth,frame.nChannels)
			util.RotateImage(imgToShow, self.scratchImages[(rotatedWidth,rotatedHeight,frame.depth,frame.nChannels)], rotate)
			imgToShow = self.scratchImages[(rotatedWidth,rotatedHeight,frame.depth,frame.nChannels)]
		cv.ShowImage(self.title,imgToShow)
		self.lastImage = imgToShow

	def StartCameraLoop(self):
		assert self.cam is not None, "No camera set"
		self.inCameraLoop = True
		frameCount = 0
		while self.inCameraLoop:
			keycode = cv.WaitKey(10)
			if keycode != -1: self.OnKey(chr(keycode), keycode)
			self.ProcessFrame(frameCount)
			frameCount+=1
	
	# you will probably override these
	def OnKey(self, char, code):
		if code == 27:
			print 'Pressed ESC. Exiting loop.'
			self.inCameraLoop = False
		else:
			print 'Pressed key %s' % char
	
	def ProcessFrame(self, frameCount):
		pass