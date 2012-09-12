# listening comes from http://www.surguy.net/articles/speechrecognition.xml
# and http://code.google.com/p/simonsays/

from win32com.client import gencache, constants
gencache.EnsureModule('{C866CA3A-32F7-11D2-9602-00C04F8EE628}', 0, 5, 4)
import win32com.client
import pythoncom, time

# timeout in seconds. default is one minute
def listenForWords(words, timeout=60):
	listener = win32com.client.Dispatch("SAPI.SpInProcRecognizer")
	listener.AudioInputStream = win32com.client.Dispatch("SAPI.SpMMAudioIn")
	context = listener.CreateRecoContext()
	grammar = context.CreateGrammar()
		
	# recognize the words in the grammar only
	grammar.DictationSetState(0)
		
	# Create a new rule for the grammar, that is top level (so it begins
	# a recognition) and dynamic (ie we can change it at runtime)
	wordsRule = grammar.Rules.Add("wordsRule", constants.SRATopLevel + constants.SRADynamic, 0)
	for word in words: wordsRule.InitialState.AddWordTransition(None, word)
		
	# Set the wordsRule to be active
	grammar.Rules.Commit()
	grammar.CmdSetRuleState("wordsRule", 1)
		
	# Commit the changes to the grammar
	grammar.Rules.Commit()
		
	# And add an event handler that's called back when recognition occurs
	eventHandler = EventHandler(context)
	startTime = time.time()
	while time.time() - startTime < timeout:
		pythoncom.PumpWaitingMessages()
		if hasattr(eventHandler, 'result'): 
			return eventHandler.result
	return None
	
class EventHandler(win32com.client.getevents("SAPI.SpSharedRecoContext")):
	def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
		newResult = win32com.client.Dispatch(Result)
		word = newResult.PhraseInfo.GetText().lower()
		self.result = word

if __name__=='__main__':
	words = [ "one","two","three","four" ]
	print 'listening for ', words
	print listenForWords(words) 
