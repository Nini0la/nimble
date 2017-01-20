"""
Unit tests for data creation functions other than createData, which generate
the values placed in the data object. Specifically tested are:
UML.createRandomData, UML.ones, UML.zeros, UML.identity

"""


import numpy
import copy
from nose.tools import *

import UML
from UML.exceptions import ArgumentException
from UML import createRandomData


returnTypes = copy.copy(UML.data.available)


########################
### createRandomData ###
########################

def testReturnsFundamentalsCorrect():
	"""
	function that tests
	-the size of the underlying data is consistent with that requested through our API
	-the data class requested (Matrix, Sparse, List) is that which you get back
	-the data fundamental data type used to store the value of (point, feature) pairs
		is what the user requests ('int' or 'float')
	Note:
	These tests are run for all combinations of the paramaters:
		supportedFundamentalTypes = ['int', 'float']
		returnTypes = ['Matrix','Sparse','List']
		sparsities = [0.0, 0.5, .99]
	"""

	supportedFundamentalTypes = ['int', 'float']
	sparsities = [0.0, 0.5, .99]

	nPoints = 100
	nFeatures = 200
	#sparsity = .5

	for curType in supportedFundamentalTypes:
		for curReturnType in returnTypes:
			for curSparsity in sparsities:

				returned = createRandomData(curReturnType, nPoints, nFeatures, curSparsity, numericType=curType)
				
				assert(returned.pointCount == nPoints)
				assert(returned.featureCount == nFeatures)

				#assert that the requested numerical type was returned
				assert type(returned[0,0] == curType)


#note: makes calls to Base.data with assumptions about underlying datatstructure for sparse data
def testSparsityReturnedPlausible():
	"""
	function that tests:
	-for a dataset with 1500 points and 2000 features (2M pairs) that the number of 
		zero entries is reasonably close to the amount requested.
	Notes:
	-Because the generation of zeros is done stochastically, exact numbers of zeros
		is not informative. Instead, the test checks that the ratio of zeros to all
		points (zeros and non zeros) is within 1 percent of the 1 - sparsity.
	-These tests are run for all combinations of the paramaters:
		supportedFundamentalTypes = ['int', 'float']
		returnTypes = ['Matrix','Sparse','List']
		sparsities = [0.0, 0.5, .99]
	"""
	supportedFundamentalTypes = ['int', 'float']
	sparsities = [0.0, 0.5, .99]

	nPoints = 800
	nFeatures = 1000
	#sparsity = .5

	for curType in supportedFundamentalTypes:
		for curReturnType in returnTypes:
			for curSparsity in sparsities:
				returned = createRandomData(curReturnType, nPoints, nFeatures, curSparsity, numericType=curType)

				if curReturnType.lower() == 'matrix' or curReturnType.lower() == 'list':
					nonZerosCount = numpy.count_nonzero(returned.copyAs('numpyarray'))
					actualSparsity = 1.0 - nonZerosCount/float(nPoints * nFeatures)
					difference = abs(actualSparsity - curSparsity)
					
					assert(difference < .01)
					
				else: #is sparse matrix
					nonZerosCount = returned.data.nnz
					actualSparsity = 1.0 - nonZerosCount/float(nPoints * nFeatures)
					difference = abs(actualSparsity - curSparsity)
					
					assert(difference < .01)

#todo check that sizes of returned objects are what you request via npoints and nfeatures




#######################
### shared backends ###
#######################

def back_constant_sizeChecking(toTest):	
	try:
		toTest("Matrix", -1, 5)
		assert False  # expected ArgmentException for negative numPoints
	except ArgumentException:
		pass
	except Exception:
		assert False  # expected ArgmentException for negative numPoints

	try:
		toTest("Matrix", 4, -3)
		assert False  # expected ArgmentException for negative numFeatures
	except ArgumentException:
		pass
	except Exception:
		assert False  # expected ArgmentException for negative numFeatures

	try:
		toTest("Matrix", 0, 0)
		assert False  # expected ArgmentException for 0 by 0 sized object
	except ArgumentException:
		pass
	except Exception:
		assert False  # expected ArgmentException for 0 by 0 sized object

def back_constant_emptyCreation(toTest):
	fEmpty = numpy.array([[],[]])
	pEmpty = fEmpty.T

	for t in returnTypes:
		retPEmpty = toTest(t, 0, 2)
		retFEmpty = toTest(t, 2, 0)

		expFEmpty = UML.createData(t, fEmpty)
		expPEmpty = UML.createData(t, pEmpty)

		assert retPEmpty == expPEmpty
		assert retFEmpty == expFEmpty

def back_constant_correctSizeAndContents(toTest, value):
	checkSizes = [(1,1), (1,5), (4,1), (10,10), (20,5)]

	for t in returnTypes:
		for size in checkSizes:
			ret = toTest(t, size[0], size[1])
			assert t == ret.getTypeString()

			assert ret.pointCount == size[0]
			assert ret.featureCount == size[1]

			for p in xrange(size[0]):
				for f in xrange(size[1]):
					assert ret[p,f] == value

def back_constant_correctNames(toTest):
	objName = "checkObjName"
	pnames = ["p1", "p2"]
	fnames = ["f1", "f2"]

	for t in returnTypes:
		ret = toTest(t, 2, 2, pointNames=pnames, featureNames=fnames, name=objName)

		assert ret.getPointNames() == pnames
		assert ret.getFeatureNames() == fnames
		assert ret.name == objName

def back_constant_conversionEqualityBetweenTypes(toTest):
	p,f = (10, 2)

	for makeT in returnTypes:
		ret = toTest(makeT, p, f)

		for matchT in returnTypes:
			convertedRet = ret.copyAs(matchT)
			toMatch = toTest(matchT, p, f)

			assert convertedRet == toMatch


############
### ones ###
############

#UML.ones(returnType, numPoints, numFeatures, pointNames=None, featureNames=None, name=None)

# This function relies on createData to actually instantiate our data, and
# never touches the pointNames, featureNames, or names arguments. The
# validity checking of those arguments is therefore not tested, since 
# it is done exclusively in createData. We only check for successful behaviour.

def test_ones_sizeChecking():
	back_constant_sizeChecking(UML.ones)

def test_ones_emptyCreation():
	back_constant_emptyCreation(UML.ones)

def test_ones_correctSizeAndContents():
	back_constant_correctSizeAndContents(UML.ones, 1)

def test_ones_correctNames():
	back_constant_correctNames(UML.ones)

def test_ones_conversionEqualityBetweenTypes():
	back_constant_conversionEqualityBetweenTypes(UML.ones)


#############
### zeros ###
#############

#UML.zeros(returnType, numPoints, numFeatures, pointNames=None, featureNames=None, name=None)

# This function relies on createData to actually instantiate our data, and
# never touches the pointNames, featureNames, or names arguments. The
# validity checking of those arguments is therefore not tested, since 
# it is done exclusively in createData. We only check for successful behaviour.

def test_zeros_sizeChecking():
	back_constant_sizeChecking(UML.zeros)

def test_zeros_emptyCreation():
	back_constant_emptyCreation(UML.zeros)

def test_zeros_correctSizeAndContents():
	back_constant_correctSizeAndContents(UML.zeros, 0)

def test_zeros_correctNames():
	back_constant_correctNames(UML.zeros)

def test_zeros_conversionEqualityBetweenTypes():
	back_constant_conversionEqualityBetweenTypes(UML.zeros)


################
### identity ###
################

#UML.identity(returnType, size, pointNames=None, featureNames=None, name=None)

# This function relies on createData to actually instantiate our data, and
# never touches the pointNames, featureNames, or names arguments. The
# validity checking of those arguments is therefore not tested, since 
# it is done exclusively in createData. We only check for successful behaviour.


def test_identity_sizeChecking():
	try:
		UML.identity("Matrix", -1)
		assert False  # expected ArgmentException for negative size
	except ArgumentException:
		pass
	except Exception:
		assert False  # expected ArgmentException for negative size

	try:
		UML.identity("Matrix", 0)
		assert False  # expected ArgmentException for 0 valued size
	except ArgumentException:
		pass
	except Exception:
		assert False  # expected ArgmentException for 0 valued size


def test_identity_correctSizeAndContents():
	for t in returnTypes:
		for size in xrange(1,5):
			toTest = UML.identity(t, size)
			assert t == toTest.getTypeString()
			for p in xrange(size):
				for f in xrange(size):
					if p == f:
						assert toTest[p,f] == 1
					else:
						assert toTest[p,f] == 0


def test_identity_correctNames():
	objName = "checkObjName"
	pnames = ["p1", "p2"]
	fnames = ["f1", "f2"]

	for t in returnTypes:
		ret = UML.identity(t, 2, pointNames=pnames, featureNames=fnames, name=objName)

		assert ret.getPointNames() == pnames
		assert ret.getFeatureNames() == fnames
		assert ret.name == objName


def test_identity_conversionEqualityBetweenTypes():
	size = 7

	for makeT in returnTypes:
		ret = UML.identity(makeT, size)

		for matchT in returnTypes:
			convertedRet = ret.copyAs(matchT)
			toMatch = UML.identity(matchT, size)

			assert convertedRet == toMatch



# EOF Marker