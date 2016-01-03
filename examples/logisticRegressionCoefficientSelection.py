"""
An example script defining a custom learner and running it on the
data given via a path on the command line.

"""

from allowImports import boilerplate
boilerplate()

import sys
import numpy

import UML
from UML.customLearners import CustomLearner
from UML.helpers import generateClassificationData
from UML.calculate import fractionIncorrect
from UML.exceptions import ArgumentException

class LogisticRegressionSelectByRegularization(CustomLearner):
	learnerType = "classification"

	def train(
			self, trainX, trainY, desiredNonZero, verboseStandardOut=False,
			allowSubLogging=False):
		if desiredNonZero > trainX.featureCount:
			desiredNonZero = trainX.featureCount

		def countNonZero(tl):
			coefs = tl.getAttributes()['coef_']
			return numpy.count_nonzero(coefs)

		# Define those arguments that will be fixed over all calls
		arguments = {}
		arguments['penalty'] = "l1"

		inC = 1
		sklLogReg = "scikitlearn.LogisticRegression"
		trained = UML.train(sklLogReg, trainX, trainY, C=inC, useLog=allowSubLogging, **arguments)

		# the first entry will be our downward multiplicative adjustment,
		# the second entry will be our upward adjustment
		adjustment = [3./4, 5./4]
		iteration = 1
		numNZ = countNonZero(trained)
		
		# we stop when the number of non-zero coefficients is precisely
		# what we want it to be
		while numNZ != desiredNonZero:
			# determine which adjustment is appropriate
			if numNZ < desiredNonZero:
				multiplier = adjustment[1]
			else:  # numNZ > desiredNonZero
				multiplier = adjustment[0]
			inC = inC * multiplier
			
			trained = UML.train(sklLogReg, trainX, trainY, C=inC,  useLog=allowSubLogging, **arguments)
			numNZ = countNonZero(trained)
			iteration += 1

			if verboseStandardOut:
				print '\n# iteration #: ' + str(iteration)
				print 'multiplier: ' + str(multiplier)
				print 'inC: ' + str(inC)
				print 'nz: '+str(numpy.count_nonzero(trained.getAttributes()['coef_']))

		self._trained = trained
		# expose everything from the underlying learner
		toExpose = trained.getAttributes()
		for key in toExpose:
			setattr(self, key, toExpose[key])

	def apply(self, testX):
		return self._trained.apply(testX)



class LogisticRegressionSelectByOmission(CustomLearner):
	learnerType = "classification"

	def train(self, trainX, trainY, numberToOmit, method, C, **kwargs):
		accepted = ["least magnitude", "highest magnitude", "least value",
				"highest value"]

		kwargs['C'] = C

		side = method.split(" ")[0]
		ordering = method.split(" ")[1]

		if method not in accepted:
			pretty = UML.exceptions.prettyListString(accepted)
			raise ArgumentException("method must be in: " + pretty)

		# do NOT log the sub calls
		kwargs['useLog'] = False

		sklLogReg = "scikitlearn.LogisticRegression"
		trained = UML.train(sklLogReg, trainX, trainY, **kwargs)

		coefs = trained.getAttributes()['coef_'].flatten()

#		print "\norig coefs\n" + str(coefs)

		if ordering == 'magnitude':
			coefs = map(abs, coefs)
#			print "\nafter abs\n" + str(coefs)

		withIndices = zip(coefs, range(len(coefs)))
		withIndices.sort(key=lambda x:x[0])

#		print "\nsorted\n" + str(withIndices)

		# retrain without those features????
		removalIndices = [withIndices[n][1] for n in range(numberToOmit)]

#		print "\nremovalIndices\n" + str(removalIndices)

		self.wantedIndices = list(set(xrange(trainX.featureCount)) - set(removalIndices))

#		print self.wantedIndices
#		print len(self.wantedIndices)

		inTrainX = trainX.copyFeatures(self.wantedIndices)
		self._trained = UML.train(sklLogReg, inTrainX, trainY, **kwargs)

#		print "\nnew coefs\n" + str(self._trained.getAttributes()['coef_'].flatten())

	def apply(self, testX):
		inTestX = testX.copyFeatures(self.wantedIndices)
		return self._trained.apply(inTestX, useLog=False)





def sanityCheck(trainX, totalScores):
	assert trainX.featureCount == 84

	for name in trainX.getFeatureNames():
		assert name[-3:] == "(M)" or name[-3:] == "(F)"

	# gotta fix data's __getitem__ so we can just pass python's sum function
	def summer(point):
		total = 0
		for value in point:
			total += value
		return total

	summed = trainX.applyToPoints(summer, inPlace=False)
	summed.setFeatureName(0, "totalScorePosOrNeg")
	assert summed == totalScores

def seperateData(dataAll, omitCultureQuestions):
	# grab the features we want to be in the training data; including raw
	# data that we may later choose to omit
	nameOfFirst = "I do not enjoy watching dance performances. (M)"
	indexOfFirst = dataAll.getFeatureIndex(nameOfFirst)

	usedData = dataAll.extractFeatures(start=indexOfFirst, end=None)
	usedData.appendFeatures(dataAll.copyFeatures("isMale"))
	usedData.appendFeatures(dataAll.copyFeatures("InTestSet"))

	if omitCultureQuestions:
		toOmit = []
		toOmit.append("I do not enjoy watching dance performances. (M)")
		toOmit.append(" I would be good at rescuing someone from a burning building. (M)")
		toOmit.append(" I am interested in science. (M)")
		toOmit.append(" I find political discussions interesting. (M)")
		toOmit.append(" I face danger confidently. (M)")
		toOmit.append(" I do not like concerts. (M)")
		toOmit.append(" I do not enjoy going to art museums. (M)")
		toOmit.append(" I would fear walking in a high-crime part of a city. (F)")
		toOmit.append(" I begin to panic when there is danger. (F)")
		usedData.extractFeatures(toOmit)

	print "Splitting data into training and testing..."

	def selectInTestSet(point):
		if point["InTestSet"] > 0:
			return True
		return False

	testingSet = usedData.extractPoints(selectInTestSet)
	testY = testingSet.extractFeatures("isMale")
	testingSet.extractFeatures("InTestSet")
	testX = testingSet

	trainY = usedData.extractFeatures("isMale")
	usedData.extractFeatures("InTestSet")
	trainX = usedData

	return trainX, trainY, testX, testY

def printCoefficients(trainedLearner):
	coefs = trainedLearner.getAttributes()["coef_"]
#	intercept = trainedLearner.getAttributes()["intercept_"]
	coefs = coefs.flatten()
	chosen = []
	chosenCoefs = []
	for i in xrange(len(coefs)):
		value = coefs[i]
		if value != 0:
			chosen.append(trainX.getFeatureName(i))
			chosenCoefs.append(coefs[i])

	# display those questions which were the most useful
	print "\n"
	i = 1
	for question, coef in zip(chosen, chosenCoefs):
		print str(i).ljust(3) + "    " + str(round(coef,2)).ljust(8) + question.strip()
		i = i + 1

if __name__ == "__main__":

	# Some variables to control the flow of the program
	defaultFile = "/Users/spencer2/Dropbox/Spencer/Work/ClearerThinking.org/Programs and modules/Gender continuum test/gender continuum train and test ready to predict.csv"
	omitCultureQuestions = True
	desiredNonZeroCoefficients = 75  # 50
	performSanityCheck = False

	UML.registerCustomLearner("custom", LogisticRegressionSelectByRegularization)
	UML.registerCustomLearner("custom", LogisticRegressionSelectByOmission)

	if len(sys.argv) <= 1:
		origFileName = defaultFile
	else:
		origFileName = sys.argv[1]
	
	dataAll = UML.createData("Matrix", origFileName, featureNames=True, fileType='csv',
		ignoreNonNumericalFeatures=True)

	# call helper to remove extraneous features, omit undesired
	# ones, and to seperate into training and testing sets according
	# to the 'InTestSet' feature.
	trainX, trainY, testX, testY = seperateData(dataAll, omitCultureQuestions)

	trainX.name = "Training Data"
	trainY.name = "Training Labels"
	testX.name = "Testing Data"
	testY.name = "Testing Labels"

	# Check some of the expectations we had on the data to make sure
	# we've extracted the right stuff
	if performSanityCheck:
		totalScores = dataAll.extractFeatures("totalScorePosOrNeg")
		sanityCheck(trainX, totalScores)  # defined above __main__

	print ""
	print "Train points: " + str(trainX.pointCount) 
	print "Test points: " + str(testX.pointCount) 
	print "Starting number of features: " + str(trainX.featureCount)
	print ""


	predictionPossibilities = []
	predictionPossibilities.append("SVC full data out-sample only")  # 0
	predictionPossibilities.append("Prediction: LogReg with L1")  # 1
	predictionPossibilities.append("Prediction: LogReg with L2")  # 2
	predictionPossibilities.append("Prediction: SVM Linear kernel")  # 3
	predictionPossibilities.append("Prediction: SVM rbf kernel")  # 4
	predictionPossibilities.append("Prediction: SVM with poly kernel deg 2")  # 5
	predictionPossibilities.append("Prediction: SVM with poly kernel deg 3")  # 6

	predictionPossibilities.append("Coefficient selection by regularization")  # 7
	predictionPossibilities.append("Coefficient removal by least magnitude")  # 8
	predictionPossibilities.append("Coefficient removal by least value")  # 9
	predictionMode = predictionPossibilities[8]

	print "Learning..."
	print predictionMode
	print ""

	# 0
	if predictionMode == "SVC full data out-sample only":
		Cs = tuple([4**k for k in xrange(-8,8)])
#		bestError = UML.trainAndTest("scikitlearn.SVC", trainX, trainY, testX, testY, performanceFunction=fractionIncorrect, C=0.3) #19.7% out of sample error
#		bestError = UML.trainAndTest("scikitlearn.SVC", trainX, trainY, testX, testY, performanceFunction=fractionIncorrect, kernel="poly", degree=2, coef0=1, C=0.01) #19.2%
		bestError = UML.trainAndTest("scikitlearn.SVC", trainX, trainY, testX, testY, performanceFunction=fractionIncorrect, kernel="poly", degree=3, coef0=1, C=0.1) 
		print "bestError out of sample: ", str(round(bestError*100,1)) + "%"
		sys.exit(0)
	# 1
	elif predictionMode == "Prediction: LogReg with L1":
		name = "scikitlearn.LogisticRegression"
		cVals = tuple([100. / (10**n) for n in range(7)])
		print "Cross validated over C with values of: " + str(cVals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, penalty='l1',
			performanceFunction=fractionIncorrect)
	# 2
	elif predictionMode == "Prediction: LogReg with L2":
		name = "scikitlearn.LogisticRegression"
		cVals = tuple([100. / (10**n) for n in range(7)])
		print "Cross validated over C with values of: " + str(cVals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, penalty='l2',
			performanceFunction=fractionIncorrect)
	# 3
	elif predictionMode == "Prediction: SVM Linear kernel":
		name = "scikitlearn.SVC"
		cVals = tuple([100. / (10**n) for n in range(7)])

		print "Cross validated over C with values of: " + str(cVals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, kernel='linear', performanceFunction=fractionIncorrect)
	# 4
	elif predictionMode == "Prediction: SVM rbf kernel":
		name = "scikitlearn.SVC"
		cVals = tuple([100. / (10**n) for n in range(7)])
		gamVals = tuple([100. / (10**n) for n in range(7)])

		print "Cross validated over C with values of: " + str(cVals)
		print "Cross validated over gamma with values of: " + str(gamVals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, gamma=gamVals, kernel='rbf', performanceFunction=fractionIncorrect)
	# 5
	elif predictionMode == "Prediction: SVM with poly kernel deg 2":
		name = "scikitlearn.SVC"
		cVals = tuple([100. / (10**n) for n in range(7)])
		coef0Vals = tuple([100. / (10**n) for n in range(7)])

		print "Cross validated over C with values of: " + str(cVals)
		print "Cross validated over coef0 with values of: " + str(coef0Vals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, coef0=coef0Vals, kernel='poly', degree=2,
			performanceFunction=fractionIncorrect)
	# 6
	elif predictionMode == "Prediction: SVM with poly kernel deg 3":
		name = "scikitlearn.SVC"
		cVals = tuple([100. / (10**n) for n in range(7)])
		coef0Vals = tuple([100. / (10**n) for n in range(7)])

		print "Cross validated over C with values of: " + str(cVals)
		print "Cross validated over coef0 with values of: " + str(coef0Vals)
		trainedLearner = UML.train(
			name, trainX, trainY, C=cVals, coef0=coef0Vals, kernel='poly', degree=3,
			performanceFunction=fractionIncorrect)
	# 7
	elif predictionMode == "Coefficient selection by regularization":
		name = "custom.LogisticRegressionSelectByRegularization"
#		print "Finding exactly " + str(desiredNonZeroCoefficients) + " coefficients..."
		trainedLearner = UML.train(name, trainX, trainY, desiredNonZero=desiredNonZeroCoefficients)
	# 8
	elif predictionMode == "Coefficient removal by least magnitude":
		name = "custom.LogisticRegressionSelectByOmission"
		cVals = tuple([100. / (10**n) for n in range(7)])
#		cVals = (100., 55., 10., 5.5, 1., 0.55, 0.1, 0.055, 0.01, 0.0055, 0.001, 0.00055, 0.0001)
#		cVals = 1

		print "Cross validated over C with values of: " + str(cVals)

		results = []
		omit = [0,10,15,20,25,30,35,40,45,50,55,60,65,70]
		for num in omit:
			trainedLearner = UML.train(
					name, trainX, trainY, numberToOmit=num, method="least magnitude",
					C=cVals, performanceFunction=fractionIncorrect)
			result = trainedLearner.test(testX, testY,
				performanceFunction=fractionIncorrect)
			results.append(result)
	
		pnames = ['number Omitted', 'out sample error: fractionIncorrect']
		objName = predictionMode
		raw = UML.createData("List", [omit, results], pointNames=pnames, name=objName)
		figurePath = './results-least_magnitude.png'
		raw.plotPointAgainstPoint(0,1, outPath=figurePath)
		exit(0)
	# 9
	elif predictionMode == "Coefficient removal by least value":
		name = "custom.LogisticRegressionSelectByOmission"
		cVals = tuple([100. / (10**n) for n in range(7)])
#		cVals = (100., 55., 10., 5.5, 1., 0.55, 0.1, 0.055, 0.01, 0.0055, 0.001, 0.00055, 0.0001)
#		cVals = 1

		print "Cross validated over C with values of: " + str(cVals)

		results = []
		omit = [0,10,15,20,25,30,35,40,45,50,55,60,65,70]
		for num in omit:
			trainedLearner = UML.train(
					name, trainX, trainY, numberToOmit=num, method="least value",
					C=cVals, performanceFunction=fractionIncorrect)
			result = trainedLearner.test(testX, testY, performanceFunction=fractionIncorrect)
			print result
			results.append(result)
	
		pnames = ['number Omitted', 'out sample error: fractionIncorrect']
		objName = predictionMode
		raw = UML.createData("List", [omit, results], pointNames=pnames, name=objName)
		figurePath = './results-least_value.png'
		raw.plotPointAgainstPoint(0,1, outPath=figurePath)
		exit(0)
	else:
		raise Exception("Bad prediction mode!")
	
	# grab the feature names associated with the non-zero coefficients
#	printCoefficients(trainedLearner)

	#Now measure the accuracy of the model
	print "\n\n"
	errorOutSample = trainedLearner.test(testX, testY, performanceFunction=fractionIncorrect)
	print "Out of sample error rate: " + str(round(errorOutSample*100,1)) + "%"
	errorInSample = trainedLearner.test(trainX, trainY, performanceFunction=fractionIncorrect)
	print "In sample error rate: " + str(round(errorInSample*100,1)) + "%"
	print ""

	exit(0)