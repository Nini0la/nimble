"""
Unit tests for keras_interface.py

"""

from __future__ import absolute_import

import UML
from UML import createData

import numpy as np

def testKerasAPI():
    """
    Test Keras can handle a variety of arguments passed to all major learning functions
    """
    x_train = createData('Matrix', np.random.random((1000, 20)))
    y_train = createData('Matrix', np.random.randint(2, size=(1000, 1)))

    layer0 = {'type':'Dense', 'units':64, 'activation':'relu', 'input_dim':20}
    layer1 = {'type':'Dropout', 'rate':0.5}
    layer2 = {'type':'Dense', 'units':1, 'activation':'sigmoid'}
    layers = [layer0, layer1, layer2]

    #####test fit
    mym = UML.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer='sgd',
                    layers=layers, loss='binary_crossentropy', metrics=['accuracy'],
                    epochs=20, batch_size=128, lr=0.1, decay=1e-6, momentum=0.9,
                    nesterov=True)

    #######test apply
    x = mym.apply(testX=x_train)

    #########test trainAndApply
    x = UML.trainAndApply('keras.Sequential', trainX=x_train, trainY=y_train, testX=x_train,
                          optimizer='sgd', layers=layers, loss='binary_crossentropy',
                          metrics=['accuracy'], epochs=20, batch_size=128, lr=0.1,
                          decay=1e-6, momentum=0.9, nesterov=True)

    #########test trainAndTest
    x = UML.trainAndTest('keras.Sequential', trainX=x_train, testX=x_train, trainY=y_train,
                         testY=y_train, optimizer='sgd', layers=layers,
                         loss='binary_crossentropy', metrics=['accuracy'], epochs=20,
                         batch_size=128, lr=0.1, decay=1e-6, momentum=0.9, nesterov=True,
                         performanceFunction=UML.calculate.loss.rootMeanSquareError)

    #########test CV
    bestArgument, bestScore = UML.crossValidateReturnBest("keras.Sequential", X=x_train, Y=y_train, optimizer='sgd', layers=layers, loss='binary_crossentropy', metrics=['accuracy'], epochs=20, batch_size=128, lr=0.1, decay=1e-6, momentum=0.9, nesterov=True, performanceFunction=UML.calculate.loss.rootMeanSquareError)

def testKerasIncremental():
    """
    Test Keras can handle and incrementalTrain call
    """
    x_train = createData('Matrix', np.random.random((1000, 20)))
    y_train = createData('Matrix', np.random.randint(2, size=(1000, 1)))

    layer0 = {'type':'Dense', 'units':64, 'activation':'relu', 'input_dim':20}
    layer1 = {'type':'Dropout', 'rate':0.5}
    layer2 = {'type':'Dense', 'units':1, 'activation':'sigmoid'}
    layers = [layer0, layer1, layer2]

    #####test fit
    mym = UML.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer='sgd',
                    layers=layers, loss='binary_crossentropy', metrics=['accuracy'],
                    epochs=20, batch_size=128, lr=0.1, decay=1e-6, momentum=0.9,
                    nesterov=True)

    #####test incrementalTrain
    mym.incrementalTrain(x_train, y_train)

    x = mym.apply(testX=x_train)
    assert len(x.points) == len(x_train.points)

def testKeras_Sparse_FitGenerator():
    """
    Test Keras on Sparse data; uses different training method - fit_generator
    """
    x_data = np.random.random((20, 7))
    y_data = np.random.randint(2, size=(20, 1))

    x_train = createData('Sparse', x_data)
    y_train = createData('Matrix', y_data)

    layer0 = {'type':'Dense', 'units':64, 'activation':'relu', 'input_dim':7}
    layer1 = {'type':'Dropout', 'rate':0.5}
    layer2 = {'type':'Dense', 'units':1, 'activation':'sigmoid'}
    layers = [layer0, layer1, layer2]

    mym = UML.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer='sgd',
                    layers=layers, loss='binary_crossentropy', metrics=['accuracy'],
                    epochs=2, batch_size=1, lr=0.1, decay=1e-6, momentum=0.9, nesterov=True,
                    steps_per_epoch=20, max_queue_size=1, shuffle=False, steps=20)

    x = mym.apply(testX=x_train)
    assert len(x.points) == len(x_train.points)
