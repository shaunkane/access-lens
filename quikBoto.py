# knockoff quikturkit using Boto, since quikturkit is broken
from boto.mturk.connection import MTurkConnection
from boto.mturk.question import QuestionForm, ExternalQuestion
import time
import sys
import json
from log import *

class QuikBoto(object):
	def __init__(self):
		self.testing = False
		self.mtc = MTurkConnection(aws_access_key_id=ACCESS_ID, aws_secret_access_key=SECRET_KEY,host=HOST)

	def CreateOCRTask(self):
		title = 'Transcribe simple image - quick'
		description = ('View photographs of simple text (1-3 words) and transcribe it')
		keywords = 'image, transcription'
		q1 = ExternalQuestion('https://umbc-cloud.appspot.com/transcribe?tasks=%d' % numImages,600)
		
		if not self.testing: self.mtc.create_hit(question=q1,
			max_assignments=1,
			title=title,
			description=description,
			keywords=keywords,
			duration = 60*1,
			reward=hitPrice)
		
		logging.debug('Creating HIT')	
	def DeleteAllHits(self):
		logging.debug( 'Disabling hits')
		hits = list(self.mtc.get_all_hits())
		for hit in hits:
			if not self.testing: self.mtc.disable_hit(hit.HITId)
		available = sum([int(h.NumberOfAssignmentsAvailable) for h in hits])
		inProgress = sum([int(h.NumberOfAssignmentsPending) for h in hits])
		transcriptRequest = urllib2.Request(statusUrl)
		status = json.loads(urllib2.urlopen(transcriptRequest).read())
		
		print '%d in progress, %d available, %d seconds since last upload' % (inProgress, available, status['time'])
	
	def GetStatus(self):
		hits = list(self.mtc.get_all_hits())
		available = sum([int(h.NumberOfAssignmentsAvailable) for h in hits])
		inProgress = sum([int(h.NumberOfAssignmentsPending) for h in hits])
		transcriptRequest = urllib2.Request(statusUrl)
		status = json.loads(urllib2.urlopen(transcriptRequest).read())
		imagesToTranscribe = status['cnt'] == 0
		timeSinceTranscript = status['time']
		
		return inProgress, available, imagesToTranscribe, timeSinceTranscript
	
	# get things started
	def StartTasks(self):
		inProgress, available, imagesToTranscribe, timeSinceTranscript = self.GetStatus()
		
		logging.debug( '%d in progress, %d available, %s: images to transcribe, %d seconds since last upload' % (inProgress, available, imagesToTranscribe, timeSinceTranscript) )
		if timeSinceTranscript < 120: # ramp it up
			target = assignmentsPerHit*2
		else:
			target = assignmentsPerHit
		if available < target:
			for i in range(0, assignmentsPerHit):
				self.CreateOCRTask()
	
	# once everything is recognized, shut it down
	def FinishTasks(self):
		inProgress, available, imagesToTranscribe, timeSinceTranscript = self.GetStatus()
		logging.debug( '%d in progress, %d available, %s: images to transcribe, %d seconds since last upload' % (inProgress, available, imagesToTranscribe, timeSinceTranscript) )
		if imagesToTranscribe:
			if timeSinceTranscript < 120: # ramp it up
				target = assignmentsPerHit*2
			else:
				target = assignmentsPerHit
			if available < target:
				for i in range(0, assignmentsPerHit):
					self.CreateOCRTask()
		else:
			self.DeleteAllHits() 
 
ACCESS_ID ='0QTWFA25NHV69QZV7JG2'
SECRET_KEY = 'tA/iP8BAfPeBpOPJhn/NBGpf8CeUaM4PEaEQealS'
#HOST = 'mechanicalturk.sandbox.amazonaws.com'
HOST = 'mechanicalturk.amazonaws.com'

import urllib2
statusUrl = 'http://umbc-cloud.appspot.com/status'

numImages=1
assignmentsPerHit = 20
maxAssignments= 100
hitPrice=0.02
sleepTime=5