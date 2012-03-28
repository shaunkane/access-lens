import subprocess
if os.name == 'nt': import speech

class SpeechManager(object):
	def __init__(self, useQueue = True):
		# keep track of speech processes we generate
		self.speechProcesses = []
		self.queue = []
		self.useQueue = useQueue
	
	def IsSpeaking(self):
		self.speechProcesses = [p for p in self.speechProcesses if p.poll() is None]
		return len(self.speechProcesses) > 0
	
	def Beep(self):
		print '\a'
		
	def Say(self, text, interrupt=False):
		if interrupt and self.IsSpeaking(): # interrupt, or speak simultaneously
			self.StopSpeaking()
		try:
			print 'Speaking: %s' % text
			if os.name == 'nt':
				speech.say(text)
			else:
				proc = subprocess.Popen('say "%s"' % text,shell=True)
				self.speechProcesses.append(proc)
		except e:
			print "Failed to speak: %s" % e
			
	def StopSpeaking(self):
		for p in self.speechProcesses:
			p.kill()
		self.speechProcesses = []
		self.queue = []
	
	def listen(self, phrases=None):
		if os.name == 'nt':
			text = speech.input(phraselist=phrases)
			return text
		else:
			print 'Speech recognition currently not supported'
			return None

def main(): # test
	s = SpeechManager()
	s.Say('this is a test of the emergency speech system')
	for i in xrange(0,50000):
		print s.IsSpeaking()
	s.StopSpeaking()

if __name__ == "__main__": main()