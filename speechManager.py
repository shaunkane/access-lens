import subprocess, multiprocessing, os
# if windows, we use espeak: http://espeak.sourceforge.net

class SpeechManager(object):
	def __init__(self, useQueue = True):
		# keep track of speech processes we generate
		self.speechProcesses = []
		self.queue = []
		self.useQueue = useQueue
	
	def IsSpeaking(self):
		self.speechProcesses = []
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
				proc = subprocess.Popen('"C:\Program Files (x86)\eSpeak\command_line\espeak" -v en-us "%s"' % text,shell=True)	
			else:
				proc = subprocess.Popen('say "%s"' % text,shell=True)
			self.speechProcesses.append(proc)
		except Exception as e:
			print "Failed to speak: %s" % e
			
	def StopSpeaking(self):
		for p in self.speechProcesses:
			p.terminate()
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