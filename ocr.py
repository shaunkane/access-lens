# ocr only
import numpy, os, cv, uuid, subprocess
import abbyy

def ClearOCRTempFiles(workingDirectory='./ocrtemp/', fileTypes = ['txt','tiff','png']):
	for fname in os.listdir(workingDirectory):
		if fname.partition('.')[2] in fileTypes:
			os.unlink(os.path.join(workingDirectory, fname))

# ocr engine is tesseract or abbyy
# cloud fix later if we have time...
def CallOCREngine(fileID, workingDirectory='./ocrtemp/', recognizer = 'tesseract'):
	fname = CreateTempFile(image=None, box=None, fileID=fileID) # just get the name
	
	result = ''
	if recognizer == 'tesseract':
		result = ocr_tesseract(fileID,fname,workingDirectory)
	elif recognizer == 'abbyy':
		result = ocr_abbyy(workingDirectory+fname)
	
	return (result, fileID)

def CreateTempFile(image, box, fileID, workingDirectory='./ocrtemp/'):
	imageName = 'box%d.%s' % (fileID, 'png')
		
	if image is not None:
		cv.SetImageROI(image, box)
		cv.SaveImage(os.path.join(workingDirectory,imageName), image)
		cv.ResetImageROI(image)
	return imageName

################
# ocr engines
################

def ocr_abbyy(fname):
	return abbyy.DoCloudOCR(fname)

def ocr_tesseract(fileID,fname,workingDirectory='./ocrtemp/'):
	output = 'out%s' % fileID
	proc = subprocess.Popen('tesseract %s %s -l eng alphanumeric' % (fname,output), cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
	
	proc.wait()
	return open(os.path.join(workingDirectory,'%s.txt' % output)).read().strip()
