from util import X,Y,WIDTH,HEIGHT

# gui settings: for dioptra.py
windowName = 'AccessCam'
bgModelScale = 1
rotate = -90
defaultCamIndex=0
dwell_time = 60 # in frames

# video sizes: 2592x1944, 1920x1080, 3648x2736?
sizeSmall = (640,480)
sizeLarge = (800,600)
sizeHalf = (int(sizeLarge[X]*bgModelScale), int(sizeLarge[Y]*bgModelScale))

# document sizes for rectification
DocumentSize = (8.5,11.0)
AspectRatios=((8.5,11.),(5.,5.),(7.5,5.),(3.75,8.5))

# files
dictFile = 'dict/wordfreq.txt'
userDictFile = 'dict/userdict.txt'
savedAreaFile = 'areas.json'

# ocr params
BoxAspectThresh = 0
DilateSteps = 2
WindowSize = 4

# color tracking variables for the green thing. tweak to track different greens
greenLow = 40
greenHigh = 70