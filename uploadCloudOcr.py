# requires (and copied from) http://atlee.ca/software/poster/
# test_client.py
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
import sys
import time

baseUrl = 'http://umbc-cloud.appspot.com'
#baseUrl = 'http://localhost:8081'

if len(sys.argv) < 3:
	print 'Syntax: python post.py [sessionID] [filenames]'
	sys.exit()

sessionID = int(sys.argv[1])
filenames = []

for i in range(2, len(sys.argv)):
	filenames.append(sys.argv[i])

# Register the streaming http handlers with urllib2
register_openers()

# upload each file and get the key
keys = []

index = 0
for fname in filenames:	
	# headers contains the necessary Content-Type and Content-Length
	# datagen is a generator object that yields the encoded parameters
	datagen, headers = multipart_encode({"file": open(fname, "rb")})
	
	# Create the Request object
	request = urllib2.Request('%s/upload?sessionID=%d&index=%d' % (baseUrl,sessionID,index), datagen, headers)
	# Get the key
	key = urllib2.urlopen(request).read()
	keys.append(key)
	index += 1

# return comma separated keys
print ','.join(keys)