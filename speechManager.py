import subprocess, multiprocessing, os
# if windows, we use multiprocessing and the speech api. else we use subprocess.
if os.name == 'nt': import speech

class SpeechManager(object):
	def __init__(self, useQueue = True):
		# keep track of speech processes we generate
		self.speechProcesses = []
		self.queue = []
		self.useQueue = useQueue
	
	def IsSpeaking(self):
		self.speechProcesses = []
		if os.name == 'nt': self.speechProcesses = [p for p in self.speechProcesses if p.poll() is None]
		else: self.speechProcesses = [p for p in self.speechProcesses if p.is_alive()]
		return len(self.speechProcesses) > 0
	
	def Beep(self):
		print '\a'
		
	def Say(self, text, interrupt=False):
		if interrupt and self.IsSpeaking(): # interrupt, or speak simultaneously
			self.StopSpeaking()
		try:
			print 'Speaking: %s' % text
			if os.name == 'nt':
				proc = multiprocessing.Process(target=lambda x: speech.say(x), args=(text,))	
				proc.start()			
				# speech.say(text)
			else:
				proc = subprocess.Popen('say "%s"' % text,shell=True)
			self.speechProcesses.append(proc)
		except e:
			print "Failed to speak: %s" % e
			
	def StopSpeaking(self):
		for p in self.speechProcesses:
			if os.name == 'nt': p.kill()
			else: p.terminate()
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