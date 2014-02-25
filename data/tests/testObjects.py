
import UML

from derived_backend import DerivedBackend
from high_level_backend import HighLevelBackend
from low_level_backend import LowLevelBackend

class TestList(DerivedBackend, HighLevelBackend):
	def __init__(self):
		def maker(data=None, featureNames=None):
			return UML.createData("List", data=data, featureNames=featureNames)

		super(TestList, self).__init__(maker)


class TestMatrix(DerivedBackend, HighLevelBackend):
	def __init__(self):
		def maker(data, featureNames=None):
			return UML.createData("Matrix", data=data, featureNames=featureNames)

		super(TestMatrix, self).__init__(maker)

	def test_foldIterator_ordering(self):
		""" Test that foldIterator() yields folds in the proper order: X and Y folds should be in the same order"""
		twoColumnData = [[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9], [10, 10]]
		matrixObj = UML.createData('Matrix', twoColumnData)
		Ydata = matrixObj.extractFeatures([1])
		Xdata = matrixObj
		XIterator = Xdata.foldIterator(numFolds=2)
		YIterator = Ydata.foldIterator(numFolds=2)
		
		while True: #need to add a test here for when iterator .next() is done
			try:
				curTrainX, curTestX = XIterator.next()
				curTrainY, curTestY = YIterator.next()
			except StopIteration:	#once we've gone through all the folds, this exception gets thrown and we're done!
				break
			curTrainXList = curTrainX.copy(asType="python list")
			curTestXList = curTestX.copy(asType="python list")
			curTrainYList = curTrainY.copy(asType="python list")
			curTestYList = curTestY.copy(asType="python list")

			for i in range(len(curTrainXList)):
				assert curTrainXList[i][0] == curTrainYList[i][0]

			for i in range(len(curTestXList)):
				assert curTestXList[i][0] == curTestYList[i][0]



class TestSparse(DerivedBackend, HighLevelBackend):
	def __init__(self):	
		def maker(data, featureNames=None):
			return UML.createData("Sparse", data=data, featureNames=featureNames)

		super(TestSparse, self).__init__(maker)


class TestBase(LowLevelBackend):
	def __init__(self):
		def makeConst(num):
			def const(dummy=2):
				return num
			return const
		def makeAndDefine(featureNames=None, size=0):
			""" Make a base data object that will think it has as many features as it has featureNames,
			even though it has no actual data """
			cols = size if featureNames is None else len(featureNames)
			specificImp = makeConst(cols)
			UML.data.Base._features_implementation = specificImp
			ret = UML.data.Base((1,cols),featureNames)
			ret._features_implementation = specificImp
			return ret

		super(TestBase, self).__init__(makeAndDefine)