import cv, numpy, sys, pickle, math
import ocr2, util, bg2, camera, gui, hand2, dict
from settings import *
from util import X,Y,WIDTH,HEIGHT
import pickle, os
import multiprocessing, subprocess
import time

class Stuff(object):
	def __init__(self):
		self.mode = 0
		self.corners = []
		self.boxes = []
		self.text = []
		self.transform = None
		self.transformInv = None
		self.ocrItemsRemaining = 0

# def DoOCR(rectified, dict):
# 	try:
# 		ocr = ocr2.OCRManager(rectified.width, rectified.height, boxAspectThresh = 0, dilateSteps = 5)
# 		ocr.ClearOCRTempFiles()
# 		boxes = ocr.FindTextAreas(rectified, verbose=True)
# 		for box in boxes:
# 			file, id = ocr.CreateTempFile(rectified, box)
# 			uncorrected = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
# 			corrected = dict.CorrectPhrase(uncorrected)
# 			box2 = [(box.x,box.y),(box.x+box.width,box.y),(box.x+box.width,box.y+box.height),(box.x,box.y+box.height)]
# 			util.DrawPolyLine(rectified, box2)
# 			cv.SaveImage('output/textboxes.png',rectified)
# 			print '----'
# 			print 'uncorrected: %s' % uncorrected
# 			print 'corrected: %s' % corrected
# 			
# 	except Exception, err:
# 		print 'Could not rectify image: %s' % err

stuff = Stuff()
	
def onMouse(event, x, y, flags, param):
	global stuff
	if stuff.mode == 0 and event == cv.CV_EVENT_LBUTTONDOWN:
		if len(stuff.corners) > 3: stuff.corners = []
		stuff.corners.append((x,y))
		print 'Added corner (%d,%d)' % (x,y)
	
def main():
	global stuff
	if os.path.exists('stuff.pickle'): stuff = pickle.load(open('stuff.pickle', 'rb'))
	
	windowTitle = 'ocrTestWindow'
	img = cv.LoadImage(sys.argv[1])
	imgCopy = cv.CreateImage((img.width, img.height), img.depth, img.nChannels)
	imgGray = cv.CreateImage((img.width, img.height), img.depth, 1)
	imgRect = None

	cv.CvtColor(img, imgGray, cv.CV_BGR2GRAY)
	d = dict.DictionaryManager(dictFile, userDictFile, verbose=True)
	# DoOCR(image, d)

	
	cv.NamedWindow(windowTitle, 1) 
	cv.SetMouseCallback(windowTitle, onMouse, None)

	
	while True:
		key = cv.WaitKey(10)
		if key == 27: break
		
		# handle keys
		if key != -1:
			char = chr(key)
			if char == 'r': # find text areas
				if stuff.mode == 0 and len(stuff.corners) == 4:
					stuff.mode = 1
					imgRect, stuff.transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))
					stuff.transformInv = numpy.linalg.inv(stuff.transform)
				else:
					stuff.mode = 0
			elif char == 'a': # find text areas
				imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))	
				ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = 1.5, dilateSteps = 3, windowSize = 4, boxMinSize = 15)
				ocr.ClearOCRTempFiles()
		
				# find text areas
				stuff.boxes = ocr.FindTextAreas(imgRect, verbose=True)
				#stuff.boxes.sort(key=lambda box: (box[Y], box[X]))
				
			elif char == 'o': # do ocr
				sessionID = int(time.time())
				# re-rectify to clear drawn lines
				cv.Copy(img, imgCopy)
				imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))
				if stuff.mode == 0: cv.ShowImage(windowTitle, imgCopy)
				elif stuff.mode == 1: cv.ShowImage(windowTitle, imgRect)
				
				cv.WaitKey(10)
				ocr = ocr2.OCRManager(imgRect.width, imgRect.height, boxAspectThresh = BoxAspectThresh, dilateSteps = 3, windowSize = 4, boxMinSize = 30)

				# clear out text
				stuff.text = [''] * len(stuff.boxes)

				filenames = ['ocrtemp/box%d.png' % i for i in range(0, len(stuff.boxes))]

				for boxIndex in range(0, len(stuff.boxes)):
					box = stuff.boxes[boxIndex]
					fname = ocr.CreateTempFile(imgRect, box, boxIndex)

					#pool.apply_async(CallOCREngine, (id, ocr2.DefaultWorkingDirectory, ocr2.DefaultRecognizer, i), callback=setText)
					
					#text = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
					#text = ''
					# text = self.dict.CorrectPhrase(text, verbose=True)
					#if text is not None: 
					#	print 'Recognized %s' % text
					#	setText(i, text)
				
				print 'uploading images'
				cloudKeys = CloudUpload(sessionID, filenames)
				print 'images uploaded'

				stuff.ocrItemsRemaining = len(stuff.boxes)
				
				cloudKeys = cloudKeys.split(',')
				# setting up pool
				pool = multiprocessing.Pool(50)
				
				ResetCloudOCR()
				print 'sending images to mturk'
				for boxIndex in range(0, len(stuff.boxes)):
					pool.apply_async(CloudOCR,(boxIndex, cloudKeys[boxIndex]), callback=setText)
				print 'done. %d items to recognize' % stuff.ocrItemsRemaining		
				#pool.close()
				#pool.join()
				
		# show image
		if stuff.mode == 0:
			cv.Copy(img, imgCopy)	
			#betterCorners = cv.FindCornerSubPix(imgGray, corners, (20,20), (-1,-1), (cv.CV_TERMCRIT_ITER,10,0))
			util.DrawPoints(imgCopy, stuff.corners, color=(255,0,0))
			
			for i in range(0,len(stuff.boxes)):
				t = stuff.text[i]
				if t is not None:
					b = stuff.boxes[i]
					util.DrawRect(imgCopy, b, color=(0,255,0), transform=stuff.transformInv)
					if t != '': 
						p = util.Transform((b[X],b[Y]), stuff.transformInv)
						util.DrawText(imgCopy, t, p[X], p[Y], color=(0,255,0))

			
			cv.ShowImage(windowTitle, imgCopy)
		elif stuff.mode == 1:
			imgRect, transform = util.GetRectifiedImage(img, stuff.corners, aspectRatio=(11,8.5))			
			
			for i in range(0,len(stuff.boxes)):
				t = stuff.text[i]
				if t is not None:
					b = stuff.boxes[i]
					util.DrawRect(imgRect, b, color=(0,255,0))
					if t != '': util.DrawText(imgRect, t, b[X], b[Y], color=(0,255,0))	
			cv.ShowImage(windowTitle, imgRect)

	# save for later
	pickle.dump(stuff, open('stuff.pickle', 'wb'))	

def ResetCloudOCR():
	os.system('pkill -f getCloudOcr.py')

def CloudUpload(sessionID, filenames):
	cmd = 'python uploadCloudOcr.py %d %s > ocrtemp/cloudkeys.txt' % (sessionID, ' '.join(filenames))
	#print 'Executing command %s' % cmd
	os.system(cmd)
	#print 'Done'
	result = open('ocrtemp/cloudkeys.txt').read().strip()
	return result
	
def CloudOCR(boxIndex, cloudKey):
	os.system('python getCloudOcr.py %s 1> ocrtemp/box%d.txt 2> ocrtemp/box%derror.txt' % (cloudKey,boxIndex,boxIndex))
	result = open('ocrtemp/box%d.txt' % (boxIndex)).read().strip()
	return (result, boxIndex)
	
def CallOCREngine(fileID, workingDirectory=ocr2.DefaultWorkingDirectory, recognizer=ocr2.DefaultRecognizer, tag=None):
	outputName = 'box' + str(fileID)
	stdout = os.system('tesseract ocrtemp/box%s.tiff ocrtemp/box%s -l eng 2> ocrtemp/scratch.txt' % (fileID, fileID)) # 2> redirects stderr to a scratch file
	#proc = subprocess.call(['ls'], cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	result = open(os.path.join(workingDirectory,outputName+'.txt')).read().strip()
	return (result, tag)

def setText(result):
	global stuff
	text, index = result
	if text is not None: 
		print 'recognized %s (%d/%d)' % (text, len(stuff.text)-stuff.ocrItemsRemaining+1, len(stuff.text))

		if text == '*': stuff.text[index] = None
		else:
			# print 'async recoed %s' % text
			stuff.text[index] = text
		stuff.ocrItemsRemaining -= 1
		if stuff.ocrItemsRemaining == 0:
			print 'BOOM! Recognized all text'
if __name__ == "__main__": main()