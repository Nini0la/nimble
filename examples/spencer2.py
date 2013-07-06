

from allowImports import boilerplate
boilerplate()
import UML


if __name__ == "__main__":

	from UML import crossValidateReturnBest
	from UML import loadTrainingAndTesting
	from UML import functionCombinations
	from UML import create
	from UML import runAndTest
	from UML.metrics import classificationError


	print "UML dir", dir(UML)
	# path to input specified by command line argument
	pathIn = "datasets/sparseSample.mtx"
	allData = create('coo', pathIn, fileType="mtx")

	print "data loaded"

	yData = allData.extractFeatures([5])
	xData = allData

	yData = yData.toDenseMatrixData()

	print "data formatted"

	# setup parameters we want to cross validate over, and the functions and metrics to evaluate
	toRun = 'runAndTest("shogun.MulticlassOCAS", trainX, testX, trainY, testY, {"C":<1.0>}, [classificationError])'
	runs = functionCombinations(toRun)
	extraParams = {'runAndTest':runAndTest, 'classificationError':classificationError}

	print "runs prepared"

	bestFunction, performance = crossValidateReturnBest(xData, yData, runs, mode='min', numFolds=5, extraParams=extraParams)
	print bestFunction
	print performance
