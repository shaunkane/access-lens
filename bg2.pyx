# python wrapper
import numpy, cv

def FindBackground(frame, bg, model, update=1, doCleanup=False, findShadow=0):
	_FindBackground(numpy.asarray(cv.GetMat(frame)), numpy.asarray(cv.GetMat(bg)), model, bg.width, bg.height, update=update, findShadow=findShadow) 
	if doCleanup:
		cv.MorphologyEx(bg,bg,None,None,cv.CV_MOP_OPEN,3)
		#cv.MorphologyEx(bg,bg,None,None,cv.CV_MOP_CLOSE,2)

def FindSkin(ycc, bg, doCleanup=False, showMaybeSkin=False):
	cv.Zero(bg)
	_FindSkin(numpy.asarray(cv.GetMat(ycc)), numpy.asarray(cv.GetMat(bg)), bg.width, bg.height, (1 if showMaybeSkin else 0))
	if doCleanup:
		cv.MorphologyEx(bg,bg,None,None,cv.CV_MOP_OPEN,2)
		#cv.MorphologyEx(bg,bg,None,None,cv.CV_MOP_CLOSE,2)
		
# cython stuff
cimport numpy
cimport cython

cdef extern from "math.h":
	cdef double sqrt(double x) nogil

cdef extern from "stdlib.h":
	cdef void free(void* ptr)
	cdef void* malloc(size_t size)

ctypedef struct Mode:
	double variance, muB, muG, muR, weight
	double varR, varG, varB # used for shadow mode only

cdef class BackgroundModel:
	cdef Mode *modes
	cdef int *numModesInUse
	cdef public int width, height, maxModes, trackShadowComponents, yccMode
	cdef public float backgroundCover, fitThreshold, defaultVariance, defaultAlpha, shadowMaxDarken, shadowColorDiff, yThreshold
	
	def __init__(self, int width, int height, int maxModes=3, float backgroundCover=0.75, float fitThreshold=9.0, float defaultVariance=36.0, float alpha=0.05, float shadowColorDiff=20.0, float shadowMaxDarken=0.8, int trackShadowComponents = 1, float yThreshold = 20, int yccMode=0):
		self.modes = <Mode*>malloc(sizeof(Mode)*width*height*maxModes)
		self.numModesInUse = <int*>malloc(sizeof(int)*width*height)
		self.width = width
		self.height = height
		self.maxModes = maxModes
		self.backgroundCover = backgroundCover
		self.fitThreshold = fitThreshold
		self.defaultVariance = defaultVariance
		self.defaultAlpha = alpha
		self.shadowColorDiff = shadowColorDiff
		self.shadowMaxDarken = shadowMaxDarken
		self.yThreshold = yThreshold
		self.yccMode = yccMode
		self.trackShadowComponents = trackShadowComponents # if this is on, update varR,G,B so we can do shadow detection
		self.Reset()

	def __dealloc__(self):
		free(self.modes)
		free(self.numModesInUse)
		
	cpdef Reset(self):
		cdef int i
		for 0 <= i < self.width*self.height:
			self.numModesInUse[i] = 0
		for 0 <= i < self.width*self.height*self.maxModes:
			self.modes[i].weight = 0
			self.modes[i].variance = 0
			self.modes[i].muR = 0
			self.modes[i].muG = 0
			self.modes[i].muB = 0
			
			if self.trackShadowComponents:
				self.modes[i].varR = 0
				self.modes[i].varG = 0
				self.modes[i].varB = 0

# modes
cdef short FOREGROUND, BACKGROUND, SHADOW, SKIN, MAYBE_SKIN
FOREGROUND = 255
BACKGROUND = 0
SHADOW = 0
SKIN = 255
MAYBE_SKIN = 0

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef float CalculateSignificants(Mode mode) nogil:
	return mode.weight / sqrt(mode.variance)

# skin detection
# Y > 80 & 85 < Cb < 135 & 135 < Cr < 180 
# from http://stackoverflow.com/questions/5089704/skin-detection-in-the-yuv-color-space
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef _FindSkin(numpy.ndarray[numpy.uint8_t, ndim=3] ycc, numpy.ndarray[numpy.uint8_t, ndim=2] bg, int width, int height, int showMaybeSkin): # update bg and mark skin pixels
	cdef int x, y
	cdef int yy, cr, cb

	with nogil:
		for 0 <= x < width:
			for 0 <= y < height:
				yy = ycc[y,x,0]
				cr = ycc[y,x,1]
				cb = ycc[y,x,2]
				# changed from 80 to 50
				if yy > 80 and cb > 85 and cb < 135 and cr > 135 and cr < 180:
					bg[y,x] = SKIN
				elif showMaybeSkin == 1 and yy > 80 and cb > 80 and cb < 140 and cr > 130 and cr < 185:
					bg[y,x] = MAYBE_SKIN
	
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef _FindBackground(numpy.ndarray[numpy.uint8_t, ndim=3] im, numpy.ndarray[numpy.uint8_t, ndim=2] bg, BackgroundModel model, int width, int height, int update=1, int findShadow=0, int findSkin=0):
	cdef int x, y
	cdef double bgSum
	cdef int i, j, numBackgroundModes, startOfModes, maxModes
	cdef int b, g, r
	cdef double alpha
	cdef int matchedMode
	cdef double dist, dB, dG, dR, k, sigma, totalWeight
	cdef double a, c
	cdef double muR, muG, muB, varR, varG, varB, sdR, sdG, sdB
	#if True:
	with nogil:
		for 0 <= x < width:
			for 0 <= y < height:
				bg[y,x] = FOREGROUND
					
				maxModes = model.maxModes
				alpha = model.defaultAlpha
			
				startOfModes = (x+y*width)*maxModes
				
				b = im[y,x,0]
				g = im[y,x,1]
				r = im[y,x,2]
				
				# how many gaussians should be in the background? enough to sum to backgroundCover
				bgSum = 0
				numBackgroundModes = 0
				
				for startOfModes <= i < startOfModes+model.numModesInUse[x+y*width]:
					if bgSum < model.backgroundCover:
						bgSum += model.modes[i].weight
						numBackgroundModes += 1
					else: break
					
				# look for matches
				matchedMode = -1
			
				for startOfModes <= i < startOfModes+model.numModesInUse[x+y*width]:
					# did we find a match yet? if not, keep looking
					if matchedMode == -1:
						dB = model.modes[i].muB - b
						dG = model.modes[i].muG - g
						dR = model.modes[i].muR - r
						dist = dR*dR+dG*dG+dB*dB if model.yccMode == 0 else dR*dR+dG*dG
					
						if dist < model.modes[i].variance*model.fitThreshold and (model.yccMode == 0 or dB**2 < model.yThreshold**2): #match
							matchedMode = i
							if i < startOfModes+numBackgroundModes: bg[y,x] = BACKGROUND
						
							if update == 1: # update parameters
								k = alpha / model.modes[i].weight
								model.modes[i].weight = model.modes[i].weight*(1-alpha)+alpha
								model.modes[i].muB -= k*dB
								model.modes[i].muG -= k*dG
								model.modes[i].muR -= k*dR
								sigma = model.modes[i].variance + k*(dist-model.modes[i].variance)
								# for reasons i do not understand here we're bounding the
								# new variance between 4 and 5*our initial variance
								if sigma < 4: sigma = 4
								if sigma > 5*model.defaultVariance: 
									sigma = 5*model.defaultVariance
								model.modes[i].variance = sigma
								
								if model.trackShadowComponents == 1: # might be faster off, but needs to be on for shadows to work
									model.modes[i].varR += k*(dB*dB-model.modes[i].varR)
									model.modes[i].varG += k*(dB*dB-model.modes[i].varG)
									model.modes[i].varB += k*(dB*dB-model.modes[i].varB)
								
								# this mode went up, so does it move up in the ranking?
								j = i-1
								while j >= startOfModes:
									if CalculateSignificants(model.modes[j+1]) > CalculateSignificants(model.modes[j]):
										model.modes[j], model.modes[j+1] = model.modes[j+1], model.modes[j] #swap
										j -= 1
									else: break
								
						elif model.trackShadowComponents == 1 and findShadow == 1 and model.yccMode == 0: # check for shadow
							muR = model.modes[i].muR
							muG = model.modes[i].muG
							muB = model.modes[i].muB
							varR = model.modes[i].varR
							varG = model.modes[i].varG
							varB = model.modes[i].varB
							sdR = sqrt(varR)
							sdG = sqrt(varG)
							sdB = sqrt(varB)
							
							a = (r*muR/varR+g*muG/varG+b*muB/varB) / (muR/sdR*muR/sdR+muG/sdG*muG/sdG+muB/sdB*muB/sdB)
							c = sqrt((r-a*muR)/sdR*(r-a*muR)/sdR*(g-a*muG)/sdG*(g-a*muG)/sdG*(b-a*muB)/sdB*(b-a*muB)/sdB)
							if a < 1 and a > model.shadowMaxDarken and c < model.shadowColorDiff:
								matchedMode = i
								bg[y,x] = SHADOW
			
					if i != matchedMode and update == 1: # not a match, scale the weight down
						model.modes[i].weight *= (1-alpha)
						if model.modes[i].weight < 0.0: # remove this mode
							model.modes[i].weight = 0
							model.numModesInUse[x+y*width] -= 1
					
				# if we didn't find a match, add a new mode
				if matchedMode == -1 and update == 1:
					if model.numModesInUse[x+y*width] < maxModes: 
						model.numModesInUse[x+y*width] += 1
			
					# whether we added a removed an old node or not, the new one is at index i
					i = startOfModes+model.numModesInUse[x+y*width]-1
					model.modes[i].muB = b
					model.modes[i].muG = g
					model.modes[i].muR = r
					model.modes[i].variance = model.defaultVariance

					if model.trackShadowComponents == 1:
						model.modes[i].varR = model.defaultVariance
						model.modes[i].varG = model.defaultVariance
						model.modes[i].varB = model.defaultVariance
					
					if model.numModesInUse[x+y*width] == 1:
						model.modes[i].weight = 1
					else:
						model.modes[i].weight = alpha
						# this mode went up, so does it move up in the ranking?
						j = i-1
						while j >= startOfModes:
							if CalculateSignificants(model.modes[j+1]) > CalculateSignificants(model.modes[j]):
								model.modes[j], model.modes[j+1] = model.modes[j+1], model.modes[j] #swap
								j -= 1
							else: break
				
				# normalize weights
				if update == 1:
					totalWeight = 0
					for startOfModes <= i < startOfModes+model.numModesInUse[x+y*width]:
						totalWeight += model.modes[i].weight
					for startOfModes <= i < startOfModes+model.numModesInUse[x+y*width]:
						model.modes[i].weight *= 1.0/totalWeight