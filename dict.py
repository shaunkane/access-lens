import collections

WordMatch = collections.namedtuple('WordMatch', 'word MSD frequency')

class DictionaryManager(object):
	def __init__(self, dictFile, userDictFile, maxDistance=2, verbose=False):
		print 'Loading dictionary'
		self.dictionary = Dictionary(dictFile, listHasFrequencies=True)
		self.userDict = Dictionary(userDictFile, frequency=1000000)
		self.maxDistance = maxDistance
		self.verbose = verbose
		print 'Dictionary loaded'
	
	# we consider a word correctable if:
	# it's in one of our dicts OR it's at least 3 characters
	def WordIsCorrectable(self, word):
		return len(word) > 2

	def WordInDictionary(self, word):
		return self.dictionary.Contains(word) or self.userDict.Contains(word)
	
	def BestMatch(self, word, maxDistance=None):
		if maxDistance is None: maxDistance = self.maxDistance
		dictWord = self.dictionary.BestMatch(word, minLength = len(word)-maxDistance, 
													maxLength = len(word)+maxDistance)
		userWord = self.userDict.BestMatch(word, minLength = len(word)-maxDistance, 
													maxLength = len(word)+maxDistance)
		matches = []
		if dictWord is not None and dictWord.MSD <= maxDistance: matches.append(dictWord)
		if userWord is not None and userWord.MSD <= maxDistance: matches.append(userWord)
		
		if len(matches) == 0:
			return None
		elif len(matches) == 1:
			return matches[0]
		else:
			return min(matches, key = lambda m: (m.MSD, -m.frequency))
	
	def CorrectPhrase(self, phrase, verbose=False):
		words = phrase.split()
		correctWords = []
		for word in words:
			word = word.rstrip('\'"?,.!')
			if self.WordInDictionary(word):
				correctWords.append(word)
			elif self.WordIsCorrectable(word):
				match = self.BestMatch(word)
				if match is not None:
					correctWords.append(match.word)
				else:
					correctWords.append(None)
			else:
				correctWords.append(None)
	
		if not self.verbose:
			correctedPhrase = [w for w in correctWords if w is not None]
		else:
			correctedPhrase = []
			for w in correctWords:
				if w is not None: correctedPhrase.append(w)
				else: correctedPhrase.append('...')

		if len(correctedPhrase) == 0: 
			result = None
		elif not self.verbose or len(correctedPhrase) == len(words): # we corrected all the words
			result = ' '.join(correctedPhrase)
		else: # some unknown words
			result = ' '.join(correctedPhrase) + ' (missing words)'

		if verbose and result is not None: print '%s => %s' % (phrase,result)
		return result
		
				
class Dictionary(object):
	def __init__(self, fileName, listHasFrequencies=False, frequency=None):
		self.words = []
		self.wordDict = {}
		self.wordsOfLength = {}
		for word in file(fileName, 'r'):
			word = word.strip().lower()
			if listHasFrequencies:
				word, freq = word.split(' ')
				freq = int(freq)
			else:
				freq = 1
			if frequency != None: freq = frequency
			self.words.append(word)
			self.wordDict[word] = freq
			if not self.wordsOfLength.has_key(len(word)):
				self.wordsOfLength[len(word)] = [word]
			else:
				self.wordsOfLength[len(word)].append(word)
		print 'Loaded %d dictionary items' % len(self.words)

	def Contains(self, word):
		return self.wordDict.has_key(word)

	def BestMatch(self, word, minLength=None, maxLength=None):
		if minLength is None: minLength = 0
		if maxLength is None: maxLength = max(self.wordsOfLength.keys())
		matches = []
		for length in xrange(minLength, maxLength+1):
			if self.wordsOfLength.has_key(length):
				matchWord = min(self.wordsOfLength[length], key = lambda w: (MSD(w, word), -self.wordDict[w]))
				matches.append(WordMatch(matchWord, MSD(word, matchWord), self.wordDict[matchWord]))
		return (min(matches, key = lambda m: (m.MSD, -m.frequency)) 
				if len(matches) > 0 else None)
	

#cribbed from http://hetland.org/coding/python/levenshtein.py
def MSD(a,b):
    n, m = len(a), len(b)
    if n > m: # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

if __name__=="__main__":
    from sys import argv
    print MSD(argv[1],argv[2])