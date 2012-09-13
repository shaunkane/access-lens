# ocr only
import numpy, os, cv, uuid, subprocess
import abbyy

def ClearOCRTempFiles(workingDirectory='./ocrtemp/', fileTypes = ['txt','tiff','png']):
	for fname in os.listdir(workingDirectory):
		if fname.partition('.')[2] in fileTypes:
			os.unlink(os.path.join(workingDirectory, fname))

# ocr engine is tesseract or abbyy
# cloud fix later if we have time...
def CallOCREngine(image, box, fileID, lock, workingDirectory='./ocrtemp/', recognizer = 'tesseract'):
	if lock is not None: lock.acquire()
	fname = CreateTempFile(image, box, fileID)
	if lock is not None: lock.release()
	
	result = ''
	if recognizer == 'tesseract':
		result = ocr_tesseract(fileID,fname,workingDirectory)
	elif recognizer == 'abbyy':
		result = ocr_abbyy(fname)
	
	return (result, fileID)

def CreateTempFile(image, box, fileID):
	imageName = 'box%d.%s' % (boxID, 'png')
	if image is not None:
		cv.SetImageROI(image, box)
		cv.SaveImage(os.path.join(DefaultWorkingDirectory,imageName), image)
		cv.ResetImageROI(image)
	return imageName

################
# ocr engines
################

def ocr_abbyy(fname):
	return abbyy.DoCloudOCR(fname)

def ocr_tesseract(fileID,fname,workingDirectory):
	output = 'out%s.txt' % fileID
	proc = subprocess.Popen('tesseract %s %s -l eng' % (fname,output), cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
	
	proc.wait()
	return open(os.path.join(workingDirectory,output)).read().strip()
