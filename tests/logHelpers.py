import UML
from UML.configuration import configSafetyWrapper

def logCountAssertionFactory(count):
    """
    Generate a wrapper to assert the log increased by a certain count.
    """
    def logCountAssertion(function):
        @configSafetyWrapper
        def wrapped(*args, **kwargs):
            UML.settings.set('logger', 'enabledByDefault', 'True')
            UML.settings.set('logger', 'enableCrossValidationDeepLogging', 'True')
            logger = UML.logger.active
            countQuery = "SELECT COUNT(entry) FROM logger"
            startCount = logger.extractFromLog(countQuery)[0][0]
            ret = function(*args, **kwargs)
            endCount = logger.extractFromLog(countQuery)[0][0]
            print(startCount, endCount)
            UML.showLog()
            assert startCount + count == endCount
            return ret
        wrapped.__name__ = function.__name__
        wrapped.__doc__ = function.__doc__
        return wrapped
    return logCountAssertion

noLogEntryExpected = logCountAssertionFactory(0)
oneLogEntryExpected = logCountAssertionFactory(1)
twoLogEntriesExpected = logCountAssertionFactory(2)
threeLogEntriesExpected = logCountAssertionFactory(3)
fourLogEntriesExpected = logCountAssertionFactory(4)
