import subprocess, multiprocessing, os, sys
# if windows, we use espeak: http://espeak.sourceforge.net

if os.name == 'nt': import sapi

class SpeechManager(object):
	def __init__(self, useQueue = True):
		# keep track of speech processes we generate
		self.speechProcesses = []
		self.queue = []
		self.useQueue = useQueue
	
	def Beep(self):
		print '\a'
		
	def Say(self, text, interrupt=True, block=False):
		if interrupt: # interrupt, or speak simultaneously
			self.StopSpeaking()
		try:
			print 'Speaking: %s' % text
			if os.name == 'nt':
				if block: proc = subprocess.call('"C:\Program Files\eSpeak\command_line\espeak" -v en-us "%s"' % text,shell=True)
				else: 
					proc = subprocess.Popen('"C:\Program Files\eSpeak\command_line\espeak" -v en-us "%s"' % text,shell=False)	
					self.speechProcesses.append(proc)
			else:
				if block: proc = subprocess.call('say "%s"' % text,shell=True)
				else:
					proc = subprocess.Popen('say "%s"' % text,shell=True)
					self.speechProcesses.append(proc)
		except Exception as e:
			print "Failed to speak: %s" % e
			
	def StopSpeaking(self):
		for p in self.speechProcesses:
			try:
				p.terminate()
			except Exception:
				pass # whoops
			#terminate_process(p.pid)
		self.speechProcesses = []
	
	def listen(self, phrases, timeout=10):
		if os.name == 'nt':
			text = sapi.listenForWords(phrases, timeout)
			return text
		else:
			print 'Speech recognition currently not supported on Mac'
			return None

# http://stackoverflow.com/questions/1064335/in-python-2-5-how-do-i-kill-a-subprocess
def terminate_process(pid):
	# all this is because we are stuck with Python 2.5 and we cannot use Popen.terminate()
	if os.name == 'nt':
		import ctypes
		PROCESS_TERMINATE = 1
		handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
		ctypes.windll.kernel32.TerminateProcess(handle, -1)
		ctypes.windll.kernel32.CloseHandle(handle)
		print 'killed %d' % pid
	else:
		os.kill(pid, signal.SIGKILL)

if __name__ == "__main__":
	s = SpeechManager()
	s.Say('this is a test of the emergency speech system')
	s.StopSpeaking()