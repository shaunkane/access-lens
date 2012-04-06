import sys, speech

whatToSay = ' '.join(sys.argv[1:])
speech.say(whatToSay)