import cv, numpy, sys, json, math
import ocr2, util, bg2, camera, gui, hand2, dict, speech
from settings import *
from util import Size

def DoOCR(rectified, dict):
	try:
		ocr = ocr2.OCRManager(rectified.width, rectified.height, boxAspectThresh = 0, dilateSteps = 5)
		ocr.ClearOCRTempFiles()
		boxes = ocr.FindTextAreas(rectified, verbose=True)
		for box in boxes:
			file, id = ocr.CreateTempFile(rectified, box)
			uncorrected = ocr.CallOCREngine(id, recognizer=ocr2.Recognizer.TESSERACT)
			corrected = dict.CorrectPhrase(uncorrected)
			box2 = [(box.x,box.y),(box.x+box.width,box.y),(box.x+box.width,box.y+box.height),(box.x,box.y+box.height)]
			util.DrawPolyLine(rectified, box2)
			cv.SaveImage('output/textboxes.png',rectified)
			print '----'
			print 'uncorrected: %s' % uncorrected
			print 'corrected: %s' % corrected
			
	except Exception, err:
		print 'Could not rectify image: %s' % err
	
def main():
	image = cv.LoadImage(sys.argv[1])
	d = dict.DictionaryManager(dictFile, userDictFile, verbose=True)
	DoOCR(image, d)

if __name__ == "__main__": main()