# requires (and copied from) http://atlee.ca/software/poster/
# test_client.py
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
import sys
import time

#url = 'http://umbc-cloud.appspot.com/upload'
url = 'http://localhost:8081/upload'


if len(sys.argv) != 2:
	print 'Syntax: python post.py [filename]'
	sys.exit()

fname = sys.argv[1]


# Register the streaming http handlers with urllib2
register_openers()

# Start the multipart/form-data encoding of the file "DSC0001.jpg"
# "image1" is the name of the parameter, which is normally set
# via the "name" parameter of the HTML <input> tag.

# headers contains the necessary Content-Type and Content-Length
# datagen is a generator object that yields the encoded parameters
#datagen, headers = multipart_encode({"file": open(fname, "rb")})

# Create the Request object
#request = urllib2.Request(url, datagen, headers)
# Get the key
#key = urllib2.urlopen(request).read()

key = 'ag5kZXZ-dW1iYy1jbG91ZHILCxIFSW1hZ2UYBQw'

# now, wait for transcription
transcriptRequest = urllib2.Request('http://localhost:8081/getTranscript/%s' % key)

transcript = ''

while transcript == '':
	print '.'
	transcript = urllib2.urlopen(transcriptRequest).read()
	time.sleep(1)

print transcript