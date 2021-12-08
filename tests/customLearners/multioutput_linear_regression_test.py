import nimble
from nimble.learners import MultiOutputLinearRegression

# test for failure to import?

def test_MultiOutputLinearRegression_simple():
    data = [[0, 1, 0], [0, 0, 2], [12, 0, 0], [2, 2, 2]]
    trainX = nimble.data(data)

    data = [[10, -10], [2, -2], [1200, -1200], [222, -222]]
    trainY = nimble.data(data)

    trainY0 = trainY.features.copy(0)
    trainY1 = trainY.features.copy(1)

    data = [[5, 5, 5], [0, 0, 1]]
    testX = nimble.data(data)

    name = 'scikitlearn.LinearRegression'
    ret0 = nimble.trainAndApply(name, trainX=trainX, trainY=trainY0, testX=testX)
    ret1 = nimble.trainAndApply(name, trainX=trainX, trainY=trainY1, testX=testX)

    for value in ['nimble.MultiOutputLinearRegression',
                  MultiOutputLinearRegression]:
        retMulti = nimble.trainAndApply(value, trainX=trainX, trainY=trainY, testX=testX)

        assert retMulti[0, 0] == ret0[0]
        assert retMulti[0, 1] == ret1[0]
        assert retMulti[1, 0] == ret0[1]
        assert retMulti[1, 1] == ret1[1]
