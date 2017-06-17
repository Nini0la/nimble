"""
Class extending Base, using a numpy dense matrix to store data.

"""

import numpy
import sys
import itertools
import copy

import UML
from base import Base
from base_view import BaseView
from dataHelpers import View
from UML.exceptions import ArgumentException, PackageException
from UML.randomness import pythonRandom
from UML.randomness import numpyRandom
scipy = UML.importModule('scipy.io')

class Matrix(Base):
    """
    Class providing implementations of data manipulation operations on data stored
    in a numpy dense matrix.

    """

    def __initnew__(self, data, featureNames=None, reuseData=False, **kwds):
        """
        data can only be a numpy matrix
        """

        if (not isinstance(data, numpy.matrix)) and 'PassThrough' not in str(type(data)):
            msg = "the input data can only be a numpy matrix or BaseView."
            raise ArgumentException(msg)

        if isinstance(data, numpy.matrix):
            if reuseData:
                self.data = data
            else:
                self.data = copy.deepcopy(data)

        kwds['featureNames'] = featureNames
        kwds['shape'] = self.data.shape
        super(Matrix, self).__init__(**kwds)

    def __init__(self, data, featureNames=None, reuseData=False, **kwds):
        try:
            if scipy and scipy.sparse.isspmatrix(data):
                try:
                    self.data = numpy.matrix(data.todense(), dtype=numpy.float)
                except ValueError:
                    self.data = numpy.matrix(data.todense(), dtype=object)
            else:
                if reuseData and isinstance(data, numpy.matrix):
                    self.data = data
                else:
                    if isinstance(data, list) and data == []:
                        cols = 0
                        if featureNames is not None:
                            cols = len(featureNames)
                        data = numpy.empty(shape=(0, cols))
                    try:
                        self.data = numpy.matrix(data, dtype=numpy.float)
                    except ValueError:
                        self.data = numpy.matrix(data, dtype=object)
        except ValueError:
            einfo = sys.exc_info()
            #if not ignore:
            #	raise einfo[1], None, einfo[2]
            msg = "ValueError during instantiation. Matrix does not accept strings "
            msg += "in the input (with the exception of those that are directly convertible, "
            msg += "like '3' or '-11'), having included strings is the likely cause for "
            msg += "the error"
            raise ArgumentException(msg)

        kwds['featureNames'] = featureNames
        kwds['shape'] = self.data.shape
        super(Matrix, self).__init__(**kwds)


    def _transpose_implementation(self):
        """
        Function to transpose the data, ie invert the feature and point indices of the data.

        This is not an in place operation, a new list of lists is constructed.
        """
        self.data = self.data.getT()


    def _appendPoints_implementation(self, toAppend):
        """
        Append the points from the toAppend object to the bottom of the features in this object

        """
        self.data = numpy.concatenate((self.data, toAppend.data), 0)


    def _appendFeatures_implementation(self, toAppend):
        """
        Append the features from the toAppend object to right ends of the points in this object

        """
        self.data = numpy.concatenate((self.data, toAppend.data), 1)

    def _sortPoints_implementation(self, sortBy, sortHelper):
        """
        Modify this object so that the points are sorted using the built in python
        sort on point views. The input arguments are passed to that function unaltered
        This function returns a list of pointNames indicating the new order of the data.

        """
        return self._sort_implementation(sortBy, sortHelper, 'point')

    def _sortFeatures_implementation(self, sortBy, sortHelper):
        """
        Modify this object so that the features are sorted using the built in python
        sort on feature views. The input arguments are passed to that function unaltered
        This function returns a list of featureNames indicating the new order of the data.

        """
        return self._sort_implementation(sortBy, sortHelper, 'feature')

    def _sort_implementation(self, sortBy, sortHelper, axis):
        if axis == 'point':
            test = self.pointView(0)
            viewIter = self.pointIterator()
            indexGetter = self.getPointIndex
            nameGetter = self.getPointName
            nameGetterStr = 'getPointName'
        else:
            test = self.featureView(0)
            viewIter = self.featureIterator()
            indexGetter = self.getFeatureIndex
            nameGetter = self.getFeatureName
            nameGetterStr = 'getFeatureName'
        scorer = None
        comparator = None
        try:
            sortHelper(test)
            scorer = sortHelper
        except TypeError:
            pass
        try:
            sortHelper(test, test)
            comparator = sortHelper
        except TypeError:
            pass

        if sortHelper is not None and scorer is None and comparator is None:
            raise ArgumentException("sortHelper is neither a scorer or a comparator")

        if comparator is not None:
            # make array of views
            viewArray = []
            for v in viewIter:
                viewArray.append(v)

            viewArray.sort(cmp=comparator)
            indexPosition = []
            for i in xrange(len(viewArray)):
                index = indexGetter(getattr(viewArray[i], nameGetterStr)(0))
                indexPosition.append(index)
            indexPosition = numpy.array(indexPosition)
        elif hasattr(scorer, 'permuter'):
            scoreArray = scorer.indices
            indexPosition = numpy.argsort(scoreArray)
        else:
            # make array of views
            viewArray = []
            for v in viewIter:
                viewArray.append(v)

            scoreArray = viewArray
            if scorer is not None:
                # use scoring function to turn views into values
                for i in xrange(len(viewArray)):
                    scoreArray[i] = scorer(viewArray[i])
            else:
                for i in xrange(len(viewArray)):
                    scoreArray[i] = viewArray[i][sortBy]

            # use numpy.argsort to make desired index array
            # this results in an array whose ith entry contains the the
            # index into the data of the value that should be in the ith
            # position.
            indexPosition = numpy.argsort(scoreArray)

        # use numpy indexing to change the ordering
        if axis == 'point':
            self.data = self.data[indexPosition, :]
        else:
            self.data = self.data[:, indexPosition]

        # we convert the indices of the their previous location into their feature names
        newNameOrder = []
        for i in xrange(len(indexPosition)):
            oldIndex = indexPosition[i]
            newName = nameGetter(oldIndex)
            newNameOrder.append(newName)
        return newNameOrder


    def _extractPoints_implementation(self, toExtract, start, end, number, randomize):
        """
        Function to extract points according to the parameters, and return an object containing
        the removed points with default names. The actual work is done by further helper
        functions, this determines which helper to call, and modifies the input to accomodate
        the number and randomize parameters, where number indicates how many of the possibilities
        should be extracted, and randomize indicates whether the choice of who to extract should
        be by order or uniform random.

        """
        # list of identifiers
        if isinstance(toExtract, list):
            assert number == len(toExtract)
            assert not randomize
            return self._extractPointsByList_implementation(toExtract)
        # boolean function
        elif hasattr(toExtract, '__call__'):
            if randomize:
                #apply to each
                raise NotImplementedError  # TODO randomize in the extractPointByFunction case
            else:
                return self._extractPointsByFunction_implementation(toExtract, number)
        # by range
        elif start is not None or end is not None:
            return self._extractPointsByRange_implementation(start, end)
        else:
            msg = "Malformed or missing inputs"
            raise ArgumentException(msg)

    def _extractPointsByList_implementation(self, toExtract):
        """
        Modify this object to have only the points that are not given in the input,
        returning an object containing those points that are.

        """
        ret = self.data[toExtract]
        self.data = numpy.delete(self.data, toExtract, 0)

        # construct featureName list
        nameList = []
        for index in toExtract:
            nameList.append(self.getPointName(index))

        return Matrix(ret, pointNames=nameList)

    def _extractPointsByFunction_implementation(self, toExtract, number):
        """
        Modify this object to have only the points that do not satisfy the given function,
        returning an object containing those points that do.

        """
        #if the toExtract is a vectorized function, then call matrix based function
        #otherwise, call view based function
        if hasattr(toExtract, 'vectorized') and toExtract.vectorized:
            function = matrixBasedApplyAlongAxis
        else:
            function = viewBasedApplyAlongAxis
        results = function(toExtract, 'point', self)
        results = results.astype(numpy.int)

        # need to convert our 1/0 array to to list of points to be removed
        # can do this by just getting the non-zero indices
        toRemove = numpy.flatnonzero(results)
        ###spencer added this on 3/7/2017 to make it take into account number:
        if number is not None and len(toRemove) > number:
            toRemove = toRemove[:number]
            assert len(toRemove) == number
        ###end of spencer added code
        ret = self.data[toRemove, :]
        self.data = numpy.delete(self.data, toRemove, 0)

        # construct featureName list
        nameList = []
        for index in toRemove:
            nameList.append(self.getPointName(index))

        return Matrix(ret, pointNames=nameList)

    def _extractPointsByRange_implementation(self, start, end):
        """
        Modify this object to have only those points that are not within the given range,
        inclusive; returning an object containing those points that are.

        """
        # +1 on end in ranges, because our ranges are inclusive
        ret = self.data[start:end + 1, :]
        self.data = numpy.delete(self.data, numpy.s_[start:end + 1], 0)

        # construct featureName list
        nameList = []
        for index in xrange(start, end + 1):
            nameList.append(self.getPointName(index))

        return Matrix(ret, pointNames=nameList)

    def _extractFeatures_implementation(self, toExtract, start, end, number, randomize):
        """
        Function to extract features according to the parameters, and return an object containing
        the removed features with their featureName names from this object. The actual work is done by
        further helper functions, this determines which helper to call, and modifies the input
        to accomodate the number and randomize parameters, where number indicates how many of the
        possibilities should be extracted, and randomize indicates whether the choice of who to
        extract should be by order or uniform random.

        """
        # list of identifiers
        if isinstance(toExtract, list):
            assert number == len(toExtract)
            assert not randomize
            return self._extractFeaturesByList_implementation(toExtract)
        # boolean function
        elif hasattr(toExtract, '__call__'):
            if randomize:
                #apply to each
                raise NotImplementedError  # TODO
            else:
                return self._extractFeaturesByFunction_implementation(toExtract, number)
        # by range
        elif start is not None or end is not None:
            return self._extractFeaturesByRange_implementation(start, end)
        else:
            raise ArgumentException("Malformed or missing inputs")


    def _extractFeaturesByList_implementation(self, toExtract):
        """
        Modify this object to have only the features that are not given in the input,
        returning an object containing those features that are.

        """
        ret = self.data[:, toExtract]
        self.data = numpy.delete(self.data, toExtract, 1)

        # construct featureName list
        featureNameList = []
        for index in toExtract:
            featureNameList.append(self.getFeatureName(index))

        return Matrix(ret, featureNames=featureNameList, pointNames=self.getPointNames())

    def _extractFeaturesByFunction_implementation(self, toExtract, number):
        """
        Modify this object to have only the features whose views do not satisfy the given
        function, returning an object containing those features whose views do.

        """
        #if the toExtract is a vectorized function, then call matrix based function
        #otherwise, call view based function
        if hasattr(toExtract, 'vectorized') and toExtract.vectorized:
            function = matrixBasedApplyAlongAxis
        else:
            function = viewBasedApplyAlongAxis
        results = function(toExtract, 'feature', self)
        results = results.astype(numpy.int)

        # need to convert our 1/0 array to to list of points to be removed
        # can do this by just getting the non-zero indices
        toRemove = numpy.flatnonzero(results)

        return self._extractFeaturesByList_implementation(toRemove)


    def _extractFeaturesByRange_implementation(self, start, end):
        """
        Modify this object to have only those features that are not within the given range,
        inclusive; returning an object containing those features that are.

        start and end must not be null, must be within the range of possible features,
        and start must not be greater than end

        """
        # +1 on end in ranges, because our ranges are inclusive
        ret = self.data[:, start:end + 1]
        self.data = numpy.delete(self.data, numpy.s_[start:end + 1], 1)

        # construct featureName list
        featureNameList = []
        for index in xrange(start, end + 1):
            featureNameList.append(self.getFeatureName(index))

        return Matrix(ret, featureNames=featureNameList)

    def _mapReducePoints_implementation(self, mapper, reducer):
        # apply_along_axis() expects a scalar or array of scalars as output,
        # but our mappers output a list of tuples (ie a sequence type)
        # which is not allowed. This packs key value pairs into an array
        def mapperWrapper(point):
            pairs = mapper(point)
            ret = []
            for (k, v) in pairs:
                ret.append(k)
                ret.append(v)
            return numpy.array(ret)

        mapResultsMatrix = numpy.apply_along_axis(mapperWrapper, 1, self.data)
        mapResults = {}
        for pairsArray in mapResultsMatrix:
            for i in xrange(len(pairsArray) / 2):
                # pairsArray has key value pairs packed back to back
                k = pairsArray[i * 2]
                v = pairsArray[(i * 2) + 1]
                # if key is new, we must add an empty list
                if k not in mapResults:
                    mapResults[k] = []
                # append this value to the list of values associated with the key
                mapResults[k].append(v)

        # apply the reducer to the list of values associated with each key
        ret = []
        for mapKey in mapResults.keys():
            mapValues = mapResults[mapKey]
            # the reducer will return a tuple of a key to a value
            redRet = reducer(mapKey, mapValues)
            if redRet is not None:
                (redKey, redValue) = redRet
                ret.append([redKey, redValue])
        return Matrix(ret)

    def _getTypeString_implementation(self):
        return 'Matrix'

    def _isIdentical_implementation(self, other):
        if not isinstance(other, Matrix):
            return False
        if self.pointCount != other.pointCount:
            return False
        if self.featureCount != other.featureCount:
            return False

        try:
            numpy.testing.assert_equal(self.data, other.data)
        except AssertionError:
            return False
        return True

    def _writeFile_implementation(self, outPath, format, includePointNames, includeFeatureNames):
        """
        Function to write the data in this object to a file using the specified
        format. outPath is the location (including file name and extension) where
        we want to write the output file. includeNames is boolean argument
        indicating whether the file should start with comment lines designating
        pointNames and featureNames.

        """
        if format not in ['csv', 'mtx']:
            msg = "Unrecognized file format. Accepted types are 'csv' and 'mtx'. They may "
            msg += "either be input as the format parameter, or as the extension in the "
            msg += "outPath"
            raise ArgumentException(msg)

        if format == 'csv':
            return self._writeFileCSV_implementation(outPath, includePointNames, includeFeatureNames)
        if format == 'mtx':
            return self._writeFileMTX_implementation(outPath, includePointNames, includeFeatureNames)

    def _writeFileCSV_implementation(self, outPath, includePointNames, includeFeatureNames):
        """
        Function to write the data in this object to a CSV file at the designated
        path.

        """
        with open(outPath, 'w') as outFile:

            if includeFeatureNames:
                # to signal that the first line contains feature Names
                outFile.write('\n\n')

                def combine(a, b):
                    return a + ',' + b

                fnames = self.getFeatureNames()
                fnamesLine = reduce(combine, fnames)
                fnamesLine += '\n'
                if includePointNames:
                    outFile.write('point_names,')

                outFile.write(fnamesLine)

            if includePointNames:
                pnames = numpy.matrix(self.getPointNames())
                pnames = pnames.transpose()

                viewData = self.data.view()
                toWrite = numpy.concatenate((pnames, viewData), 1)

                numpy.savetxt(outFile, toWrite, delimiter=',', fmt='%s')
            else:
                numpy.savetxt(outFile, self.data, delimiter=',')


    def _writeFileMTX_implementation(self, outPath, includePointNames, includeFeatureNames):
        if not scipy:
            msg = "scipy is not available"
            raise PackageException(msg)

        def makeNameString(count, namesGetter):
            nameString = "#"
            for i in xrange(count):
                nameString += namesGetter(i)
                if not i == count - 1:
                    nameString += ','
            return nameString

        header = ''
        if includePointNames:
            header = makeNameString(self.pointCount, self.getPointName)
            header += '\n'
        else:
            header += '#\n'
        if includeFeatureNames:
            header += makeNameString(self.featureCount, self.getFeatureName)
        else:
            header += '#\n'

        if header != '':
            scipy.io.mmwrite(target=outPath, a=self.data, comment=header)
        else:
            scipy.io.mmwrite(target=outPath, a=self.data)

    def _referenceDataFrom_implementation(self, other):
        if not isinstance(other, Matrix):
            raise ArgumentException("Other must be the same type as this object")

        self.data = other.data

    def _copyAs_implementation(self, format):
        if format == 'Sparse':
            return UML.data.Sparse(self.data, pointNames=self.getPointNames(), featureNames=self.getFeatureNames())
        if format == 'List':
            return UML.data.List(self.data, pointNames=self.getPointNames(), featureNames=self.getFeatureNames())
        if format is None or format == 'Matrix':
            return UML.data.Matrix(self.data, pointNames=self.getPointNames(), featureNames=self.getFeatureNames())
        if format == 'pythonlist':
            return self.data.tolist()
        if format == 'numpyarray':
            return numpy.array(self.data)
        if format == 'numpymatrix':
            return numpy.matrix(self.data)
        if format == 'scipycsc':
            if not scipy:
                msg = "scipy is not available"
                raise PackageException(msg)
            return scipy.sparse.csc_matrix(self.data)
        if format == 'scipycsr':
            if not scipy:
                msg = "scipy is not available"
                raise PackageException(msg)
            return scipy.sparse.csr_matrix(self.data)
        if format == 'DataFrame':
            return UML.data.DataFrame(self.data, pointNames=self.getPointNames(), featureNames=self.getFeatureNames())

        return Matrix(self.data, pointNames=self.getPointNames(), featureNames=self.getFeatureNames())

    def _copyPoints_implementation(self, points, start, end):
        if points is not None:
            ret = self.data[points]
        else:
            ret = self.data[start:end + 1, :]

        return Matrix(ret)

    def _copyFeatures_implementation(self, indices, start, end):
        if indices is not None:
            ret = self.data[:, indices]
        else:
            ret = self.data[:, start:end + 1]

        return Matrix(ret)


    def _transformEachPoint_implementation(self, function, points):
        for i, p in enumerate(self.pointIterator()):
            if points is not None and i not in points:
                continue
            currRet = function(p)
            if len(currRet) != self.featureCount:
                msg = "function must return an iterable with as many elements as features in this object"
                raise ArgumentException(msg)

            self.data[i, :] = numpy.array(currRet).reshape(1, self.featureCount)

    def _transformEachFeature_implementation(self, function, features):
        for j, f in enumerate(self.featureIterator()):
            if features is not None and j not in features:
                continue
            currRet = function(f)
            if len(currRet) != self.pointCount:
                msg = "function must return an iterable with as many elements as points in this object"
                raise ArgumentException(msg)

            self.data[:, j] = numpy.array(currRet).reshape(self.pointCount, 1)

    def _transformEachElement_implementation(self, function, points, features, preserveZeros, skipNoneReturnValues):
        oneArg = False
        try:
            function(0, 0, 0)
        except TypeError:
            oneArg = True

        IDs = itertools.product(xrange(self.pointCount), xrange(self.featureCount))
        for (i, j) in IDs:
            currVal = self.data[i, j]

            if points is not None and i not in points:
                continue
            if features is not None and j not in features:
                continue
            if preserveZeros and currVal == 0:
                continue

            if oneArg:
                currRet = function(currVal)
            else:
                currRet = function(currVal, i, j)

            if skipNoneReturnValues and currRet is None:
                continue

            self.data[i, j] = currRet


    def _fillWith_implementation(self, values, pointStart, featureStart, pointEnd, featureEnd):
        if not isinstance(values, UML.data.Base):
            values = values * numpy.ones((pointEnd - pointStart + 1, featureEnd - featureStart + 1))
        else:
            values = values.data

        self.data[pointStart:pointEnd + 1, featureStart:featureEnd + 1] = values


    def _getitem_implementation(self, x, y):
        return self.data[x, y]

    def _view_implementation(self, pointStart, pointEnd, featureStart, featureEnd):
        class MatrixView(BaseView, Matrix):
            def __init__(self, **kwds):
                super(MatrixView, self).__init__(**kwds)

        kwds = {}
        kwds['data'] = self.data[pointStart:pointEnd, featureStart:featureEnd]
        kwds['source'] = self
        kwds['pointStart'] = pointStart
        kwds['pointEnd'] = pointEnd
        kwds['featureStart'] = featureStart
        kwds['featureEnd'] = featureEnd
        kwds['reuseData'] = True

        return MatrixView(**kwds)

    def _validate_implementation(self, level):
        shape = numpy.shape(self.data)
        assert shape[0] == self.pointCount
        assert shape[1] == self.featureCount


    def _containsZero_implementation(self):
        """
        Returns True if there is a value that is equal to integer 0 contained
        in this object. False otherwise

        """
        return 0 in self.data

    def _nonZeroIteratorPointGrouped_implementation(self):
        class nzIt(object):
            def __init__(self, source):
                self._source = source
                self._pIndex = 0
                self._pStop = source.pointCount
                self._fIndex = 0
                self._fStop = source.featureCount

            def __iter__(self):
                return self

            def next(self):
                while (self._pIndex < self._pStop):
                    value = self._source.data[self._pIndex, self._fIndex]

                    self._fIndex += 1
                    if self._fIndex >= self._fStop:
                        self._fIndex = 0
                        self._pIndex += 1

                    if value != 0:
                        return value

                raise StopIteration

        return nzIt(self)

    def _nonZeroIteratorFeatureGrouped_implementation(self):
        class nzIt(object):
            def __init__(self, source):
                self._source = source
                self._pIndex = 0
                self._pStop = source.pointCount
                self._fIndex = 0
                self._fStop = source.featureCount

            def __iter__(self):
                return self

            def next(self):
                while (self._fIndex < self._fStop):
                    value = self._source.data[self._pIndex, self._fIndex]

                    self._pIndex += 1
                    if self._pIndex >= self._pStop:
                        self._pIndex = 0
                        self._fIndex += 1

                    if value != 0:
                        return value

                raise StopIteration

        return nzIt(self)


    def _matrixMultiply_implementation(self, other):
        """
        Matrix multiply this UML data object against the provided other UML data
        object. Both object must contain only numeric data. The featureCount of
        the calling object must equal the pointCount of the other object. The
        types of the two objects may be different, and the return is guaranteed
        to be the same type as at least one out of the two, to be automatically
        determined according to efficiency constraints.

        """
        if isinstance(other, Matrix) or isinstance(other, UML.data.Sparse):
            return Matrix(self.data * other.data)
        else:
            return Matrix(self.data * other.copyAs("numpyarray"))

    def _elementwiseMultiply_implementation(self, other):
        """
        Perform element wise multiplication of this UML data object against the
        provided other UML data object. Both objects must contain only numeric
        data. The pointCount and featureCount of both objects must be equal. The
        types of the two objects may be different, but the returned object will
        be the inplace modification of the calling object.

        """
        if isinstance(other, UML.data.Sparse):
            self.data = numpy.matrix(other.data.multiply(self.data))
        else:
            self.data = numpy.multiply(self.data, other.data)

    def _scalarMultiply_implementation(self, scalar):
        """
        Multiply every element of this UML data object by the provided scalar.
        This object must contain only numeric data. The 'scalar' parameter must
        be a numeric data type. The returned object will be the inplace modification
        of the calling object.

        """
        self.data = self.data * scalar

    def _mul__implementation(self, other):
        if isinstance(other, UML.data.Base):
            return self._matrixMultiply_implementation(other)
        else:
            ret = self.copy()
            ret._scalarMultiply_implementation(other)
            return ret

    def _add__implementation(self, other):
        if isinstance(other, UML.data.Base):
            ret = self.data + other.data
        else:
            ret = self.data + other
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _radd__implementation(self, other):
        ret = other + self.data
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _iadd__implementation(self, other):
        if isinstance(other, UML.data.Base):
            ret = self.data + other.data
        else:
            ret = self.data + other
        self.data = ret
        return self

    def _sub__implementation(self, other):
        if isinstance(other, UML.data.Base):
            ret = self.data - other.data
        else:
            ret = self.data - other
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _rsub__implementation(self, other):
        ret = other - self.data
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _isub__implementation(self, other):
        if isinstance(other, UML.data.Base):
            ret = self.data - other.data
        else:
            ret = self.data - other
        self.data = ret
        return self

    def _div__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data / other.data.todense()
            else:
                ret = self.data / other.data
        else:
            ret = self.data / other
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _rdiv__implementation(self, other):
        ret = other / self.data
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _idiv__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data / other.data.todense()
            else:
                ret = self.data / other.data
        else:
            ret = self.data / other
        self.data = ret
        return self

    def _truediv__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data.__truediv__(other.data.todense())
            else:
                ret = self.data.__truediv__(other.data)
        else:
            ret = self.data.__itruediv__(other)
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _rtruediv__implementation(self, other):
        ret = self.data.__rtruediv__(other)
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _itruediv__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data.__itruediv__(other.data.todense())
            else:
                ret = self.data.__itruediv__(other.data)
        else:
            ret = self.data.__itruediv__(other)
        self.data = ret
        return self

    def _floordiv__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data // other.data.todense()
            else:
                ret = self.data // other.data
        else:
            ret = self.data // other
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _rfloordiv__implementation(self, other):
        ret = other // self.data
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

    def _ifloordiv__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data // other.data.todense()
            else:
                ret = self.data // other.data
        else:
            ret = self.data // other
        self.data = ret
        return self

    def _mod__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data % other.data.todense()
            else:
                ret = self.data % other.data
        else:
            ret = self.data % other
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _rmod__implementation(self, other):
        ret = other % self.data
        return Matrix(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _imod__implementation(self, other):
        if isinstance(other, UML.data.Base):
            if scipy and scipy.sparse.isspmatrix(other.data):
                ret = self.data % other.data.todense()
            else:
                ret = self.data % other.data
        else:
            ret = self.data % other
        self.data = ret
        return self


def viewBasedApplyAlongAxis(function, axis, outerObject):
    """ applies the given function to each view along the given axis, returning the results
    of the function in numpy array """
    if axis == "point":
        maxVal = outerObject.data.shape[0]
        viewMaker = outerObject.pointView
    else:
        if axis != "feature":
            raise ArgumentException("axis must be 'point' or 'feature'")
        maxVal = outerObject.data.shape[1]
        viewMaker = outerObject.featureView
    ret = numpy.zeros(maxVal, dtype=numpy.float)
    for i in xrange(0, maxVal):
        funcOut = function(viewMaker(i))
        ret[i] = funcOut

    return ret


def matrixBasedApplyAlongAxis(function, axis, outerObject):
    """
    applies the given function to the underlying numpy matrix along the given axis,
    returning the results of the function in numpy array
    """
    #make sure the 3 attributes are in the function object
    if not (hasattr(function, 'nameOfFeatureOrPoint') \
                and hasattr(function, 'valueOfFeatureOrPoint') and hasattr(function, 'optr')):
        msg = "some important attribute is missing in the input function"
        raise ArgumentException(msg)
    if axis == "point":
        #convert name of feature to index of feature
        indexOfFeature = outerObject.getFeatureIndex(function.nameOfFeatureOrPoint)
        #extract the feature from the underlying matrix
        queryData = outerObject.data[:, indexOfFeature]
    else:
        if axis != "feature":
            raise ArgumentException("axis must be 'point' or 'feature'")
        #convert name of point to index of point
        indexOfPoint = outerObject.getPointIndex(function.nameOfFeatureOrPoint)
        #extract the point from the underlying matrix
        queryData = outerObject.data[indexOfPoint, :]
    ret = function.optr(queryData, function.valueOfFeatureOrPoint)
    #convert the result from matrix to numpy array
    ret = ret.astype(numpy.float).A1

    return ret
