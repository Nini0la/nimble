

from allowImports import boilerplate
boilerplate()

if __name__ == "__main__":

	import numpy

	import UML
	from UML.customLearners.ridge_regression import RidgeRegression
	from UML.metrics import rootMeanSquareError as RMSE

	# register your custom learner, in a custom package named 'custom'
	UML.registerCustomLearner("custom", RidgeRegression)

	# produce some simple linear data
	trainPoints = 10
	testPoints = 5
	feats = 3
	targetCoefs = numpy.random.rand(feats, 1)
	trainXRaw = numpy.random.randint(-10, 10, (trainPoints, feats))
	trainYRaw = trainXRaw.dot(targetCoefs)
	testXRaw = numpy.random.randint(-10, 10, (testPoints, feats))
	testYRaw = testXRaw.dot(targetCoefs)

	# encapsulate in UML data objects
	trainX = UML.createData("Matrix", trainXRaw)
	trainY = UML.createData("Matrix", trainYRaw)
	testX = UML.createData("Matrix", testXRaw)
	testY = UML.createData("Matrix", testYRaw)

	# an example of getting a TrainedLearner and querying its attributes. In
	# RidgeRegression's case, we check the learned coefficients, named 'w'
	trained = UML.train("custom.RidgeRegression", trainX, trainY, arguments={'lamb':0})
	print "Coefficients:"
	print trained.getAttributes()['w']

	# Two ways of getting predictions
	pred1 = trained.apply(testX, arguments={'lamb':0})
	pred2 = UML.trainAndApply("custom.RidgeRegression", trainX, trainY, testX, arguments={'lamb':0})
	assert pred1.isIdentical(pred2)

	# Using cross validation to explicitly determine a winning argument set
	bestArgument, bestScore = UML.crossValidateReturnBest("custom.RidgeRegression", trainX, trainY, RMSE, lamb=(0,.5,1))
	print "Best argument set: " + str(bestArgument)
	print "Best score: " + str(bestScore)

	# Currently, testing can only be done through the top level function trainAndTest()
	# Also: arguments to the learner are given in the python **kwargs style, not as
	# an explicit dict like  seen above.
	# Using lamb = 1 in this case so that there actually are errors
	error = UML.trainAndTest("custom.RidgeRegression", trainX, trainY, testX, testY, RMSE, lamb=1)
	print "rootMeanSquareError of predictions with lamb=1: " + str(error)




	

