import ..combinations.Combinations
import ..performance.performance_interface


def runAndTest(trainData, testData, labelIndicator, functionText, performanceMetricFuncs):
	"""
		A function to go through the entire process of training and testing numerous different
		classifiers.  The different classifiers are defined in functionText, which uses the
		<...|...|...> syntax for setting the different algorithms and parameters to be tested.
		trainData and testData contain the training and testing sets, respectively, in some form
		of sparse or dense matrix (see footnote).  labelIndicator contains the index of the column
		with known class labels (i.e. the dependent variable).  performanceMetricFuncs contains
		functions that can be applied to predicted data & known data to compute a measure of error.

		1. What to do if some algorithms expect dense matrices and some expect sparse matrices?  
		Do we assume that the interface classes can handle converting input data to the proper 
		format?

		2.  Do we need to make copies of trainData or testData before calling applyCodeVersions? Is 
		that even possible, given that it's just one call?

		3.  Do we want this function to do the job of splitting data into train and test sets?  Or 
		assume it is always done before this is called (would need proportion of train and test as 
			argument...)

		4.  Should we make sure that we can handle multiple performanceMetricFuncs?  Will we ever 
		want to calculate more than one at a time?  If not, should we restrict functionality to 
		only accept one performance metric at a time?  For now, going to assume there is only one
		to simplify sorting.

		5.  applyCodeVersions doesn't return enough information to associate function/classifiers
		definition with the corresponding data set.  How do we maintain that association?  

		6.  Logging - do we try to pass the logger one object per run (after all processing is done), 
		or do we send messages to the logger multiple times throughout the process of training and 
		testing.  If it is the latter, can we be sure they will be sequential (i.e. messages from 
		one run will not be interleaved with messages from another run.)  If they won't be strictly
		sequential:  can we give each run an ID number, and include it with each message?
	"""
	combos = Combinations.functionCombinations(functionTexts)
	knownLabels = testData.extractColumns([labelIndicator])
	functionArgs = {'trainData':trainData,
					 'testData':testData,
					 'dependentVar':labelIndicator
					}

	#rawResults contains predictions for each version of a learning function in the combos list
	rawResults = Combinations.applyCodeVersions(combos, functionArgs)
	#how do we associate items in rawResults w/the function defining them?  applyCodeVersions just
	#returns data set w/predicted labels.  

	#now we need to compute performance metric(s) for all prediction sets
	performanceResults = []
	for result in rawResults:
		#are predicted labels always in column 0? 
		predictedLabels = result.extractColumns([0]);
		performanceResults.append(performance_interface.computeMetrics(knownLabels, knownValues=None, predictedLabels, perfomanceMetricFuncs))
		#issue: can we associate output values (error measure) w/input values (algorithm + parameters)?
		#issue:  computeMetrics returns hash association metric function with numerical result of that function.  
		#How do we sort, then?  





