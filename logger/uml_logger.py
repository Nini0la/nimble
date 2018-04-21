from __future__ import absolute_import
from __future__ import print_function
import os
import time
import six
import inspect
import numpy
from datetime import datetime
from dateutil.parser import parse
import ast
from textwrap import wrap
import pandas as pd

import UML
from UML.exceptions import ArgumentException

from .logger_helpers import useLogCheck
from .logger_helpers import _formatRunLine
from .logger_helpers import _logHeader
from .logger_helpers import _removeItemsWithoutData
from .logger_helpers import textSearch
from .logger_helpers import checkMaxEntries

"""
    Handle logging of creating and testing learners.
    Currently stores data in a SQLite database file and generates
    a human readable log by querying the tables within the database.
    There is a hierarchical structure to the log, allowing the user
    to specify the level of detail in the log:

    Current Hierarchy
    Level ?: Data creation and preprocessing logs
    Level 1: Outputs basic information about the run (timestamp, run number,
             learner name, train and test object details) and boolean values
             for the availability of additional information
    Level 2: Parameter, metric, and timer data if available
    Level 3: Cross validation
    Level 4: Epoch data
"""

class UmlLogger(object):
    def __init__(self, logLocation, logName):
        fullLogDesignator = os.path.join(logLocation, logName)
        self.logLocation = logLocation
        self.logName = logName
        self.logFileName = fullLogDesignator + ".csv"
        self.runNumber = None
        self.isAvailable = False
        self.suspended = False


    def setup(self, newFileName=None):
        """
            Try to open the file that will be used for logging.  If newFileName
            is present, will reset the log file to use the new file name and Attempt
            to open it.  Otherwise, will use the file name provided when this was
            instantiated.  If successfully opens the file, set isAvailable to true.
        """
        if newFileName is not None and isinstance(newFileName, (str, six.text_type)):
            self.logFileName = newFileName

        dirPath = os.path.dirname(self.logFileName)
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        if not os.path.exists(self.logFileName):
            self.logFile = open(self.logFileName, 'w')
            setupLines = "runNumber;date;loggerInfo"
            setupLines += "\n"
            self.logFile.write(setupLines)
            self.runNumber = 0
            self.logFile.close()
        else:
            self.logFile = open(self.logFileName, 'r')
            contents = self.logFile.readlines()
            lastLine = contents[-1]
            lastLineList = lastLine.split(";")
            lastRunNumber = int(lastLineList[0])
            self.runNumber = lastRunNumber + 1
            self.logFile.close()

        self.logFile = open(self.logFileName, "a")
        self.isAvailable = True

    def cleanup(self):
        # only need to call if we have previously called setup
        if self.isAvailable:
            self.logFile.close()
            self.isAvailable = False


    def insertIntoLog(self, logMessage):
        """ Inserts a json style message into the log and indexes the runNumber"""
        if not self.isAvailable:
            self.setup(self.logFileName)
            logMessage["runNumber"] = self.runNumber
        runNumber = self.runNumber
        date = datetime.date(datetime.today())
        logLine = "{0};{1};{2}\n".format(runNumber, date, logMessage)
        self.logFile.write(logLine)

    ###################
    ### CREATE LOGS ###
    ###################

    def logLoad(self, returnType, numPoints, numFeatures, name=None, path=None):
        """
        Send pertinent information about the loading of some data set to the log file
        """
        #TODO only log if name or path is present?
        logMessage = {"type": "load"}
        timestamp = (time.strftime('%Y-%m-%d %H:%M:%S'))
        logMessage["timestamp"] = timestamp
        logMessage["runNumber"] = self.runNumber
        logMessage["numPoints"] = numPoints
        logMessage["numFeatures"] = numFeatures
        logMessage["name"] = name
        logMessage["path"] = path
        self.insertIntoLog(logMessage)


    # def logData(self): #TODO
    #     """
    #     Send pertinent information about a data object that has been loaded/created to the log file
    #     """
    #     timestamp = (time.strftime('%Y-%m-%d %H:%M:%S'))
    #     logMessage = {"type" : "data",
                  # "timestamp": timestamp,
                  # "function": function, } #TODO
    #     self.insertIntoLog(logMessage)
    #
    #
    def logPrep(self, umlFunction, arguments):
        """
        Send pertinent information about the data preparation step performed to the log file
        """
        logMessage = {"type" : "prep"}
        logMessage["runNumber"] = self.runNumber
        timestamp = (time.strftime('%Y-%m-%d %H:%M:%S'))
        logMessage["timestamp"] = timestamp
        logMessage["function"] = umlFunction
        logMessage["arguments"] = arguments
        self.insertIntoLog(logMessage)


    def logRun(self, umlFunction, trainData, trainLabels, testData, testLabels,
                               learnerFunction, arguments, metrics, timer,
                               extraInfo=None, numFolds=None):
        """
        Send the pertinent information about the run to the log file
        """
        logMessage = {"type" : "run"}
        logMessage["function"] = umlFunction

        timestamp = (time.strftime('%Y-%m-%d %H:%M:%S'))
        logMessage["timestamp"] = timestamp

        logMessage["runNumber"] = self.runNumber
        if isinstance(learnerFunction, (str, six.text_type)):
            functionCall = learnerFunction
        else:
            #we get the source code of the function as a list of strings and glue them together
            funcLines = inspect.getsourcelines(learnerFunction)
            funcString = ""
            for i in range(len(funcLines) - 1):
                funcString += str(funcLines[i])
            if funcLines is None:
                funcLines = "N/A"
            functionCall = funcString
        logMessage["learner"] = functionCall

        # check for integers or strings passed for Y values. TODO Should be done somewhere else?
        if isinstance(trainLabels, (six.string_types, int, numpy.int64)):
            trainData = trainData.copy()
            trainLabels = trainData.extractFeatures(trainLabels)
        if isinstance(testLabels, (six.string_types, int, numpy.int64)):
            testData = trainData.copy()
            testLabels = trainData.extractFeatures(testLabels)
        if trainData is not None:
            logMessage["trainData"] = trainData.name
            logMessage["trainDataPoints"] = trainData.points
            logMessage["trainDataFeatures"] = trainData.features
        if trainLabels is not None:
            logMessage["trainLabels"] = trainLabels.name
            logMessage["trainLabelsPoints"] = trainLabels.points
            logMessage["trainLabelsFeatures"] = trainLabels.features
        if testData is not None:
            logMessage["testData"] = testData.name
            logMessage["testDataPoints"] = testData.points
            logMessage["testDataFeatures"] = testData.features
        if testLabels is not None:
            logMessage["testLabels"] = testLabels.name
            logMessage["testLabelsPoints"] = testLabels.points
            logMessage["testLabelsFeatures"] = testLabels.features

        if arguments is not None and arguments != {}:
            logMessage['arguments'] = arguments

        if metrics is not None and metrics is not {}:
            logMessage["metrics"] = metrics

        if timer is not None and timer.cumulativeTimes is not {}:
            logMessage["timer"] = sum(timer.cumulativeTimes.values())

        if extraInfo is not None and extraInfo is not {}:
            logMessage["extraInfo"] = extraInfo

        self.insertIntoLog(logMessage)


    def logCrossValidation(self, trainData, trainLabels, learnerName, metric, performance,
                           timer, learnerArgs, folds=None):
        """
        Send information about selection of a set of arguments using cross validation
        """
        logMessage = {"type" : "cv"}
        timestamp = (time.strftime('%Y-%m-%d %H:%M:%S'))
        logMessage["timestamp"] = timestamp
        logMessage["runNumber"] = self.runNumber
        logMessage["learner"] = learnerName
        logMessage["learnerArgs"] = learnerArgs
        logMessage["folds"] = folds
        logMessage["metric"] = metric.__name__
        logMessage["performance"] = performance

        self.insertIntoLog(logMessage)


    ###################
    ### LOG STRINGS ###
    ###################
    # TODO spacing and wrapping for long strings

    def buildRunLogString(self, log):
        """ Extracts and formats information from the 'runs' table for printable output """
        # header data
        fullLog = _logHeader(log["runNumber"], log["timestamp"])
        timer = log.get("timer", False)
        if timer:
            fullLog += "Completed in {0:.3f} seconds\n".format(log['timer'])
        fullLog += "\n"
        fullLog += 'UML.{0}("{1}")\n'.format(log['function'], log["learner"])

        # train and test data
        fullLog += _formatRunLine("Data", "# points", "# features")
        if log.get("trainData", False):
            fullLog += _formatRunLine("trainX", log["trainDataPoints"], log["trainDataFeatures"])
        if log.get("trainLabels", False):
            fullLog += _formatRunLine("trainY", log["trainLabelsPoints"], log["trainLabelsFeatures"])
        if log.get("testData", False):
            fullLog += _formatRunLine("testX", log["testDataPoints"], log["testDataFeatures"])
        if log.get("testLabels", False):
            fullLog += _formatRunLine("testY", log["testLabelsPoints"], log["testLabelsFeatures"])
        # parameter data
        if log.get("arguments", False):
            fullLog += "\n"
            argString = "Arguments: "
            argString += str(log["arguments"])
            for string in wrap(argString, 80, subsequent_indent=" "*19):
                fullLog += string
                fullLog += "\n"
            #fullLog += _logDictionary(log["arguments"])
        # metric data
        if log.get("metrics", False):
            fullLog += "\n"
            fullLog += "Metrics: "
            fullLog += str(log["metrics"])
            #fullLog += _logDictionary(log["metrics"])
        # extraInfo
        if log.get("extraInfo", False):
            fullLog += "\n"
            fullLog += "Extra Info: "
            fullLog += str(log["extraInfo"])
            #fullLog += _logDictionary(log["extraInfo"])

        return fullLog


    def buildLoadLogString(self, log):
        fullLog = _logHeader(log["runNumber"], log["timestamp"])
        dataCol = "Data Loaded"
        if log['path'] is not None:
            fullLog += _formatRunLine(dataCol, "path", log["path"])
            dataCol = ""
        if log['name'] is not None:
            fullLog += _formatRunLine(dataCol, "name", log["name"])
            dataCol = ""
        fullLog += _formatRunLine(dataCol, "# of points", log["numPoints"])
        fullLog += _formatRunLine("", "# of features", log["numFeatures"])
        return fullLog

    def buildPrepLogString(self, log):
        fullLog = _logHeader(log["runNumber"], log["timestamp"])
        fullLog += "UML.{0}\n".format(log["function"])
        argString = "Arguments: "

        argString += str(log["arguments"])
        for string in wrap(argString, 80, subsequent_indent=" "*19):
            fullLog += string
            fullLog += "\n"
        # for argName, argValue in six.iteritems(log["arguments"]):
        #     fullLog += "{} = {}, ".format(argName, argValue)
        # # remove trailing comma
        # fullLog = fullLog[:-2]
        return fullLog


    def buildCVLogString(self, log):
        fullLog = _logHeader(log["runNumber"], log["timestamp"])
        fullLog += "Cross Validating for {0}\n\n".format(log["learner"])
        # TODO when is learnerArgs returning an empty list?
        if isinstance(log["learnerArgs"], dict):
            fullLog += "Variable Arguments: "
            fullLog += str(log["learnerArgs"])
            fullLog += "\n\n"
            #fullLog += _logDictionary(log["learnerArgs"])
        folds = log["folds"]
        metric = log["metric"]
        fullLog += "{0}-folding using {1} optimizing for min values\n\n".format(folds, metric)
        fullLog += _formatRunLine("Result", "Arguments")
        for arguments, result in log["performance"]:
            fullLog += ("{0:<20.3f}{1:20s}" * len(arguments)).format(result, str(arguments))
            fullLog += "\n"
        return fullLog


    ##################
    ### PRINT LOGS ###
    ##################

    # TODO Divider for runs

    def _showLogImplementation(self, levelOfDetail, leastRunsAgo, mostRunsAgo, startDate,
                               endDate, saveToFileName, maximumEntries, searchForText):
        """ Implementation of showLog function for UML"""
        if self.isAvailable:
            self.cleanup()

        ##List of pandas operations
        # read file with ; separator
        # changed types to numeric and datetime
        # filtered dataframe by column and multiple booleans
        # indexed the last row of dataframe

        logger = pd.read_csv(self.logFileName, sep=";")
        logger['runNumber'] = pd.to_numeric(logger['runNumber'])
        logger['date'] = pd.to_datetime(logger['date'])


        # logger = UML.createData('DataFrame', logger, featureNames=True)
        # logger.transformFeatureToIntegers('runNumber', useLog=False)
        # def convertToDatetime(features):
        #     converted = []
        #     for feature in features:
        #         feature = parse(feature)
        #         feature = datetime.date(feature)
        #         converted.append(feature)
        #     return converted
        # logger.transformEachFeature(convertToDatetime, features='date')


        # search for text TODO timeit
        # if searchForText is not None:
        #     runLogs = self.log.filter(lambda log: (searchForText in log.keys() or searchForText in log.values()))

        # search by runsAgo
        if startDate is None and endDate is None:
            try:
                lastEntryLog = logger.iloc[-1]
                lastEntryRun = lastEntryLog["runNumber"]
                nextRun = lastEntryRun + 1
            except ValueError:
                nextRun = 1
            startRun = nextRun - mostRunsAgo
            if startRun < 0:
                msg = "mostRunsAgo is greater than the number of runs. "
                msg += "This number cannot exceed {}".format(nextRun)
                raise ArgumentException(msg)
            endRun = nextRun - leastRunsAgo

            if endRun < startRun:
                raise ArgumentException("leastRunsAgo must be less than mostRunsAgo")
            runNumbers = range(startRun, endRun)
            logByRun = logger[logger['runNumber'].isin(runNumbers)]
                # logByRun = logger.copy()
                # filter = "runNumber = " + str(number)
                # logByRun = logByRun.extractPoints(filter)
            logByRun = checkMaxEntries(logByRun, maximumEntries)
            runLogs = textSearch(logByRun, searchForText)
            # allRunIds = ""
            # for run in runNumbers:
            #     run = str(run)
            #     allRunIds += self.logDB[run]
            # runLogsList = allRunIds.split()
            # runLogs = [self.log.fetch(run) for run in runLogsList]

        # search by date TODO timeit
        elif startDate is not None and endDate is not None:
            #TODO ducktype dates
            startDate = parse(startDate)
            endDate = parse(endDate)
            logByDate = logger[(logger['date'] >= startDate) & (logger['date'] <= endDate)]
            logByDate = checkMaxEntries(logByDate, maximumEntries)
            runLogs = textSearch(logByDate, searchForText)
        elif startDate is not None:
            startDate = parse(startDate)
            logByDate = logger[logger['date'] >= startDate]
            logByDate = checkMaxEntries(logByDate, maximumEntries)
            runLogs = textSearch(logByDate, searchForText)
        elif endDate is not None:
            endDate = parse(endDate)
            logByDate = logger[logger['date'] <= endDate]
            logByDate = checkMaxEntries(logByDate, maximumEntries)
            runLogs = textSearch(logByDate, searchForText)
        elif searchForText is not None:
            runLogs = textSearch(dataframe, searchForText)
            runLogs = checkMaxEntries(runLogs, maximumEntries)

        fullLog = '.' * 35 + " UML LOGS " + '.' * 35
        for log in runLogs:
            log = eval(log) #TODO ast?
            # adjust for level of detail
            if log["type"] == 'load':
                fullLog += self.buildLoadLogString(log)
                fullLog += '.' * 80
            elif log["type"] == 'data':
                pass
                # fullLog += "\n"
                # fullLog +=  # TODO
                # fullLog += '.' * 80
            elif log["type"] == 'prep':
                if levelOfDetail > 1:
                    fullLog +=  self.buildPrepLogString(log)
                    fullLog += '.' * 80
            elif log["type"] == 'run':
                if levelOfDetail > 1:
                    fullLog += self.buildRunLogString(log)
                    fullLog += '.' * 80
            elif log["type"] == 'cv':
                if levelOfDetail > 2:
                    fullLog += self.buildCVLogString(log)
                    fullLog += '.' * 80
            else:
                if levelOfDetail > 3:
                    pass
                    # fullLog += "\n"
                    # fullLog += # self.buildMultiClassLogString
                    # fullLog += '.' * 80
        if saveToFileName is not None:
            # TODO check if file exists and append if already exists?
            filePath = os.path.join(self.logLocation, saveToFileName)
            with open(filePath, mode='w') as f:
                f.write(fullLog)
        else:
            print(fullLog)


#######################
### Initialization  ###
#######################

def initLoggerAndLogConfig():
    """Sets up or reads configuration options associated with logging,
    and initializes the currently active logger object using those
    options.

    """
    try:
        location = UML.settings.get("logger", "location")
        if location == "":
            location = './logs-UML'
            UML.settings.set("logger", "location", location)
            UML.settings.saveChanges("logger", "location")
    except:
        location = './logs-UML'
        UML.settings.set("logger", "location", location)
        UML.settings.saveChanges("logger", "location")
    finally:
        def cleanThenReInit_Loc(newLocation):
            UML.logger.active.cleanup()
            currName = UML.settings.get("logger", 'name')
            UML.logger.active = UmlLogger(newLocation, currName)
        UML.settings.hook("logger", "location", cleanThenReInit_Loc)

    try:
        name = UML.settings.get("logger", "name")
    except:
        name = "log-UML"
        UML.settings.set("logger", "name", name)
        UML.settings.saveChanges("logger", "name")
    finally:
        def cleanThenReInit_Name(newName):
            UML.logger.active.cleanup()
            currLoc = UML.settings.get("logger", 'location')
            UML.logger.active = UmlLogger(currLoc, newName)

        UML.settings.hook("logger", "name", cleanThenReInit_Name)

    try:
        loggingEnabled = UML.settings.get("logger", "enabledByDefault")
    except:
        loggingEnabled = 'True'
        UML.settings.set("logger", "enabledByDefault", loggingEnabled)
        UML.settings.saveChanges("logger", "enabledByDefault")

    try:
        runTests = UML.settings.get("logger", "_runTestsActive")
    except:
        runTests = 'False'
        UML.settings.set("logger", "_runTestsActive", runTests)
        UML.settings.saveChanges("logger", "_runTestsActive")

    try:
        deepCV = UML.settings.get("logger", 'enableCrossValidationDeepLogging')
    except:
        deepCV = 'False'
        UML.settings.set("logger", 'enableCrossValidationDeepLogging', deepCV)
        UML.settings.saveChanges("logger", 'enableCrossValidationDeepLogging')

    try:
        deepMulti = UML.settings.get("logger", 'enableMultiClassStrategyDeepLogging')
    except:
        deepMulti = 'False'
        UML.settings.set("logger", 'enableMultiClassStrategyDeepLogging', deepMulti)
        UML.settings.saveChanges("logger", 'enableMultiClassStrategyDeepLogging')
    UML.logger.active = UmlLogger(location, name)
