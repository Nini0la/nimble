"""
Short module demonstrating the full pipeline of train - test - log results.

"""

from allowImports import boilerplate
boilerplate()

if __name__ == "__main__":
	from UML import run
	from UML import normalize
	from UML import data
	from UML.performance.runner import runAndTest
	from UML.performance.metric_functions import classificationError

	variables = ["x1","x2","x3"]
	data1 = [[1,0,0,1], [3,3,3,1], [5,0,0,0],]
	trainObj = data('DenseMatrixData', data1, variables)

	data2 = [[1,0,0,1],[1,1,1,0],[5,1,1,0], [3,4,4,1]]
	testObj = data('DenseMatrixData', data2)

	runnerFuncStr = """def logisticRegr(trainX, testX, dependentVar):
		return run('sciKitLearn', 'LogisticRegression', trainX, testX, dependentVar)
		"""

	metricFuncs = []
	metricFuncs.append(classificationError)

	results = runAndTest(trainObj, testObj, trainDependentVar=3, testDependentVar=3, function=runnerFuncStr, performanceMetricFuncs=metricFuncs)

	hrLog = HumanReadableRunLog("~/fullCycleLogHR.txt")
	mrLog = MachineReadableRunLog("~/fullCycleLogMR.txt")
	
	hrLog.logRun(trainObj, testObj, runnerFuncStr, results)
	mrLog.logRun(trainObj, testObj, runnerFuncStr, results)