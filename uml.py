"""
Module containing most of the user facing functions for the top level uml import.

"""

import random
import numpy
import scipy.sparse
import inspect
import operator
import re 
import datetime
import os

import UML
from UML.exceptions import ArgumentException

from UML.logger import UmlLogger
from UML.logger import LogManager
from UML.logger import Stopwatch

from UML.umlHelpers import findBestInterface
from UML.umlHelpers import _loadSparse
from UML.umlHelpers import _loadMatrix
from UML.umlHelpers import _loadList
from UML.umlHelpers import executeCode
from UML.umlHelpers import _incrementTrialWindows
from UML.umlHelpers import _learnerQuery
from UML.umlHelpers import _validScoreMode
from UML.umlHelpers import _validMultiClassStrategy
from UML.umlHelpers import _unpackLearnerName
from UML.umlHelpers import _validArguments
from UML.umlHelpers import _validData
from UML.umlHelpers import LearnerInspector
from UML.umlHelpers import copyLabels
from UML.umlHelpers import computeMetrics
from UML.umlHelpers import ArgumentIterator
from UML.umlHelpers import trainAndApplyOneVsAll
from UML.umlHelpers import trainAndApplyOneVsOne

from UML.data import Base

from UML.data.dataHelpers import DEFAULT_SEED

from UML.interfaces.interface_helpers import checkClassificationStrategy





UMLPath = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

def createRandomData(retType, numPoints, numFeatures, sparsity, numericType="float", featureNames=None, name=None):
	"""
	Generates a data object with random contents and numPoints points and numFeatures features. 

	If numericType is 'float' (default) then the value of (point, feature) pairs are sampled from a normal
	distribution (location 0, scale 1).

	If numericType is 'int' then value of (point, feature) pairs are sampled from uniform integer distribution [1 100].

	The sparsity is the likelihood that the value of a (point,feature) pair is zero.

	Zeros are not counted in/do not affect the aforementioned sampling distribution.
	"""

	if numPoints < 1:
		raise ArgumentException("must specify a positive nonzero number of points")
	if numFeatures < 1:
		raise ArgumentException("must specify a positive nonzero number of features")
	if sparsity < 0 or sparsity >=1:
		raise ArgumentException("sparsity must be greater than zero and less than one")
	if numericType != "int" and numericType != "float":
		raise ArgumentException("numericType may only be 'int' or 'float'")


	#note: sparse is not stochastic sparsity, it uses rigid density measures
	if retType.lower() == 'sparse':

		density = 1.0 - float(sparsity)
		numNonZeroValues = int(numPoints * numFeatures * density)

		pointIndices = numpy.random.randint(low=0, high=numPoints, size=numNonZeroValues)
		featureIndices = numpy.random.randint(low=0, high=numFeatures, size=numNonZeroValues)

		if numericType == 'int':
			dataVector = numpy.random.randint(low=1, high=100, size=numNonZeroValues)
		#numeric type is float; distribution is normal
		else: 
			dataVector = numpy.random.normal(0, 1, size=numNonZeroValues) 

		#pointIndices and featureIndices are 
		randData = scipy.sparse.coo.coo_matrix((dataVector, (pointIndices, featureIndices)), (numPoints, numFeatures))
			
	#for non-sparse matrices, use numpy to generate matrices with sparsity characterics
	else:
		if numericType == 'int':
			filledIntMatrix = numpy.random.randint(1, 100, (numPoints, numFeatures))
		else:
			filledFloatMatrix = numpy.random.normal(loc=0.0, scale=1.0, size=(numPoints,numFeatures))

		#if sparsity is zero
		if abs(float(sparsity) - 0.0) < 0.0000000001:
			if numericType == 'int':
				randData = filledIntMatrix
			else:
				randData = filledFloatMatrix
		else:
			binarySparsityMatrix = numpy.random.binomial(1, 1.0-sparsity, (numPoints, numFeatures))

			if numericType == 'int':
				randData = binarySparsityMatrix * filledIntMatrix
			else:
				randData = binarySparsityMatrix * filledFloatMatrix

	return createData(retType, data=randData, featureNames=featureNames, name=name)



def splitData(toSplit, fractionForTestSet, labelID=None):
	"""this is a helpful function that makes it easy to do the common task of loading a dataset and splitting it into training and testing sets.
	It returns training X, training Y, testing X and testing Y"""
	testXSize = int(round(fractionForTestSet*toSplit.pointCount))
	#pull out a testing set
	testX = toSplit.extractPoints(start=0, end=toSplit.pointCount, number=testXSize, randomize=True)	
	trainY = None
	testY = None
	if labelID is not None:
		trainY = toSplit.extractFeatures(labelID)	#construct the column vector of training labels
		testY = testX.extractFeatures(labelID)	#construct the column vector of testing labels
	return toSplit, trainY, testX, testY



def normalizeData(learnerName, trainX, trainY=None, testX=None, arguments={}, mode=True):
	"""
	Calls on the functionality of a package to train on some data and then modify both
	the training data and a set of test data accroding to the produced model.

	"""
	# single call normalize, combined data
	if mode and testX is not None:
		testLength = testX.pointCount
		# glue training data at the end of test data
		testX.appendPoints(trainX)
		try:
			normalizedAll = trainAndApply(learnerName, trainX, trainY, testX, arguments=arguments)
		except ArgumentException:
			testX.extractPoints(start=testLength, end=normalizedAll.pointCount)
		# resplit normalized
		normalizedTrain = normalizedAll.extractPoints(start=testLength, end=normalizedAll.pointCount)
		normalizedTest = normalizedAll
	# two call normalize, no data combination
	else:
		normalizedTrain = trainAndApply(learnerName, trainX, trainY, trainX, arguments=arguments)
		if testX is not None:
			normalizedTest = trainAndApply(learnerName, trainX, trainY, testX, arguments=arguments)
		
	# modify references for trainX and testX
	trainX.referenceDataFrom(normalizedTrain)
	if testX is not None:
		testX.referenceDataFrom(normalizedTest)

def registerCustomLearner(customPackageName, learnerClassObject):
	"""
	Register the given customLearner class so that it is callable by the top level UML
	functions through the interface of the specified custom package.

	customPackageName : The string name of the package preface you want to use when calling
	the learner. If there is already an interface for a custom package with this name, the
	learner will be accessible through that interface. If there is no interface to a custom
	package of that name, then one will be created. You cannot register a custom learner to
	be callable through the interface for a non-custom package (such as ScikitLearn or MLPY).
	Therefore, customPackageName cannot be a value which is the accepted alias of another
	package's interface.

	learnerClassObject : The class object implementing the learner you want registered. It
	will be checked using UML.interfaces.CustomLearner.validateSubclass to ensure that all
	details of the provided implementation are acceptable.

	"""
	# TODO configuration subsystem hookin
	# detect name collision
	for currInterface in UML.interfaces.available:
		if not isinstance(currInterface, UML.interfaces.CustomLearnerInterface):
			if currInterface.isAlias(customPackageName):
				raise ArgumentException("The customPackageName '" + customPackageName + "' cannot be used: it is an accepted alias of a non-custom package")

	# do validation before we potentially construct an interface to a custom package
	UML.interfaces.CustomLearner.validateSubclass(learnerClassObject)

	try:
		currInterface = findBestInterface(customPackageName)
	except ArgumentException:
		currInterface = UML.interfaces.CustomLearnerInterface(customPackageName)
		UML.interfaces.available.append(currInterface)

	currInterface.registerLearnerClass(learnerClassObject)


def deregisterCustomLearner(customPackageName, learnerName):
	"""
	Remove accessibility of the learner with the given name from the interface of the package
	with the given name.

	customPackageName : the name of the interface / custom package from which the learner
	named 'learnerName' is to be removed from. If that learner was the last one grouped in
	that custom package, then the interface is removed from the UML.interfaces.available list.

	learnerName : the name of the learner to be removed from the interface / custom package with
	the name 'customPackageName'

	"""
	currInterface = findBestInterface(customPackageName)
	if not isinstance(currInterface, UML.interfaces.CustomLearnerInterface):
		raise ArgumentException("May only attempt to deregister learners from the interfaces of custom packages. '" + customPackageName + "' is not a custom package")
	empty = currInterface.deregisterLearner(learnerName)

	if empty:
		UML.interfaces.available.remove(currInterface)


def learnerParameters(name):
	"""
	Takes a string of the form 'package.learnerName' and returns a list of
	strings which are the names of the parameters when calling package.learnerName

	If the name cannot be found within the package, then an exception will be thrown.
	If the name is found, be for some reason we cannot determine what the parameters
	are, then we return None. Note that if we have determined that there are no
	parameters, we return an empty list. 

	"""
	return _learnerQuery(name, 'parameters')

def learnerDefaultValues(name):
	"""
	Takes a string of the form 'package.learnerName' and returns a returns a
	dict mapping of parameter names to their default values when calling
	package.learnerName

	If the name cannot be found within the package, then an exception will be thrown.
	If the name is found, be for some reason we cannot determine what the parameters
	are, then we return None. Note that if we have determined that there are no
	parameters, we return an empty dict. 

	"""
	return _learnerQuery(name, 'defaults')


def listLearners(package=None):
	"""
	Takes the name of a package, and returns a list of learners that are callable through that
	package's trainAndApply() interface.

	"""
	results = []
	if package is None:
		for interface in UML.interfaces.available:
			packageName = interface.getCanonicalName()
			currResults = interface.listLearners()
			for learnerName in currResults:
				results.append(packageName + "." + learnerName)
	else:
		interface = findBestInterface(package)
		currResults = interface.listLearners()
		for learnerName in currResults:
			results.append(learnerName)

	return results


def listDataFunctions():
	methodList = dir(UML.data.Base)
	visibleMethodList = []
	for methodName in methodList:
		if not methodName.startswith('_'):
			visibleMethodList.append(methodName)

	ret = []
	for methodName in visibleMethodList:
		currMethod = eval("UML.data.Base." + methodName)
		(args, varargs, keywords, defaults) = inspect.getargspec(currMethod)

		retString = methodName + "("
		for i in xrange(0, len(args)):
			if i != 0:
				retString += ", "
			retString += args[i]
			if defaults is not None and i >= (len(args) - len(defaults)):
				retString += "=" + str(defaults[i - (len(args) - len(defaults))])
			
		# obliterate the last comma
		retString += ")"
		ret.append(retString)

	return ret


def listUMLFunctions():
	methodList = dir(UML)

	visibleMethodList = []
	for methodName in methodList:
		if not methodName.startswith('_'):
			visibleMethodList.append(methodName)

	ret = []
	for methodName in visibleMethodList:
		currMethod = eval("UML." + methodName)
		if "__call__" not in dir(currMethod):
			continue
		(args, varargs, keywords, defaults) = inspect.getargspec(currMethod)

		retString = methodName + "("
		for i in xrange(0, len(args)):
			if i != 0:
				retString += ", "
			retString += args[i]
			if defaults is not None and i >= (len(args) - len(defaults)):
				retString += "=" + str(defaults[i - (len(args) - len(defaults))])
			
		# obliterate the last comma
		retString += ")"
		ret.append(retString)

	return ret


def createData(retType, data=None, featureNames=None, fileType=None, name=None, sendToLog=True):
	automatedRetType = False
	# determine if its a file we have to read; we assume if its a string its a path
	if isinstance(data, basestring):
		#we may log this event
		if sendToLog is not None and sendToLog is not False:
			if isinstance(sendToLog, UmlLogger):
				logger = sendToLog
			else:
				logger = LogManager()
			#logger.logLoad(retType, data, name)
		# determine the extension, call the appropriate helper
		split = data.rsplit('.', 1)
		extension = None
		if len(split) > 1:
			extension = split[1].lower()
		# if fileType is specified, it takes priority, otherwise, use the extension
		if fileType is None:
			fileType = extension
		if fileType is None:
			raise ArgumentException("The file must be recognizable by extension, or a type must be specified")
		
		if retType is None:
			automatedRetType = True
			if fileType == 'csv':
				retType = 'Matrix'
			if fileType == 'mtx':
				retType = 'Sparse'

	# if data is not a path to a file, then we don't care about the value of this flag;
	# instead we use it as an indicator flag to directly instantiate
	else:
		fileType = None
		if retType is None:
			if isinstance(data, list):
				retType = 'List'
			if isinstance(data, numpy.matrix):
				retType = 'Matrix'
			if isinstance(data, numpy.array):
				retType = 'Matrix'
			if scipy.sparse.issparse(data):
				retType = 'Sparse'


	# these should be lowercase to avoid ambiguity
	retType = retType.lower()
	sparseAlias = ["sparse"]
	matrixAlias = ['matrix']
	listAlias = ["list"]
	if retType in sparseAlias:
		ret = _loadSparse(data, featureNames, fileType, automatedRetType)
	elif retType in matrixAlias:
		ret = _loadMatrix(data, featureNames, fileType, automatedRetType)
	elif retType in listAlias:
		ret = _loadList(data, featureNames, fileType)
	else:
		msg = "Unknown data type, cannot instantiate. Only allowable inputs: "
		msg += "'List' for data in python lists, 'Matrix' for a numpy matrix, "
		msg += "'Sparse' for a scipy sparse coo_matrix, and None for automated choice."
		raise ArgumentException(msg)

	if name is not None:
		ret.nameData(name)
	return ret


#todo add seed specification support to UML.foldIterator() to avoid 
#using two harmonious iterators (methods of base) and zip()
def crossValidate(learnerName, X, Y, performanceFunction, argumentsForAlgorithm={}, numFolds=10, scoreMode='label', negativeLabel=None, sendToLog=False, foldSeed=DEFAULT_SEED):
	"""
	K-fold cross validation.
	Returns mean performance (float) across numFolds folds on a X Y.

	Parameters:

	learnerName (string) - UML compliant algorithm name in the form 
	'package.algorithm' e.g. 'sciKitLearn.KNeighborsClassifier'

	X (UML.Base subclass) - points/features data

	Y (UML.Base subclass or int index for X) - labels/data about points in X

	performanceFunction (function) - Look in UML.metrics for premade options.
	Function used by computeMetrics to generate a performance score for the run.
	function is of the form:
	def func(knownValues, predictedValues, negativeLabel).

	argumentsForAlgorithm (dict) - dictionary mapping argument names (strings)
	to their values. This parameter is sent to trainAndApply()
	example: {'dimensions':5, 'k':5}

	numFolds (int) - the number of folds used in the cross validation. Can't
	exceed the number of points in X, Y

	scoreMode - used by computeMetrics

	negativeLabel - used by computeMetrics

	sendToLog (bool) - send results/timing to log

	foldSeed - seed used to generate the folds, if you want to ensure the same
	folds for two different sets of points, provided the data has the same
	number of points, using the same seed will generate the same folds.
	"""
	if not isinstance(X, Base):
		raise ArgumentException("X must be a Base object")
	if not isinstance(Y, (Base, int)):
		raise ArgumentException("Y must be a Base object or an index (int) from X where Y's data can be found")
	if isinstance(Y, int):
		Y = X.extractFeatures(start=Y, end=Y)
	
	if not X.pointCount == Y.pointCount:
		#todo support indexing if Y is an index for X instead
		raise ArgumentException("X and Y must contain the same number of points.")

	#using the same seed (to ensure idetical folds in X and Y and thus accurate
	#linking between according points) make iterators containing folds
	foldedXIterator = X.foldIterator(numFolds, seed=foldSeed)
	foldedYIterator = Y.foldIterator(numFolds, seed=foldSeed)
	assert len(foldedXIterator.foldList) == len(foldedYIterator.foldList)

	performanceListOfFolds = []
	#for each fold get train and test sets
	for XFold, YFold in zip(foldedXIterator, foldedYIterator):
		
		curTrainX, curTestingX = XFold
		curTrainY, curTestingY = YFold

		#run algorithm on the folds' training and testing sets
		curRunResult = trainAndApply(learnerName=learnerName, trainX=curTrainX, trainY=curTrainY, testX=curTestingX, arguments=argumentsForAlgorithm, scoreMode=scoreMode, sendToLog=sendToLog)
		#calculate error of prediction, according to performanceFunction
		curPerformance = computeMetrics(curTestingY, None, curRunResult, performanceFunction, negativeLabel)

		performanceListOfFolds.append(curPerformance)

	if len(performanceListOfFolds) == 0:
		raise(ZeroDivisionError("crossValidate tried to average performance of ZERO runs"))
		
	#else average score from each fold (works for one fold as well)
	averagePerformance = sum(performanceListOfFolds)/float(len(performanceListOfFolds))
	return averagePerformance

def crossValidateReturnAll(learnerName, X, Y, performanceFunction, numFolds=10, scoreMode='label', negativeLabel=None, sendToLog=False, foldSeed=DEFAULT_SEED, **arguments):
	"""
	Calculates the cross validated error for each argument permutation that can 
	be generated by kwargs arguments.

	example **arguments: {'a':(1,2,3), 'b':(4,5)}
	generates permutations of dict in the format:
	{'a':1, 'b':4}, {'a':2, 'b':4}, {'a':3, 'b':4}, {'a':1, 'b':5}, 
	{'a':2, 'b':5}, {'a':3, 'b':5}

	For each permutation of 'arguments', crossValidateReturnAll uses cross 
	validation to generate a performance score for the algorithm, given the 
	particular argument permutation.

	Returns a list of tuples, where every tuple contains a dict representing 
	the argument sent to trainAndApply, and a float represennting the cross 
	validated error associated with that argument dict.
	example list element: ({'arg1':2, 'arg2':'max'}, 89.0000123)

	Arguments:

	learnerName (string) - UML compliant algorithm name in the form 
	'package.algorithm' e.g. 'sciKitLearn.KNeighborsClassifier'

	X (UML.Base subclass) - points/features data

	Y (UML.Base subclass or int index for X) - labels/data about points in X

	performanceFunction (function) - Look in UML.metrics for premade options.
	Function used by computeMetrics to generate a performance score for the run.
	function is of the form:
	def func(knownValues, predictedValues, negativeLabel).

	argumentsForAlgorithm (dict) - dictionary mapping argument names (strings)
	to their values. This parameter is sent to trainAndApply()
	example: {'dimensions':5, 'k':5}

	numFolds (int) - the number of folds used in the cross validation. Can't
	exceed the number of points in X, Y

	scoreMode - used by computeMetrics

	negativeLabel - used by computeMetrics

	sendToLog (bool) - send results/timing to log

	foldSeed - seed used to generate the folds, if you want to ensure the same
	folds for two different sets of points, provided the data has the same
	number of points, using the same seed will generate the same folds.

	arguments - kwargs specified variables that are passed to the learner.
	To make use of multiple permutations, sepcify different values for a
	paramater as a tuple. eg. a=(1,2,3) will generate an error score for 
	the learner when the learner was passed all three values of a, seperately.

	"""

	#get an iterator for the argumet combinations- iterator
	#handles case of arguments being {}
	argumentCombinationIterator = ArgumentIterator(arguments)

	performanceList = []
	#make sure that the folds are identical for all trials, so that no argument combination gets
	#a lucky/easy fold set
	commonFoldSeed = foldSeed

	for curArgumentCombination in argumentCombinationIterator:
		#calculate cross validated performance, given the current argument dict
		errorForArgument = crossValidate(learnerName, X, Y, performanceFunction, curArgumentCombination, numFolds, scoreMode, negativeLabel, sendToLog, foldSeed=commonFoldSeed)
		#store the tuple with the current argument and cross validated performance	
		performanceList.append((curArgumentCombination, errorForArgument))
	#return the list of tuples - tracking the performance of each argument
	return performanceList


def crossValidateReturnBest(learnerName, X, Y, performanceFunction, numFolds=10, scoreMode='label', negativeLabel=None, sendToLog=False, foldSeed=DEFAULT_SEED, maximize=False, **arguments):
	"""
	For each possible argument permutation generated by arguments, 
	crossValidateReturnBest runs crossValidate to compute a mean error for the 
	argument combination. 

	crossValidateReturnBest then RETURNS the best argument and error as a tuple:
	(argument_as_dict, cross_validated_performance_float)

	Arguments:
	learnerName (string) - UML compliant algorithm name in the form 
	'package.algorithm' e.g. 'sciKitLearn.KNeighborsClassifier'

	X (UML.Base subclass) - points/features data

	Y (UML.Base subclass or int index for X) - labels/data about points in X

	performanceFunction (function) - Look in UML.metrics for premade options.
	Function used by computeMetrics to generate a performance score for the run.
	function is of the form:
	def func(knownValues, predictedValues, negativeLabel).

	argumentsForAlgorithm (dict) - dictionary mapping argument names (strings)
	to their values. This parameter is sent to trainAndApply()
	example: {'dimensions':5, 'k':5}

	numFolds (int) - the number of folds used in the cross validation. Can't
	exceed the number of points in X, Y

	scoreMode - used by computeMetrics

	negativeLabel - used by computeMetrics

	sendToLog (bool) - send results/timing to log

	foldSeed - seed used to generate the folds, if you want to ensure the same
	folds for two different sets of points, provided the data has the same
	number of points, using the same seed will generate the same folds.

	"""

	resultsAll = crossValidateReturnAll(learnerName, X, Y, performanceFunction, numFolds, scoreMode, negativeLabel, sendToLog, foldSeed, **arguments)

	bestArgumentAndScoreTuple = None

	for curResultTuple in resultsAll:
		curArgument, curScore = curResultTuple
		#if curArgument is the first or best we've seen: 
		#store its details in bestArgumentAndScoreTuple
		if bestArgumentAndScoreTuple is None:
			bestArgumentAndScoreTuple = curResultTuple
		else:
			if (maximize and curScore > bestArgumentAndScoreTuple[1]) or ((not maximize) and curScore < bestArgumentAndScoreTuple[1]):
				bestArgumentAndScoreTuple = curResultTuple

	return bestArgumentAndScoreTuple


def learnerType(learnerNames):
	"""
	Returns the string or list of strings representation of a best guess for 
	the type of learner(s) specified by the learner name(s) in learnerNames.

	If learnerNames is a single string (not a list of strings), then only a single 
	result is returned, instead of a list.
	
	LearnerType first queries the appropriate interface object for a definitive return
	value. If the interface doesn't provide a satisfactory answer, then this method
	calls a backend which generates a series of artificial data sets with particular
	traits to look for heuristic evidence of a classifier, regressor, etc.
	"""
	#argument checking
	if not isinstance(learnerNames, list):
		learnerNames = [learnerNames]

	splitNames = []
	associated = []
	for name in learnerNames:
		if not isinstance(name, str):
			raise ArgumentException("learnerNames must be a string or a list of strings.")

		splitTuple = _unpackLearnerName(name)
		currInterface = findBestInterface(splitTuple[0])
		allValidLearnerNames = currInterface.listLearners()
		if not splitTuple[1] in allValidLearnerNames:
			raise ArgumentException(name + " is not a valid learner on your machine.")
		splitNames.append(splitTuple)
		associated.append(currInterface)

	resultsList = []
	secondPassLearnerNames = []
	for index in range(len(splitNames)):
		(curPackage, curName) = splitNames[index]
		interface = associated[index]
		result = interface.learnerType(curName)
		if result == 'UNKNOWN' or result == 'other' or result is None:
			resultsList.append(None)
			secondPassLearnerNames.append((curPackage, curName))
		else:
			resultsList.append(result)
			secondPassLearnerNames.append(None)

	#have valid arguments - a list of learner names
	learnerInspectorObj = LearnerInspector()

	for index in range(len(secondPassLearnerNames)):
		curLearnerName = secondPassLearnerNames[index]
		if curLearnerName is None:
			continue
		resultsList[index] = learnerInspectorObj.learnerType(curLearnerName)

	#if only one algo was requested, remove type from list an return as single string
	if len(resultsList) == 1:
		resultsList = resultsList[0]

	return resultsList


def train(learnerName, trainX, trainY, arguments={},  multiClassStrategy='default', sendToLog=True):
	(package, learnerName) = _unpackLearnerName(learnerName)
	_validData(trainX, trainY, None, None, [False, False])
	_validArguments(arguments)

	if sendToLog:
		timer = Stopwatch()
	else:
		timer = None

	interface = findBestInterface(package)

	# TODO how do we do multiclassStrategy?

	trainedLearner = interface.train(learnerName, trainX, trainY, arguments, timer)

	# TODO logging where should the stuff below go? somewhere in UniversalInterface?
#	if sendToLog:
#		logManager = LogManager()
#		funcString = interface.getCanonicalName() + '.' + learnerName
#		logManager.logRun(trainX, testX, funcString, None, None, timer, extraInfo=arguments)

	return trainedLearner

def trainAndApply(learnerName, trainX, trainY=None, testX=None, arguments={}, output=None, scoreMode='label', multiClassStrategy='default', sendToLog=True):
	(package, learnerName) = _unpackLearnerName(learnerName)
	fullName = package + '.' + learnerName
	_validData(trainX, trainY, testX, None, [False, False])
	_validScoreMode(scoreMode)
	_validMultiClassStrategy(multiClassStrategy)
	_validArguments(arguments)

	if testX is None:
		testX = trainX

	if sendToLog:
		timer = Stopwatch()
	else:
		timer = None

	interface = findBestInterface(package)

	results = None
	if multiClassStrategy != 'default':
		trialResult = checkClassificationStrategy(interface.trainAndApply, learnerName, arguments)
		# We only use our own version of the strategy if the internal method is different than
		# what we want.
		if multiClassStrategy == 'OneVsAll' and trialResult != 'OneVsAll':
			results = trainAndApplyOneVsAll(fullName, trainX, trainY, testX, arguments=arguments, scoreMode=scoreMode, timer=timer)
		if multiClassStrategy == 'OneVsOne' and trialResult != 'OneVsOne':
			results = trainAndApplyOneVsOne(fullName, trainX, trainY, testX, arguments=arguments, scoreMode=scoreMode, timer=timer)
	
	if results is None:
		results = interface.trainAndApply(learnerName, trainX, trainY, testX, arguments, output, scoreMode, timer)

	if sendToLog:
		logManager = LogManager()
		funcString = interface.getCanonicalName() + '.' + learnerName
		logManager.logRun(trainX, testX, funcString, None, None, timer, extraInfo=arguments)

	return results


def trainAndTest(learnerName, trainX, trainY, testX, testY, performanceFunction, output=None, scoreMode='label', negativeLabel=None, multiClassStrategy='default', sendToLog=False, **arguments):
	"""
	Supply optional algorithm parameters via **arguments as kwargs

	For each permutation of 'arguments' (more below), trainAndTest uses cross validation to generate a
	performance score for the algorithm, given the particular argument permutation.
	The argument permutation that performed best cross validating over the training data
	is then used as the lone argument for training on the whole training data set.
	Finally, the learned model generates predictions for the testing set, and the
	performance of those predictions is calculated and returned.

	If no additional arguments are supplied via **arguments, then trainAndTest just returns
	the performance of the algorithm with default arguments on the testing data.

	ARGUMENTS:
	
	learnerName: training algorithm to be called, in the form 'package.algorithmName'.

	trainX: data set to be used for training (as some form of Base object)

	testX: data set to be used for testing (as some form of Base object)
	
	trainY: used to retrieve the known class labels of the traing data. Either
	contains the labels themselves (as a Base object) or an index (numerical or string) 
	that defines their locale in the trainX object
	
	testY: used to retrieve the known class labels of the test data. Either
	contains the labels themselves (as a Base object) or an index (numerical or string) 
	that defines their locale in the testX object.  If left blank, trainAndTest() assumes 
	that testY is the same as trainY.
	
	negativeLabel: Argument required if performanceFunction contains proportionPercentPositive90
	or proportionPercentPositive50.  Identifies the 'negative' label in the data set.  Only
	applies to data sets with 2 class labels.

	multiClassStrategy: may only be 'default' 'OneVsAll' or 'OneVsOne'
	
	sendToLog: optional boolean valued parameter; True meaning the results should be logged

	arguments: optional arguments to be passed to the function specified by 'algorithm'
	The syntax for prescribing different arguments for algorithm:
	**arguments of the form arg1=(1,2,3), arg2=(4,5,6)
	correspond to permutations/argument states with one element from arg1 and one element 
	from arg2, such that an example generated permutation/argument state would be "arg1=2, arg2=4"
	"""
	_validData(trainX, trainY, testX, testY, [True, True])
	
	#if testY is empty, attempt to use trainY
	if testY is None and isinstance(trainY, (str, unicode, int)):
		testY = trainY

	trainY = copyLabels(trainX, trainY)
	testY = copyLabels(testX, testY)

	#if we are logging this run, we need to start the timer
	if sendToLog:
		timer = Stopwatch()
		timer.start('crossValidateReturnBest')
	#sig (learnerName, X, Y, performanceFunction, numFolds=10, scoreMode='label', negativeLabel=None, sendToLog=False, foldSeed=DEFAULT_SEED, maximize=False, **arguments):
	bestArgument, bestScore = UML.crossValidateReturnBest(learnerName, trainX, trainY, performanceFunction, scoreMode=scoreMode, sendToLog=False, **arguments)

	if sendToLog:
		timer.stop('crossValidateReturnBest')
		timer.start('trainAndApply')

	predictions = trainAndApply(learnerName, trainX, trainY, testX, bestArgument, output, scoreMode, multiClassStrategy, sendToLog)

	if sendToLog:
		timer.stop('trainAndApply')
		timer.start('errorComputation')

	performance = computeMetrics(testY, None, predictions, performanceFunction, negativeLabel)

	if sendToLog:
		timer.stop('errorComputation')

	if sendToLog:
		logManager = LogManager()
		logManager.logRun(trainX, testX, learnerName, [performanceFunction], [performance], timer,)

	return performance



