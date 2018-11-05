"""
Class extending Base, defining an object to hold and manipulate a scipy coo_matrix.

"""

from __future__ import division
from __future__ import absolute_import
import numpy
import copy
from collections import defaultdict

import UML

from UML.exceptions import ArgumentException, PackageException
from six.moves import range
from functools import reduce

scipy = UML.importModule('scipy')
if scipy is not None:
    from scipy.sparse import coo_matrix
    from scipy.io import mmwrite

import UML.data
from . import dataHelpers
from .base import Base, cmp_to_key
from .base_view import BaseView
from .dataHelpers import inheritDocstringsFactory
from .dataHelpers import DEFAULT_PREFIX
from .dataHelpers import allDataIdentical

from UML.exceptions import ImproperActionException
from UML.exceptions import PackageException
from UML.randomness import pythonRandom
pd = UML.importModule('pandas')
import warnings

@inheritDocstringsFactory(Base)
class Sparse(Base):

    def __init__(self, data, pointNames=None, featureNames=None, reuseData=False, elementType=None, **kwds):
        """

        """
        if not scipy:
            msg = 'To use class Sparse, scipy must be installed.'
            raise PackageException(msg)

        if (not isinstance(data, numpy.matrix)) and (not scipy.sparse.isspmatrix(data)):
            msg = "the input data can only be a scipy sparse matrix or a numpy matrix or CooWithEmpty or CooDummy."
            raise ArgumentException(msg)

        if scipy.sparse.isspmatrix_coo(data):
            if reuseData:
                self.data = data
            else:
                self.data = data.copy()
        elif scipy.sparse.isspmatrix(data):
            #data is a spmatrix in other format instead of coo
            self.data = data.tocoo()
        else:#data is numpy.matrix
            self.data = scipy.sparse.coo_matrix(data)

        self._sorted = None
        kwds['shape'] = self.data.shape
        kwds['pointNames'] = pointNames
        kwds['featureNames'] = featureNames
        super(Sparse, self).__init__(**kwds)


    def getdata(self):
        return self.data


    def _features_implementation(self):
        (points, cols) = scipy.shape(self.data)
        return cols

    def _points_implementation(self):
        (points, cols) = scipy.shape(self.data)
        return points


    def pointIterator(self):
        self._sortInternal('point')

        class pointIt(object):
            def __init__(self, outer):
                self._outer = outer
                self._nextID = 0
                self._stillSorted = True
                self._sortedPosition = 0

            def __iter__(self):
                return self

            def next(self):
                if self._nextID >= self._outer.points:
                    raise StopIteration
                if self._outer._sorted != "point" or not self._stillSorted:
                #					print "actually called"
                    self._stillSorted = False
                    value = self._outer.pointView(self._nextID)
                else:
                    end = self._sortedPosition
                    #this ensures end is always in range, and always exclusive
                    while (end < len(self._outer.data.data) and self._outer.data.row[end] == self._nextID):
                        end += 1
                    value = self._outer.pointView(self._nextID)
                    self._sortedPosition = end
                self._nextID += 1
                return value

            def __next__(self):
                return self.next()

        return pointIt(self)


    def featureIterator(self):
        self._sortInternal('feature')

        class featureIt():
            def __init__(self, outer):
                self._outer = outer
                self._nextID = 0
                self._stillSorted = True
                self._stilled = True
                self._sortedPosition = 0

            def __iter__(self):
                return self

            def next(self):
                if self._nextID >= self._outer.features:
                    raise StopIteration
                if self._outer._sorted != "feature" or not self._stillSorted:
                #					print "actually called"
                    self._stillSorted = False
                    value = self._outer.featureView(self._nextID)
                else:
                    end = self._sortedPosition
                    #this ensures end is always in range, and always exclusive
                    while (end < len(self._outer.data.data) and self._outer.data.col[end] == self._nextID):
                        end += 1
                    value = self._outer.featureView(self._nextID)
                    self._sortedPosition = end
                self._nextID += 1
                return value

            def __next__(self):
                return self.next()

        return featureIt(self)

    def plot(self, outPath=None, includeColorbar=False):
        toPlot = self.copyAs("Matrix")
        toPlot.plot(outPath, includeColorbar)

    def _plot(self, outPath=None, includeColorbar=False):
        toPlot = self.copyAs("Matrix")
        return toPlot._plot(outPath, includeColorbar)

    def _addPoints_implementation(self, toAdd, insertBefore):
        """
        Insert the points from the toAdd object below the provided index in
        this object, the remaining points from this object will continue below
        the inserted points

        """
        self._sortInternal('point')
        newData = []
        newRow = []
        newCol = []
        # add original data until insert location
        for i, row in enumerate(self.data.row):
            if row < insertBefore:
                newRow.append(row)
                newCol.append(self.data.col[i])
                newData.append(self.data.data[i])
            else:
                break
        splitLength = len(newRow)
        # add inserted data with adjusted row
        for i, row in enumerate(toAdd.data.row):
            newRow.append(row + insertBefore)
            newCol.append(toAdd.data.col[i])
            newData.append(toAdd.data.data[i])
        # add remaining original data with adjusted row
        for i, row in enumerate(self.data.row[splitLength:]):
            newRow.append(row + toAdd.points)
            newCol.append(self.data.col[splitLength:][i])
            newData.append(self.data.data[splitLength:][i])
        # handle conflicts between original dtype and inserted data
        try:
            newData = numpy.array(newData, dtype=self.data.dtype)
        except ValueError:
            newData = numpy.array(newData, dtype=numpy.object_)
        numNewRows = self.points + toAdd.points
        self.data = coo_matrix((newData, (newRow, newCol)), shape=(numNewRows, self.features))
        self._sorted = None


    def _addFeatures_implementation(self, toAdd, insertBefore):
        """
        Insert the features from the toAdd object to the right of the
        provided index in this object, the remaining points from this object
        will continue to the right of the inserted points

        """
        self._sortInternal('feature')
        newData = []
        newRow = []
        newCol = []
        # add original data until insert location
        for i, col in enumerate(self.data.col):
            if col < insertBefore:
                newRow.append(self.data.row[i])
                newCol.append(col)
                newData.append(self.data.data[i])
            else:
                break
        # add inserted data with adjusted col
        splitLength = len(newCol)
        for i, col in enumerate(toAdd.data.col):
            newRow.append(toAdd.data.row[i])
            newCol.append(col + insertBefore)
            newData.append(toAdd.data.data[i])
        # add remaining original data with adjusted col
        for i, col in enumerate(self.data.col[splitLength:]):
            newRow.append(self.data.row[splitLength:][i])
            newCol.append(col + toAdd.features)
            newData.append(self.data.data[splitLength:][i])
        # handle conflicts between original dtype and inserted data
        try:
            newData = numpy.array(newData, dtype=self.data.dtype)
        except ValueError:
            newData = numpy.array(newData, dtype=numpy.object_)

        numNewCols = self.features + toAdd.features
        self.data = coo_matrix((newData, (newRow, newCol)), shape=(self.points, numNewCols))
        self._sorted = None


    def _sortPoints_implementation(self, sortBy, sortHelper):
        indices = self._sort_general_implementation(sortBy, sortHelper, 'point')
        self._sorted = None
        return indices


    def _sortFeatures_implementation(self, sortBy, sortHelper):
        indices = self._sort_general_implementation(sortBy, sortHelper, 'feature')
        self._sorted = None
        return indices


    def _sort_general_implementation(self, sortBy, sortHelper, axisType):
        scorer = None
        comparator = None
        if axisType == 'point':
            viewMaker = self.pointView
            getViewIter = self.pointIterator
            targetAxis = self.data.row
            indexGetter = self.getPointIndex
            nameGetter = self.getPointName
            nameGetterStr = 'getPointName'
            names = self.getPointNames()
        else:
            viewMaker = self.featureView
            targetAxis = self.data.col
            getViewIter = self.featureIterator
            indexGetter = self.getFeatureIndex
            nameGetter = self.getFeatureName
            nameGetterStr = 'getFeatureName'
            names = self.getFeatureNames()

        if isinstance(sortHelper, list):
            sortedData = []
            idxDict = {val: idx for idx, val in enumerate(sortHelper)}
            if axisType == 'point':
                sortedData = [idxDict[val] for val in self.data.row]
                self.data.row = numpy.array(sortedData)
            else:
                sortedData = [idxDict[val] for val in self.data.col]
                self.data.col = numpy.array(sortedData)
            newNameOrder = [names[idx] for idx in sortHelper]
            return newNameOrder

        test = viewMaker(0)
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
            viewIter = getViewIter()
            for v in viewIter:
                viewArray.append(v)

            viewArray.sort(key=cmp_to_key(comparator))
            indexPosition = []
            for i in range(len(viewArray)):
                index = indexGetter(getattr(viewArray[i], nameGetterStr)(0))
                indexPosition.append(index)
            indexPosition = numpy.array(indexPosition)
        elif hasattr(scorer, 'permuter'):
            scoreArray = scorer.indices
            indexPosition = numpy.argsort(scoreArray)
        else:
            # make array of views
            viewArray = []
            viewIter = getViewIter()
            for v in viewIter:
                viewArray.append(v)

            scoreArray = viewArray
            if scorer is not None:
                # use scoring function to turn views into values
                for i in range(len(viewArray)):
                    scoreArray[i] = scorer(viewArray[i])
            else:
                for i in range(len(viewArray)):
                    scoreArray[i] = viewArray[i][sortBy]

            # use numpy.argsort to make desired index array
            # this results in an array whose ith entry contains the the
            # index into the data of the value that should be in the ith
            # position.
            indexPosition = numpy.argsort(scoreArray)

        # since we want to access with with positions in the original
        # data, we reverse the 'map'
        reverseIndexPosition = numpy.empty(indexPosition.shape[0])
        for i in range(indexPosition.shape[0]):
            reverseIndexPosition[indexPosition[i]] = i

        if axisType == 'point':
            self.data.row[:] = reverseIndexPosition[self.data.row]
        else:
            self.data.col[:] = reverseIndexPosition[self.data.col]

        # we need to return an array of the feature names in their new order.
        # we convert the indices of the their previous location into their names
        newNameOrder = []
        for i in range(len(indexPosition)):
            oldIndex = indexPosition[i]
            newName = nameGetter(oldIndex)
            newNameOrder.append(newName)
        return newNameOrder


    def _structuralBackend_implementation(self, structure, axis, targetList):
        """
        Backend for extractPoints/Features, deletePoints/Features, retainPoints/Features, and
        copyPoints/Features. Returns a new object containing only the points in targetList and
        performs some modifications to the original object if necessary. This function does not
        perform all of the modification or process how each function handles the returned value,
        these are managed separately by each frontend function.
        """
        if self.data.data is not None and self.data.data.dtype != 'O':
            return self._structuralVectorized_implementation(structure, axis, targetList)
        else:
            # object dtype or SparseView
            return self._structuralIterative_implementation(structure, axis, targetList)


    def _structuralVectorized_implementation(self, structure, axis, targetList):
        """
        Make use of scipy csr or csc matrices for indexing targeted values

        """
        axisNames = []
        if axis == 'point':
            getAxisName = self.getPointName
            getOtherNames = self.getFeatureNames
            data = self.data.tocsr()
            targeted = data[targetList, :]
            if structure != 'copy':
                notTarget = [idx for idx in range(self.points) if idx not in targetList]
                notTargeted = data[notTarget, :]
        else:
            getAxisName = self.getFeatureName
            getOtherNames = self.getPointNames
            data = self.data.tocsc()
            targeted = data[:, targetList]
            if structure != 'copy':
                notTarget = [idx for idx in range(self.features) if idx not in targetList]
                notTargeted = data[:, notTarget]

        self._validateAxis(axis)

        for index in targetList:
            axisNames.append(getAxisName(index))
        otherNames = getOtherNames()

        if structure != 'copy':
            self.data = notTargeted.tocoo()
            self._sortInternal(axis)

        ret = targeted.tocoo()

        if axis == 'point':
            return Sparse(ret, pointNames=axisNames, featureNames=otherNames, reuseData=True)
        else:
            return Sparse(ret, pointNames=otherNames, featureNames=axisNames, reuseData=True)


    def _structuralIterative_implementation(self, structure, axis, targetList):
        """
        Iterate through each point in the object to index targeted values

        """
        dtype = numpy.object_
        if axis == 'point':
            viewIterator = self.pointIterator
            targetCount = self.points
        else:
            viewIterator = self.featureIterator
            targetCount = self.features

        targetLength = len(targetList)
        targetData = []
        targetRows = []
        targetCols = []
        keepData = []
        keepRows = []
        keepCols = []
        keepIndex = 0

        # iterate through axis data
        for targetID, view in enumerate(viewIterator()):
            # coo_matrix data for return object
            if targetID in targetList:
                for otherID, value in enumerate(view.data.data):
                    targetData.append(value)
                    if axis == 'point':
                        targetRows.append(targetList.index(targetID))
                        targetCols.append(view.data.col[otherID])
                    else:
                        targetRows.append(view.data.row[otherID])
                        targetCols.append(targetList.index(targetID))
            # coo_matrix data for modified self
            elif structure != 'copy':
                for otherID, value in enumerate(view.data.data):
                    keepData.append(value)
                    if axis == 'point':
                        keepRows.append(keepIndex)
                        keepCols.append(view.data.col[otherID])
                    else:
                        keepRows.append(view.data.row[otherID])
                        keepCols.append(keepIndex)
                keepIndex += 1

        # instantiate return data
        (selfShape, targetShape) = _calcShapes(self.data.shape, targetLength, axis)
        if structure != 'copy':
            otherData = numpy.array(keepData, dtype=dtype)
            self.data = coo_matrix((otherData, (keepRows, keepCols)), shape=selfShape)
        # coo_matrix will force list to simplest numpy dtype unless converted to an array
        targetData = numpy.array(targetData, dtype=dtype)
        ret = coo_matrix((targetData, (targetRows, targetCols)), shape=targetShape)

        # get names for return obj
        pnames = []
        fnames = []
        if axis == 'point':
            for index in targetList:
                pnames.append(self.getPointName(index))
            fnames = self.getFeatureNames()
        else:
            pnames = self.getPointNames()
            for index in targetList:
                fnames.append(self.getFeatureName(index))

        return Sparse(ret, pointNames=pnames, featureNames=fnames, reuseData=True)


    def _transpose_implementation(self):
        self.data = self.data.transpose()
        self._sorted = None
        #_resync(self.data)

    #		if self._sorted == 'point':
    #			self._sorted = 'feature'
    #		elif self._sorted == 'feature':
    #			self._sorted = 'point'


    def _mapReducePoints_implementation(self, mapper, reducer):
        self._sortInternal("point")
        mapperResults = {}
        maxVal = self.features

        # consume zeroed vectors, up to the first nonzero value
        if self.data.data[0] != 0:
            for i in range(0, self.data.row[0]):
                currResults = mapper(self.pointView(i))
                for (k, v) in currResults:
                    if not k in mapperResults:
                        mapperResults[k] = []
                    mapperResults[k].append(v)

        vectorStartIndex = 0
        #walk through each coordinate entry
        for i in range(len(self.data.data)):
            #collect values into points
            targetValue = self.data.row[i]
            #if this is the end of a point
            if i == len(self.data.data) - 1 or self.data.row[i + 1] != targetValue:
                #evaluate whether curr point is to be extracted or not
                # and perform the appropriate copies
                currResults = mapper(self.pointView(targetValue))
                for (k, v) in currResults:
                    if not k in mapperResults:
                        mapperResults[k] = []
                    mapperResults[k].append(v)

                # process zeroed vectors up to the ID of the new vector
                if i < len(self.data.data) - 1:
                    nextValue = self.data.row[i + 1]
                else:
                    nextValue = self.points
                for j in range(targetValue + 1, nextValue):
                    currResults = mapper(self.pointView(j))
                    for (k, v) in currResults:
                        if not k in mapperResults:
                            mapperResults[k] = []
                        mapperResults[k].append(v)

                #reset the vector starting index
                vectorStartIndex = i + 1

        # apply the reducer to the list of values associated with each key
        ret = []
        for mapKey in mapperResults.keys():
            mapValues = mapperResults[mapKey]
            # the reducer will return a tuple of a key to a value
            redRet = reducer(mapKey, mapValues)
            if redRet is not None:
                (redKey, redValue) = redRet
                ret.append([redKey, redValue])
        return Sparse(numpy.matrix(ret))

    def _isIdentical_implementation(self, other):
        if not isinstance(other, Sparse):
            return False
        # for nonempty matrices, we use a shape mismatch to indicate non-equality
        if self.data.shape != other.data.shape:
            return False

        if isinstance(other, SparseView):
            return other._isIdentical_implementation(self)
        else:
            #let's do internal sort first then compare
            tmpLeft = self.copy()
            tmpRight = other.copy()
            tmpLeft._sortInternal('feature')
            tmpRight._sortInternal('feature')

            return (allDataIdentical(tmpLeft.data.data, tmpRight.data.data) and
                    allDataIdentical(tmpLeft.data.row, tmpRight.data.row) and
                    allDataIdentical(tmpLeft.data.col, tmpRight.data.col))

    def _getTypeString_implementation(self):
        return 'Sparse'

    def _writeFileCSV_implementation(self, outPath, includePointNames, includeFeatureNames):
        """
        Function to write the data in this object to a CSV file at the designated
        path.

        """
        outFile = open(outPath, 'w')

        if includeFeatureNames:
            def combine(a, b):
                return a + ',' + b

            fnames = self.getFeatureNames()
            fnamesLine = reduce(combine, fnames)
            fnamesLine += '\n'
            if includePointNames:
                outFile.write('point_names,')

            outFile.write(fnamesLine)

        # sort by rows first, then columns
        placement = numpy.lexsort((self.data.col, self.data.row))
        self.data.data[placement]
        self.data.row[placement]
        self.data.col[placement]

        pointer = 0
        pmax = len(self.data.data)
        for i in range(self.points):
            currPname = self.getPointName(i)
            if includePointNames:
                outFile.write(currPname)
                outFile.write(',')
            for j in range(self.features):
                if pointer < pmax and i == self.data.row[pointer] and j == self.data.col[pointer]:
                    value = self.data.data[pointer]
                    pointer = pointer + 1
                else:
                    value = 0

                if j != 0:
                    outFile.write(',')
                outFile.write(str(value))
            outFile.write('\n')

        outFile.close()

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

    def _writeFileMTX_implementation(self, outPath, includePointNames, includeFeatureNames):
        def makeNameString(count, namesItoN):
            nameString = "#"
            for i in range(count):
                nameString += namesItoN[i]
                if not i == count - 1:
                    nameString += ','
            return nameString

        header = ''
        if includePointNames:
            header = makeNameString(self.points, self.getPointNames())
            header += '\n'
        else:
            header += '#\n'
        if includeFeatureNames:
            header += makeNameString(self.features, self.getFeatureNames())
            header += '\n'
        else:
            header += '#\n'

        if header != '':
            mmwrite(target=outPath, a=self.data, comment=header)
        else:
            mmwrite(target=outPath, a=self.data)


    def _referenceDataFrom_implementation(self, other):
        if not isinstance(other, Sparse):
            raise ArgumentException("Other must be the same type as this object")

        self.data = other.data
        self._sorted = other._sorted

    def _copyAs_implementation(self, format):

        if format is None or format == 'Sparse':
            ret = UML.createData('Sparse', self.data)
            # Due to duplicate removal done in createData, we cannot guarantee that the internal
            # sorting is preserved in the returned object.
            return ret
        if format == 'List':
            return UML.createData('List', self.data)
        if format == 'Matrix':
            return UML.createData('Matrix', self.data)
        if format == 'DataFrame':
            return UML.createData('DataFrame', self.data)
        if format == 'pythonlist':
            return self.data.todense().tolist()
        if format == 'numpyarray':
            return numpy.array(self.data.todense())
        if format == 'numpymatrix':
            return self.data.todense()
        if format == 'scipycsc':
            return self.data.tocsc()
        if format == 'scipycsr':
            return self.data.tocsr()


    def _calculateForEachElement_implementation(self, function, points, features,
                                                preserveZeros, outputType):
        if not isinstance(self, BaseView):
            data = self.data.data
            row = self.data.row
            col = self.data.col
        else:
            # initiate generic implementation for view types
            preserveZeros = False
        # all data
        if preserveZeros and points is None and features is None:
            try:
                data = function(data)
            except Exception:
                function.otypes = [numpy.object_]
                data = function(data)
            values = coo_matrix((data, (row, col)), shape=self.data.shape)
            # note: even if function transforms nonzero values into zeros
            # our init methods will filter them out from the data attribute
            return UML.createData(outputType, values)
        # subset of data
        if preserveZeros:
            dataSubset = []
            rowSubset = []
            colSubset = []
            for idx in range(len(data)):
                if row[idx] in points and col[idx] in features:
                    rowSubset.append(row[idx])
                    colSubset.append(col[idx])
                    dataSubset.append(data[idx])
            dataSubset = function(dataSubset)
            values = coo_matrix((dataSubset, (rowSubset, colSubset)))
            # note: even if function transforms nonzero values into zeros
            # our init methods will filter them out from the data attribute
            return UML.createData(outputType, values)
        # zeros not preserved
        return self._calculateForEachElementGenericVectorized(
               function, points, features, outputType)


    def _transformEachPoint_implementation(self, function, points):
        self._transformEach_implementation(function, points, 'point')


    def _transformEachFeature_implementation(self, function, features):
        self._transformEach_implementation(function, features, 'feature')


    def _transformEach_implementation(self, function, included, axis):
        modData = []
        modRow = []
        modCol = []

        if axis == 'point':
            viewIterator = self.pointIterator()
            modTarget = modRow
            modOther = modCol
        else:
            viewIterator = self.featureIterator()
            modTarget = modCol
            modOther = modRow

        for viewID, view in enumerate(viewIterator):
            if included is not None and viewID not in included:
                currOut = list(view)
            else:
                currOut = function(view)

            # easy way to reuse code if we have a singular return
            if not hasattr(currOut, '__iter__'):
                currOut = [currOut]

            # if there are multiple values, they must be random accessible
            if not hasattr(currOut, '__getitem__'):
                raise ArgumentException("function must return random accessible data (ie has a __getitem__ attribute)")

            for i, retVal in enumerate(currOut):
                if retVal != 0:
                    modData.append(retVal)
                    modTarget.append(viewID)
                    modOther.append(i)

        if len(modData) != 0:
            self.data = coo_matrix((modData, (modRow, modCol)), shape=(self.points, self.features))
            self._sorted = None

        ret = None
        return ret


    def _transformEachElement_implementation(self, toTransform, points, features, preserveZeros, skipNoneReturnValues):
        oneArg = False
        try:
            toTransform(0, 0, 0)
        except TypeError:
            if isinstance(toTransform, dict):
                oneArg = None
            else:
                oneArg = True

        if oneArg and toTransform(0) == 0:
            preserveZeros = True

        if preserveZeros:
            self._transformEachElement_zeroPreserve_implementation(toTransform, points, features, skipNoneReturnValues,
                                                                   oneArg)
        else:
            self._transformEachElement_noPreserve_implementation(toTransform, points, features, skipNoneReturnValues,
                                                                 oneArg)

    def _transformEachElement_noPreserve_implementation(self, toTransform, points, features, skipNoneReturnValues, oneArg):
        # returns None if outside of the specified points and feature so that
        # when calculateForEach is called we are given a full data object
        # with only certain values modified.
        def wrapper(value, pID, fID):
            if points is not None and pID not in points:
                return None
            if features is not None and fID not in features:
                return None

            if oneArg is None:
                if value in toTransform.keys():
                    return toTransform[value]
                else:
                    return None
            elif oneArg:
                return toTransform(value)
            else:
                return toTransform(value, pID, fID)

        # perserveZeros is always False in this helper, skipNoneReturnValues
        # is being hijacked by the wrapper: even if it was False, Sparse can't
        # contain None values.
        ret = self.calculateForEachElement(wrapper, None, None, preserveZeros=False, skipNoneReturnValues=True)

        pnames = self.getPointNames()
        fnames = self.getFeatureNames()
        self.referenceDataFrom(ret)
        self.setPointNames(pnames)
        self.setFeatureNames(fnames)


    def _transformEachElement_zeroPreserve_implementation(self, toTransform, points, features, skipNoneReturnValues,
                                                          oneArg):
        for index, val in enumerate(self.data.data):
            pID = self.data.row[index]
            fID = self.data.col[index]
            if points is not None and pID not in points:
                continue
            if features is not None and fID not in features:
                continue

            if oneArg is None:
                if val in toTransform.keys():
                    currRet = toTransform[val]
                else:
                    continue
            elif oneArg:
                currRet = toTransform(val)
            else:
                currRet = toTransform(val, pID, fID)

            if skipNoneReturnValues and currRet is None:
                continue

            self.data.data[index] = currRet


    def _fillWith_implementation(self, values, pointStart, featureStart, pointEnd, featureEnd):
        # sort values or call helper as needed
        constant = not isinstance(values, UML.data.Base)
        if constant:
            if values == 0:
                self._fillWith_zeros_implementation(pointStart, featureStart, pointEnd, featureEnd)
                return
        else:
            values._sortInternal('point')

        # this has to be after the possible call to _fillWith_zeros_implementation;
        # it is uncessary for that helper
        self._sortInternal('point')

        self_i = 0
        vals_i = 0
        copyIndex = 0
        toAddData = []
        toAddRow = []
        toAddCol = []
        selfEnd = numpy.searchsorted(self.data.row, pointEnd, 'right')
        if constant:
            valsEnd = (pointEnd - pointStart + 1) * (featureEnd - featureStart + 1)
        else:
            valsEnd = len(values.data.data)

        # Adjust self_i so that it begins at the values that might need to be
        # replaced, or, if no such values exist, set self_i such that the main loop
        # will ignore the contents of self.
        if len(self.data.data) > 0:
            self_i = numpy.searchsorted(self.data.row, pointStart, 'left')

            pcheck = self.data.row[self_i]
            fcheck = self.data.col[self_i]
            # the condition in the while loop is a natural break, if it isn't
            # satisfied then self_i will be exactly where we want it
            while fcheck < featureStart or fcheck > featureEnd:
                # this condition is an unatural break, when it is satisfied,
                # that means no value of self_i will point into the desired
                # values
                if pcheck > pointEnd or self_i == len(self.data.data) - 1:
                    self_i = selfEnd
                    break

                self_i += 1
                pcheck = self.data.row[self_i]
                fcheck = self.data.col[self_i]

            copyIndex = self_i

        # Walk full contents of both, modifying, shifing, or setting aside values as needed.
        # We will only ever increment one of self_i or vals_i at a time, meaning if there are
        # matching entries, we will encounter them. Due to the sorted precondition, if
        # the location in one object is less than the location in the other object, the
        # lower one CANNOT have a match.
        while self_i < selfEnd or vals_i < valsEnd:
            if self_i < selfEnd:
                locationSP = self.data.row[self_i]
                locationSF = self.data.col[self_i]
            else:
                # we want to use unreachable values as sentials, so we + 1 since we're
                # using inclusive endpoints
                locationSP = pointEnd + 1
                locationSF = featureEnd + 1

            # we adjust the 'values' locations into the scale of the calling object
            locationVP = pointStart
            locationVF = featureStart
            if constant:
                vData = values
                locationVP += vals_i / (featureEnd - featureStart + 1)# uses truncation of int division
                locationVF += vals_i % (featureEnd - featureStart + 1)
            elif vals_i >= valsEnd:
                locationVP += pointEnd + 1
                locationVF += featureEnd + 1
            else:
                vData = values.data.data[vals_i]
                locationVP += values.data.row[vals_i]
                locationVF += values.data.col[vals_i]

            pCmp = locationSP - locationVP
            fCmp = locationSF - locationVF
            trueCmp = pCmp if pCmp != 0 else fCmp

            # Case: location at index into self is higher than location at index into values.
            # No matching entry in self; copy if space, or record to be added at end.
            if trueCmp > 0:
                # can only copy into self if there is open space
                if copyIndex < self_i:
                    self.data.data[copyIndex] = vData
                    self.data.row[copyIndex] = locationVP
                    self.data.col[copyIndex] = locationVF
                    copyIndex += 1
                else:
                    toAddData.append(vData)
                    toAddRow.append(locationVP)
                    toAddCol.append(locationVF)

                #increment vals_i
                vals_i += 1
            # Case: location at index into other is higher than location at index into self.
            # no matching entry in values - fill this entry in self with zero
            # (by shifting past it)
            elif trueCmp < 0:
                # need to do cleanup if we're outside of the relevant bounds
                if locationSF < featureStart or locationSF > featureEnd:
                    self.data.data[copyIndex] = self.data.data[self_i]
                    self.data.row[copyIndex] = self.data.row[self_i]
                    self.data.col[copyIndex] = self.data.col[self_i]
                    copyIndex += 1
                self_i += 1
            # Case: indices point to equal locations.
            else:
                self.data.data[copyIndex] = vData
                self.data.row[copyIndex] = locationVP
                self.data.col[copyIndex] = locationVF
                copyIndex += 1

                # increment both??? or just one?
                self_i += 1
                vals_i += 1

        # Now we have to walk through the rest of self, finishing the copying shift
        # if necessary
        if copyIndex != self_i:
            while self_i < len(self.data.data):
                self.data.data[copyIndex] = self.data.data[self_i]
                self.data.row[copyIndex] = self.data.row[self_i]
                self.data.col[copyIndex] = self.data.col[self_i]
                self_i += 1
                copyIndex += 1
        else:
            copyIndex = len(self.data.data)

        newData = numpy.empty(copyIndex + len(toAddData), dtype=self.data.data.dtype)
        newData[:copyIndex] = self.data.data[:copyIndex]
        newData[copyIndex:] = toAddData
        newRow = numpy.empty(copyIndex + len(toAddRow))
        newRow[:copyIndex] = self.data.row[:copyIndex]
        newRow[copyIndex:] = toAddRow
        newCol = numpy.empty(copyIndex + len(toAddCol))
        newCol[:copyIndex] = self.data.col[:copyIndex]
        newCol[copyIndex:] = toAddCol
        self.data = scipy.sparse.coo_matrix((newData, (newRow, newCol)), (self.points, self.features))

        if len(toAddData) != 0:
            self._sorted = None


    def _flattenToOnePoint_implementation(self):
        self._sortInternal('point')
        pLen = self.features
        numElem = self.points * self.features
        for i in range(len(self.data.data)):
            if self.data.row[i] > 0:
                self.data.col[i] += (self.data.row[i] * pLen)
                self.data.row[i] = 0

        self.data = coo_matrix((self.data.data, (self.data.row, self.data.col)), (1, numElem))

    def _flattenToOneFeature_implementation(self):
        self._sortInternal('feature')
        fLen = self.points
        numElem = self.points * self.features
        for i in range(len(self.data.data)):
            if self.data.col[i] > 0:
                self.data.row[i] += (self.data.col[i] * fLen)
                self.data.col[i] = 0

        self.data = coo_matrix((self.data.data, (self.data.row, self.data.col)), (numElem, 1))


    def _unflattenFromOnePoint_implementation(self, numPoints):
        # only one feature, so both sorts are the same order
        if self._sorted is None:
            self._sortInternal('point')

        numFeatures = self.features // numPoints
        newShape = (numPoints, numFeatures)

        for i in range(len(self.data.data)):
            # must change the row entry before modifying the col entry
            self.data.row[i] = self.data.col[i] / numFeatures
            self.data.col[i] = self.data.col[i] % numFeatures

        self.data = coo_matrix((self.data.data, (self.data.row, self.data.col)), newShape)
        self._sorted = 'point'

    def _unflattenFromOneFeature_implementation(self, numFeatures):
        # only one feature, so both sorts are the same order
        if self._sorted is None:
            self._sortInternal('feature')

        numPoints = self.points // numFeatures
        newShape = (numPoints, numFeatures)

        for i in range(len(self.data.data)):
            # must change the col entry before modifying the row entry
            self.data.col[i] = self.data.row[i] / numPoints
            self.data.row[i] = self.data.row[i] % numPoints

        self.data = coo_matrix((self.data.data, (self.data.row, self.data.col)), newShape)
        self._sorted = 'feature'

    def _mergeIntoNewData(self, copyIndex, toAddData, toAddRow, toAddCol):
        #instead of always copying, use reshape or resize to sometimes cut array down
        # to size???
        pass

    def _fillWith_zeros_implementation(self, pointStart, featureStart, pointEnd, featureEnd):
        #walk through col listing and partition all data: extract, and kept, reusing the sparse matrix
        # underlying structure to save space
        copyIndex = 0

        for lookIndex in range(len(self.data.data)):
            currP = self.data.row[lookIndex]
            currF = self.data.col[lookIndex]
            # if it is in range we want to obliterate the entry by just passing it by
            # and copying over it later
            if currP >= pointStart and currP <= pointEnd and currF >= featureStart and currF <= featureEnd:
                pass
            else:
                self.data.data[copyIndex] = self.data.data[lookIndex]
                self.data.row[copyIndex] = self.data.row[lookIndex]
                self.data.col[copyIndex] = self.data.col[lookIndex]
                copyIndex += 1

        # reinstantiate self
        # (cannot reshape coo matrices, so cannot do this in place)
        newData = (self.data.data[0:copyIndex], (self.data.row[0:copyIndex], self.data.col[0:copyIndex]))
        self.data = scipy.sparse.coo_matrix(newData, (self.points, self.features))

    def _handleMissingValues_implementation(self, method='remove points', featuresList=None, arguments=None, alsoTreatAsMissing=[], markMissing=False):
        """
        This function is to
        1. drop points or features with missing values
        2. fill missing values with mean, median, mode, or zero or a constant value
        3. fill missing values by forward or backward filling
        4. imput missing values via linear interpolation

        Detailed steps are:
        1. from alsoTreatAsMissing, generate a Set for elements which are not None nor NaN but should be considered as missing
        2. from featuresList, generate 2 dicts missingIdxDictFeature and missingIdxDictPoint to store locations of missing values
        3. replace missing values in features in the featuresList with NaN
        4. based on method and arguments, process self.data
        5. update points and features information.
        """
        def featureMeanMedianMode(func):
            featureMean = self.calculateForEachFeature(func, features=featuresList)
            for tmpItem in missingIdxDictFeature.items():
                j = tmpItem[0]
                for i in tmpItem[1]:
                    self.fillWith(featureMean[0, j], i, j, i, j)

        alsoTreatAsMissingSet = set(alsoTreatAsMissing)
        missingIdxDictFeature = {i: [] for i in featuresList}
        missingIdxDictPoint = {i: [] for i in range(self.points)}
        for i in range(self.points):
            for j in featuresList:
                tmpV = self[i, j]
                if tmpV in alsoTreatAsMissingSet or (tmpV != tmpV) or tmpV is None:
                    self.fillWith(numpy.NaN, i, j, i, j)
                    missingIdxDictPoint[i].append(j)
                    missingIdxDictFeature[j].append(i)
        #import pdb; pdb.set_trace()
        if markMissing:
            #add extra columns to indicate if the original value was missing or not
            extraFeatureNames = []
            extraDummy = []
            for tmpItem in missingIdxDictFeature.items():
                extraFeatureNames.append(self.getFeatureName(tmpItem[0]) + '_missing')
            for tmpItem in missingIdxDictPoint.items():
                extraDummy.append([True if i in tmpItem[1] else False for i in featuresList])

        #from now, based on method and arguments, process self.data
        if method == 'remove points':
            msg = 'for method = "remove points", the arguments can only be all( or None) or any.'
            if arguments is None or arguments.lower() == 'any':
                missingIdx = [i[0] for i in missingIdxDictPoint.items() if len(i[1]) > 0]
            elif arguments.lower() == 'all':
                missingIdx = [i[0] for i in missingIdxDictPoint.items() if len(i[1]) == self.features]
            else:
                raise ArgumentException(msg)
            nonmissingIdx = [i for i in range(self.points) if i not in missingIdx]
            if len(nonmissingIdx) == 0:
                msg = 'All data are removed. Please use another method or other arguments.'
                raise ArgumentException(msg)

            if len(missingIdx) > 0:
                self.extractPoints(toExtract=missingIdx)
                if markMissing:
                    extraDummy = [extraDummy[i] for i in nonmissingIdx]
        elif method == 'remove features':
            msg = 'for method = "remove features", the arguments can only be all( or None) or any.'
            if arguments is None or arguments.lower() == 'any':
                missingIdx = [i[0] for i in missingIdxDictFeature.items() if len(i[1]) > 0]
            elif arguments.lower() == 'all':
                missingIdx = [i[0] for i in missingIdxDictFeature.items() if len(i[1]) == self.points]
            else:
                raise ArgumentException(msg)
            nonmissingIdx = [i for i in range(self.features) if i not in missingIdx]
            if len(nonmissingIdx) == 0:
                msg = 'All data are removed. Please use another method or other arguments.'
                raise ArgumentException(msg)

            if len(missingIdx) > 0:
                self.extractFeatures(toExtract=missingIdx)
                if markMissing:
                    extraDummy = [[i[j] for j in nonmissingIdx] for i in extraDummy]
                    extraFeatureNames = [extraFeatureNames[i] for i in nonmissingIdx]
        elif method == 'feature mean':
            featureMeanMedianMode(UML.calculate.mean)
        elif method == 'feature median':
            featureMeanMedianMode(UML.calculate.median)
        elif method == 'feature mode':
            featureMeanMedianMode(UML.calculate.mode)
        elif method == 'zero':
            for tmpItem in missingIdxDictFeature.items():
                j = tmpItem[0]
                for i in tmpItem[1]:
                    self.fillWith(0, i, j, i, j)
        elif method == 'constant':
            msg = 'for method = "constant", the arguments must be the constant.'
            if arguments is not None:
                for tmpItem in missingIdxDictFeature.items():
                    j = tmpItem[0]
                    for i in tmpItem[1]:
                        self.fillWith(arguments, i, j, i, j)
            else:
                raise ArgumentException(msg)
        elif method == 'forward fill':
            for tmpItem in missingIdxDictFeature.items():
                    j = tmpItem[0]
                    for i in tmpItem[1]:
                        if i > 0:
                            self.fillWith(self[i-1, j], i, j, i, j)
        elif method == 'backward fill':
            for tmpItem in missingIdxDictFeature.items():
                    j = tmpItem[0]
                    for i in sorted(tmpItem[1], reverse=True):
                        if i < self.points - 1:
                            self.fillWith(self[i+1, j], i, j, i, j)
        elif method == 'interpolate':
            for tmpItem in missingIdxDictFeature.items():
                j = tmpItem[0]
                interpX = tmpItem[1]
                if len(interpX) == 0:
                    continue
                if arguments is None:
                    xp = [i for i in range(self.points) if i not in interpX]
                    fp = [self[i, j] for i in xp]
                    tmpArguments = {'x': interpX, 'xp': xp, 'fp': fp}
                elif isinstance(arguments, dict):
                    tmpArguments = arguments.copy()
                    tmpArguments['x'] = interpX
                else:
                    msg = 'for method = "interpolate", the arguments must be None or a dict.'
                    raise ArgumentException(msg)

                tmpV = numpy.interp(**tmpArguments)
                for k, i in enumerate(interpX):
                    self.fillWith(tmpV[k], i, j, i, j)

        if markMissing:
            toAppend = UML.createData('Sparse', extraDummy, featureNames=extraFeatureNames, pointNames=self.getPointNames())
            self._sorted = None#need to reset this, o.w. may fail in validate
            self.addFeatures(toAppend)

    def _binarySearch(self, x, y):
            if self._sorted == 'point':
                start, end = numpy.searchsorted(self.data.row, [x, x+1])#binary search
                if start == end:#x is not in self.data.row
                    return 0
                k = numpy.searchsorted(self.data.col[start:end], y) + start
                if k < end and self.data.col[k] == y:
                    return self.data.data[k]
                return 0
            elif self._sorted == 'feature':
                start, end = numpy.searchsorted(self.data.col, [y, y+1])#binary search
                if start == end:#x is not in self.data.col
                    return 0
                k = numpy.searchsorted(self.data.row[start:end], x) + start
                if k < end and self.data.row[k] == x:
                    return self.data.data[k]
                return 0
            else:
                raise ImproperActionException('self._sorted is not either point nor feature.')

    def _merge_implementation(self, other, point, feature, onFeature, matchingFtIdx):
        leftFtCount = self.features
        rightFtCount = other.features - len(matchingFtIdx[0])
        if onFeature:
            onIdxL = self.getFeatureIndex(onFeature)
            onIdxR = other.getFeatureIndex(onFeature)
            leftData = self.data.data
            leftRow = self.data.row
            leftCol = self.data.col
            rightData = other.data.data.copy()
            rightRow = other.data.row.copy()
            rightCol = other.data.col.copy()
        else:
            onIdxL = 0
            onIdxR = 0
            leftData = self.data.data.astype(numpy.object_)
            if not self._anyDefaultPointNames():
                leftData = numpy.append([self.getPointNames()], leftData)
            elif self._pointNamesCreated():
                # differentiate default names between objects; note still start with DEFAULT_PREFIX
                leftNames = [n + '_l' if n.startswith(DEFAULT_PREFIX) else n
                             for n in self.getPointNames()]
                leftData = numpy.append([leftNames], leftData)
            else:
                leftData = numpy.append([DEFAULT_PREFIX + str(i) for i in range(self.points)], leftData)
            leftRow = numpy.append([i for i in range(self.points)], self.data.row)
            leftCol = numpy.append([0 for i in range(self.points)], self.data.col + 1)
            rightData = other.data.data.copy().astype(numpy.object_)
            if not other._anyDefaultPointNames():
                rightData = numpy.append([other.getPointNames()], rightData)
            elif other._pointNamesCreated():
                # differentiate default names between objects; note still start with DEFAULT_PREFIX
                rightNames = [n + '_r' if n.startswith(DEFAULT_PREFIX) else n
                             for n in other.getPointNames()]
                rightData = numpy.append([rightNames], rightData)
            else:
                rightData = numpy.append([DEFAULT_PREFIX + str(i) for i in range(self.points, self.points + other.points)], rightData)

            rightRow = numpy.append([i for i in range(other.points)], other.data.row.copy())
            rightCol = numpy.append([0 for i in range(other.points)], other.data.col.copy() + 1)
            matchingFtIdx[0] = list(map(lambda x: x + 1, matchingFtIdx[0]))
            matchingFtIdx[0].insert(0, 0)
            matchingFtIdx[1] = list(map(lambda x: x + 1, matchingFtIdx[1]))
            matchingFtIdx[1].insert(0, 0)

        mergedData = numpy.empty((0,0), dtype=numpy.object_)
        mergedRow = []
        mergedCol = []
        matched = []
        nextPt = 0
        numPts = 0

        for ptIdxL, target in enumerate(leftData[leftCol == onIdxL]):
            rowIdxR = numpy.where(rightData[rightCol == onIdxR] == target)[0]
            if len(rowIdxR) > 0:
                for ptIdxR in rowIdxR:
                    ptL = leftData[leftRow == ptIdxL]
                    ptR = rightData[rightRow == ptIdxR]
                    matches = ptL[matchingFtIdx[0]] == ptR[matchingFtIdx[1]]
                    nansL = ptL[matchingFtIdx[0]] != ptL[matchingFtIdx[0]]
                    nansR = ptR[matchingFtIdx[1]] != ptR[matchingFtIdx[1]]
                    acceptableValues = matches + nansL + nansR
                    if not all(acceptableValues):
                        msg = "The objects contain different values for the same feature"
                        raise ArgumentException(msg)
                    if len(nansL) > 0:
                        # fill any nan values in left with the corresponding right value
                        for i, value in enumerate(ptL[matchingFtIdx[0]]):
                            if value != value:
                                ptL[matchingFtIdx[0]][i] = ptR[matchingFtIdx[1]][i]
                    ptR = ptR[[i for i in range(len(ptR)) if i not in matchingFtIdx[1]]]
                    pt = numpy.append(ptL, ptR)
                    if feature == "intersection":
                        pt = pt[matchingFtIdx[0]]
                        leftFtCount = len(matchingFtIdx[0])
                    elif onFeature and feature == "left":
                        pt = pt[:self.features]
                    elif feature == "left":
                        pt = pt[:self.features + 1]
                    if onFeature is None:
                        pt = pt[1:]
                    matched.append(target)
                    mergedData = numpy.append(mergedData, pt)
                    mergedRow.extend([nextPt] * len(pt))
                    mergedCol.extend([i for i in range(len(pt))])
                    nextPt += 1
                    numPts += 1
            elif point == "union" or point == "left":
                ptL = leftData[leftRow == ptIdxL]
                if onFeature:
                    ptR = [numpy.nan] * (other.features - len(matchingFtIdx[1]))
                else:
                    ptR = [numpy.nan] * (other.features - len(matchingFtIdx[1]) + 1)
                pt = numpy.append(ptL, ptR)
                if feature == "intersection":
                    pt = pt[matchingFtIdx[0]]
                elif onFeature and feature == "left":
                    pt = pt[:self.features]
                elif feature == "left":
                    pt = pt[:self.features + 1]
                if onFeature is None:
                    pt = pt[1:]
                mergedData = numpy.append(mergedData, pt)
                mergedRow.extend([nextPt] * len(pt))
                mergedCol.extend([i for i in range(len(pt))])
                nextPt += 1
                numPts += 1

        if point == 'union':
            for ptIdxR, target in enumerate(rightData[rightCol == onIdxR]):
                if target not in matched:
                    if onFeature:
                        ptL = numpy.array([numpy.nan] * self.features, dtype=numpy.object_)
                    else:
                        ptL = numpy.array([numpy.nan] * (self.features + 1), dtype=numpy.object_)
                    ptL[matchingFtIdx[0]] = rightData[(rightRow == ptIdxR)][matchingFtIdx[1]]
                    # only unmatched points from right
                    ptR = rightData[(rightRow == ptIdxR) & (numpy.in1d(rightCol, matchingFtIdx[1], invert=True))]
                    pt = numpy.append(ptL, ptR)
                    if feature == "intersection":
                        pt = pt[matchingFtIdx[0]]
                    elif onFeature and feature == "left":
                        pt = pt[:self.features]
                    elif feature == "left":
                        pt = pt[:self.features + 1]
                    if onFeature is None:
                        # remove pointNames column added
                        pt = pt[1:]
                    mergedData = numpy.append(mergedData, pt)
                    mergedRow.extend([nextPt] * len(pt))
                    mergedCol.extend([i for i in range(len(pt))])
                    nextPt += 1
                    numPts += 1

        numFts = leftFtCount + rightFtCount
        if onFeature and feature == "intersection":
            numFts = len(matchingFtIdx[0])
        elif feature == "intersection":
            numFts = len(matchingFtIdx[0]) - 1
        elif feature == "left":
            numFts = self.features
        if len(mergedData) == 0:
            mergedData = []

        self._featureCount = numFts
        self._pointCount = numPts

        self.data = coo_matrix((mergedData, (mergedRow, mergedCol)), shape=(numPts, numFts))

    def _getitem_implementation(self, x, y):
        """
        currently, we sort the data first and then do binary search
        """

        if self._sorted is None:
            self._sortInternal('point')
            self._sorted = 'point'

        return self._binarySearch(x, y)

    def _view_implementation(self, pointStart, pointEnd, featureStart, featureEnd):
        """
        The Sparse object specific implementation necessarly to complete the Base
        object's view method. pointStart and feature start are inclusive indices,
        pointEnd and featureEnd are exclusive indices.

        """
        kwds = {}
        kwds['source'] = self
        kwds['pointStart'] = pointStart
        kwds['pointEnd'] = pointEnd
        kwds['featureStart'] = featureStart
        kwds['featureEnd'] = featureEnd
        kwds['reuseData'] = True

        allPoints = pointStart == 0 and pointEnd == self.points
        singlePoint = pointEnd - pointStart == 1
        allFeats = featureStart == 0 and featureEnd == self.features
        singleFeat = featureEnd - featureStart == 1
        # singleFeat = singlePoint = False
        if singleFeat or singlePoint:
            if singlePoint:
                if self._sorted is None or self._sorted == 'feature':
                    self._sortInternal('point')
                sortedIndices = self.data.row

                start = numpy.searchsorted(sortedIndices, pointStart, 'left')
                end = numpy.searchsorted(sortedIndices, pointEnd - 1, 'right')

                if not allFeats:
                    sortedIndices = self.data.col[start:end]
                    innerStart = numpy.searchsorted(sortedIndices, featureStart, 'left')
                    innerEnd = numpy.searchsorted(sortedIndices, featureEnd - 1, 'right')
                    outerStart = start
                    start = start + innerStart
                    end = outerStart + innerEnd

                row = numpy.tile([0], end - start)
                col = self.data.col[start:end] - featureStart

            else:  # case single feature
                if self._sorted is None or self._sorted == 'point':
                    self._sortInternal('feature')
                sortedIndices = self.data.col

                start = numpy.searchsorted(sortedIndices, featureStart, 'left')
                end = numpy.searchsorted(sortedIndices, featureEnd - 1, 'right')

                if not allPoints:
                    sortedIndices = self.data.row[start:end]
                    innerStart = numpy.searchsorted(sortedIndices, pointStart, 'left')
                    innerEnd = numpy.searchsorted(sortedIndices, pointEnd - 1, 'right')
                    outerStart = start
                    start = start + innerStart
                    end = outerStart + innerEnd

                row = self.data.row[start:end] - pointStart
                col = numpy.tile([0], end - start)

            data = self.data.data[start:end]
            pshape = pointEnd - pointStart
            fshape = featureEnd - featureStart

            newInternal = scipy.sparse.coo_matrix((data, (row, col)), shape=(pshape, fshape))
            kwds['data'] = newInternal

            return SparseVectorView(**kwds)

        else:  # window shaped View
            #the data should be dummy data, but data.shape must be = (pointEnd - pointStart, featureEnd - featureStart)
            newInternal = scipy.sparse.coo_matrix([])
            newInternal._shape = (pointEnd - pointStart, featureEnd - featureStart)
            newInternal.data = None
            kwds['data'] = newInternal

            return SparseView(**kwds)

    def _validate_implementation(self, level):
        assert self.data.shape[0] == self.points
        assert self.data.shape[1] == self.features
        assert scipy.sparse.isspmatrix_coo(self.data)

        if level > 0:
            try:
                tmpBool = all(self.data.data != 0)
                #numpy may say: elementwise comparison failed; returning scalar instead,
                # but in the future will perform elementwise comparison
            except Exception:
                tmpBool = all([i != 0 for i in self.data.data])
            assert tmpBool

            assert self.data.dtype.type is not numpy.string_

            if self._sorted == 'point':
                assert all(self.data.row[:-1] <= self.data.row[1:])

            if self._sorted == 'feature':
                assert all(self.data.col[:-1] <= self.data.col[1:])

            without_replicas_coo = removeDuplicatesNative(self.data)
            assert len(self.data.data) == len(without_replicas_coo.data)

    def _containsZero_implementation(self):
        """
        Returns True if there is a value that is equal to integer 0 contained
        in this object. False otherwise

        """
        return (self.data.shape[0] * self.data.shape[1]) > self.data.nnz


    def _nonZeroIteratorPointGrouped_implementation(self):
        self._sortInternal('point')
        return self._nonZeroIterator_general_implementation()

    def _nonZeroIteratorFeatureGrouped_implementation(self):
        self._sortInternal('feature')
        return self._nonZeroIterator_general_implementation()

    def _nonZeroIterator_general_implementation(self):
        # Assumption: underlying data already correctly sorted by
        # per axis helper; will not be modified during iteration
        class nzIt(object):
            def __init__(self, source):
                self._source = source
                self._index = 0

            def __iter__(self):
                return self

            def next(self):
                while (self._index < len(self._source.data.data)):
                    value = self._source.data.data[self._index]

                    self._index += 1
                    if value != 0:
                        return value

                raise StopIteration

            def __next__(self):
                return self.next()

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
        if isinstance(other, BaseView):
            retData = other.copyAs('scipycsr')
            retData = self.data * retData
        else:
            # for other.data as any dense or sparse matrix
            retData = self.data * other.data

        return UML.createData('Sparse', retData)


    def _elementwiseMultiply_implementation(self, other):
        """
        Perform element wise multiplication of this UML data object against the
        provided other UML data object. Both objects must contain only numeric
        data. The pointCount and featureCount of both objects must be equal. The
        types of the two objects may be different, but the returned object will
        be the inplace modification of the calling object.

        """
        # CHOICE OF OUTPUT WILL BE DETERMINED BY SCIPY!!!!!!!!!!!!
        # for other.data as any dense or sparse matrix
        toMul = None
        directMul = isinstance(other, Sparse) or isinstance(other, UML.data.Matrix)
        notView = not isinstance(other, BaseView)
        if directMul and notView:
            toMul = other.data
        else:
            toMul = other.copyAs('numpyarray')
        raw = self.data.multiply(coo_matrix(toMul))
        if scipy.sparse.isspmatrix(raw):
            self.data = raw.tocoo()
        else:
            self.data = coo_matrix(raw, shape=self.data.shape)


    def _scalarMultiply_implementation(self, scalar):
        """
        Multiply every element of this UML data object by the provided scalar.
        This object must contain only numeric data. The 'scalar' parameter must
        be a numeric data type. The returned object will be the inplace modification
        of the calling object.

        """
        if scalar != 0:
            scaled = self.data.data * scalar
            self.data.data = scaled
            self.data.data = scaled
        else:
            self.data = coo_matrix(([], ([], [])), shape=(self.points, self.features))

    def _mul__implementation(self, other):
        if isinstance(other, UML.data.Base):
            return self._matrixMultiply_implementation(other)
        else:
            ret = self.copy()
            ret._scalarMultiply_implementation(other)
            return ret

        #	def _div__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr() / other.copyAs("scipycsr")
        #			ret = ret.tocoo()
        #		else:
        #			retData = self.data.data / other
        #			retRow = numpy.array(self.data.row)
        #			retCol = numpy.array(self.data.col)
        #			ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


        #	def _rdiv__implementation(self, other):
        #		retData = other / self.data
        #		retRow = numpy.array(self.data.row)
        #		retCol = numpy.array(self.data.col)
        #		ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

        #	def _idiv__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr() / other.copyAs("scipycsr")
        #			ret = ret.tocoo()
        #		else:
        #			ret = self.data.data / other
        #		self.data = ret
        #		return self

        #	def _truediv__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr().__truediv__(other.copyAs("scipycsr"))
        #			ret = ret.tocoo()
        #		else:
        #			retData = self.data.data.__truediv__(other)
        #			retRow = numpy.array(self.data.row)
        #			retCol = numpy.array(self.data.col)
        #			ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

        #	def _rtruediv__implementation(self, other):
        #		retData = self.data.data.__rtruediv__(other)
        #		retRow = numpy.array(self.data.row)
        #		retCol = numpy.array(self.data.col)
        #		ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))

        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

        #	def _itruediv__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr().__itruediv__(other.copyAs("scipycsr"))
        #			ret = ret.tocoo()
        #		else:
        #			retData = self.data.data.__itruediv__(other)
        #			retRow = numpy.array(self.data.row)
        #			retCol = numpy.array(self.data.col)
        #			ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		self.data = ret
        #		return self

        #	def _floordiv__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr() // other.copyAs("scipycsr")
        #			ret = ret.tocoo()
        #		else:
        #			retData = self.data.data // other
        #			nzIDs = numpy.nonzero(retData)
        #			retData = retData[nzIDs]
        #			retRow = self.data.row[nzIDs]
        #			retCol = self.data.col[nzIDs]
        #			ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


        #	def _rfloordiv__implementation(self, other):
        #		retData = other // self.data.data
        #		nzIDs = numpy.nonzero(retData)
        #		retData = retData[nzIDs]
        #		retRow = self.data.row[nzIDs]
        #		retCol = self.data.col[nzIDs]
        #		ret = scipy.sparse.coo_matrix((retData,(retRow, retCol)))
        #		return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)

        #	def _ifloordiv__implementation(self, other):
        #		if isinstance(other, UML.data.Base):
        #			ret = self.data.tocsr() // other.copyAs("scipycsr")
        #			ret = ret.tocoo()
        #		else:
        #			ret = self.data // other
        #			nzIDs = numpy.nonzero(ret)
        #			ret = ret[nzIDs]

        #		self.data = ret
        #		return self

    def _mod__implementation(self, other):
        if isinstance(other, UML.data.Base):
            return super(Sparse, self).__mod__(other)
        else:
            retData = self.data.data % other
            retRow = numpy.array(self.data.row)
            retCol = numpy.array(self.data.col)
            ret = scipy.sparse.coo_matrix((retData, (retRow, retCol)))
        return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _rmod__implementation(self, other):
        retData = other % self.data.data
        retRow = numpy.array(self.data.row)
        retCol = numpy.array(self.data.col)
        ret = scipy.sparse.coo_matrix((retData, (retRow, retCol)))

        return Sparse(ret, pointNames=self.getPointNames(), featureNames=self.getFeatureNames(), reuseData=True)


    def _imod__implementation(self, other):
        if isinstance(other, UML.data.Base):
            return super(Sparse, self).__imod__(other)
        else:
            ret = self.data.data % other
        self.data.data = ret
        return self

    ###########
    # Helpers #
    ###########

    def _sortInternal(self, axis):
        if axis != 'point' and axis != 'feature':
            raise ArgumentException("invalid axis type")

        if self._sorted == axis or self.points == 0 or self.features == 0:
            return

        sortAsParam = 'row-major' if axis == 'point' else 'col-major'
        _sortInternal_coo_matrix(self.data, sortAsParam)

        # flag that we are internally sorted
        self._sorted = axis


###################
# Generic Helpers #
###################


def _sortInternal_coo_matrix(obj, sortAs):
    if sortAs != 'row-major' and sortAs != 'col-major':
        raise ArgumentException("invalid axis type")

    # sort least significant axis first
    if sortAs == "row-major":
        sortPrime = obj.row
        sortOff = obj.col
    else:
        sortPrime = obj.col
        sortOff = obj.row

    sortKeys = numpy.lexsort((sortOff, sortPrime))

    obj.data = obj.data[sortKeys]
    obj.row = obj.row[sortKeys]
    obj.col = obj.col[sortKeys]

    # newData = obj.data[sortKeys]
    # newRow = obj.row[sortKeys]
    # newCol = obj.col[sortKeys]
    #
    # n = len(newData)
    # obj.data[:n] = newData
    # obj.row[:n] = newRow
    # obj.col[:n] = newCol

def _numLessThan(value, toCheck): # TODO caching
    ltCount = 0
    for i in range(len(toCheck)):
        if toCheck[i] < value:
            ltCount += 1

    return ltCount


def _calcShapes(currShape, numExtracted, axisType):
    (rowShape, colShape) = currShape
    if axisType == "feature":
        selfRowShape = rowShape
        selfColShape = colShape - numExtracted
        extRowShape = rowShape
        extColShape = numExtracted
    elif axisType == "point":
        selfRowShape = rowShape - numExtracted
        selfColShape = colShape
        extRowShape = numExtracted
        extColShape = colShape
    else:
        raise ArgumentException("invalid axis type")

    return ((selfRowShape, selfColShape), (extRowShape, extColShape))


def _resync(obj):
    if 0 in obj.shape:
        obj.nnz = 0
        obj.data = numpy.array([])
        obj.row = numpy.array([])
        obj.col = numpy.array([])
        obj.shape = obj.shape
    else:
        obj.nnz = obj.nnz
        obj.data = obj.data
        obj.row = obj.row
        obj.col = obj.col
        obj.shape = obj.shape


def removeDuplicatesNative(coo_obj):
    """
    Creates a new coo_matrix, using summation for numeric data to remove duplicates.
    If there are duplicate entires involving non-numeric data, an exception is raised.

    coo_obj : the coo_matrix from which the data of the return object originates from. It
    will not be modified by the function.

    Returns : a new coo_matrix with the same data as in the input matrix, except with duplicate
    numerical entries summed to a single value. This operation is NOT stable - the row / col
    attributes are not guaranteed to have an ordering related to those from the input object.
    This operation is guaranteed to not introduce any 0 values to the data attribute.

    """
    if coo_obj.data is None:
        #When coo_obj data is not iterable: Empty
        #It will throw TypeError: zip argument #3 must support iteration.
        #Decided just to do this quick check instead of duck typing.
        return coo_obj

    seen = {}
    for i,j,v in zip(coo_obj.row, coo_obj.col, coo_obj.data):
        if (i,j) not in seen:
            # all types are allows to be present once
            seen[(i,j)] = v
        else:
            try:
                seen[(i,j)] += float(v)
            except ValueError:
                raise ValueError('Unable to represent this configuration of data in Sparse object.\
                                At least one removeDuplicatesNativeof the duplicate entries is a non-numerical type')

    rows = []
    cols = []
    data = []

    for (i,j) in seen:
        if seen[(i,j)] != 0:
            rows.append(i)
            cols.append(j)
            data.append(seen[(i,j)])

    dataNP = numpy.array(data)
    # if there are mixed strings and numeric values numpy will automatically turn everything
    # into strings. This will check to see if that has happened and use the object dtype instead.
    if len(dataNP) > 0 and isinstance(dataNP[0], numpy.flexible):
        dataNP = numpy.array(data, dtype='O')
    new_coo = coo_matrix((dataNP, (rows, cols)), shape=coo_obj.shape)

    return new_coo


def removeDuplicatesByConversion(coo_obj):
    try:
        return coo_obj.tocsr().tocoo()
        # return coo_obj.tocsc().tocoo()
    except TypeError:
        raise TypeError('Unable to represent this configuration of data in Sparse object.')




class SparseVectorView(BaseView, Sparse):
    """
    A view of a Sparse data object limited to a full point or full feature

    """

    def __init__(self, **kwds):
        super(SparseVectorView, self).__init__(**kwds)


class SparseView(BaseView, Sparse):
    def __init__(self, **kwds):
        super(SparseView, self).__init__(**kwds)

    def _validate_implementation(self, level):
        self._source.validate(level)

    def _getitem_implementation(self, x, y):
        adjX = x + self._pStart
        adjY = y + self._fStart
        return self._source[adjX, adjY]

    def pointIterator(self):
        return self._generic_iterator("point")

    def featureIterator(self):
        return self._generic_iterator("feature")

    def _generic_iterator(self, axis):
        source = self._source
        if axis == 'point':
            positionLimit = self._pStart + self.points
            sourceStart = self._pStart
            # Needs to be None if we're dealing with a fully empty point
            fixedStart = self._fStart if self._fStart != 0 else None
            # self._fEnd is exclusive, but view takes inclusive indices
            fixedEnd = (self._fEnd - 1) if self._fEnd != 0 else None
        else:
            positionLimit = self._fStart + self.features
            sourceStart = self._fStart
            # Needs to be None if we're dealing with a fully empty feature
            fixedStart = self._pStart if self._pStart != 0 else None
            # self._pEnd is exclusive, but view takes inclusive indices
            fixedEnd = (self._pEnd - 1) if self._pEnd != 0 else None

        class GenericIt(object):
            def __init__(self):
                self._position = sourceStart

            def __iter__(self):
                return self

            def next(self):
                if self._position < positionLimit:
                    if axis == 'point':
                        value = source.view(self._position, self._position, fixedStart, fixedEnd)
                    else:
                        value = source.view(fixedStart, fixedEnd, self._position, self._position)
                    self._position += 1
                    return value

                raise StopIteration

            def __next__(self):
                return self.next()

        return GenericIt()

    def _copyAs_implementation(self, format):
        if self.points == 0 or self.features == 0:
            emptyStandin = numpy.empty((self.points, self.features))
            intermediate = UML.createData('Matrix', emptyStandin)
            return intermediate.copyAs(format)

        if format == 'numpyarray':
            pStart, pEnd = self._pStart, self._pEnd
            fStart, fEnd = self._fStart, self._fEnd
            limited = self._source.data.todense()[pStart:pEnd, fStart:fEnd]
            return numpy.array(limited)

        limited = self._source.copyPoints(start=self._pStart, end=self._pEnd - 1)
        limited = limited.copyFeatures(start=self._fStart, end=self._fEnd - 1)

        if format is None or format == 'Sparse':
            return limited
        else:
            return limited._copyAs_implementation(format)

    def _isIdentical_implementation(self, other):
        if not isinstance(other, Sparse):
            return False
        # for nonempty matrices, we use a shape mismatch to indicate non-equality
        if self.data.shape != other.data.shape:
            return False

        # empty object means no values. Since shapes match they're equal
        if self.data.shape[0] == 0 or self.data.shape[1] == 0:
            return True

        sIt = self.pointIterator()
        oIt = other.pointIterator()
        for sPoint in sIt:
            oPoint = next(oIt)

            for i, val in enumerate(sPoint):
                if val != oPoint[i] and val == val:
                    return False

        return True

    def _containsZero_implementation(self):
        for sPoint in self.pointIterator():
            if sPoint.containsZero():
                return True

        return False

    def __abs__(self):
        """ Perform element wise absolute value on this object """
        ret = self.copyAs("Sparse")
        numpy.absolute(ret.data.data, out=ret.data.data)
        ret._name = dataHelpers.nextDefaultObjectName()

        return ret

    def _mul__implementation(self, other):
        selfConv = self.copyAs("Sparse")
        if isinstance(other, BaseView):
            other = other.copyAs(other.getTypeString())
        return selfConv._mul__implementation(other)

    def _genericNumericBinary_implementation(self, opName, other):
        if isinstance(other, BaseView):
            other = other.copyAs(other.getTypeString())

        implName = opName[1:] + 'implementation'
        opType = opName[-5:-2]

        if opType in ['add', 'sub', 'div', 'truediv', 'floordiv']:
            selfConv = self.copyAs("Matrix")
            toCall = getattr(selfConv, implName)
            ret = toCall(other)
            ret = UML.createData("Sparse", ret.data)
            return ret

        selfConv = self.copyAs("Sparse")

        toCall = getattr(selfConv, implName)
        ret = toCall(other)
        ret = UML.createData(self.getTypeString(), ret.data)

        return ret


    def _nonZeroIteratorPointGrouped_implementation(self):
        return self._nonZeroIterator_general_implementation(self.pointIterator())

    def _nonZeroIteratorFeatureGrouped_implementation(self):
        return self._nonZeroIterator_general_implementation(self.featureIterator())

    def _nonZeroIterator_general_implementation(self, sourceIter):
        # IDEA: check if sorted in the way you want.
        # if yes, iterate through
        # if no, use numpy argsort? this gives you indices that
        # would sort it, iterate through those indices to do access?
        #
        # safety: somehow check that your sorting setup hasn't changed

        class nzIt(object):
            def __init__(self):
                self._sourceIter = sourceIter
                self._currGroup = None
                self._index = 0

            def __iter__(self):
                return self

            def next(self):
                while True:
                    try:
                        value = self._currGroup[self._index]
                        self._index += 1

                        if value != 0:
                            return value
                    except:
                        self._currGroup = next(self._sourceIter)
                        self._index = 0

            def __next__(self):
                return self.next()

        return nzIt()
