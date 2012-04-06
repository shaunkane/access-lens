# requires (and copied from) http://atlee.ca/software/poster/
# test_client.py
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
import sys
import time

baseUrl = 'http://umbc-cloud.appspot.com'
#baseUrl = 'http://localhost:8081'


if len(sys.argv) != 2:
	print 'Syntax: python post.py [cloudKey]'
	sys.exit()

cloudKey = sys.argv[1]

# Register the streaming http handlers with urllib2
register_openers()

# now, wait for transcription
transcriptRequest = urllib2.Request('%s/getTranscript/%s' % (baseUrl,cloudKey))

transcript = ''

while transcript == '':
	transcript = urllib2.urlopen(transcriptRequest).read()
	time.sleep(1)

print transcript