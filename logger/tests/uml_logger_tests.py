from __future__ import absolute_import

import os
import shutil
import time
import ast
import six
import sqlite3
from nose import with_setup
from nose.tools import raises

import UML
from UML.helpers import generateClassificationData
from UML.calculate import rootMeanSquareError as RMSE
from UML.calculate import fractionIncorrect
from UML.exceptions import ArgumentException

"""
Unit tests for functionality of the UMLLogger
"""
def setup_func():
    UML.logger.active.cleanup()
    UML.settings.set("logger", "enabledByDefault", "True")
    UML.settings.set("logger", "enableCrossValidationDeepLogging", "True")

def teardown_func():
    UML.logger.active.cleanup()
    UML.settings.set("logger", "enabledByDefault", "False")
    UML.settings.set("logger", "enableCrossValidationDeepLogging", "False")

def removeLogFile():
    UML.logger.active.cleanup()
    location = UML.settings.get("logger", "location")
    name = UML.settings.get("logger", "name")
    pathToFile = os.path.join(location, name + ".mr")
    if os.path.exists(pathToFile):
        os.remove(pathToFile)

def singleValueQueries(*queries):
    out = []
    for query in queries:
        valueList = UML.logger.active.extractFromLog(query)
        singleValue = valueList[0][0]
        out.append(singleValue)
    return out

@with_setup(setup_func, teardown_func)
def testLogDirectoryAndFileSetup():
    """assert a new directory and log file are created with first attempt to log"""
    location = UML.settings.get("logger", "location")
    name = UML.settings.get("logger", "name")
    pathToFile = os.path.join(location, name + ".mr")
    if os.path.exists(location):
        shutil.rmtree(location)

    X = UML.createData("Matrix", [])

    assert os.path.exists(location)
    assert os.path.exists(pathToFile)

#############
### INPUT ###
#############

@with_setup(setup_func, teardown_func)
def testTopLevelInputFunction():
    removeLogFile()
    """assert the UML.log function correctly inserts data into the log"""
    logType = "input"
    logInfo = {"test": "testInput"}
    UML.log(logType, logInfo)
    # select all columns from the last entry into the logger
    query = "SELECT * FROM logger"
    lastLog = UML.logger.active.extractFromLog(query)
    lastLog = lastLog[0]

    assert lastLog[0] == 1
    assert lastLog[2] == 0
    assert lastLog[3] == logType
    assert lastLog[4] == str(logInfo)

@with_setup(setup_func, teardown_func)
def testNewRunNumberEachSetup():
    removeLogFile()
    """assert that a new, sequential runNumber is generated each time the log file is reopened"""
    for run in range(5):
        logType = "newRunNumber"
        logInfo = {"test": "testNewRunNumberEachSetup"}
        UML.logger.active.insertIntoLog(logType, logInfo)
        # cleanup will require setup before the next log entry
        UML.logger.active.cleanup()
    query = "SELECT runNumber FROM logger"
    lastLogs = UML.logger.active.extractFromLog(query)

    for entry, log in enumerate(lastLogs):
        assert log[0] == entry

@with_setup(setup_func, teardown_func)
def testLoadTypeFunctionsUseLog():
    """tests that top level functions not tested in testLoggingFlags are being logged"""
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    infoQuery = "SELECT logInfo FROM logger ORDER BY entry DESC LIMIT 1"
    lengthExpected = 0
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == lengthExpected

    # data
    trainX = [[1,0,0], [0,1,0], [0,0,1], [1,0,0], [0,1,0], [0,0,1],
              [1,0,0], [0,1,0], [0,0,1], [1,0,0], [0,1,0], [0,0,1]]
    trainY = [[0], [1], [2], [0], [1], [2], [0], [1], [2], [0], [1], [2]]
    testX = [[1,0,0], [0,1,0], [0,0,1], [1,1,0]]
    testY = [[0], [1], [2], [1]]

    # createData
    trainXObj = UML.createData("Matrix", trainX)
    lengthExpected += 1
    trainYObj = UML.createData("Matrix", trainY)
    lengthExpected += 1
    testXObj = UML.createData("Matrix", testX)
    lengthExpected += 1
    testYObj = UML.createData("Matrix", testY)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert testYObj.getTypeString() in logInfo


@with_setup(setup_func, teardown_func)
def testRunTypeFunctionsUseLog():
    """tests that top level functions not tested in testLoggingFlags are being logged"""
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    infoQuery = "SELECT logInfo FROM logger ORDER BY entry DESC LIMIT 1"
    lengthExpected = 0
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == lengthExpected

    # data
    trainX = [[1,0,0], [0,1,0], [0,0,1], [1,0,0], [0,1,0], [0,0,1],
              [1,0,0], [0,1,0], [0,0,1], [1,0,0], [0,1,0], [0,0,1]]
    trainY = [[0], [1], [2], [0], [1], [2], [0], [1], [2], [0], [1], [2]]
    testX = [[1,0,0], [0,1,0], [0,0,1], [1,1,0]]
    testY = [[0], [1], [2], [1]]

    trainXObj = UML.createData("Matrix", trainX, useLog=False)
    trainYObj = UML.createData("Matrix", trainY, useLog=False)
    testXObj = UML.createData("Matrix", testX, useLog=False)
    testYObj = UML.createData("Matrix", testY, useLog=False)

    #normalizeData
    # copy to avoid modifying original data
    trainXNormalize = trainXObj.copy()
    testXNormalize = testXObj.copy()
    UML.normalizeData('mlpy.PCA', trainXNormalize, testX=testXNormalize, arguments={'k': 1})
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'normalizeData'" in logInfo

    #trainAndTestOnTrainingData
    results = UML.trainAndTestOnTrainingData("sciKitLearn.SVC", trainXObj, trainYObj,
                                             performanceFunction=RMSE)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'trainAndTestOnTrainingData'" in logInfo

@with_setup(setup_func, teardown_func)
def testPrepTypeFunctionsUseLog():
    """Test that the functions in base using useLog are being logged"""
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    infoQuery = "SELECT logInfo FROM logger ORDER BY entry DESC LIMIT 1"
    lengthExpected = 0
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == lengthExpected

    data = [["a", 1, 1], ["a", 1, 1], ["a", 1, 1], ["a", 1, 1], ["a", 1, 1], ["a", 1, 1],
            ["b", 2, 2], ["b", 2, 2], ["b", 2, 2], ["b", 2, 2], ["b", 2, 2], ["b", 2, 2],
            ["c", 3, 3], ["c", 3, 3], ["c", 3, 3], ["c", 3, 3], ["c", 3, 3], ["c", 3, 3]]

    # dropFeaturesContainingType; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.dropFeaturesContainingType(str)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'dropFeaturesContainingType'" in logInfo

    # replaceFeatureWithBinaryFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.replaceFeatureWithBinaryFeatures(0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'replaceFeatureWithBinaryFeatures'" in logInfo

    # transformFeatureToIntegers; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.transformFeatureToIntegers(0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'transformFeatureToIntegers'" in logInfo

    # extractPointsByCoinToss; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    extracted = dataObj.extractPointsByCoinToss(0.5)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'extractPointsByCoinToss'" in logInfo

    # mapReducePoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    def simpleMapper(point):
        pID = point[0]
        intList = []
        for i in range(1, len(point)):
            intList.append(point[i])
        ret = []
        for value in intList:
            ret.append((pID, value))
        return ret

    def simpleReducer(identifier, valuesList):
        total = 0
        for value in valuesList:
            total += value
        return (identifier, total)

    calculated = dataObj.mapReducePoints(simpleMapper,simpleReducer)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'mapReducePoints'" in logInfo

    # groupByFeature; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    calculated = dataObj.groupByFeature(by=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'groupByFeature'" in logInfo

    # calculateForEachElement; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    calculated = dataObj.calculateForEachElement(lambda x: len(x), features=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'calculateForEachElement'" in logInfo

    # calculateForEachPoint; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    calculated = dataObj.calculateForEachPoint(lambda x: len(x))
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'calculateForEachPoint'" in logInfo

    # calculateForEachFeature; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    calculated = dataObj.calculateForEachFeature(lambda x: len(x), features=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'calculateForEachFeature'" in logInfo

    # shufflePoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.shufflePoints()
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'shufflePoints'" in logInfo

    # shuffleFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.shuffleFeatures()
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'shuffleFeatures'" in logInfo

    # trainAndTestSets; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    train, test = dataObj.trainAndTestSets(testFraction=0.5)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'trainAndTestSets'" in logInfo

    # normalizePoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.normalizePoints(subtract=0, divide=1)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'normalizePoints'" in logInfo

    # normalizeFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.normalizeFeatures(subtract=0, divide=1)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'normalizeFeatures'" in logInfo

    # sortPoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.sortPoints(sortBy=dataObj.getFeatureName(0))
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'sortPoints'" in logInfo

    # sortFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataObj.sortFeatures(sortBy=dataObj.getFeatureName(0))
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'sortFeatures'" in logInfo

    # extractPoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    extracted = dataObj.extractPoints(toExtract=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'extractPoints'" in logInfo

    # extractFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    extracted = dataObj.extractFeatures(toExtract=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'extractFeatures'" in logInfo

    # transformEachPoint; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copy()
    calculated = dataCopy.transformEachPoint(lambda x: [point for point in x])
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'transformEachPoint'" in logInfo

    # transformEachFeature; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copy()
    calculated = dataCopy.transformEachFeature(lambda x: [point for point in x], features=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'transformEachFeature'" in logInfo

    # transformEachElement; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copy()
    calculated = dataCopy.transformEachElement(lambda x: [point for point in x], features=0)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'function': 'transformEachElement'" in logInfo

@with_setup(setup_func, teardown_func)
def testDataTypeFunctionsUseLog():
    """Test that the functions in base using useLog are being logged"""
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    infoQuery = "SELECT logInfo FROM logger ORDER BY entry DESC LIMIT 1"
    lengthExpected = 0
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == lengthExpected

    data = [["a", 1], ["a", 1], ["a", 1], ["a", 1], ["a", 1], ["a", 1],
            ["b", 2], ["b", 2], ["b", 2], ["b", 2], ["b", 2], ["b", 2],
            ["c", 3], ["c", 3], ["c", 3], ["c", 3], ["c", 3], ["c", 3]]

    # featureReport; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    fReport = dataObj[:,1].featureReport()
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert "'reportType': 'feature'" in logInfo

    # summaryReport; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    sReport = dataObj.summaryReport()
    lengthExpected += 1

@with_setup(setup_func, teardown_func)
def testBaseObjectFunctionsWithoutUseLog():
    """test a handful of base objects that make calls to logged functions are not logged"""
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == 0

    data = [["a", 1], ["a", 1], ["a", 1], ["a", 1], ["a", 1], ["a", 1],
            ["b", 2], ["b", 2], ["b", 2], ["b", 2], ["b", 2], ["b", 2],
            ["c", 3], ["c", 3], ["c", 3], ["c", 3], ["c", 3], ["c", 3]]

    # copyPoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copyPoints(start=1)

    logLength = singleValueQueries(lengthQuery)[0]
    assert logLength == 0

    # copyFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copyFeatures(start=1)

    logLength = singleValueQueries(lengthQuery)[0]
    assert logLength == 0

    # copyAs; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    dataCopy = dataObj.copyAs("pythonlist")

    logLength = singleValueQueries(lengthQuery)[0]
    assert logLength == 0

    # countPoints; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    count = dataObj.countPoints(lambda x: x>0)

    logLength = singleValueQueries(lengthQuery)[0]
    assert logLength == 0

    # countFeatures; createData not logged
    dataObj = UML.createData("Matrix", data, useLog=False)
    count = dataObj.countFeatures(lambda x: x>0)

    logLength = singleValueQueries(lengthQuery)[0]
    assert logLength == 0


@with_setup(setup_func, teardown_func)
def testHandmadeLogEntriesInput():
    removeLogFile()
    lengthQuery = "SELECT COUNT(entry) FROM logger"
    infoQuery = "SELECT logInfo FROM logger ORDER BY entry DESC LIMIT 1"
    lengthExpected = 0
    lengthLog = UML.logger.active.extractFromLog(lengthQuery)[0][0] # returns list of tuples i.e. [(0,)]
    # ensure starting table has no values
    assert lengthLog == lengthExpected

    # custom string
    customString = "enter this string into the log"
    UML.log("customString", customString)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    assert customString in logInfo

    #custom list
    customList = ["this", "custom", "list", 1, 2, 3, {"list":"tested"}]
    UML.log("customList", customList)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    for value in customList:
        assert str(value) in logInfo

    #custom dict
    customDict = {"custom":"dict", "log":"testing", 1:2, 3:"four"}
    UML.log("customDict", customDict)
    lengthExpected += 1

    logLength, logInfo = singleValueQueries(lengthQuery, infoQuery)
    assert logLength == lengthExpected
    for key in customDict.keys():
        assert str(key) in logInfo
    for value in customDict.values():
        assert str(value) in logInfo

@raises(ArgumentException)
def testLogUnacceptedlogType():
    UML.log(["unacceptable"], "you can't do this")

@raises(ArgumentException)
def testLogUnacceptedlogInfo():
    dataObj = UML.createData("Matrix", [[1]], useLog=False)
    UML.log("acceptable", dataObj)

##############
### OUTPUT ###
##############

@with_setup(setup_func, teardown_func)
def testShowLogToFile():
    removeLogFile()
    UML.createData("Matrix", [[1], [2], [3]], useLog = True)
    UML.createData("Matrix", [[4], [5], [6]], useLog = True)
    #write to log
    location = UML.settings.get("logger", "location")
    name = "showLogTestFile.txt"
    pathToFile = os.path.join(location,name)
    UML.showLog(saveToFileName=pathToFile)
    assert os.path.exists(pathToFile)

    originalSize = os.path.getsize(pathToFile)
    removeLogFile()

    #overwrite
    UML.createData("Matrix", [[1], [2], [3]], useLog = True)
    UML.showLog(saveToFileName=pathToFile)
    overwriteSize = os.path.getsize(pathToFile)
    assert overwriteSize < originalSize

    #append
    UML.createData("Matrix", [[4], [5], [6]], useLog = True)
    UML.showLog(saveToFileName=pathToFile, append=True)
    appendSize = os.path.getsize(pathToFile)
    assert appendSize > originalSize


@with_setup(setup_func, teardown_func)
def testShowLogSearchFilters():
    """test the level of detail, runNumber, date, text, maxEntries search filters"""
    removeLogFile()
    # create an example log file
    variables = ["x1", "x2", "x3", "label"]
    data1 = [[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3], [1, 0, 0, 1], [0, 1, 0, 2],
             [0, 0, 1, 3], [1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3], [1, 0, 0, 1],
             [0, 1, 0, 2], [0, 0, 1, 3], [1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3],
             [1, 0, 0, 3], [0, 1, 0, 1], [0, 0, 1, 2]]
    data2 = [[1, 0, 0, 1],
             [0, 1, 0, 2],
             [0, 0, 1, 3]]
    # add data to log
    for i in range(5):
        # load
        trainObj = UML.createData('Matrix', data=data1, featureNames=variables)
        testObj = UML.createData('Matrix', data=data2, featureNames=variables)
        # data
        report = trainObj.summaryReport()
        # prep
        trainYObj = trainObj.extractFeatures(3)
        testYObj = testObj.extractFeatures(3)
        # run and crossVal
        results = UML.trainAndTest('sciKitLearn.SVC', trainX=trainObj, trainY=trainYObj,
                                testX=testObj, testY=testYObj, performanceFunction=fractionIncorrect,
                                arguments={"C":(1,0.1)})
    # edit log runNumbers and timestamps
    location = UML.settings.get("logger", "location")
    name = UML.settings.get("logger", "name")
    pathToFile = os.path.join(location, name + ".mr")
    conn = sqlite3.connect(pathToFile)
    c = conn.cursor()
    c.execute("UPDATE logger SET timestamp = '2018-03-22 12:00:00' WHERE entry <= 7")
    conn.commit()
    c.execute("UPDATE logger SET runNumber = 1, timestamp = '2018-03-23 12:00:00' WHERE entry > 7 AND entry <= 14")
    conn.commit()
    c.execute("UPDATE logger SET runNumber = 2, timestamp = '2018-03-23 18:00:00' WHERE entry > 14 AND entry <= 21")
    conn.commit()
    c.execute("UPDATE logger SET runNumber = 3, timestamp = '2018-03-25 12:00:00' WHERE entry > 21 AND entry <= 28")
    conn.commit()
    c.execute("UPDATE logger SET runNumber = 4, timestamp = '2018-04-24 12:00:00' WHERE entry > 28")
    conn.commit()

    location = UML.settings.get("logger", "location")
    name = "showLogTestFile.txt"
    pathToFile = os.path.join(location,name)
    UML.showLog(levelOfDetail=3, leastRunsAgo=0, mostRunsAgo=5, maximumEntries=100, saveToFileName=pathToFile)
    fullShowLogSize = os.path.getsize(pathToFile)

    # level of detail
    UML.showLog(levelOfDetail=3, saveToFileName=pathToFile)
    mostDetailedSize = os.path.getsize(pathToFile)

    UML.showLog(levelOfDetail=2, saveToFileName=pathToFile)
    lessDetailedSize = os.path.getsize(pathToFile)
    assert lessDetailedSize < mostDetailedSize

    UML.showLog(levelOfDetail=1, saveToFileName=pathToFile)
    leastDetailedSize = os.path.getsize(pathToFile)
    assert leastDetailedSize < lessDetailedSize

    # runNumber
    UML.showLog(levelOfDetail=3, mostRunsAgo=4, saveToFileName=pathToFile)
    fewerRunsAgoSize = os.path.getsize(pathToFile)
    assert fewerRunsAgoSize < fullShowLogSize

    UML.showLog(levelOfDetail=3, leastRunsAgo=1, mostRunsAgo=5, saveToFileName=pathToFile)
    moreRunsAgoSize = os.path.getsize(pathToFile)
    assert moreRunsAgoSize < fullShowLogSize

    assert moreRunsAgoSize == fewerRunsAgoSize

    UML.showLog(levelOfDetail=3, leastRunsAgo=2, mostRunsAgo=4, saveToFileName=pathToFile)
    runSelectionSize = os.path.getsize(pathToFile)
    assert runSelectionSize < moreRunsAgoSize

    # startDate
    UML.showLog(levelOfDetail=3, mostRunsAgo=5, startDate="2018-03-23", saveToFileName=pathToFile)
    startLaterSize = os.path.getsize(pathToFile)
    assert startLaterSize < fullShowLogSize

    UML.showLog(levelOfDetail=3, mostRunsAgo=5, startDate="2018-04-24", saveToFileName=pathToFile)
    startLastSize = os.path.getsize(pathToFile)
    assert startLastSize < startLaterSize

    # endDate
    UML.showLog(levelOfDetail=3, mostRunsAgo=5, endDate="2018-03-25", saveToFileName=pathToFile)
    endEarlierSize = os.path.getsize(pathToFile)
    assert endEarlierSize < fullShowLogSize

    UML.showLog(levelOfDetail=3, mostRunsAgo=5, endDate="2018-03-22", saveToFileName=pathToFile)
    endEarliestSize = os.path.getsize(pathToFile)
    assert endEarliestSize < endEarlierSize

    # startDate and endDate
    UML.showLog(levelOfDetail=3, mostRunsAgo=5, startDate="2018-03-23", endDate="2018-03-25", saveToFileName=pathToFile)
    dateSelectionSize = os.path.getsize(pathToFile)
    assert dateSelectionSize < startLaterSize
    assert dateSelectionSize < endEarlierSize

    #text
    UML.showLog(levelOfDetail=3, mostRunsAgo=1, searchForText=None, saveToFileName=pathToFile)
    oneRunSize = os.path.getsize(pathToFile)

    UML.showLog(levelOfDetail=3, mostRunsAgo=1, searchForText="trainAndTest", saveToFileName=pathToFile)
    trainSearchSize = os.path.getsize(pathToFile)
    assert trainSearchSize < oneRunSize

    UML.showLog(levelOfDetail=3, mostRunsAgo=1, searchForText="Matrix", saveToFileName=pathToFile)
    loadSearchSize = os.path.getsize(pathToFile)
    assert loadSearchSize < oneRunSize

    # regex
    UML.showLog(levelOfDetail=3, mostRunsAgo=1, searchForText="Mat.+x", regex=True, saveToFileName=pathToFile)
    loadRegexSize = os.path.getsize(pathToFile)
    assert loadSearchSize == loadRegexSize

    # maximumEntries
    UML.showLog(levelOfDetail=3, mostRunsAgo=5, maximumEntries=34, saveToFileName=pathToFile)
    oneLessSize = os.path.getsize(pathToFile)
    assert oneLessSize < fullShowLogSize

    UML.showLog(levelOfDetail=3, mostRunsAgo=5, maximumEntries=33, saveToFileName=pathToFile)
    twoLessSize = os.path.getsize(pathToFile)
    assert twoLessSize < oneLessSize

    UML.showLog(levelOfDetail=3, mostRunsAgo=5, maximumEntries=7, saveToFileName=pathToFile)
    maxEntriesOneRun = os.path.getsize(pathToFile)
    assert maxEntriesOneRun == oneRunSize


# TODO
# @with_setup(setup_func, teardown_func)
# def testShowLogToStdOut():
#     pass
#
# TODO
# @with_setup(setup_func, teardown_func)
# def testHandmadeLogEntriesOutput():
#     pass
