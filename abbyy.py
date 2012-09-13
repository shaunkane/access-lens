# my hacked version
#!/usr/bin/python
# Usage: recognize.py <input file> <output file> [-language <Language>] [-pdf|-txt|-rtf|-docx|-xml]

import argparse, base64, getopt, MultipartPostHandler, os, re, sys, time, urllib2, urllib, xml.dom.minidom
import StringIO
import xml.etree.ElementTree as ET

class Task:
	Status = "Unknown"
	Id = None
	DownloadUrl = None
	def IsActive( self ):
		if self.Status == "InProgress" or self.Status == "Queued": return True
		else: return False

class AbbyyOnlineSdk:
	ServerUrl = "http://cloud.ocrsdk.com/"
	ApplicationId = "AccessLensTest"
	Password = "KEvprOeZEVQEtlq/1NgBSR2Q"
	Proxy = None
	enableDebugging = 0

	def ProcessImage( self, filePath ): # whole page
		urlParams = urllib.urlencode({"language" : settings.Language, "exportFormat" : settings.OutputFormat})
		requestUrl = self.ServerUrl + "processImage?" + urlParams
		bodyParams = { "file" : open( filePath, "rb" )  }
		request = urllib2.Request( requestUrl, None, self.buildAuthInfo() )
		response = self.getOpener().open(request, bodyParams).read()
		if response.find( '<Error>' ) != -1 : return None
		# Any response other than HTTP 200 means error - in this case exception will be thrown
		# parse response xml and extract task ID
		task = self.DecodeResponse( response )
		return task

	def ProcessTextField( self, filePath ):
		requestUrl = self.ServerUrl + "processTextField?"
		bodyParams = { "file" : open( filePath, "rb" )  }
		request = urllib2.Request( requestUrl, None, self.buildAuthInfo() )
		response = self.getOpener().open(request, bodyParams).read()
		if response.find( '<Error>' ) != -1 : return None
		# parse response xml and extract task ID
		task = self.DecodeResponse( response )
		return task

	def GetTaskStatus( self, task ):
		urlParams = urllib.urlencode( { "taskId" : task.Id } )
		statusUrl = self.ServerUrl + "getTaskStatus?" + urlParams
		request = urllib2.Request( statusUrl, None, self.buildAuthInfo() )
		response = self.getOpener().open( request ).read()
		task = self.DecodeResponse( response )
		return task

	def DownloadResult( self, task, outputPath ):
		getResultParams = urllib.urlencode( { "taskId" : task.Id } )
		getResultUrl = self.ServerUrl + "getResult?" + getResultParams
		request = urllib2.Request( getResultUrl, None, self.buildAuthInfo() )
		fileResponse = self.getOpener().open( request ).read()
		resultFile = open( outputPath, "wb" )
		resultFile.write( fileResponse )

	def DownloadResultXML(self, task):
		getResultParams = urllib.urlencode( { "taskId" : task.Id } )
		getResultUrl = self.ServerUrl + "getResult?" + getResultParams
		request = urllib2.Request( getResultUrl, None, self.buildAuthInfo() )
		fileResponse = self.getOpener().open( request ).read()
		resultFile = StringIO.StringIO()
		resultFile.write( fileResponse )
		return resultFile.getvalue()

	def DecodeResponse( self, xmlResponse ):# """ Decode xml response of the server. Return Task object """
		dom = xml.dom.minidom.parseString( xmlResponse )
		taskNode = dom.getElementsByTagName( "task" )[0]
		task = Task()
		task.Id = taskNode.getAttribute( "id" )
		task.Status = taskNode.getAttribute( "status" )
		if task.Status == "Completed": task.DownloadUrl = taskNode.getAttribute( "resultUrl" )
		return task

	def buildAuthInfo( self ):
		return { "Authorization" : "Basic %s" % base64.encodestring( "%s:%s" % (self.ApplicationId, self.Password) ) }

	def getOpener( self ):
		if self.Proxy == None: self.opener = urllib2.build_opener( MultipartPostHandler.MultipartPostHandler,urllib2.HTTPHandler(debuglevel=self.enableDebugging))
		else: self.opener = urllib2.build_opener(self.Proxy, MultipartPostHandler.MultipartPostHandler,urllib2.HTTPHandler(debuglevel=self.enableDebugging))
		return self.opener

def DoCloudOCR(fname):
	processor = AbbyyOnlineSdk() 
	task = processor.ProcessTextField(fname)
	while True: # wait for task
		task = processor.GetTaskStatus(task)
		if task.IsActive() == False: break
		time.sleep(1)
	if task.DownloadUrl != None:
		xml = processor.DownloadResultXML(task)
		root = ET.fromstring(xml)
		try:
			text = root.find('{@link}field').find('{@link}value').text
			return text
		except Exception:
			return ''
	else: return ''


# main	
if __name__ == "__main__":
	# filename
	fname = sys.argv[1]
	print DoCloudOCR(fname)