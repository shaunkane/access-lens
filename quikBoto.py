# knockoff quikturkit using Boto, since quikturkit is broken
from boto.mturk.connection import MTurkConnection
from boto.mturk.question import QuestionForm, ExternalQuestion
import time
import sys
import json
 
ACCESS_ID ='0QTWFA25NHV69QZV7JG2'
SECRET_KEY = 'tA/iP8BAfPeBpOPJhn/NBGpf8CeUaM4PEaEQealS'
#HOST = 'mechanicalturk.sandbox.amazonaws.com'
HOST = 'mechanicalturk.amazonaws.com'

import urllib2
statusUrl = 'http://umbc-cloud.appspot.com/status'


mtc = MTurkConnection(aws_access_key_id=ACCESS_ID,
                      aws_secret_access_key=SECRET_KEY,
                      host=HOST)

numImages=1
assignmentsPerHit = 10
maxWaiting = 10
maxAssignments= 30
hitPrice=0.01
sleepTime=5

def CreateOCRTask():
	title = 'Transcribe simple image - quick'
	description = ('View photographs of simple text (1-3 words) and transcribe it')
	keywords = 'image, transcription'
	q1 = ExternalQuestion('https://umbc-cloud.appspot.com/transcribe?tasks=%d' % numImages,600)
	
	mtc.create_hit(question=q1,
		max_assignments=1,
		title=title,
		description=description,
		keywords=keywords,
		duration = 60*1,
		reward=hitPrice)

def DeleteAllHits():
	print 'Disabling hits'
	hits = list(mtc.get_all_hits())
	for hit in hits:
		mtc.disable_hit(hit.HITId)
	available = sum([int(h.NumberOfAssignmentsAvailable) for h in hits])
	inProgress = sum([int(h.NumberOfAssignmentsPending) for h in hits])
	transcriptRequest = urllib2.Request(statusUrl)
	status = json.loads(urllib2.urlopen(transcriptRequest).read())
	
	print '%d in progress, %d available, %d seconds since last upload' % (inProgress, available, status['time'])

taskStarted = False

def CheckTasks():
	global taskStarted
	hits = list(mtc.get_all_hits())
	available = sum([int(h.NumberOfAssignmentsAvailable) for h in hits])
	inProgress = sum([int(h.NumberOfAssignmentsPending) for h in hits])
	transcriptRequest = urllib2.Request(statusUrl)
	status = json.loads(urllib2.urlopen(transcriptRequest).read())
	
	count = status['cnt']
	if not taskStarted and count == 0:
		print 'Task uploaded'
		taskStarted = True
	elif taskStarted and count > 0:
		print 'Task completed!'
		DeleteAllHits()
		sys.exit()
		
	print '%d in progress, %d available, %d seconds since last upload' % (inProgress, available, status['time'])
	if taskStarted:
		target = maxAssignments
	else:
		target = maxWaiting
	if available < target:
		for i in range(0, assignmentsPerHit):
			CreateOCRTask()

def main():
	if len(sys.argv) == 2 and sys.argv[1] == 'd':
		DeleteAllHits()
	else:
		while True:
			CheckTasks()
			time.sleep(sleepTime)

if __name__ == "__main__":
	main()