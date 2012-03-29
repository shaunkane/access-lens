from util import Size, Point

# gui settings: for dioptra.py
windowName = 'AccessCam'
bgModelScale = 1
rotate = -90
defaultCamIndex=1
useGestures = False

# video sizes: 2592x1944, 1920x1080, 3648x2736?
sizeSmall = Size(640,480)
sizeLarge = Size(640,480)
sizeHalf = Size(int(sizeLarge.width*bgModelScale), int(sizeLarge.height*bgModelScale))

# document sizes for rectification
DocumentSize = Size(8.5,11.0)
AspectRatios=(Point(8.5,11.),Point(5.,5.),Point(7.5,5.),Point(3.75,8.5))

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
greenHigh = 60