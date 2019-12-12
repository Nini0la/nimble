"""
Class extending Base, using a numpy dense matrix to store data.
"""

from __future__ import division
from __future__ import absolute_import
import copy
import itertools
from functools import reduce

import numpy
from six.moves import range

import nimble
from nimble import match
from nimble.exceptions import InvalidArgumentType, InvalidArgumentValue
from nimble.exceptions import PackageException
from nimble.utility import inheritDocstringsFactory, numpy2DArray, is2DArray
from nimble.utility import ImportModule
from .base import Base
from .base_view import BaseView
from .matrixPoints import MatrixPoints, MatrixPointsView
from .matrixFeatures import MatrixFeatures, MatrixFeaturesView
from .dataHelpers import DEFAULT_PREFIX
from .dataHelpers import allDataIdentical
from .dataHelpers import createDataNoValidation
from .dataHelpers import denseCountUnique
from .dataHelpers import DenseElementIterator

scipy = ImportModule('scipy')
pd = ImportModule('pandas')

@inheritDocstringsFactory(Base)
class Matrix(Base):
    """
    Class providing implementations of data manipulation operations on
    data stored in a numpy dense matrix.

    Parameters
    ----------
    data : object
        Must be a two-dimensional numpy array.
    reuseData : bool
    elementType : type
        The numpy dtype of this object.
    kwds
        Included due to best practices so args may automatically be
        passed further up into the hierarchy if needed.
    """

    def __init__(self, data, reuseData=False, elementType=None, **kwds):
        if not is2DArray(data):
            msg = "the input data can only be a two-dimensional numpy array."
            raise InvalidArgumentType(msg)

        if isinstance(data, numpy.matrix):
            data = numpy2DArray(data)
        if elementType is not None:
            data = data.astype(elementType)
        if reuseData:
            self.data = data
        else:
            self.data = data.copy()

        kwds['shape'] = self.data.shape
        super(Matrix, self).__init__(**kwds)

    def _getPoints(self):
        return MatrixPoints(self)

    def _getFeatures(self):
        return MatrixFeatures(self)

    def _transform_implementation(self, toTransform, points, features):
        IDs = itertools.product(range(len(self.points)),
                                range(len(self.features)))
        for i, j in IDs:
            currVal = self.data[i, j]

            if points is not None and i not in points:
                continue
            if features is not None and j not in features:
                continue

            if toTransform.oneArg:
                currRet = toTransform(currVal)
            else:
                currRet = toTransform(currVal, i, j)

            self.data[i, j] = currRet
            # numpy modified data due to int dtype
            if self.data[i, j] != currRet:
                if match.nonNumeric(currRet) and currRet is not None:
                    self.data = self.data.astype(numpy.object_)
                else:
                    self.data = self.data.astype(numpy.float)
                self.data[i, j] = currRet

    def _calculate_implementation(self, function, points, features,
                                  preserveZeros, outputType):
        return self._calculate_genericVectorized(
            function, points, features, outputType)

    def _countUnique_implementation(self, points, features):
        return denseCountUnique(self, points, features)

    def _transpose_implementation(self):
        """
        Function to transpose the data, ie invert the feature and point
        indices of the data.

        This is not an in place operation, a new list of lists is
        constructed.
        """
        self.data = self.data.transpose()

    def _getTypeString_implementation(self):
        return 'Matrix'

    def _isIdentical_implementation(self, other):
        if not isinstance(other, Matrix):
            return False
        if len(self.points) != len(other.points):
            return False
        if len(self.features) != len(other.features):
            return False

        return allDataIdentical(self.data, other.data)

    def _writeFile_implementation(self, outPath, fileFormat, includePointNames,
                                  includeFeatureNames):
        """
        Function to write the data in this object to a file using the
        specified format. outPath is the location (including file name
        and extension) where we want to write the output file.
        ``includeNames`` is boolean argument indicating whether the file
        should start with comment lines designating pointNames and
        featureNames.
        """
        # if format not in ['csv', 'mtx']:
        #     msg = "Unrecognized file format. Accepted types are 'csv' and "
        #     msg += "'mtx'. They may either be input as the format parameter, "
        #     msg += "or as the extension in the outPath"
        #     raise InvalidArgumentValue(msg)

        if fileFormat == 'csv':
            return self._writeFileCSV_implementation(
                outPath, includePointNames, includeFeatureNames)
        if fileFormat == 'mtx':
            return self._writeFileMTX_implementation(
                outPath, includePointNames, includeFeatureNames)

    def _writeFileCSV_implementation(self, outPath, includePointNames,
                                     includeFeatureNames):
        """
        Function to write the data in this object to a CSV file at the
        designated path.
        """
        with open(outPath, 'w') as outFile:

            if includeFeatureNames:
                def combine(a, b):
                    return a + ',' + b

                fnames = self.features.getNames()
                fnamesLine = reduce(combine, fnames)
                fnamesLine += '\n'
                if includePointNames:
                    outFile.write('pointNames,')

                outFile.write(fnamesLine)

        with open(outPath, 'ab') as outFile:#python3 need this.
            if includePointNames:
                pnames = numpy2DArray(self.points.getNames())
                pnames = pnames.transpose()

                viewData = self.data.view()
                toWrite = numpy.concatenate((pnames, viewData), 1)

                numpy.savetxt(outFile, toWrite, delimiter=',', fmt='%s')
            else:
                numpy.savetxt(outFile, self.data, delimiter=',')

    def _writeFileMTX_implementation(self, outPath, includePointNames,
                                     includeFeatureNames):
        if not scipy:
            msg = "scipy is not available"
            raise PackageException(msg)

        def makeNameString(count, namesGetter):
            nameString = "#"
            for i in range(count):
                nameString += namesGetter(i)
                if not i == count - 1:
                    nameString += ','
            return nameString

        header = ''
        if includePointNames:
            header = makeNameString(len(self.points), self.points.getName)
            header += '\n'
        else:
            header += '#\n'
        if includeFeatureNames:
            header += makeNameString(len(self.features), self.features.getName)
        else:
            header += '#\n'

        if header != '':
            scipy.io.mmwrite(target=outPath, a=self.data, comment=header)
        else:
            scipy.io.mmwrite(target=outPath, a=self.data)

    def _referenceDataFrom_implementation(self, other):
        if not isinstance(other, Matrix):
            msg = "Other must be the same type as this object"
            raise InvalidArgumentType(msg)

        self.data = other.data

    def _copy_implementation(self, to):
        if to in nimble.data.available:
            ptNames = self.points._getNamesNoGeneration()
            ftNames = self.features._getNamesNoGeneration()
            # reuseData=False since using original data
            return createDataNoValidation(to, self.data, ptNames, ftNames)
        if to == 'pythonlist':
            return self.data.tolist()
        if to == 'numpyarray':
            return self.data.copy()
        if to == 'numpymatrix':
            return numpy.matrix(self.data)
        if 'scipy' in to:
            if not scipy:
                msg = "scipy is not available"
                raise PackageException(msg)
            if to == 'scipycsc':
                return scipy.sparse.csc_matrix(self.data)
            if to == 'scipycsr':
                return scipy.sparse.csr_matrix(self.data)
            if to == 'scipycoo':
                return scipy.sparse.coo_matrix(self.data)
        if to == 'pandasdataframe':
            if not pd:
                msg = "pandas is not available"
                raise PackageException(msg)
            return pd.DataFrame(self.data.copy())


    def _fillWith_implementation(self, values, pointStart, featureStart,
                                 pointEnd, featureEnd):
        if not isinstance(values, Base):
            values = values * numpy.ones((pointEnd - pointStart + 1,
                                          featureEnd - featureStart + 1))
        else:
            values = values.data

        # numpy is exclusive
        pointEnd += 1
        featureEnd += 1
        self.data[pointStart:pointEnd, featureStart:featureEnd] = values

    def _flattenToOnePoint_implementation(self):
        numElements = len(self.points) * len(self.features)
        self.data = self.data.reshape((1, numElements), order='C')

    def _flattenToOneFeature_implementation(self):
        numElements = len(self.points) * len(self.features)
        self.data = self.data.reshape((numElements, 1), order='F')

    def _unflattenFromOnePoint_implementation(self, numPoints):
        numFeatures = len(self.features) // numPoints
        self.data = self.data.reshape((numPoints, numFeatures), order='C')

    def _unflattenFromOneFeature_implementation(self, numFeatures):
        numPoints = len(self.points) // numFeatures
        self.data = self.data.reshape((numPoints, numFeatures), order='F')

    def _merge_implementation(self, other, point, feature, onFeature,
                              matchingFtIdx):
        self.data = numpy.array(self.data, dtype=numpy.object_)
        otherArr = numpy.array(other.data, dtype=numpy.object_)
        if onFeature:
            if feature in ["intersection", "left"]:
                onFeatureIdx = self.features.getIndex(onFeature)
                onIdxLoc = matchingFtIdx[0].index(onFeatureIdx)
                onIdxL = onIdxLoc
                onIdxR = onIdxLoc
                right = otherArr[:, matchingFtIdx[1]]
                # matching indices in right were sorted when slicing above
                matchingFtIdx[1] = list(range(right.shape[1]))
                if feature == "intersection":
                    self.data = self.data[:, matchingFtIdx[0]]
                    # matching indices in left were sorted when slicing above
                    matchingFtIdx[0] = list(range(self.data.shape[1]))
            else:
                onIdxL = self.features.getIndex(onFeature)
                onIdxR = other.features.getIndex(onFeature)
                right = otherArr
        else:
            # using pointNames, prepend pointNames to left and right arrays
            onIdxL = 0
            onIdxR = 0
            if not self._anyDefaultPointNames():
                ptsL = numpy.array(self.points.getNames(), dtype=numpy.object_)
                ptsL = ptsL.reshape(-1, 1)
            elif self._pointNamesCreated():
                # differentiate default names between objects;
                # note still start with DEFAULT_PREFIX
                namesL = [n + '_l' if n.startswith(DEFAULT_PREFIX) else n
                          for n in self.points.getNames()]
                ptsL = numpy.array(namesL, dtype=numpy.object_)
                ptsL = ptsL.reshape(-1, 1)
            else:
                defNames = [DEFAULT_PREFIX + '_l' for _
                            in range(len(self.points))]
                ptsL = numpy.array(defNames, dtype=numpy.object_)
                ptsL = ptsL.reshape(-1, 1)
            if not other._anyDefaultPointNames():
                ptsR = numpy.array(other.points.getNames(),
                                   dtype=numpy.object_)
                ptsR = ptsR.reshape(-1, 1)
            elif other._pointNamesCreated():
                # differentiate default names between objects;
                # note still start with DEFAULT_PREFIX
                namesR = [n + '_r' if n.startswith(DEFAULT_PREFIX) else n
                          for n in other.points.getNames()]
                ptsR = numpy.array(namesR, dtype=numpy.object_)
                ptsR = ptsR.reshape(-1, 1)
            else:
                defNames = [DEFAULT_PREFIX + '_r' for _
                            in range(len(other.points))]
                ptsR = numpy.array(defNames, dtype=numpy.object_)
                ptsR = ptsR.reshape(-1, 1)
            if feature == "intersection":
                concatL = (ptsL, self.data[:, matchingFtIdx[0]])
                self.data = numpy.concatenate(concatL, axis=1)
                concatR = (ptsR, otherArr[:, matchingFtIdx[1]])
                right = numpy.concatenate(concatR, axis=1)
                # matching indices were sorted when slicing above
                # this also accounts for prepended column
                matchingFtIdx[0] = list(range(self.data.shape[1]))
                matchingFtIdx[1] = matchingFtIdx[0]
            elif feature == "left":
                self.data = numpy.concatenate((ptsL, self.data), axis=1)
                concatR = (ptsR, otherArr[:, matchingFtIdx[1]])
                right = numpy.concatenate(concatR, axis=1)
                # account for new column in matchingFtIdx
                matchingFtIdx[0] = list(map(lambda x: x + 1, matchingFtIdx[0]))
                matchingFtIdx[0].insert(0, 0)
                # matching indices were sorted when slicing above
                # this also accounts for prepended column
                matchingFtIdx[1] = list(range(right.shape[1]))
            else:
                self.data = numpy.concatenate((ptsL, self.data), axis=1)
                right = numpy.concatenate((ptsR, otherArr), axis=1)
                # account for new column in matchingFtIdx
                matchingFtIdx[0] = list(map(lambda x: x + 1, matchingFtIdx[0]))
                matchingFtIdx[0].insert(0, 0)
                matchingFtIdx[1] = list(map(lambda x: x + 1, matchingFtIdx[1]))
                matchingFtIdx[1].insert(0, 0)
        left = self.data

        matched = []
        merged = []
        unmatchedPtCountR = right.shape[1] - len(matchingFtIdx[1])
        matchMapper = {}
        for pt in left:
            match = right[right[:, onIdxR] == pt[onIdxL]]
            if len(match) > 0:
                matchMapper[pt[onIdxL]] = match
        for ptL in left:
            target = ptL[onIdxL]
            if target in matchMapper:
                matchesR = matchMapper[target]
                for ptR in matchesR:
                    # check for conflicts between matching features
                    matches = ptL[matchingFtIdx[0]] == ptR[matchingFtIdx[1]]
                    nansL = numpy.array([x != x for x
                                         in ptL[matchingFtIdx[0]]])
                    nansR = numpy.array([x != x for x
                                         in ptR[matchingFtIdx[1]]])
                    acceptableValues = matches + nansL + nansR
                    if not all(acceptableValues):
                        msg = "The objects contain different values for the "
                        msg += "same feature"
                        raise InvalidArgumentValue(msg)
                    if nansL.any():
                        # fill any nan values in left with the corresponding
                        # right value
                        for i, value in enumerate(ptL[matchingFtIdx[0]]):
                            if value != value:
                                fill = ptR[matchingFtIdx[1]][i]
                                ptL[matchingFtIdx[0]][i] = fill
                    ptR = numpy.delete(ptR, matchingFtIdx[1])
                    pt = numpy.concatenate((ptL, ptR)).flatten()
                    merged.append(pt)
                matched.append(target)
            elif point in ['union', 'left']:
                ptL = ptL.reshape(1, -1)
                ptR = numpy.ones((1, unmatchedPtCountR)) * numpy.nan
                pt = numpy.append(ptL, ptR)
                merged.append(pt)

        if point == 'union':
            notMatchingR = [i for i in range(right.shape[1])
                            if i not in matchingFtIdx[1]]
            for row in right:
                target = row[onIdxR]
                if target not in matched:
                    ones = numpy.ones((left.shape[1] + unmatchedPtCountR,),
                                      dtype=numpy.object_)
                    pt = ones * numpy.nan
                    pt[matchingFtIdx[0]] = row[matchingFtIdx[1]]
                    pt[left.shape[1]:] = row[notMatchingR]
                    merged.append(pt)


        self._featureCount = left.shape[1] + unmatchedPtCountR
        self._pointCount = len(merged)
        if len(merged) == 0 and onFeature is None:
            merged = numpy.empty((0, left.shape[1] + unmatchedPtCountR - 1))
            self._featureCount -= 1
        elif len(merged) == 0:
            merged = numpy.empty((0, left.shape[1] + unmatchedPtCountR))
        elif onFeature is None:
            # remove point names feature
            merged = [row[1:] for row in merged]
            self._featureCount -= 1

        self.data = numpy2DArray(merged, dtype=numpy.object_)

    def _replaceFeatureWithBinaryFeatures_implementation(self, uniqueVals):
        toFill = numpy.zeros((len(self.points), len(uniqueVals)))
        for ptIdx, val in enumerate(self.data):
            ftIdx = uniqueVals.index(val)
            toFill[ptIdx, ftIdx] = 1
        return Matrix(toFill)

    def _getitem_implementation(self, x, y):
        return self.data[x, y]

    def _view_implementation(self, pointStart, pointEnd, featureStart,
                             featureEnd):
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
        assert shape[0] == len(self.points)
        assert shape[1] == len(self.features)


    def _containsZero_implementation(self):
        """
        Returns True if there is a value that is equal to integer 0
        contained in this object. False otherwise
        """
        return 0 in self.data


    def _binaryOperations_implementation(self, opName, other):
        """
        Attempt to perform operation with data as is, preserving sparse
        representations if possible. Otherwise, uses the generic
        implementation.
        """
        if isinstance(other, nimble.data.Sparse) and opName.startswith('__r'):
            # rhs may return array of sparse matrices so use default
            return self._defaultBinaryOperations_implementation(opName, other)
        try:
            ret = getattr(self.data, opName)(other.data)
            return Matrix(ret)
        except (AttributeError, InvalidArgumentType):
            return self._defaultBinaryOperations_implementation(opName, other)

    def _matmul__implementation(self, other):
        """
        Matrix multiply this nimble Base object against the provided
        other nimble Base object. Both object must contain only numeric
        data. The featureCount of the calling object must equal the
        pointCount of the other object. The types of the two objects may
        be different, and the return is guaranteed to be the same type
        as at least one out of the two, to be automatically determined
        according to efficiency constraints.
        """
        if isinstance(other, Matrix):
            return Matrix(numpy.matmul(self.data, other.data))
        elif isinstance(other, nimble.data.Sparse):
            # '*' is matrix multiplication in scipy
            return Matrix(self.data * other.data)
        return Matrix(numpy.matmul(self.data, other.copy(to="numpyarray")))

    def _iterElements_implementation(self, order, only):
        return DenseElementIterator(self, order, only)

def viewBasedApplyAlongAxis(function, axis, outerObject):
    """
    Applies the given function to each view along the given axis,
    returning the results of the function in numpy array
    """
    if axis == "point":
        maxVal = outerObject.data.shape[0]
        viewMaker = outerObject.pointView
    else:
        if axis != "feature":
            raise InvalidArgumentValue("axis must be 'point' or 'feature'")
        maxVal = outerObject.data.shape[1]
        viewMaker = outerObject.featureView
    ret = numpy.zeros(maxVal, dtype=numpy.float)
    for i in range(0, maxVal):
        funcOut = function(viewMaker(i))
        ret[i] = funcOut

    return ret

def matrixBasedApplyAlongAxis(function, axis, outerObject):
    """
    applies the given function to the underlying numpy matrix along the
    given axis, returning the results of the function in numpy array
    """
    #make sure the 3 attributes are in the function object
    if not (hasattr(function, 'nameOfFeatureOrPoint')
            and hasattr(function, 'valueOfFeatureOrPoint')
            and hasattr(function, 'optr')):
        msg = "some important attribute is missing in the input function"
        raise AttributeError(msg)
    if axis == "point":
        #convert name of feature to index of feature
        index = function.nameOfFeatureOrPoint
        indexOfFeature = outerObject.features.getIndex(index)
        #extract the feature from the underlying matrix
        queryData = outerObject.data[:, indexOfFeature]
    else:
        if axis != "feature":
            raise InvalidArgumentValue("axis must be 'point' or 'feature'")
        #convert name of point to index of point
        index = function.nameOfFeatureOrPoint
        indexOfPoint = outerObject.points.getIndex(index)
        #extract the point from the underlying matrix
        queryData = outerObject.data[indexOfPoint, :]
    ret = function.optr(queryData, function.valueOfFeatureOrPoint)
    #convert the result from matrix to numpy array
    ret = ret.astype(numpy.float).A1

    return ret


class MatrixView(BaseView, Matrix):
    """
    Read only access to a Matrix object.
    """
    def __init__(self, **kwds):
        super(MatrixView, self).__init__(**kwds)

    def _getPoints(self):
        return MatrixPointsView(self)

    def _getFeatures(self):
        return MatrixFeaturesView(self)
