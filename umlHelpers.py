"""
Helper functions for any functions defined in uml.py

They are separated here so that that (most) top level
user facing functions are contained in uml.py without
the distraction of helpers

"""

import inspect
import numpy
import scipy.io
import os.path
import re 
import datetime
import random
import copy

import UML
from UML.exceptions import ArgumentException, ImproperActionException
from UML.data import Sparse
from UML.data import Matrix
from UML.data import List
from UML.data import Base


def findBestInterface(package):
	"""
	Takes the name of a possible interface provided to some other function by
	a UML user, and attempts to find the interface which best matches that name
	amoung those available. If it does not match any available interfaces, then
	an exception is thrown.
	
	"""
	for interface in UML.interfaces.available:
		if package == interface.getCanonicalName():
			return interface
	for interface in UML.interfaces.available:
		if interface.isAlias(package):
			return interface

	raise ArgumentException("package '" + package +"' was not associated with any of the available package interfaces")


def _learnerQuery(name, queryType):
	"""
	Takes a string of the form 'package.learnerName' and a string defining
	a queryType of either 'parameters' or 'defaults' then returns the results
	of either the package's getParameters(learnerName) function or the
	package's getDefaultValues(learnerName) function.

	"""
	[package, learnerName] = name.split('.')

	if queryType == "parameters":
		toCallName = 'getLearnerParameterNames'
	elif queryType == 'defaults':
		toCallName = 'getLearnerDefaultValues'
	else:
		raise ArgumentException("Unrecognized queryType: " + queryType)

	interface = findBestInterface(package)
	return getattr(interface, toCallName)(learnerName)


def _loadSparse(data, featureNames, fileType, automatedRetType=False):
	if fileType is None:
		return Sparse(data, featureNames)

	# since file type is not None, that is an indicator that we must read from a file
	path = data
	tempFeatureNames = None
	if fileType == 'csv':
		(data, tempFeatureNames) = _loadCSVtoMatrix(path)
	elif fileType == 'mtx':
		(data, tempFeatureNames) = _loadMTXtoAuto(path)
	else:
		raise ArgumentException("Unrecognized file type")

	if tempFeatureNames is not None:
			featureNames = tempFeatureNames

	# if we allow the return type to be chosen by the data, and the scipy's mmread
	# (as wrapped by loadMTXtoAuto) returns a dense matrix, then we want to return
	# a Matrix object
	if automatedRetType and not scipy.sparse.issparse(data):
		return Matrix(data, featureNames)

	return Sparse(data, featureNames, os.path.basename(path), path)


def _loadMatrix(data, featureNames, fileType, automatedRetType=False):
	if fileType is None:
		return Matrix(data, featureNames)

	# since file type is not None, that is an indicator that we must read from a file
	path = data
	tempFeatureNames = None
	if fileType == 'csv':
		(data, tempFeatureNames) = _loadCSVtoMatrix(path, automatedRetType)
	elif fileType == 'mtx':
		(data, tempFeatureNames) = _loadMTXtoAuto(path)
	else:
		raise ArgumentException("Unrecognized file type")

	if tempFeatureNames is not None:
			featureNames = tempFeatureNames

	# if we allow the return type to be chosen by the data, and the scipy's mmread
	# (as wrapped by loadMTXtoAuto) returns a sparse matrix, then we want to return
	# a Sparse object
	if automatedRetType and scipy.sparse.issparse(data):
		return Sparse(data, featureNames)

	return Matrix(data, featureNames, os.path.basename(path), path)


def _loadList(data, featureNames, fileType):
	if fileType is None:
		return List(data, featureNames)

	# since file type is not None, that is an indicator that we must read from a file
	path = data
	tempFeatureNames = None
	if fileType == 'csv':
		(data, tempFeatureNames) =_loadCSVtoList(data)
	elif fileType == 'mtx':
		(data, tempFeatureNames) = _loadMTXtoAuto(data)
	else:
		raise ArgumentException("Unrecognized file type")

	# if we load from file, we assume that data will be read; feature names may not
	# be, thus we check
	if tempFeatureNames is not None:
			featureNames = tempFeatureNames

	return List(data, featureNames, os.path.basename(path), path)

def _loadCSVtoMatrix(path, automatedRetType=False):
	inFile = open(path, 'rU')
	firstLine = inFile.readline()
	featureNames = None
	skip_header = 0

	# test if this is a line defining featureNames
	if firstLine[0] == "#":
		# strip '#' from the begining of the line
		scrubbedLine = firstLine[1:]
		# strip newline from end of line
		scrubbedLine = scrubbedLine.rstrip()
		featureNames = scrubbedLine.split(',')
		skip_header = 1

	# check the types in the first data containing line.
	line = firstLine
	while (line == "") or (line[0] == '#'):
		line = inFile.readline()
	lineList = line.split(',')
	for datum in lineList:
		try:
			num = numpy.float(datum)
		except ValueError:
			# if the data contains non numerical values, and we allow the automated
			# choice of the return type, then we should try to load this data
			# as a List
			if automatedRetType:
				return _loadCSVtoList(path)
			raise ValueError("Cannot load a file with non numerical typed columns")

	inFile.close()

	data = numpy.genfromtxt(path, delimiter=',', skip_header=skip_header)
	if len(data.shape) == 1:
		data = numpy.matrix(data)
	return (data, featureNames)

def _loadMTXtoAuto(path):
	"""
	Uses scipy helpers to read a matrix market file; returning whatever is most
	appropriate for the file. If it is a matrix market array type, a numpy
	dense matrix is returned as data, if it is a matrix market coordinate type, a
	sparse scipy coo_matrix is returned as data. If featureNames are present,
	they are also read.

	"""
	inFile = open(path, 'rU')
	featureNames = None

	# read through the comment lines
	while True:
		currLine = inFile.readline()
		if currLine[0] != '%':
			break
		if len(currLine) > 1 and currLine[1] == "#":
			# strip '%#' from the begining of the line
			scrubbedLine = currLine[2:]
			# strip newline from end of line
			scrubbedLine = scrubbedLine.rstrip()
			featureNames = scrubbedLine.split(',')

	inFile.close()

	data = scipy.io.mmread(path)
	return (data, featureNames)

def _intFloatOrString(inString):
	ret = inString
	try:
		ret = int(inString)
	except ValueError:
		ret = float(inString)
	# this will return an int or float if either of the above two are successful
	finally:
		if ret == "":
			return None
		return ret

def _defaultParser(line):
	"""
	When given a comma separated value line, it will attempt to convert
	the values first to int, then to float, and if all else fails will
	keep values as strings. Returns list of values.

	"""
	ret = []
	lineList = line.split(',')
	for entry in lineList:
		ret.append(_intFloatOrString(entry))
	return ret


def _loadCSVtoList(path):
	inFile = open(path, 'rU')
	firstLine = inFile.readline()
	featureNameList = None

	# test if this is a line defining featureNames
	if firstLine[0] == "#":
		# strip '#' from the begining of the line
		scrubbedLine = firstLine[1:]
		# strip newline from end of line
		scrubbedLine = scrubbedLine.rstrip()
		featureNameList = scrubbedLine.split(',')
		featureNameMap = {}
		for name in featureNameList:
			featureNameMap[name] = featureNameList.index(name)
	#if not, get the iterator pointed back at the first line again	
	else:
		inFile.close()
		inFile = open(path, 'rU')

	#list of datapoints in the file, where each data point is a list
	data = []
	for currLine in inFile:
		currLine = currLine.rstrip()
		#ignore empty lines
		if len(currLine) == 0:
			continue

		data.append(_defaultParser(currLine))

	if featureNameList == None:
		return (data, None)

	inFile.close()

	return (data, featureNameMap)



def countWins(predictions):
	"""
	Count how many contests were won by each label in the set.  If a class label doesn't
	win any predictions, it will not be included in the results.  Return a dictionary:
	{classLabel: # of contests won}
	"""
	predictionCounts = {}
	for prediction in predictions:
		if prediction in predictionCounts:
			predictionCounts[prediction] += 1
		else:
			predictionCounts[prediction] = 1

	return predictionCounts

def extractWinningPredictionLabel(predictions):
	"""
	Provided a list of tournament winners (class labels) for one point/row in a test set,
	choose the label that wins the most tournaments.  Returns the winning label.
	"""
	#Count how many times each class won
	predictionCounts = countWins(predictions)

	#get the class that won the most tournaments
	#TODO: what if there are ties?
	return max(predictionCounts.iterkeys(), key=(lambda key: predictionCounts[key]))


def extractWinningPredictionIndex(predictionScores):
	"""
	Provided a list of confidence scores for one point/row in a test set,
	return the index of the column (i.e. label) of the highest score.  If
	no score in the list of predictionScores is a number greater than negative
	infinity, returns None.  
	"""

	maxScore = float("-inf")
	maxScoreIndex = -1
	for i in range(len(predictionScores)):
		score = predictionScores[i]
		if score > maxScore:
			maxScore = score
			maxScoreIndex = i

	if maxScoreIndex == -1:
		return None
	else:
		return maxScoreIndex

def extractWinningPredictionIndexAndScore(predictionScores, featureNamesInverse):
	"""
	Provided a list of confidence scores for one point/row in a test set,
	return the index of the column (i.e. label) of the highest score.  If
	no score in the list of predictionScores is a number greater than negative
	infinity, returns None.  
	"""
	allScores = extractConfidenceScores(predictionScores, featureNamesInverse)

	if allScores is None:
		return None
	else:
		return allScores[0]


def extractConfidenceScores(predictionScores, featureNamesInverse):
	"""
	Provided a list of confidence scores for one point/row in a test set,
	return an ordered list of (label, score) tuples.  List is ordered
	by score in descending order.
	"""

	if predictionScores is None or len(predictionScores) == 0:
		return None

	scoreMap = {}
	for i in range(len(predictionScores)):
		score = predictionScores[i]
		label = featureNamesInverse[i]
		scoreMap[label] = score

	return scoreMap


#TODO this is a helper, move to utilities package?
def copyLabels(dataSet, dependentVar):
	"""
		A helper function to simplify the process of obtaining a 1-dimensional matrix of class
		labels from a data matrix.  Useful in functions which have an argument that may be
		a column index or a 1-dimensional matrix.  If 'dependentVar' is an index, this function
		will return a copy of the column in 'dataSet' indexed by 'dependentVar'.  If 'dependentVar'
		is itself a column (1-dimensional matrix w/shape (nx1)), dependentVar will be returned.

		dataSet:  matrix containing labels and, possibly, features.  May be empty if 'dependentVar'
		is a 1-column matrix containing labels.

		dependentVar: Either a column index indicating which column in dataSet contains class labels,
		or a matrix containing 1 column of class labels.

		returns A 1-column matrix of class labels
	"""
	if isinstance(dependentVar, Base):
		#The known Indicator argument already contains all known
		#labels, so we do not need to do any further processing
		labels = dependentVar
	elif isinstance(dependentVar, (str, unicode, int)):
		#known Indicator is an index; we extract the column it indicates
		#from knownValues
		labels = dataSet.copyFeatures([dependentVar])
	else:
		raise ArgumentException("Missing or improperly formatted indicator for known labels in computeMetrics")

	return labels




def applyCodeVersions(functionTextList, inputHash):
	"""applies all the different various versions of code that can be generated from functionText to each of the variables specified in inputHash, where
	data is plugged into the variable with name inputVariableName. Returns the result of each application as a list.
	functionTextList is a list of text objects, each of which defines a python function
	inputHash is of the form {variable1Name:variable1Value, variable2Name:variable2Value, ...}
	"""
	results = []
	for codeText in functionTextList:
		results.append(executeCode(codeText, inputHash))
	return results



def executeCode(code, inputHash):
	"""Execute the given code stored as text in codeText, starting with the variable values specified in inputHash
	This function assumes the code consists of EITHER an entire function definition OR a single line of code with
	statements seperated by semi-colons OR as a python function object.
	"""
	#inputHash = inputHash.copy() #make a copy so we don't modify it... but it doesn't seem necessary
	if isSingleLineOfCode(code): return executeOneLinerCode(code, inputHash) #it's one line of text (with ;'s to seperate statemetns')
	elif isinstance(code, (str, unicode)): return executeFunctionCode(code, inputHash) #it's the text of a function definition
	else: return code(**inputHash)	#assume it's a function itself


def executeOneLinerCode(codeText, inputHash):
	"""Execute the given code stored as text in codeText, starting with the variable values specified in inputHash
	This function assumes the code consists of just one line (with multiple statements seperated by semi-colans.
	Note: if the last statement in the line starts X=... then the X= gets stripped off (to prevent it from getting broken by A=(X=...)).
	"""
	if not isSingleLineOfCode(codeText): raise Exception("The code text was not just one line of code.")
	codeText = codeText.strip()
	localVariables = inputHash.copy()
	pieces = codeText.split(";")
	lastPiece = pieces[-1].strip()
	lastPiece = re.sub("\A([\w])+[\s]*=", "",  lastPiece) #if the last statement begins with something like X = ... this removes the X = part.
	lastPiece = lastPiece.strip()
	pieces[-1] = "RESULTING_VALUE_ZX7_ = (" + lastPiece + ")"
	codeText = ";".join(pieces)
	#oneLiner = True

#	print "Code text: "+str(codeText)
	exec(codeText, globals(), localVariables)	#apply the code
	return localVariables["RESULTING_VALUE_ZX7_"]



def executeFunctionCode(codeText, inputHash):
	"""Execute the given code stored as text in codeText, starting with the variable values specified in inputHash
	This function assumes the code consists of an entire function definition.
	"""
	if not "def" in codeText: raise Exception("No function definition was found in this code!")
	localVariables = {}
	exec(codeText, globals(), localVariables)	#apply the code, which declares the function definition
	#foundFunc = False
	#result = None
	for varName, varValue in localVariables.iteritems():
		if "function" in str(type(varValue)):
			return varValue(**inputHash)
	

def isSingleLineOfCode(codeText):
	if not isinstance(codeText, (str, unicode)): return False
	codeText = codeText.strip()
	try:
		codeText.strip().index("\n")
		return False
	except ValueError:
		return True



def _incrementTrialWindows(allData, orderedFeature, currEndTrain, minTrainSize, maxTrainSize, stepSize, gap, minTestSize, maxTestSize):
	"""
	Helper which will calculate the start and end of the training and testing sizes given the current
	position in the full data set. 

	"""
#	set_trace()
	# determine the location of endTrain.
	if currEndTrain is None:
		# points are zero indexed, thus -1 for the num of points case
#		set_trace()
		endTrain = _jumpForward(allData, orderedFeature, 0, minTrainSize, -1)
	else:
		endTrain =_jumpForward(allData, orderedFeature, currEndTrain, stepSize)

	# the value we don't want to split from the training set
	nonSplit = allData[endTrain,orderedFeature]
	# we're doing a lookahead here, thus -1 from the last possible index, and  +1 to our lookup
	while (endTrain < allData.pointCount - 1 and allData[endTrain+1,orderedFeature] == nonSplit):
		endTrain += 1

	if endTrain == allData.pointCount -1:
		return None

	# we get the start for training by counting back from endTrain
	startTrain = _jumpBack(allData, orderedFeature, endTrain, maxTrainSize, -1)
	if startTrain < 0:
		startTrain = 0
#	if _diffLessThan(allData, orderedFeature, startTrain, endTrain, minTrainSize):
#		return _incrementTrialWindows(allData, orderedFeature, currEndTrain+1, minTrainSize, maxTrainSize, stepSize, gap, minTestSize, maxTestSize)
#		return None

	# we get the start and end of the test set by counting forward from endTrain
	# speciffically, we go forward by one, and as much more forward as specified by gap
	startTest = _jumpForward(allData, orderedFeature, endTrain+1, gap)
	if startTest >= allData.pointCount:
		return None

	endTest = _jumpForward(allData, orderedFeature, startTest, maxTestSize, -1)
	if endTest >= allData.pointCount:
		endTest = allData.pointCount - 1
	if _diffLessThan(allData, orderedFeature, startTest, endTest, minTestSize):
#		return _incrementTrialWindows(allData, orderedFeature, currEndTrain+1, minTrainSize, maxTrainSize, stepSize, gap, minTestSize, maxTestSize)
		return None

	return (startTrain, endTrain, startTest, endTest)


def _jumpBack(allData, orderedFeature, start, delta, intCaseOffset=0):
	if isinstance(delta,datetime.timedelta):
		endPoint = start
		startVal = datetime.timedelta(float(allData[start,orderedFeature]))
		# loop as long as we don't run off the end of the data
		while (endPoint > 0):
			if (startVal - datetime.timedelta(float(allData[endPoint-1,orderedFeature])) > delta):
				break
			endPoint = endPoint - 1 
	else:
		endPoint = start - (delta + intCaseOffset)

	return endPoint


def _jumpForward(allData, orderedFeature, start, delta, intCaseOffset=0):
	if isinstance(delta,datetime.timedelta):
		endPoint = start
		startVal = datetime.timedelta(float(allData[start,orderedFeature]))
		# loop as long as we don't run off the end of the data
		while (endPoint < allData.pointCount - 1):
			if (datetime.timedelta(float(allData[endPoint+1,orderedFeature])) - startVal > delta):
				break
			endPoint = endPoint + 1 
	else:
		endPoint = start + (delta + intCaseOffset)

	return endPoint



def _diffLessThan(allData, orderedFeature, startPoint, endPoint, delta):
	if isinstance(delta,datetime.timedelta):
		startVal = datetime.timedelta(float(allData[startPoint,orderedFeature]))
		endVal = datetime.timedelta(float(allData[endPoint,orderedFeature]))
		return (endVal - startVal) < delta
	else:
		return (endPoint - startPoint + 1) < delta





def computeMetrics(dependentVar, knownData, predictedData, performanceFunction, negativeLabel=None):
	"""
		Calculate one or more error metrics, given a list of known labels and a list of
		predicted labels.  Return as a dictionary associating the performance metric with
		its numerical result.

		dependentVar: either an int/string representing a column index in knownData
		containing the known labels, or an n x 1 matrix that contains the known labels

		knownData: matrix containing the known labels of the test set, as well as the
		features of the test set. Can be None if 'knownIndicator' contains the labels,
		and none of the performance functions needs features as input.

		predictedData: Matrix containing predicted class labels for a testing set.
		Assumes that the predicted label in the nth row of predictedLabels is associated
		with the same data point/instance as the label in the nth row of knownLabels.

		performanceFunction: single function or list of functions that compute some kind
		of error metric. Functions must be either a string that defines a proper function,
		a one-liner function (see Combinations.py), or function code.  Also, they are
		expected to take at least 2 arguments:  a vector or known labels and a vector of
		predicted labels.  Optionally, they may take the features of the test set as a
		third argument, as a matrix.

		negativeLabel: Label of the 'negative' class in the testing set.  This parameter is
		only relevant for binary class problems; and only needed for some error metrics
		(proportionPerentNegative50/90).

		Returns: a dictionary associating each performance metric with the (presumably)
		numerical value computed by running the function over the known labels & predicted labels
	"""
	from UML.metrics import fractionTrueNegativeTop90
	from UML.metrics import fractionTrueNegativeTop50
	from UML.metrics import fractionTrueNegativeBottom10

	if isinstance(dependentVar, (list, Base)):
		#The known Indicator argument already contains all known
		#labels, so we do not need to do any further processing
		knownLabels = dependentVar
	elif dependentVar is not None:
		#known Indicator is an index; we extract the column it indicates
		#from knownValues
		knownLabels = knownData.copyColumns([dependentVar])
	else:
		raise ArgumentException("Missing indicator for known labels in computeMetrics")

	singleReturn = False
	if not isinstance(performanceFunction, list):
		performanceFunction = [performanceFunction]
		singleReturn = True

	results = []
	parameterHash = {"knownValues":knownLabels, "predictedValues":predictedData}
	for func in performanceFunction:
		#some functions need negativeLabel as an argument.
		if func == fractionTrueNegativeTop90 or func == fractionTrueNegativeTop50 or func == fractionTrueNegativeBottom10:
			parameterHash["negativeLabel"] = negativeLabel
			results.append(executeCode(func, parameterHash))
			del parameterHash["negativeLabel"]
		elif len(inspect.getargspec(func).args) == 2:
			#the metric function only takes two arguments: we assume they
			#are the known class labels and the predicted class labels
			if func.__name__ != "<lambda>":
				results.append(executeCode(func, parameterHash))
			else:
				results.append(executeCode(func, parameterHash))
		elif len(inspect.getargspec(func).args) == 3:
			#the metric function takes three arguments:  known class labels,
			#features, and predicted class labels. add features to the parameter hash
			#divide X into labels and features
			#TODO correctly separate known labels and features in all cases
			parameterHash["features"] = knownData
			if func.__name__ != "<lambda>":
				results.append(executeCode(func, parameterHash))
			else:
				results.append(executeCode(func, parameterHash))
		else:
			raise Exception("One of the functions passed to computeMetrics has an invalid signature: "+func.__name__)
	
	if singleReturn:
		return results[0]
	else:
		return results

def confusion_matrix_generator(knownY, predictedY):
	""" Given two vectors, one of known class labels (as strings) and one of predicted labels,
	compute the confusion matrix.  Returns a 2-dimensional dictionary in which outer label is
	keyed by known label, inner label is keyed by predicted label, and the value stored is the count
	of instances for each combination.  Works for an indefinite number of class labels.
	"""
	confusionCounts = {}
	for known, predicted in zip(knownY, predictedY):
		if confusionCounts[known] is None:
			confusionCounts[known] = {predicted:1}
		elif confusionCounts[known][predicted] is None:
			confusionCounts[known][predicted] = 1
		else:
			confusionCounts[known][predicted] += 1

	#if there are any entries in the square matrix confusionCounts,
	#then there value must be 0.  Go through and fill them in.
	for knownY in confusionCounts:
		if confusionCounts[knownY][knownY] is None:
			confusionCounts[knownY][knownY] = 0

	return confusionCounts

def print_confusion_matrix(confusionMatrix):
	""" Print a confusion matrix in human readable form, with
	rows indexed by known labels, and columns indexed by predictedlabels.
	confusionMatrix is a 2-dimensional dictionary, that is also primarily
	indexed by known labels, and secondarily indexed by predicted labels,
	with the value at confusionMatrix[knownLabel][predictedLabel] being the
	count of posts that fell into that slot.  Does not need to be sorted.
	"""
	#print heading
	print "*"*30 + "Confusion Matrix"+"*"*30
	print "\n\n"

	#print top line - just the column headings for
	#predicted labels
	spacer = " "*15
	sortedLabels = sorted(confusionMatrix.iterKeys())
	for knownLabel in sortedLabels:
		spacer += " "*(6 - len(knownLabel)) + knownLabel

	print spacer
	totalPostCount = 0
	for knownLabel in sortedLabels:
		outputBuffer = knownLabel+" "*(15 - len(knownLabel))
		for predictedLabel in sortedLabels:
			count = confusionMatrix[knownLabel][predictedLabel]
			totalPostCount += count
			outputBuffer += " "*(6 - len(count)) + count
		print outputBuffer

	print "Total post count: " + totalPostCount

def checkPrintConfusionMatrix():
	X = {"classLabel": ["A", "B", "C", "C", "B", "C", "A", "B", "C", "C", "B", "C", "A", "B", "C", "C", "B", "C"]}
	Y = ["A", "C", "C", "A", "B", "C", "A", "C", "C", "A", "B", "C", "A", "C", "C", "A", "B", "C"]
	functions = [confusion_matrix_generator]
	classLabelIndex = "classLabel"
	confusionMatrixResults = computeMetrics(classLabelIndex, X, Y, functions)
	confusionMatrix = confusionMatrixResults["confusion_matrix_generator"]
	print_confusion_matrix(confusionMatrix)



def computeError(knownValues, predictedValues, loopFunction, compressionFunction):
	"""
		A generic function to compute different kinds of error metrics.  knownValues
		is a 1d Base object with one known label (or number) per row. predictedValues is a 1d Base
		object with one predictedLabel (or score) per row.  The ith row in knownValues should refer
		to the same point as the ith row in predictedValues. loopFunction is a function to be applied
		to each row in knownValues/predictedValues, that takes 3 arguments: a known class label,
		a predicted label, and runningTotal, which contains the successive output of loopFunction.
		compressionFunction is a function that should take two arguments: runningTotal, the final
		output of loopFunction, and n, the number of values in knownValues/predictedValues.
	"""
	if knownValues is None or not isinstance(knownValues, Base) or knownValues.pointCount == 0:
		raise ArgumentException("Empty 'knownValues' argument in error calculator")
	elif predictedValues is None or not isinstance(predictedValues, Base) or predictedValues.pointCount == 0:
		raise ArgumentException("Empty 'predictedValues' argument in error calculator")

	if not isinstance(knownValues, Matrix):
#		knownValues = knownValues.copyAs(format="Matrix")
		knownValues = Matrix(knownValues.data, knownValues.featureNames)

	if not isinstance(predictedValues, Matrix):
#		predictedValues = predictedValues.copyAs(format="Matrix")
		predictedValues = Matrix(predictedValues.data, predictedValues.featureNames)

	n=0.0
	runningTotal=0.0
	#Go through all values in known and predicted values, and pass those values to loopFunction
	for i in xrange(predictedValues.pointCount):
		pV = predictedValues[i,0]
		aV = knownValues[i,0]
		runningTotal = loopFunction(aV, pV, runningTotal)
		n += 1
	if n > 0:
		try:
			#provide the final value from loopFunction to compressionFunction, along with the
			#number of values looped over
			runningTotal = compressionFunction(runningTotal, n)
		except ZeroDivisionError:
			raise ZeroDivisionError('Tried to divide by zero when calculating performance metric')
			return
	else:
		raise ArgumentException("Empty argument(s) in error calculator")

	return runningTotal



def generateAllPairs(items):
	"""
		Given a list of items, generate a list of all possible pairs 
		(2-combinations) of items from the list, and return as a list
		of tuples.  Assumes that no two items in the list refer to the same
		object or number.  If there are duplicates in the input list, there
		will be duplicates in the output list.
	"""
	if items is None or len(items) == 0:
		return None

	pairs = []
	for i in range(len(items)):
		firstItem = items[i]
		for j in range(i+1, len(items)):
			secondItem = items[j]
			pair = (firstItem, secondItem)
			pairs.append(pair)

	return pairs


def foldIterator(dataList, folds):
	"""
	Takes a list of data objects and a number of folds, returns an iterator
	which will return a list containing the folds for each object, where
	the list has as many (training, testing) tuples as the length of the input list

	"""
	if dataList is None or len(dataList) == 0:
		raise ArgumentException("dataList may not be None, or empty")

	points = dataList[0].pointCount
	for data in dataList:
		if data.pointCount == 0:
			raise ArgumentException("One of the objects has 0 points, it is impossible to specify a valid number of folds")
		if data.pointCount != dataList[0].pointCount:
			raise ArgumentException("All data objects in the list must have the same number of points and features")

	# note: we want truncation here
	numInFold = int(points / folds)
	if numInFold == 0:
		raise ArgumentException("Must specifiy few enough folds so there is a point in each")

	# randomly select the folded portions
	indices = range(points)
	random.shuffle(indices)
	foldList = []
	for fold in xrange(folds):
		start = fold * numInFold
		if fold == folds - 1:
			end = points
		else:
			end = (fold + 1) * numInFold
		foldList.append(indices[start:end])

	# return that lists iterator as the fold iterator 	
	return _foldIteratorClass(dataList, foldList,)


class _foldIteratorClass():
	def __init__(self, dataList, foldList):
		self.foldList= foldList
		self.index = 0
		self.dataList = dataList

	def __iter__(self):
		return self

	def next(self):
		if self.index >= len(self.foldList):
			raise StopIteration
		# we're going to be separating training and testing sets through extraction,
		# so we have to copy the data in order not to destroy the original sets
		# across multiple folds
		copiedList = []
		for data in self.dataList:
			copiedList.append(data.copy())

		# we want each training set to be permuted wrt its ordering in the original
		# data. This is setting up a permutation to be applied to each object
		indices = range(0, copiedList[0].pointCount - len(self.foldList[self.index]))
		random.shuffle(indices)

		resultsList = []
		for copied in copiedList:
			currTest = copied.extractPoints(self.foldList[self.index])
			currTrain = copied	
			currTrain.shufflePoints(indices)
			resultsList.append((currTrain, currTest))
		self.index = self.index +1
		return resultsList



class ArgumentIterator:
	"""
	Constructor takes a dict mapping strings to tuples.
	e.g. {'a':(1,2,3), 'b':(4,5)}

	ArgumentBuilder generates permutations of dict in the format:
	{'a':1, 'b':4}, {'a':2, 'b':4}, {'a':3, 'b':4}, {'a':1, 'b':5}, {'a':2, 'b':5}, {'a':3, 'b':5}
	and supports popping one such permutation at a time via pop().

	Convenience methods:
	hasNext() - check if all permutations have been popped. Returns boolean.
	reset() - reset object so pop() again returns first permutation.
	"""
	def __init__(self, rawArgumentInput):
		self.rawArgumentInput = rawArgumentInput
		self.index = 0
		if not isinstance(rawArgumentInput, dict):
			raise ArgumentException("ArgumentIterator objects require dictionary's to initialize- e.g. {'a':(1,2,3), 'b':(4,5)} This is the form default generated by **args in a function argument.")

		# i.e. if rawArgumentInput == {}
		if len(rawArgumentInput) == 0:
			self.numPermutations = 1
			self.permutationsList = [{}]
		else:
			self.numPermutations = 1
			for key in rawArgumentInput.keys():
				try:
					self.numPermutations *= len(rawArgumentInput[key])
				except(TypeError): #taking len of non tuple
					pass #numPermutations not increased
			self.permutationsList = _buildArgPermutationsList([],{},0,rawArgumentInput)

			assert(len(self.permutationsList) == self.numPermutations)

	def __iter__(self):
		return self

	def hasNext(self):
		if self.index >= self.numPermutations:
			return False
		else:
			return True

	def next(self):
		if self.index >= self.numPermutations:
			self.index = 0
			raise StopIteration
		else:
			permutation = self.permutationsList[self.index]
			self.index += 1
			return permutation

	def reset(self):
		self.index = 0

#example call: _buildArgPermutationsList([],{},0,arg)
def _buildArgPermutationsList(listOfDicts, curCompoundArg, curKeyIndex, rawArgInput):
	"""
	Recursive function that generates a list of dicts, where each dict is a permutation
	of rawArgInput's values.
	
	Should be called externally with:
	listOfDicts = []
	curCompoundArg = {}
	curKeyIndex = 0

	and rawArgInput as a dict mapping variables to tuples.

	example:
	if rawArgInput is {'a':(1,2,3), 'b':(4,5)}
	then _buildArgPermutationsList([],{},0,rawArgInput)
	returns [{'a':1, 'b':4}, {'a':2, 'b':4}, {'a':3, 'b':4}, {'a':1, 'b':5}, {'a':2, 'b':5}, {'a':3, 'b':5},]
	"""

	#stop condition: if current dict has a value for every key
	#append a DEEP COPY of the dict to the listOfDicts. Copy is deep
	#because dict entries will be changed when recursive stack is popped.
	#Only complete, and distict dicts are appended to listOfDicts
	if curKeyIndex >= len(rawArgInput.keys()):
		listOfDicts.append(copy.deepcopy(curCompoundArg))
		return listOfDicts

	else:
		#retrieve all values for the current key being populated
		curKey = rawArgInput.keys()[curKeyIndex]
		curValues = rawArgInput[curKey]

		try:
			#if there are multiple values, add one key-value pair to the
			#the current dict, make recursive call to build the rest of the dict
			#then after it returns, remove current key-value pair and add the
			#next pair.
			valueIterator = iter(curValues)
			for value in valueIterator:
				curCompoundArg[curKey] = value
				listOfDicts = _buildArgPermutationsList(listOfDicts, curCompoundArg, curKeyIndex + 1, rawArgInput)
				del curCompoundArg[curKey]
		#if there is only one value, curValues is not iterable, so add
		#curKey[value] to the dict and make recursive call.
		except TypeError:
			value = curValues
			curCompoundArg[curKey] = value
			listOfDicts = _buildArgPermutationsList(listOfDicts, curCompoundArg, curKeyIndex + 1, rawArgInput)
			del curCompoundArg[curKey]

		return listOfDicts


#with class-based refactor:
#todo add scale control as paramater for generateClusteredPoints - remember to scale noise term accordingly
def generateClusteredPoints(numClusters, numPointsPerCluster, numFeaturesPerPoint, addFeatureNoise=True, addLabelNoise=True, addLabelColumn=False, retType='Matrix'):
	"""
	Function to generate Data object with arbitrary number of points, number of clusters, and number of features.

	The function returns the dataset in an object, 'labels' for each point in the dataset (noise optional), and 
	the 'noiseless' labels for the points, which is the central value used to define the feature values for each point

	generateClusteredPoints() outputs a dataset of the following format:
	each point associated with a cluster has numFeaturesPerPoint features. The value of each entry in the feature vector
	is clusterNumber+noise. Each point in the cluster has the same feature vector, with different noise.

	NOTE: if addFeatureNoise and addLabelNoise are false, then the 'clusters' are actually all
	contain just repeated points, where each point in the cluster has the same features and the same labels

	returns tuple of UML.Base objects: (pointsObj, labelsObj, noiselessLabelsObj)
	"""

	pointsList = []
	labelsList = []
	clusterNoiselessLabelList = []

	def _noiseTerm():
		return random.random()*0.0001 - 0.00005

	for curCluster in xrange(numClusters):
		for curPoint in xrange(numPointsPerCluster):
			curFeatureVector = [float(curCluster) for x in xrange(numFeaturesPerPoint)]
			
			if addFeatureNoise:
				curFeatureVector = [_noiseTerm()+entry for entry in curFeatureVector]
			
			if addLabelNoise:
				curLabel = _noiseTerm()+curCluster
			else:
				curLabel = curCluster

			if addLabelColumn:
				curFeatureVector.append(curLabel)

			#append curLabel as a list to maintain dimensionality
			labelsList.append([curLabel])

			pointsList.append(curFeatureVector)
			clusterNoiselessLabelList.append([float(curCluster)])


	#todo verify that your list of lists is valid initializer for all datatypes, not just matrix
	#then convert
	#finally make matrix object out of the list of points w/ labels in last column of each vector/entry:
	pointsObj = UML.createData('Matrix', pointsList)

	labelsObj = UML.createData('Matrix', labelsList)

	#todo change actuallavels to something like associatedClusterCentroid
	noiselessLabelsObj = UML.createData('Matrix', clusterNoiselessLabelList)

	#convert datatype if not matrix
	if retType.lower() != 'matrix':
		pointsObj = pointsObj.copyAs(retType)
		labelsObj = labelsObj.copyAs(retType)
		noiselessLabelsObj = noiselessLabelsObj.copyAs(retType)
	
	return (pointsObj, labelsObj, noiselessLabelsObj)


def sumAbsoluteDifference(dataOne, dataTwo):
	"""
	Aggregates absolute difference between corresponding entries in base objects dataOne and dataTwo.

	Checks to see that the vectors (which must be base objects) are of the same shape, first.
	Next it iterates through the corresponding points in each vector/matrix and appends the absolute difference
	between corresponding points to a list.
	Finally, the function returns the sum of the absolute differences.
	"""

	#compare shapes of data to make sure a comparison is sensible.
	if dataOne.featureCount != dataTwo.featureCount:
		raise ArgumentException("Can't calculate difference between corresponding entries in dataOne and dataTwo, the underlying data has different numbers of features.")
	if dataOne.pointCount != dataTwo.pointCount:
		raise ArgumentException("Can't calculate difference between corresponding entries in dataOne and dataTwo, the underlying data has different numbers of points.")

	numpyOne = dataOne.copyAs('numpyarray')
	numpyTwo = dataTwo.copyAs('numpyarray')

	differences = numpyOne - numpyTwo

	absoluteDifferences = numpy.abs(differences)

	sumAbsoluteDifferences = numpy.sum(absoluteDifferences)

	return sumAbsoluteDifferences

class LearnerInspector:
	"""Class using heirustics to classify the 'type' of problem an algorithm is meant to work on.
	e.g. classification, regression, dimensionality reduction, etc.

	Use:
	A LearnerInspector object generates private datasets that are intentionally constructed to 
	invite particular results when an algorithm is run on them. Once a user has a LearnerInspector
	object, she can call learnerType(algorithmName) and get the 'best guess' type for that algorithm.

	Note:
	If characterizing multiple algorithms, use the SAME LearnerInspector object, and call learnerType()
	once for each algorithm you are trying to classify. 
	"""

	def __init__(self):
		"""Caches the regressor and classifier datasets, to speed up learnerType() calls 
		for multiple learners.
		"""

		self.NEAR_THRESHHOLD = .01
		self.EXACT_THRESHHOLD = .00000001

		#initialize datasets for tests
		self.regressorDataTrain, self.regressorDataTest = self._regressorDataset()
		#todo use classifier
		self.classifierDataTrain, self.classifierDataTest = self._classifierDataset()

	def learnerType(self, learnerName):
		"""Returns, as a string, the heuristically determined best guess for the type 
		of problem the learnerName learner is designed to run on.
		Example output: 'classifier', 'regressor', 'other'
		"""

		return self._classifyAlgorithmDecisionTree(learnerName)

	#todo pull from each 'trail' function to find out what possible results it can have
	#then make sure that you've covered all possible combinations
	def _classifyAlgorithmDecisionTree(self, learnerName):
		"""Implements a decision tree based off of the predicted labels returned from 
		the datasets.

		Fundamentally, if the classifier dataset has no error, that means the algorithm 
		is likely a classifier, but it could be a regressor, if its error is low, however,
		the algorithm is likely a regressor, and if its error is high, or the algorithm 
		crashes with the dataset, then the algorithm is likely neither classifier nor regressor.

		Next, if the classifier dataset had no error, we want to see if the error on the
		regressor dataset is low. Also, we want to see if the algorithm is capable of generating
		labels that it hasn't seen (interpolating a la a regressor).

		If the algorithm doesn't produce any new labels, despite no repeated labels, then
		we assume it is a classifier. If the error on the classifier dataset is low, however,
		and the algorithm interpolates labels, then we assume it is a regressor.
		"""

		regressorTrialResult = self._regressorTrial(learnerName)
		classifierTrialResult = self._classifierTrial(learnerName)

		#decision tree:
		#if classifier tests gives exact results
		if classifierTrialResult == 'exact': #could be classifier or regressor at this point
			#if when given unrepeating labels, algorithm generates duplicate of already seen labels, 
			#it is classifer
			if regressorTrialResult == 'repeated_labels':
				return 'classifier'
			if regressorTrialResult == 'near':
				return 'regressor'
			if regressorTrialResult == 'other':
				return 'classifier'
			#should be covered by all cases, raise exception
			raise AttributeError('Decision tree needs to be updated to account for other results from regressorTrialResult')

		# if the classifer data set genereated a low error, but not exact, it is regressor
		elif classifierTrialResult == 'near':
			return 'regressor'

		#if the classifier dataset doesn't see classifier or regerssor behavior, return other
		#todo this is where to insert future sensors for other types of algorithms, but
		#currently we can only resolve classifiers, regressors, and other.
		else:
			return 'other'

	def _regressorDataset(self):
		"""Generates clustered points, where the labels of the points within a single cluster are all very similar,
		but non-identical
		"""

		clusterCount = 3
		pointsPer = 10
		featuresPer = 5

		#add noise to both the features and the labels
		regressorTrainData, trainLabels, noiselessTrainLabels = generateClusteredPoints(clusterCount, pointsPer, featuresPer, addFeatureNoise=True, addLabelNoise=True, addLabelColumn=False)
		regressorTestData, testLabels, noiselessTestLabels = generateClusteredPoints(clusterCount, 1, featuresPer, addFeatureNoise=True, addLabelNoise=True, addLabelColumn=False)

		return ((regressorTrainData, trainLabels, noiselessTrainLabels), (regressorTestData, testLabels, noiselessTestLabels))

	def _classifierDataset(self):
		"""Generates clustered points, hwere the labels of the points within each cluster are all identical.
		"""

		clusterCount = 3
		pointsPer = 10
		featuresPer = 5

		#add noise to the features only
		trainData, trainLabels, noiselessTrainLabels = generateClusteredPoints(clusterCount, pointsPer, featuresPer, addFeatureNoise=True, addLabelNoise=False, addLabelColumn=False)
		testData, testLabels, noiselessTestLabels = generateClusteredPoints(clusterCount, 1, featuresPer, addFeatureNoise=True, addLabelNoise=False, addLabelColumn=False)

		return ((trainData, trainLabels, noiselessTrainLabels), (testData, testLabels, noiselessTestLabels))

	def _regressorTrial(self, learnerName):
		"""Run trainAndApply on the regressor dataset and make judgments about the learner based on 
		the results of trainAndApply
		"""

		#unpack already-initialized datasets
		regressorTrainData, trainLabels, noiselessTrainLabels = self.regressorDataTrain
		regressorTestData, testLabels, noiselessTestLabels = self.regressorDataTest

		try:
			runResults = UML.trainAndApply(learnerName, trainX=regressorTrainData, trainY=trainLabels, testX=regressorTestData)
		except Exception:
			return 'other'

		try:
			sumError = sumAbsoluteDifference(runResults, noiselessTestLabels)
		except ArgumentException:
			return 'other'

		#if the labels are repeated from those that were trained on, then it is a classifier
		#so pass back that labels are repeated
		# if runResults are all in trainLabels, then it's repeating:
		alreadySeenLabelsList = []
		for curPointIndex in xrange(trainLabels.pointCount):
			alreadySeenLabelsList.append(trainLabels[curPointIndex, 0])

		#check if the learner generated any new label (one it hadn't seen in training)
		unseenLabelFound = False
		for curResultPointIndex in xrange(runResults.pointCount):
			if runResults[curResultPointIndex,0] not in alreadySeenLabelsList:
				unseenLabelFound = True
				break

		if not unseenLabelFound:
			return 'repeated_labels'

		if sumError > self.NEAR_THRESHHOLD:
			return 'other'
		else:
			return 'near'


	def _classifierTrial(self, learnerName):
		"""Run trainAndApply on the classifer dataset and make judgments about the learner based on 
		the results of trainAndApply.
		"""

		#unpack initialized datasets
		trainData, trainLabels, noiselessTrainLabels = self.classifierDataTrain
		testData, testLabels, noiselessTestLabels = self.classifierDataTest

		try:
			runResults = UML.trainAndApply(learnerName, trainX=trainData, trainY=trainLabels, testX=testData)
		except Exception:
			return 'other'

		try:
			sumError = sumAbsoluteDifference(runResults, testLabels) #should be identical to noiselessTestLabels
		except ArgumentException:
			return 'other'

		if sumError > self.NEAR_THRESHHOLD:
			return 'other'
		elif sumError > self.EXACT_THRESHHOLD:
			return 'near'
		else:
			return 'exact'




