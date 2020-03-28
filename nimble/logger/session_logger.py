"""
Handle logging of creating and testing learners.

Currently stores data in a SQLite database file and generates
a human readable log by querying the table within the database.
There is a hierarchical structure to the log, this limits the to
entries with only the specified level of detail.

Also included are the wrappers to ensure that logged functions are
logged only when necessary.

Hierarchy
Level 1: Data creation and preprocessing logs
Level 2: Outputs basic information about learner runs, including
         timestamp, session number, learner name, train and test object
         details, parameter, metric and timer data if available
Level 3: Cross validation
"""

import os
import sys
import time
import inspect
import re
import sqlite3
from ast import literal_eval
from textwrap import wrap
from functools import wraps
import datetime

import numpy

import nimble
from nimble.exceptions import InvalidArgumentValue
from nimble.configuration import configErrors
from .stopwatch import Stopwatch

class SessionLogger(object):
    """
    Handle logging of nimble functions and generating the log output.

    Parameters
    ----------
    logLocation : str
        The path to the directory containing the log file
    logName : str
        The name of the log file. The suffix '.mr' will be added to the
        name, to indicate this is the 'machine-readable' version of the
        logged information.
    """
    def __init__(self, logLocation, logName):
        fullLogDesignator = os.path.join(logLocation, logName)
        self.logLocation = logLocation
        self.logName = logName
        self.logFileName = fullLogDesignator + ".mr"
        self.sessionNumber = None
        self.connection = None
        self.cursor = None
        self.isAvailable = False
        self.logTypes = {'load': self.logLoad, 'prep': self.logPrep,
                         'run': self.logRun, 'data': self.logData,
                         'crossVal': self.logCrossValidation,
                         'setRandomSeed': self.logRandomSeed}


    def setup(self, newFileName=None):
        """
        Open or create the log file.

        Try to open the file that will be used for logging.  If
        ``newFileName`` is present, will reset the log file to use the
        new file name and attempt to open it.  Otherwise, will use the
        file name provided when this was instantiated.  If successfully
        opens the file, set isAvailable to true.

        Parameters
        ----------
        newFileName : str
            The name new logging file.
        """
        if (newFileName is not None
                and isinstance(newFileName, str)):
            self.logFileName = newFileName

        dirPath = os.path.dirname(self.logFileName)
        if not os.path.exists(dirPath):
            os.makedirs(dirPath)
        self.connection = sqlite3.connect(self.logFileName)
        def regexp(y, x, search=re.search):
            return 1 if search(y, x) else 0
        self.connection.create_function('regexp', 2, regexp)
        self.cursor = self.connection.cursor()
        statement = """
        CREATE TABLE IF NOT EXISTS logger (
        entry INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        sessionNumber INTEGER,
        logType TEXT,
        logInfo TEXT);
        """
        self.cursor.execute(statement)
        self.connection.commit()

        statement = "SELECT MAX(sessionNumber) FROM logger;"
        self.cursor.execute(statement)
        lastSession = self.cursor.fetchone()[0] #fetchone returns a tuple
        if lastSession is not None:
            self.sessionNumber = lastSession + 1
        else:
            self.sessionNumber = 0

        self.isAvailable = True


    def cleanup(self):
        """
        Closes the connection to the logger database, if it is open.
        """
        # only need to call if we have previously called setup
        if self.isAvailable:
            self.connection.close()
            self.isAvailable = False


    def log(self, logType, logInfo):
        """
        Add information into the log file.

        Inserts timestamp, sessionNumber, ``logType`` in their
        respective columns of the sqlite table. A string of ``logInfo``
        will be stored in the final column.

        Parameters
        ----------
        logType : str
            The type of information being added to the log. The values
            'load', 'prep', 'run', 'data', and 'crossVal', generate a
            custom output of the ``logInfo`` when printing the log.  Any
            other log type will print a string of ``logInfo`` without
            any additional formatting.
        logInfo : dict, list, str
            All types for this value will be converted and added to the
            log. If provided a dictionary; ``logType`` 'load', 'prep',
            'run', 'data', and 'crossVal' generate a custom output when
            printing the log.
        """
        if not self.isAvailable:
            self.setup(self.logFileName)

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        sessionNum = self.sessionNumber
        logInfo = repr(logInfo)
        statement = "INSERT INTO logger "
        statement += "(timestamp,sessionNumber,logType,logInfo) "
        statement += "VALUES (?,?,?,?);"
        self.cursor.execute(statement, (timestamp, sessionNum, logType,
                                        logInfo))
        self.connection.commit()


    def extractFromLog(self, query, values=None):
        """
        Fetch data from log file.

        Return a list of tuples for values matching a SQLite query
        statement.

        Parameters
        ----------
        query : str
            a SQLite query statement.
        values : tuple
            values to use in place of the "?" placeholders used in the
            query.
        """
        if not self.isAvailable:
            self.setup()
        if values is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, values)
        ret = self.cursor.fetchall()
        return ret

    ###################
    ### LOG ENTRIES ###
    ###################

    def logLoad(self, useLog, returnType, numPoints=None, numFeatures=None,
                name=None, path=None, sparsity=None, seed=None,
                learnerName=None, learnerArgs=None):
        """
        Log information about the loading of data or a trained learner.

        If this will be logged, store an entry in the database with
        "load" as the logType and a dictionary (stored as a string) of
        attributes for the loaded object as the logInfo.

        Parameters
        ----------
        returnType : str
            The type of the loaded object.
        numPoints : int
            The number of points in the loaded object.
        numFeatures : int
            The number of features in the loaded object.
        name : str
            The name of the loaded object.
        path : str
            The path to the data in the loaded object.
        """
        if enableLogging(useLog):
            logType = "load"
            logInfo = {}
            logInfo["returnType"] = returnType
            logInfo["numPoints"] = numPoints
            logInfo["numFeatures"] = numFeatures
            logInfo["name"] = name
            logInfo["path"] = path
            logInfo["sparsity"] = sparsity
            logInfo["seed"] = seed
            logInfo["learnerName"] = learnerName
            logInfo["learnerArgs"] = learnerArgs

            self.log(logType, logInfo)

    def logData(self, useLog, reportType, reportInfo):
        """
        Log an object's information reports.

        If this will be logged, store an entry in the database with
        "data" as the logType and a dictionary (stored as a string) of
        the report data as the logInfo.

        reportType : str
            'feature' or 'summary' based on the type of report.
        reportInfo : str
            The information generated during the call to the report
            function.
        """
        if enableLogging(useLog):
            logType = "data"
            logInfo = {}
            logInfo["reportType"] = reportType
            logInfo["reportInfo"] = reportInfo

            self.log(logType, logInfo)

    def logPrep(self, useLog, nimbleFunction, dataObject, func, *args,
                **kwargs):
        """
        Log information about a data preparation step performed.

        If this will be logged, store an entry in the database with
        "prep" as the logType and a dictionary (stored as a string) of
        the preprocessing function called and its arguments as the
        logInfo.

        Parameters
        ----------
        nimbleFunction : str
            The name of the nimble function called.
        dataObject : str
            The class of the calling object.
        arguments : dict
            A mapping of the argument name to the argument's value.
        """
        if enableLogging(useLog):
            logType = "prep"
            logInfo = {}
            logInfo["function"] = nimbleFunction
            logInfo["object"] = dataObject
            arguments = _buildArgDict(func, *args, **kwargs)
            logInfo["arguments"] = arguments

            self.log(logType, logInfo)

    def logRun(self, useLog, nimbleFunction, trainData, trainLabels, testData,
               testLabels, learnerFunction, arguments, metrics=None,
               extraInfo=None, time=None):
        """
        Log information about each run.

        If this will be logged, store an entry in the database with
        "run" as the logType and a dictionary (stored as a string) of
        the learner function called and its arguments as the logInfo.

        Parameters
        ----------
        nimbleFunction : str
            The name of the nimble function called.
        trainData : nimble data object
            The object containing the training data.
        trainLabels : nimble data object, int
            The object or feature in ``trainData`` containing the
            training labels.
        testData : nimble data object
            The object containing the testing data.
        testLabels : nimble data object, int
            The object or feature in ``testData`` containing the
            training labels.
        learnerFunction : str
            The name of learner function.
        arguments : dict
            The arguments passed to the learner.
        metrics : dict
            The results of the testing on a run.
        extraInfo: dict
            Any extra information to add to the log. Typically provides
            the best parameters from cross validation.
        time : float, None
            The time to run the function. None if function is not timed.
        """
        if enableLogging(useLog):
            logType = "run"
            logInfo = {}
            logInfo["function"] = nimbleFunction
            if isinstance(learnerFunction, str):
                functionCall = learnerFunction
            else:
                # TODO test this
                # we get the source code of the function as a list of strings
                # and glue them together
                funcLines = inspect.getsourcelines(learnerFunction)
                funcString = ""
                for i in range(len(funcLines) - 1):
                    funcString += str(funcLines[i])
                if funcLines is None:
                    funcLines = "N/A"
                functionCall = funcString
            logInfo["learner"] = functionCall
            # integers or strings passed for Y values, convert if necessary
            if isinstance(trainLabels, (str, int, numpy.int64)):
                trainData = trainData.copy()
                trainLabels = trainData.features.extract(trainLabels,
                                                         useLog=False)
            if isinstance(testLabels, (str, int, numpy.int64)):
                testData = testData.copy()
                testLabels = testData.features.extract(testLabels,
                                                       useLog=False)
            if trainData is not None:
                logInfo["trainData"] = trainData.name
                logInfo["trainDataPoints"] = len(trainData.points)
                logInfo["trainDataFeatures"] = len(trainData.features)
            if trainLabels is not None:
                logInfo["trainLabels"] = trainLabels.name
                logInfo["trainLabelsPoints"] = len(trainLabels.points)
                logInfo["trainLabelsFeatures"] = len(trainLabels.features)
            if testData is not None:
                logInfo["testData"] = testData.name
                logInfo["testDataPoints"] = len(testData.points)
                logInfo["testDataFeatures"] = len(testData.features)
            if testLabels is not None:
                logInfo["testLabels"] = testLabels.name
                logInfo["testLabelsPoints"] = len(testLabels.points)
                logInfo["testLabelsFeatures"] = len(testLabels.features)

            if arguments is not None and arguments != {}:
                for name, value in arguments.items():
                    try:
                        literal_eval(repr(value))
                        arguments[name] = value
                    except (ValueError, SyntaxError):
                        # use repr for objects which cannot eval
                        arguments[name] = repr(value)
                logInfo['arguments'] = arguments

            if metrics is not None and metrics != {}:
                logInfo["metrics"] = metrics

            if extraInfo is not None and extraInfo != {}:
                logInfo["extraInfo"] = extraInfo

            if time:
                logInfo["time"] = time

            self.log(logType, logInfo)

    def logCrossValidation(self, useLog, trainData, trainLabels,
                           learnerFunction, arguments, metric, performance,
                           folds=None):
        """
        Log the results of cross validation.

        If this will be logged, store an entry in the database with
        "crossVal" as the logType and a dictionary (stored as a string)
        of the preprocessing function called and its arguments as the
        logInfo. Cross validation can occur at any time, even by
        internal calls to the function, based on the useLog value and
        the value of enableCrossValidationDeepLogging in config.

        Parameters
        ----------
        trainData : nimble data object
            The object containing the training data.
        trainLabels : nimble data object, int
            The object or feature in ``trainData`` containing the
            training labels.
        learnerFunction : str
            The name of the learner function.
        arguments : dict
            The arguments passed to the learner.
        metric : function
            The results of the testing on a run.
        performance : list
            A list of the performance results of each permutation.
        folds : int
            The number of folds.
        """
        if enableLogging(useLog) and enableDeepLogging():
            logType = "crossVal"
            logInfo = {}
            logInfo["learner"] = learnerFunction
            for name, value in arguments.items():
                if isinstance(value, nimble.CV):
                    arguments[name] = repr(value)
            logInfo["learnerArgs"] = arguments
            logInfo["folds"] = folds
            logInfo["metric"] = (metric.__name__, metric.optimal)
            logInfo["performance"] = performance

            self.log(logType, logInfo)

    def logRandomSeed(self, useLog, seed):
        if enableLogging(useLog):
            logType = 'setRandomSeed'
            logInfo = {'seed': seed}
            self.log(logType, logInfo)

    ###################
    ### LOG OUTPUT ###
    ##################

    def showLog(self, levelOfDetail=2, leastSessionsAgo=0, mostSessionsAgo=2,
                startDate=None, endDate=None, maximumEntries=100,
                searchForText=None, regex=False, saveToFileName=None,
                append=False):
        """
        Output data from the logger.

        Parse the log based on the arguments passed and print a human
        readable interpretation of the log file.

        Parameters
        ----------
        levelOfDetail:  int
            The value for the level of detail from 1, the least detail,
            to 3 (most detail). Default is 2.
            * Level 1 - Data loading, data preparation and
              preprocessing, custom user logs.
            * Level 2 - Outputs basic information about learner runs.
              Includes timestamp, session number, learner name, train
              and test object details, parameter, metric, and timer data
              if available.
            * Level 3 - Include cross-validation data.
        leastSessionsAgo : int
            The least number of sessions since the most recent session
            to include in the log. Default is 0.
        mostSessionsAgo : int
            The most number of sessions since the most recent session to
            include in the log. Default is 2.
        startDate :  str, datetime
            A string or datetime object of the date to begin adding
            sessions from the log.
            Acceptable formats:
            * "YYYY-MM-DD"
            * "YYYY-MM-DD HH:MM"
            * "YYYY-MM-DD HH:MM:SS"
        endDate : str, datetime
            A string or datetime object of the date to stop adding
            sessions from the log.
            See ``startDate`` for formatting.
        maximumEntries : int
            Maximum number of entries to allow before stopping the log.
            None will allow all entries provided from the query. Default
            is 100.
        searchForText :  str, regex
            Search for in each log entry. Default is None.
        saveToFileName : str
            The name of a file to write the human readable log. It will
            be saved in the same directory as the logger database.
            Default is None, showLog will print to standard out.
        append : bool
            Append logs to the file in saveToFileName instead of
            overwriting file. Default is False.
        """

        if not self.isAvailable:
            self.setup()

        query, values = _showLogQueryAndValues(leastSessionsAgo,
                                               mostSessionsAgo, startDate,
                                               endDate, maximumEntries,
                                               searchForText, regex)
        sessionLogs = self.extractFromLog(query, values)

        logOutput = _showLogOutputString(sessionLogs, levelOfDetail, append)

        if saveToFileName is not None:
            filePath = os.path.join(self.logLocation, saveToFileName)
            if append:
                with open(filePath, mode='a') as f:
                    f.write("\n")
                    f.write(logOutput)
            else:
                with open(filePath, mode='w') as f:
                    f.write(logOutput)
        else:
            print(logOutput)

###################
### LOG HELPERS ###
###################

def enableLogging(useLog):
    """
    Access useLog value from configuration, if not explictly defined.
    """
    if useLog is None:
        useLog = nimble.settings.get("logger", "enabledByDefault")
        useLog = useLog.lower() == 'true'
    return useLog

def enableDeepLogging():
    """
    Access enableCrossValidationDeepLogging value from configuration.
    """
    deepLog = nimble.settings.get("logger", "enableCrossValidationDeepLogging")
    deepLog = deepLog.lower() == 'true'
    return deepLog

def handleLogging(useLog, logType, *args, **kwargs):
    """
    Store information to be logged in the logger.
    """
    if enableLogging(useLog):
        logFunc = nimble.logger.active.logTypes[logType]
        logFunc(useLog, *args, **kwargs)

def stringToDatetime(string):
    """
    Convert a string into a datetime object.

    The format must be YYYY-MM-DD', 'YYYY-MM-DD HH:MM', or
    'YYYY-MM-DD HH:MM:SS'. Therefore, only 3 valid string lengths are
    possible. Any string not that length will fail the first assertion.
    Otherwise, the string will be parsed storing the locations of valid
    values as arguments to pass to datetime.datetime. The remaining
    three assertions will fail if the dividers are invalid. To create
    the object, integer arguments are required. A ValueError is raised
    if any value cannot be converted to an integer. Last, an attempt to
    create the datetime.datetime object is made, if it deems a value to
    be invalid (i.e a date that doesn't exist) this will also raise a
    ValueError.
    """
    string = string.strip()

    datetimeArgs = []
    dateDividers = []
    dateTimeDivider = None
    timeDividers = []

    if len(string) in [10, 16, 19]:
        datetimeArgs.append(string[:4])
        dateDividers.append(string[4])
        datetimeArgs.append(string[5:7])
        dateDividers.append(string[7])
        datetimeArgs.append(string[8:10])
        if len(string) > 10:
            dateTimeDivider = string[10]
            datetimeArgs.append(string[11:13])
            timeDividers.append(string[13])
            datetimeArgs.append(string[14:16])
        if len(string) > 16:
            timeDividers.append(string[16])
            datetimeArgs.append(string[17:])

    try:
        assert len(datetimeArgs)
        assert all(div == "-" for div in dateDividers)
        if dateTimeDivider is not None:
            assert dateTimeDivider == " "
        if timeDividers:
            assert all(div == ":" for div in timeDividers)
        datetimeArgs = list(map(int, datetimeArgs))

        return datetime.datetime(*datetimeArgs)

    except (AssertionError, ValueError):
        msg = "Invalid datetime format. The accepted formats are: "
        msg += "'YYYY-MM-DD', 'YYYY-MM-DD HH:MM', or 'YYYY-MM-DD HH:MM:SS'"
        raise InvalidArgumentValue(msg)

def _showLogQueryAndValues(leastSessionsAgo, mostSessionsAgo, startDate,
                           endDate, maximumEntries, searchForText, regex):
    """
    Constructs the query string and stores the variables based on the
    arguments passed to the showLog function.
    """
    selectQuery = "SELECT timestamp, sessionNumber, logType, logInfo "
    selectQuery += "FROM (SELECT * FROM logger"
    whereQueryList = []
    includedValues = []
    if leastSessionsAgo is not None:
        # final session value
        # difference between the next sessionNumber and leastSessionsAgo
        where = "sessionNumber <= "
        where += "((SELECT MAX(sessionNumber) FROM logger) - ?)"
        whereQueryList.append(where)
        includedValues.append(leastSessionsAgo)
    if mostSessionsAgo is not None:
        # starting session value
        # difference between the next sessionNumber and mostSessionsAgo
        where = "sessionNumber > ((SELECT MAX(sessionNumber) FROM logger) - ?)"
        whereQueryList.append(where)
        includedValues.append(mostSessionsAgo)
    if startDate is not None:
        whereQueryList.append("timestamp >= ?")
        includedValues.append(stringToDatetime(startDate))
    if endDate is not None:
        whereQueryList.append("timestamp <= ?")
        includedValues.append(stringToDatetime(endDate))
    if searchForText is not None:
        # convert to regex and get pattern
        if regex:
            searchForText = re.compile(searchForText).pattern
            whereQueryList.append("(logType REGEXP ? or logInfo REGEXP ?)")
        else:
            searchForText = "%" + searchForText + "%"
            whereQueryList.append("(logType LIKE ? or logInfo LIKE ?)")
        includedValues.append(searchForText)
        includedValues.append(searchForText)

    if whereQueryList != []:
        whereQuery = " and ".join(whereQueryList)
        fullQuery = selectQuery + " WHERE " + whereQuery
    else:
        fullQuery = selectQuery

    if maximumEntries is not None:
        fullQuery += " ORDER BY entry DESC "
        fullQuery += "LIMIT ?"
        includedValues.append(maximumEntries)
    fullQuery += ") ORDER BY entry ASC;"
    includedValues = tuple(includedValues)

    return fullQuery, includedValues

def _showLogOutputString(listOfLogs, levelOfDetail, append):
    """
    Formats the string that will be output for calls to the showLog
    function.
    """
    fullLog = ""
    if not append:
        fullLog = "{0:^79}\n".format("NIMBLE LOGS")
        fullLog += "." * 79
    previousLogSessionNumber = None
    for log in listOfLogs:
        timestamp = log[0]
        sessionNumber = log[1]
        logType = log[2]
        logString = log[3]
        try:
            logInfo = literal_eval(logString)
        except (ValueError, SyntaxError):
            # logString is a string (cannot eval)
            logInfo = logString
        if sessionNumber != previousLogSessionNumber:
            # skip first new line if appending because append inserts newline
            if not (previousLogSessionNumber is None and append):
                fullLog += "\n"
            logString = "SESSION {0}".format(sessionNumber)
            fullLog += ".{0:^77}.".format(logString)
            fullLog += "\n"
            fullLog += "." * 79
            previousLogSessionNumber = sessionNumber
        try:
            if logType not in ["load", "data", "prep", "run", "crossVal"]:
                fullLog += _buildDefaultLogString(timestamp, logType, logInfo)
                fullLog += '.' * 79
            elif logType == 'load':
                fullLog += _buildLoadLogString(timestamp, logInfo)
                fullLog += '.' * 79
            elif logType == 'data':
                fullLog += _buildDataLogString(timestamp, logInfo)
                fullLog += '.' * 79
            elif logType == 'prep' and levelOfDetail > 1:
                fullLog += _buildPrepLogString(timestamp, logInfo)
                fullLog += '.' * 79
            elif logType == 'run' and levelOfDetail > 1:
                fullLog += _buildRunLogString(timestamp, logInfo)
                fullLog += '.' * 79
            elif logType == 'crossVal' and levelOfDetail > 2:
                fullLog += _buildCVLogString(timestamp, logInfo)
                fullLog += '.' * 79
        except (TypeError, KeyError):
            fullLog += _buildDefaultLogString(timestamp, logType, logInfo)
            fullLog += '.' * 79
    return fullLog

def _buildLoadLogString(timestamp, log):
    """
    Constructs the string that will be output for load logTypes.
    """
    dataCol = "{0} Loaded".format(log["returnType"])
    fullLog = _logHeader(dataCol, timestamp)
    if log["returnType"] != "TrainedLearner":
        fullLog += _formatSessionLine("# of points", log["numPoints"])
        fullLog += _formatSessionLine("# of features", log["numFeatures"])
        for title in ['sparsity', 'name', 'path', 'seed']:
            if log[title] is not None:
                fullLog += _formatSessionLine(title, log[title])
    else:
        fullLog += _formatSessionLine("Learner name", log["learnerName"])
        if log['learnerArgs'] is not None and log['learnerArgs'] != {}:
            argString = "Arguments: "
            argString += _dictToKeywordString(log["learnerArgs"])
            for string in wrap(argString, 79, subsequent_indent=" "*11):
                fullLog += string
                fullLog += "\n"
    return fullLog

def _buildPrepLogString(timestamp, log):
    """
    Constructs the string that will be output for prep logTypes.
    """
    function = "{0}.{1}".format(log["object"], log["function"])
    fullLog = _logHeader(function, timestamp)
    if log['arguments'] != {}:
        argString = "Arguments: "
        argString += _dictToKeywordString(log["arguments"])
        for string in wrap(argString, 79, subsequent_indent=" "*11):
            fullLog += string
            fullLog += "\n"
    return fullLog

def _buildDataLogString(timestamp, log):
    """
    Constructs the string that will be output for data logTypes.
    """
    reportName = log["reportType"].capitalize() + " Report"
    fullLog = _logHeader(reportName, timestamp)
    fullLog += "\n"
    fullLog += log["reportInfo"]
    return fullLog

def _buildRunLogString(timestamp, log):
    """
    Constructs the string that will be output for run logTypes.
    """
    # header data
    time = log.get("time", "")
    if time:
        time = "Completed in {0:.3f} seconds".format(log['time'])
    fullLog = _logHeader(time, timestamp)
    fullLog += '\n{0}("{1}")\n'.format(log['function'], log["learner"])
    # train and test data
    fullLog += _formatSessionLine("Data", "# points", "# features")
    if log.get("trainData", False):
        if log["trainData"].startswith("OBJECT_#"):
            fullLog += _formatSessionLine("trainX", log["trainDataPoints"],
                                      log["trainDataFeatures"])
        else:
            fullLog += _formatSessionLine(log["trainData"],
                                          log["trainDataPoints"],
                                          log["trainDataFeatures"])
    if log.get("trainLabels", False):
        if log["trainLabels"].startswith("OBJECT_#"):
            fullLog += _formatSessionLine("trainY", log["trainLabelsPoints"],
                                      log["trainLabelsFeatures"])
        else:
            fullLog += _formatSessionLine(log["trainLabels"],
                                      log["trainLabelsPoints"],
                                      log["trainLabelsFeatures"])
    if log.get("testData", False):
        if log["testData"].startswith("OBJECT_#"):
            fullLog += _formatSessionLine("testX", log["testDataPoints"],
                                      log["testDataFeatures"])
        else:
            fullLog += _formatSessionLine(log["testData"],
                                          log["testDataPoints"],
                                          log["testDataFeatures"])
    if log.get("testLabels", False):
        if log["testLabels"].startswith("OBJECT_#"):
            fullLog += _formatSessionLine("testY", log["testLabelsPoints"],
                                      log["testLabelsFeatures"])
        else:
            fullLog += _formatSessionLine(log["testLabels"],
                                      log["testLabelsPoints"],
                                      log["testLabelsFeatures"])
    fullLog += "\n"
    # parameter data
    if log.get("arguments", False):
        argString = "Arguments: "
        argString += _dictToKeywordString(log["arguments"])
        for string in wrap(argString, 79, subsequent_indent=" "*11):
            fullLog += string
            fullLog += "\n"
    # metric data
    if log.get("metrics", False):
        fullLog += "Metrics: "
        fullLog += _dictToKeywordString(log["metrics"])
        fullLog += "\n"
    # extraInfo
    if log.get("extraInfo", False):
        fullLog += "Extra Info: "
        fullLog += _dictToKeywordString(log["extraInfo"])
        fullLog += "\n"

    return fullLog

def _buildCVLogString(timestamp, log):
    """
    Constructs the string that will be output for crossVal logTypes.
    """
    crossVal = "Cross Validating for {0}".format(log["learner"])
    fullLog = _logHeader(crossVal, timestamp)
    fullLog += "\n"
    if isinstance(log["learnerArgs"], dict):
        fullLog += "Variable Arguments: "
        fullLog += _dictToKeywordString(log["learnerArgs"])
        fullLog += "\n\n"
    folds = log["folds"]
    metricName, metricOptimal = log["metric"]
    fullLog += "{0}-folding using {1} ".format(folds, metricName)
    fullLog += "optimizing for {0} values\n\n".format(metricOptimal)
    fullLog += "{0:<20s}{1:20s}\n".format("Results", "Arguments")
    for arguments, result in log["performance"]:
        argString = _dictToKeywordString(arguments)
        fullLog += "{0:<20.3f}{1:20s}".format(result, argString)
        fullLog += "\n"
    return fullLog

def _buildDefaultLogString(timestamp, logType, log):
    """
    Constructs the string that will be output for any unrecognized
    logTypes. Formatting varies based on string, list and dictionary
    types passed as the log.
    """
    fullLog = _logHeader(logType, timestamp)
    if isinstance(log, str):
        for string in wrap(log, 79):
            fullLog += string
            fullLog += "\n"
    elif isinstance(log, list):
        listString = _formatSessionLine(log)
        for string in wrap(listString, 79):
            fullLog += string
            fullLog += "\n"
    else:
        dictString = _dictToKeywordString(log)
        for string in wrap(dictString, 79):
            fullLog += string
            fullLog += "\n"
    return fullLog

def _dictToKeywordString(dictionary):
    """
    Formats dictionaries to be more human-readable.
    """
    kvStrings = []
    for key, value in dictionary.items():
        string = "{0}={1}".format(key, value)
        kvStrings.append(string)
    return ", ".join(kvStrings)

def _formatSessionLine(*args):
    """
    Formats equally spaced values for each column.
    """
    args = list(map(str, args))
    lineLog = ""
    equalSpace = int(79 / len(args))
    for arg in args:
        whitespace = equalSpace - len(arg)
        if len(arg) < equalSpace:
            lineLog += arg + " " * whitespace
        else:
            lineLog += arg[:equalSpace - 4] + "... "
    lineLog += "\n"

    return lineLog

def _logHeader(left, right):
    """
    Formats the first line of each log entry.
    """
    lineLog = "\n"
    lineLog += "{0:60}{1:>19}\n".format(left, right)
    return lineLog

def _buildArgDict(func, *args, **kwargs):
    """
    Creates the dictionary of arguments for the prep logType. Adds all
    required arguments and any keyword arguments that are not the
    default values.

    Parameters
    ----------
    argNames : tuple
        The names of all arguments in the function.
    defaults : tuple
        The default values of the arguments.
    """
    argNames, _, _, defaults = nimble.helpers.inspectArguments(func)
    argNames = argNames[1:] # ignore self arg
    nameArgMap = {}
    for name, arg in zip(argNames, args):
        if callable(arg):
            nameArgMap[name] = _extractFunctionString(arg)
        elif isinstance(arg, nimble.data.Base):
            nameArgMap[name] = arg.name
        else:
            nameArgMap[name] = str(arg)

    defaultDict = {}
    if defaults:
        startDefaults = len(argNames) - len(defaults)
        defaultArgs = argNames[startDefaults:]
        for name, value in zip(defaultArgs, defaults):
            if name != 'useLog':
                defaultDict[name] = str(value)

    argDict = {}
    for name in nameArgMap:
        if name not in defaultDict:
            argDict[name] = nameArgMap[name]
        elif nameArgMap[name] != defaultDict[name]:
            argDict[name] = nameArgMap[name]
    for name, value in kwargs.items():
        value = str(value)
        if name in defaultDict and value != defaultDict[name]:
            argDict[name] = value
        else:
            argDict[name] = value

    return argDict

def _extractFunctionString(function):
    """
    Extracts function name or lambda function if passed a function,
    Otherwise returns a string.
    """
    try:
        functionName = function.__name__
        if functionName != "<lambda>":
            return functionName
        else:
            return _lambdaFunctionString(function)
    except AttributeError:
        return str(function)

def _lambdaFunctionString(function):
    """
    Returns a string of a lambda function.

    The lambda function would appear after a call to a nimble function,
    such as calculate(). Because of this, some items on the source line
    may be unrelated to lambda function. For example,
    calculate(lambda x: x + 1, features=0). The end of the lambda
    function occurs either when the open parenthesis from calculate is
    closed or a comma occurs that is not nested within a data structure.
    """
    try:
        sourceLine = inspect.getsourcelines(function)[0][0]
        line = re.findall(r'lambda.*', sourceLine)[0]
        lambdaString = ""
        afterColon = False
        # lambda always starts after open parenthesis
        isOpen = 1
        openers = ['(', '[', '{']
        closers = [')', ']', '}']
        for letter in line:
            if letter in openers:
                isOpen += 1
            elif letter in closers:
                isOpen -= 1
            elif letter == ":":
                afterColon = True
            elif letter == "," and afterColon and isOpen == 1:
                # everything else is not part of lambda
                return lambdaString
            if isOpen == 0:
                return lambdaString
            else:
                lambdaString += letter
    except OSError:
        lambdaString = "<lambda>"
    return lambdaString

def startTimer(useLog):
    """
    Start and return a timer object if this will be logged.
    """
    if enableLogging(useLog):
        timer = Stopwatch()
        timer.start("timer")
        return timer
    return

def stopTimer(timer):
    """
    Stop the timer and return the run time.
    """
    if timer is not None:
        timer.stop("timer")
        return timer.calcRunTime("timer")
    return

#######################
### Initialization  ###
#######################

def initLoggerAndLogConfig():
    """
    Sets up or reads configuration options associated with logging, and
    initializes the currently active logger object using those options.
    """
    try:
        location = nimble.settings.get("logger", "location")
        if location == "":
            location = './logs-nimble'
            nimble.settings.set("logger", "location", location)
            nimble.settings.saveChanges("logger", "location")
    except configErrors:
        location = './logs-nimble'
        nimble.settings.set("logger", "location", location)
        nimble.settings.saveChanges("logger", "location")
    finally:
        nimble.settings.hook("logger", "location", cleanThenReInit_Loc)

    try:
        name = nimble.settings.get("logger", "name")
    except configErrors:
        name = "log-nimble"
        nimble.settings.set("logger", "name", name)
        nimble.settings.saveChanges("logger", "name")
    finally:
        nimble.settings.hook("logger", "name", cleanThenReInit_Name)

    try:
        loggingEnabled = nimble.settings.get("logger", "enabledByDefault")
    except configErrors:
        loggingEnabled = 'True'
        nimble.settings.set("logger", "enabledByDefault", loggingEnabled)
        nimble.settings.saveChanges("logger", "enabledByDefault")

    try:
        deepCV = nimble.settings.get("logger",
                                     'enableCrossValidationDeepLogging')
    except configErrors:
        deepCV = 'False'
        nimble.settings.set("logger", 'enableCrossValidationDeepLogging',
                            deepCV)
        nimble.settings.saveChanges("logger",
                                    'enableCrossValidationDeepLogging')

    return SessionLogger(location, name)


def cleanThenReInit_Loc(newLocation):
    nimble.logger.active.cleanup()
    currName = nimble.settings.get("logger", 'name')
    nimble.logger.active = SessionLogger(newLocation, currName)


def cleanThenReInit_Name(newName):
    nimble.logger.active.cleanup()
    currLoc = nimble.settings.get("logger", 'location')
    nimble.logger.active = SessionLogger(currLoc, newName)
