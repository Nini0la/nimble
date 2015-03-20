
from nose.tools import raises

import UML

from UML import createData
from UML import trainAndTest

from UML.calculate import fractionIncorrect
from UML.randomness import pythonRandom
from UML.exceptions import ArgumentException



#todo set seed and verify that you can regenerate error several times with
#crossValidateReturnBest, trainAndApply, and your own computeMetrics
def test_trainAndTest():
	"""Assert valid results returned for different arguments to the algorithm:
	with default ie no args
	with one argument for the algorithm
	with multiple values for one argument for the algorithm (triggers CV)
	with multiple values and a small dataset (triggers CV with intelligent folding)
	"""
	variables = ["x1", "x2", "x3", "label"]
	numPoints = 20
	data1 = [[pythonRandom.random(), pythonRandom.random(), pythonRandom.random(), int(pythonRandom.random()*3)+1] for _pt in xrange(numPoints)]
	# data1 = [[1,0,0,1], [0,1,0,2], [0,0,1,3], [1,0,0,1], [0,1,0,2], [0,0,1,3], [1,0,0,1], [0,1,0,2], [0,0,1,3], [1,0,0,1], [0,1,0,2], [0,0,1,3], [1,0,0,1],[0,1,0,2], [0,0,1,3], [1,0,0,3], [0,1,0,1], [0,0,1,2]]
	trainObj1 = createData('Matrix', data=data1, featureNames=variables)

	testData1 = [[1, 0, 0, 1],[0, 1, 0, 2],[0, 0, 1, 3]]
	testObj1 = createData('Matrix', data=testData1)

	#with default ie no args
	runError = trainAndTest('Custom.KNNClassifier', trainObj1, 3, testObj1, 3, fractionIncorrect)
	assert isinstance(runError, float)

	#with one argument for the algorithm
	runError = trainAndTest('Custom.KNNClassifier', trainObj1, 3, testObj1, 3, fractionIncorrect, k=1)
	assert isinstance(runError, float)

	#with multiple values for one argument for the algorithm
	runError = trainAndTest('Custom.KNNClassifier', trainObj1, 3, testObj1, 3, fractionIncorrect, k=(1,2))
	assert isinstance(runError, float)

	#with small data set
	data1 = [[1,0,0,1], [0,1,0,2], [0,0,1,3], [1,0,0,1], [0,1,0,2]]
	trainObj1 = createData('Matrix', data=data1, featureNames=variables)
	runError = trainAndTest('Custom.KNNClassifier', trainObj1, 3, testObj1, 3, fractionIncorrect, k=(1,2))
	assert isinstance(runError, float)




def test_multioutput_learners_callable_from_all():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	trainY0 = trainY.copyFeatures(0)
	trainY1 = trainY.copyFeatures(1)

	data = [[5,5,5],[0,0,1]]
	testX = UML.createData('Matrix', data)

	data = [[555,-555], [1,-1]]
	testY = UML.createData('Matrix', data)

	testY0 = testY.copyFeatures(0)
	testY1 = testY.copyFeatures(1)

	testName = 'Custom.MultiOutputRidgeRegression'
	wrappedName = 'Custom.RidgeRegression'

	metric = UML.calculate.meanFeaturewiseRootMeanSquareError

	# trainAndApply()
	ret_TA_multi = UML.trainAndApply(testName, trainX=trainX, trainY=trainY, testX=testX, lamb=1)
	ret_TA_0 = UML.trainAndApply(wrappedName, trainX=trainX, trainY=trainY0, testX=testX, lamb=1)
	ret_TA_1 = UML.trainAndApply(wrappedName, trainX=trainX, trainY=trainY1, testX=testX, lamb=1)

	#train, then 
	TLmulti = UML.train(testName, trainX=trainX, trainY=trainY, lamb=1)
	TL0 = UML.train(wrappedName, trainX=trainX, trainY=trainY0, lamb=1)
	TL1 = UML.train(wrappedName, trainX=trainX, trainY=trainY1, lamb=1)

	# tl.apply()
	ret_TLA_multi = TLmulti.apply(testX)
	ret_TLA_0 = TL0.apply(testX)
	ret_TLA_1 = TL1.apply(testX)

	# trainAndTest()
	ret_TT_multi = UML.trainAndTest(testName, trainX=trainX, trainY=trainY, testX=testX, testY=testY, performanceFunction=metric, lamb=1)
	ret_TT_0 = UML.trainAndTest(wrappedName, trainX=trainX, trainY=trainY0, testX=testX, testY=testY0, performanceFunction=metric, lamb=1)
	ret_TT_1 = UML.trainAndTest(wrappedName, trainX=trainX, trainY=trainY1, testX=testX, testY=testY1, performanceFunction=metric, lamb=1)

	# tl.test()
	ret_TLT_multi = TLmulti.test(testX, testY, metric)
	ret_TLT_0 = TL0.test(testX, testY0, metric)
	ret_TLT_1 = TL1.test(testX, testY1, metric)

	# confirm consistency

	# individual columns in multioutput returns should match their single output
	# counterparts
	assert ret_TA_multi[0,0] == ret_TA_0[0]
	assert ret_TA_multi[0,1] == ret_TA_1[0]
	assert ret_TA_multi[1,0] == ret_TA_0[1]
	assert ret_TA_multi[1,1] == ret_TA_1[1]

	assert ret_TLA_multi[0,0] == ret_TLA_0[0]
	assert ret_TLA_multi[0,1] == ret_TLA_1[0]
	assert ret_TLA_multi[1,0] == ret_TLA_0[1]
	assert ret_TLA_multi[1,1] == ret_TLA_1[1]

	assert ret_TT_multi == ret_TT_0
	assert ret_TT_multi == ret_TT_1

	assert ret_TLT_multi == ret_TLT_0
	assert ret_TLT_multi == ret_TLT_1

	# using trainAndApply vs getting a trained learner shouldn't matter
	assert ret_TA_multi[0,0] == ret_TLA_0[0]
	assert ret_TA_multi[0,1] == ret_TLA_1[0]
	assert ret_TA_multi[1,0] == ret_TLA_0[1]
	assert ret_TA_multi[1,1] == ret_TLA_1[1]

	assert ret_TLA_multi[0,0] == ret_TA_0[0]
	assert ret_TLA_multi[0,1] == ret_TA_1[0]
	assert ret_TLA_multi[1,0] == ret_TA_0[1]
	assert ret_TLA_multi[1,1] == ret_TA_1[1]

	assert ret_TT_multi == ret_TLT_0
	assert ret_TT_multi == ret_TLT_1

	assert ret_TLT_multi == ret_TT_0
	assert ret_TLT_multi == ret_TT_1



@raises(ArgumentException)
def test_train_multiclassStrat_disallowed_multioutput():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	testName = 'Custom.MultiOutputRidgeRegression'

	TLmulti = UML.train(testName, trainX=trainX, trainY=trainY, multiClassStrategy='OneVsOne', lamb=1)


@raises(ArgumentException)
def test_trainAndApply_scoreMode_disallowed_multiOutput():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	data = [[5,5,5],[0,0,1]]
	testX = UML.createData('Matrix', data)

	testName = 'Custom.MultiOutputRidgeRegression'

	UML.trainAndApply(testName, trainX=trainX, trainY=trainY, testX=testX, scoreMode="allScores", lamb=1)


@raises(ArgumentException)
def test_trainAndApply_multiClassStrat_disallowed_multiOutput():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	data = [[5,5,5],[0,0,1]]
	testX = UML.createData('Matrix', data)

	testName = 'Custom.MultiOutputRidgeRegression'

	UML.trainAndApply(testName, trainX=trainX, trainY=trainY, testX=testX, multiClassStrategy="OneVsOne", lamb=1)


@raises(ArgumentException)
def test_trainAndTest_scoreMode_disallowed_multioutput():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	data = [[5,5,5],[0,0,1]]
	testX = UML.createData('Matrix', data)

	data = [[555,-555], [1,-1]]
	testY = UML.createData('Matrix', data)

	testName = 'Custom.MultiOutputRidgeRegression'
	metric = UML.calculate.meanFeaturewiseRootMeanSquareError

	UML.trainAndTest(testName, trainX=trainX, trainY=trainY, testX=testX, testY=testY, performanceFunction=metric, scoreMode="allScores", lamb=1)


@raises(ArgumentException)
def test_trainAndTest_multiclassStrat_disallowed_multioutput():
	data = [[0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2], [12,0,0], [2,2,2], [0,1,0], [0,0,2],]
	trainX = UML.createData('Matrix', data)

	data = [[10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2], [1200, -1200], [222,-222], [10, -10], [2, -2]]
	trainY = UML.createData('Matrix', data)

	data = [[5,5,5],[0,0,1]]
	testX = UML.createData('Matrix', data)

	data = [[555,-555], [1,-1]]
	testY = UML.createData('Matrix', data)

	testName = 'Custom.MultiOutputRidgeRegression'
	metric = UML.calculate.meanFeaturewiseRootMeanSquareError

	UML.trainAndTest(testName, trainX=trainX, trainY=trainY, testX=testX, testY=testY, performanceFunction=metric, multiClassStrategy="OneVsOne", lamb=1)
