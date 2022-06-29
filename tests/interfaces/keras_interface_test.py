"""
Unit tests for keras_interface.py

Cannot test for expected result equality due to inability to control for
randomness in Keras.
"""
import functools
import warnings

import numpy as np
import pytest

import nimble
from nimble.core.interfaces.keras_interface import Keras
from nimble.exceptions import InvalidArgumentValue
from nimble._utility import DeferredModuleImport
from tests.helpers import raises
from tests.helpers import logCountAssertionFactory, noLogEntryExpected
from tests.helpers import skipMissingPackage
from tests.helpers import generateClassificationData

keras = DeferredModuleImport("keras")
tfKeras = DeferredModuleImport('tensorflow.keras')

try:
    from tensorflow.keras.models import Sequential
except ImportError:
    from keras.models import Sequential


keraSkipDec = skipMissingPackage('Keras')

@pytest.fixture
def optimizer():
    """
    Need fixture for parameter but value chosen by chooseOptimizer decorator.
    """

def chooseOptimizer(func):
    """
    Optimizer objects and/or parameters vary by keras API being used.
    """
    @functools.wraps(func)
    def wrapped(optimizer):
        kwOld = {'lr': 0.1, 'decay': 1e-6, 'momentum': 0.9, 'nesterov': True}
        # keras 2.3+ decay deprecated and lr changed to learning_rate
        kwNew =  {'learning_rate': 0.1, 'momentum': 0.9, 'nesterov': True}
        try:
            optimizer = nimble.Init('SGD', **kwNew)
            return func(optimizer=optimizer)
        except InvalidArgumentValue:
            pass
        # execute this case outside of the except clause; makes for
        # slightly clearer output if there is a subsequent exception
        optimizer = nimble.Init('SGD', **kwOld)
        return func(optimizer=optimizer)

    return wrapped

@keraSkipDec
@noLogEntryExpected
def test_Keras_version():
    interface = Keras()
    if tfKeras.nimbleAccessible():
        # tensorflow.keras is prioritized based on recommendation from keras
        version = tfKeras.__version__
    elif keras.nimbleAccessible():
        version = keras.__version__
    assert interface.version() == version

@keraSkipDec
@logCountAssertionFactory(4)
@chooseOptimizer
def testKerasAPIClassification(optimizer):
    """
    Test Keras can handle a variety of arguments passed to all major learning functions
    """
    numClasses = 3
    allData = generateClassificationData(numClasses, 100, 16, 5)
    ((x_train, y_train), (x_test, y_test)) = allData

    x_np = x_train.copy(to="numpyarray")
    y_np = y_train.copy(to="numpyarray")
    x_np_test = x_test.copy(to="numpyarray")
    y_np_test = y_test.copy(to="numpyarray")

    layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=16)
    layer1 = nimble.Init('Dropout', rate=0.5)
    layer2 = nimble.Init('Dense', units=numClasses, activation='softmax')
    layers = [layer0, layer1, layer2]
    #####test fit
    mym = nimble.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer=optimizer,
                       layers=layers, loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                       epochs=20, batch_size=50)
    assert mym.learnerType == 'classification'

    #######test apply
    ret_A = mym.apply(testX=x_test)

    #########test trainAndApply
    ret_TaA = nimble.trainAndApply('keras.Sequential', trainX=x_train, trainY=y_train, testX=x_test,
                             optimizer=optimizer, layers=layers, loss='sparse_categorical_crossentropy',
                             metrics=['accuracy'], epochs=20, batch_size=50)

    # Comparison to raw in-keras calculation. Different versions require different access
    try:
        if tfKeras.nimbleAccessible():
            opt_raw = getattr(tfKeras.optimizers, optimizer.name)(**optimizer.kwargs)
    except AttributeError:
        if keras.nimbleAccessible():
            opt_raw = getattr(keras.optimizers, optimizer.name)(**optimizer.kwargs)

    raw = Sequential(layers)
    raw.compile(optimizer=opt_raw, loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    raw.fit(x=x_np, y=y_np, epochs=20, batch_size=50)

    ret_raw_scores = raw.predict(x=x_np_test)
    # convert scores to labels
    ret_raw = np.argmax(ret_raw_scores, axis=1)
    ret_raw_obj = nimble.data(ret_raw.reshape(len(y_test.points),1), useLog=False)

    assert ret_A == ret_raw_obj
    assert ret_TaA == ret_raw_obj
    assert ret_raw_obj == y_test

    #########test trainAndTest
    FC = nimble.calculate.fractionCorrect
    ret_TaT = nimble.trainAndTest('keras.Sequential', FC, trainX=x_train,
                            testX=x_test, trainY=y_train, testY=y_test,
                            optimizer=optimizer, layers=layers,
                            loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                            epochs=20, batch_size=50)

    ### Comparison of trainAndTest results with raw predict results scores and evaluate
    ret_raw_test = FC(y_test, ret_raw_obj)
    raw_eval = raw.evaluate(x_np_test, y_np_test)
    assert ret_TaT == ret_raw_test
    assert ret_TaT == raw_eval[1]

@keraSkipDec
@logCountAssertionFactory(8)
@chooseOptimizer
def testKerasIncremental(optimizer):
    """
    Test Keras can handle and incrementalTrain call
    """
    numClasses = 3
    small = generateClassificationData(numClasses, 1, 16, 0)
    ((x_small, y_small), (_, _)) = small

    ret = generateClassificationData(numClasses, 100, 16, 10)
    ((x_train, y_train), (x_test, y_test)) = ret
    FC = nimble.calculate.fractionCorrect

    layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=16)
    layer1 = nimble.Init('Dropout', rate=0.5)
    layer2 = nimble.Init('Dense', units=numClasses, activation='softmax')
    layers = [layer0, layer1, layer2]
    ##### Poor Fit using a tiny portion of the data, without all of the labels represented
    # delete data associated with label 1
    x_small.points.delete(1,useLog=False)
    y_small.points.delete(1,useLog=False)
    mym = nimble.train('keras.Sequential', trainX=x_small, trainY=y_small, optimizer=optimizer,
                       layers=layers, loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                       epochs=1)

    before = mym.test(FC, x_test, y_test)

    ##### Better fit after 5 more batches over all the data, with all possible labels
    for _ in range(5):
        mym.incrementalTrain(x_train, y_train)

    after  = mym.test(FC, x_test, y_test)
    assert after > before

@keraSkipDec
@logCountAssertionFactory(2)
@chooseOptimizer
def testKeras_Sparse_Input(optimizer):
    """
    Test Keras on Sparse data; formerly uses different training method - fit_generator, should
    now usable with normal pipeline.
    """
    numClasses = 3
    allData = generateClassificationData(numClasses, 20, 16, 5)
    ((x_train, y_train), (x_test, y_test)) = allData

    layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=16)
    layer1 = nimble.Init('Dropout', rate=0.5)
    layer2 = nimble.Init('Dense', units=numClasses, activation='softmax')
    layers = [layer0, layer1, layer2]

    mym = nimble.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer=optimizer,
                       layers=layers, loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                       epochs=5, steps_per_epoch=20)

    ret = mym.apply(testX=x_test)
    assert ret == y_test

@keraSkipDec
@logCountAssertionFactory(3)
@chooseOptimizer
def testKeras_TrainedLearnerApplyArguments(optimizer):
    """ Test a keras function that accept arguments for predict"""
    x_train = nimble.data(np.random.random((1000, 20)), useLog=False)
    y_train = nimble.data(np.random.randint(2, size=(1000, 1)),
                          convertToType=float, useLog=False)

    layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=20)
    layer1 = nimble.Init('Dropout', rate=0.5)
    layer2 = nimble.Init('Dense', units=1, activation='sigmoid')
    layers = [layer0, layer1, layer2]

    # Sequential.predict takes a 'steps' argument. Default is 20
    mym = nimble.train(
        'keras.Sequential', trainX=x_train, trainY=y_train,
        optimizer=optimizer, layers=layers, loss='binary_crossentropy',
        metrics=['accuracy'], epochs=1, shuffle=False)

    # Setup the callback we'll be passing to apply
    try:
        if tfKeras.nimbleAccessible():
            CBBase = getattr(tfKeras.callbacks, "Callback")
    except AttributeError:
        if keras.nimbleAccessible():
            CBBase = getattr(keras.callbacks, "Callback")
    class CustomCallback(CBBase):
        def __init__(self):
            self.numHits = 0

        def on_predict_batch_begin(self, batch, logs=None):
            self.numHits += 1

    # using arguments parameter
    first = CustomCallback()
    assert first.numHits == 0
    _ = mym.apply(testX=x_train, arguments={'steps': 10, "callbacks":[first]})
    assert first.numHits == 10
    # using kwarguments
    second = CustomCallback()
    assert second.numHits == 0
    _ = mym.apply(testX=x_train, steps=30, callbacks=[second])
    assert second.numHits == 30

@keraSkipDec
@logCountAssertionFactory(1)
@chooseOptimizer
def testKeras_TrainedLearnerApplyArguments_exception(optimizer):
    """ Test an keras function with invalid arguments for predict"""
    x_train = nimble.data(np.random.random((1000, 20)), useLog=False)
    y_train = nimble.data(np.random.randint(2, size=(1000, 1)),
                          convertToType=float, useLog=False)

    layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=20)
    layer1 = nimble.Init('Dropout', rate=0.5)
    layer2 = nimble.Init('Dense', units=1, activation='sigmoid')
    layers = [layer0, layer1, layer2]

    # Sequential.predict does not take a 'foo' argument.
    mym = nimble.train(
        'keras.Sequential', trainX=x_train, trainY=y_train,
        optimizer=optimizer, layers=layers, loss='binary_crossentropy',
        metrics=['accuracy'], epochs=1, shuffle=False)
    with raises(InvalidArgumentValue):
        # using arguments parameter
        newArgs1 = mym.apply(testX=x_train, arguments={'foo': 50})
    with raises(InvalidArgumentValue):
        # using kwarguments
        newArgs2 = mym.apply(testX=x_train, foo=50)

@keraSkipDec
@noLogEntryExpected
@chooseOptimizer
def testKerasReproducibility(optimizer):
    tfVersion1 = False
    try:
        from tensorflow import __version__
        if __version__[:2] == '1.':
            tfVersion1 = True
    except ImportError:
        pass

    if tfVersion1:
        # can't control randomness in this version. For testing, keras has
        # already been loaded, but by instantiating a new Keras instance we can
        # check that the warning will be displayed when users first use keras
        with warnings.catch_warnings(record=True) as rec:
            warnings.filterwarnings('always', module=r'.*keras_interface')
            _ = nimble.core.interfaces.keras_interface.Keras()
            start = "Randomness is outside of Nimble's control"
            assert rec and str(rec[0].message).startswith(start)
    else:
        # for version2 we expect reproducibility
        numClasses = 3
        x_data = nimble.random.numpyRandom.random((1000, 20))
        y_data = nimble.random.numpyRandom.randint(numClasses, size=(1000, 1))
        x_train = nimble.data(x_data, useLog=False)
        y_train = nimble.data(y_data, convertToType=float, useLog=False)

        nimble.random.setSeed(1234, useLog=False)
        layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=20)
        layer1 = nimble.Init('Dropout', rate=0.5)
        layer2 = nimble.Init('Dense', units=numClasses, activation='sigmoid')
        layers = [layer0, layer1, layer2]
        mym = nimble.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer=optimizer,
                           layers=layers, loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                           epochs=20, batch_size=128, useLog=False)

        applied1 = mym.apply(testX=x_train, useLog=False)


        nimble.random.setSeed(1234, useLog=False)
        layer0 = nimble.Init('Dense', units=64, activation='relu', input_dim=20)
        layer1 = nimble.Init('Dropout', rate=0.5)
        layer2 = nimble.Init('Dense', units=numClasses, activation='sigmoid')
        layers = [layer0, layer1, layer2]
        mym = nimble.train('keras.Sequential', trainX=x_train, trainY=y_train, optimizer=optimizer,
                           layers=layers, loss='sparse_categorical_crossentropy', metrics=['accuracy'],
                           epochs=20, batch_size=128, useLog=False)

        applied2 = mym.apply(testX=x_train, useLog=False)

        assert applied1 == applied2

@keraSkipDec
def testLearnerTypes():
    learners = ['keras.' + l for l in nimble.learnerNames('keras')]
    assert all(lt == 'undefined' for lt in nimble.learnerType(learners))

@keraSkipDec
def testLossCoverage():
    kerasInt = nimble.core._learnHelpers.findBestInterface('keras')
    lts = nimble.core.interfaces.keras_interface.LEARNERTYPES
    fullLossList = lts["classification"] + lts["regression"]

    # For all Loss classes (which should cover all possiblilities that Keras
    # provides), check to see that it is represented in the LEARNERTYPES
    # constant.
    for n in dir(kerasInt.package.losses):
        val = getattr(kerasInt.package.losses, n)
        if type(val) is type and issubclass(val, kerasInt.package.losses.Loss):
            if not (val is kerasInt.package.losses.Loss):
                assert val.__name__ in fullLossList
