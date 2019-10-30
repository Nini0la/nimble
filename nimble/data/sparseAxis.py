"""
Implementations and helpers specific to performing axis-generic
operations on a nimble Sparse object.
"""

from __future__ import absolute_import
from abc import abstractmethod

import numpy

import nimble
from nimble.exceptions import InvalidArgumentType, InvalidArgumentValue
from nimble.utility import OptionalPackage
from .axis import Axis
from .points import Points
from .dataHelpers import sortIndexPosition

scipy = OptionalPackage('scipy')

class SparseAxis(Axis):
    """
    Differentiate how Sparse methods act dependent on the axis.

    Also includes abstract methods which will be required to perform
    axis-specific operations.

    Parameters
    ----------
    base : Sparse
        The Sparse instance that will be queried and modified.
    """

    ##############################
    # Structural implementations #
    ##############################

    def _structuralBackend_implementation(self, structure, targetList):
        """
        Backend for points/features.extract points/features.delete,
        points/features.retain, and points/features.copy. Returns a new
        object containing only the points or features in targetList and
        performs some modifications to the original object if necessary.
        This function does not perform all of the modification or
        process how each function handles the returned value, these are
        managed separately by each frontend function.
        """
        pointNames, featureNames = self._getStructuralNames(targetList)
        # SparseView or object dtype
        if (isinstance(self._base, nimble.data.BaseView)
                or self._base.data.dtype == numpy.object_):
            return self._structuralIterative_implementation(
                structure, targetList, pointNames, featureNames)
        # nonview numeric objects
        return self._structuralVectorized_implementation(
            structure, targetList, pointNames, featureNames)

    def _sort_implementation(self, indexPosition):
        # since we want to access with with positions in the original
        # data, we reverse the 'map'
        reverseIdxPosition = numpy.empty(len(indexPosition))
        for i, idxPos in enumerate(indexPosition):
            reverseIdxPosition[idxPos] = i

        if isinstance(self, Points):
            self._base.data.row[:] = reverseIdxPosition[self._base.data.row]
        else:
            self._base.data.col[:] = reverseIdxPosition[self._base.data.col]
        self._base._sorted = None

    def _transform_implementation(self, function, limitTo):
        modData = []
        modRow = []
        modCol = []

        if isinstance(self, Points):
            modTarget = modRow
            modOther = modCol
        else:
            modTarget = modCol
            modOther = modRow

        for viewID, view in enumerate(self):
            if limitTo is not None and viewID not in limitTo:
                currOut = list(view)
            else:
                currOut = function(view)

            # easy way to reuse code if we have a singular return
            if not hasattr(currOut, '__iter__'):
                currOut = [currOut]

            # if there are multiple values, they must be random accessible
            if not hasattr(currOut, '__getitem__'):
                msg = "function must return random accessible data "
                msg += "(ie has a __getitem__ attribute)"
                raise InvalidArgumentType(msg)

            for i, retVal in enumerate(currOut):
                if retVal != 0:
                    modData.append(retVal)
                    modTarget.append(viewID)
                    modOther.append(i)

        if len(modData) != 0:
            try:
                modData = numpy.array(modData, dtype=numpy.float)
            except Exception:
                modData = numpy.array(modData, dtype=numpy.object_)
            shape = (len(self._base.points), len(self._base.features))
            self._base.data = scipy.sparse.coo_matrix(
                (modData, (modRow, modCol)), shape=shape)
            self._base._sorted = None

        ret = None
        return ret

    def _add_implementation(self, toAdd, insertBefore):
        """
        Insert the points/features from the toAdd object below the
        provided index in this object, the remaining points/features
        from this object will continue below the inserted
        points/features.
        """
        selfData = self._base.data.data
        addData = toAdd.data.data
        newData = numpy.concatenate((selfData, addData))
        if isinstance(self, Points):
            selfAxis = self._base.data.row.copy()
            selfOffAxis = self._base.data.col
            addAxis = toAdd.data.row.copy()
            addOffAxis = toAdd.data.col
            addLength = len(toAdd.points)
            shape = (len(self) + addLength, len(self._base.features))
        else:
            selfAxis = self._base.data.col.copy()
            selfOffAxis = self._base.data.row
            addAxis = toAdd.data.col.copy()
            addOffAxis = toAdd.data.row
            addLength = len(toAdd.features)
            shape = (len(self._base.points), len(self) + addLength)

        selfAxis[selfAxis >= insertBefore] += addLength
        addAxis += insertBefore

        newAxis = numpy.concatenate((selfAxis, addAxis))
        newOffAxis = numpy.concatenate((selfOffAxis, addOffAxis))

        if isinstance(self, Points):
            rowColTuple = (newAxis, newOffAxis)
        else:
            rowColTuple = (newOffAxis, newAxis)

        self._base.data = scipy.sparse.coo_matrix((newData, rowColTuple),
                                                  shape=shape)
        self._base._sorted = None

    def _repeat_implementation(self, totalCopies, copyValueByValue):
        if copyValueByValue:
            numpyFunc = numpy.repeat
        else:
            numpyFunc = numpy.tile
        repData = numpyFunc(self._base.data.data, totalCopies)
        fillDup = numpy.empty_like(repData, dtype=numpy.int)
        if isinstance(self, Points):
            repCol = numpyFunc(self._base.data.col, totalCopies)
            repRow = fillDup
            toRepeat = self._base.data.row
            numRepeatd = len(self)
            startIdx = 0
            shape = ((len(self) * totalCopies), len(self._base.features))
        else:
            repRow = numpyFunc(self._base.data.row, totalCopies)
            repCol = fillDup
            toRepeat = self._base.data.col
            numRepeatd = len(self)
            shape = (len(self._base.points), (len(self) * totalCopies))

        startIdx = 0
        if copyValueByValue:
            for idx in toRepeat:
                endIdx = startIdx + totalCopies
                indexRange = numpy.array(range(totalCopies))
                adjustedIndices = indexRange + (totalCopies * idx)
                fillDup[startIdx:endIdx] = adjustedIndices
                startIdx = endIdx
        else:
            for i in range(totalCopies):
                endIdx = len(toRepeat) * (i + 1)
                fillDup[startIdx:endIdx] = toRepeat + (numRepeatd * i)
                startIdx = endIdx

        repeated = scipy.sparse.coo_matrix((repData, (repRow, repCol)),
                                           shape=shape)
        self._base._sorted = None

        return repeated

    #########################
    # Query implementations #
    #########################

    def _nonZeroIterator_implementation(self):
        if isinstance(self, Points):
            self._base._sortInternal('point')
        else:
            self._base._sortInternal('feature')

        return nzIt(self._base)

    ######################
    # Structural Helpers #
    ######################

    def _structuralVectorized_implementation(self, structure, targetList,
                                             pointNames, featureNames):
        """
        Use scipy csr or csc matrices for indexing targeted values
        """
        if structure != 'copy':
            notTarget = []
            for idx in range(len(self)):
                if idx not in targetList:
                    notTarget.append(idx)

        if isinstance(self, Points):
            data = self._base.data.tocsr()
            targeted = data[targetList, :]
            if structure != 'copy':
                notTargeted = data[notTarget, :]
        else:
            data = self._base.data.tocsc()
            targeted = data[:, targetList]
            if structure != 'copy':
                notTargeted = data[:, notTarget]

        if structure != 'copy':
            self._base.data = notTargeted.tocoo()
            self._base._sorted = None

        ret = targeted.tocoo()

        return nimble.data.Sparse(ret, pointNames=pointNames,
                                  featureNames=featureNames,
                                  reuseData=True)

    def _structuralIterative_implementation(self, structure, targetList,
                                            pointNames, featureNames):
        """
        Iterate through each member to index targeted values
        """
        dtype = numpy.object_

        targetLength = len(targetList)
        targetData = []
        targetRows = []
        targetCols = []
        keepData = []
        keepRows = []
        keepCols = []
        keepIndex = 0

        # iterate through self._axis data
        for targetID, view in enumerate(self):
            # coo_matrix data for return object
            if targetID in targetList:
                for otherID, value in enumerate(view.data.data):
                    targetData.append(value)
                    if isinstance(self, Points):
                        targetRows.append(targetList.index(targetID))
                        targetCols.append(view.data.col[otherID])
                    else:
                        targetRows.append(view.data.row[otherID])
                        targetCols.append(targetList.index(targetID))
            # coo_matrix data for modified self._base
            elif structure != 'copy':
                for otherID, value in enumerate(view.data.data):
                    keepData.append(value)
                    if isinstance(self, Points):
                        keepRows.append(keepIndex)
                        keepCols.append(view.data.col[otherID])
                    else:
                        keepRows.append(view.data.row[otherID])
                        keepCols.append(keepIndex)
                keepIndex += 1

        # instantiate return data
        selfShape, targetShape = _calcShapes(self._base.data.shape,
                                             targetLength, self._axis)
        if structure != 'copy':
            keepData = numpy.array(keepData, dtype=dtype)
            self._base.data = scipy.sparse.coo_matrix(
                (keepData, (keepRows, keepCols)), shape=selfShape)
            self._base._sorted = None
        # need to manually set dtype or coo_matrix will force to simplest dtype
        targetData = numpy.array(targetData, dtype=dtype)
        ret = scipy.sparse.coo_matrix((targetData, (targetRows, targetCols)),
                                      shape=targetShape)

        return nimble.data.Sparse(ret, pointNames=pointNames,
                                  featureNames=featureNames, reuseData=True)

    def _unique_implementation(self):
        if self._base._sorted is None:
            self._base._sortInternal("feature")
        count = len(self)
        hasAxisNames = self._namesCreated()
        getAxisName = self._getName
        getAxisNames = self._getNames
        data = self._base.data.data
        row = self._base.data.row
        col = self._base.data.col
        if isinstance(self, Points):
            axisLocator = row
            offAxisLocator = col
            hasOffAxisNames = self._base._featureNamesCreated()
            getOffAxisNames = self._base.features.getNames
        else:
            axisLocator = col
            offAxisLocator = row
            hasOffAxisNames = self._base._pointNamesCreated()
            getOffAxisNames = self._base.points.getNames

        unique = set()
        uniqueData = []
        uniqueAxis = []
        uniqueOffAxis = []
        keepNames = []
        axisCount = 0
        for i in range(count):
            axisLoc = axisLocator == i
            # data values can look the same but have zeros in different places;
            # zip with offAxis to ensure the locations are the same as well
            key = tuple(zip(data[axisLoc], offAxisLocator[axisLoc]))
            if key not in unique:
                unique.add(key)
                uniqueData.extend(data[axisLoc])
                uniqueAxis.extend([axisCount for _ in range(sum(axisLoc))])
                uniqueOffAxis.extend(offAxisLocator[axisLoc])
                if hasAxisNames:
                    keepNames.append(getAxisName(i))
                axisCount += 1

        if hasAxisNames and keepNames == getAxisNames():
            return self._base.copy()

        axisNames = False
        offAxisNames = False
        if len(keepNames) > 0:
            axisNames = keepNames
        if hasOffAxisNames:
            offAxisNames = getOffAxisNames()
        self._base._sorted = None

        uniqueData = numpy.array(uniqueData, dtype=numpy.object_)
        if isinstance(self, Points):
            shape = (axisCount, len(self._base.features))
            uniqueCoo = scipy.sparse.coo_matrix(
                (uniqueData, (uniqueAxis, uniqueOffAxis)), shape=shape)
            return nimble.createData('Sparse', uniqueCoo, pointNames=axisNames,
                                     featureNames=offAxisNames, useLog=False)
        else:
            shape = (len(self._base.points), axisCount)
            uniqueCoo = scipy.sparse.coo_matrix(
                (uniqueData, (uniqueOffAxis, uniqueAxis)), shape=shape)
            return nimble.createData('Sparse', uniqueCoo, pointNames=offAxisNames,
                                     featureNames=axisNames, useLog=False)

    ####################
    # Abstract Methods #
    ####################

    # @abstractmethod
    # def _flattenToOne_implementation(self):
    #     pass
    #
    # @abstractmethod
    # def _unflattenFromOne_implementation(self, divideInto):
    #     pass

###################
# Generic Helpers #
###################

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

    return ((selfRowShape, selfColShape), (extRowShape, extColShape))

class nzIt(object):
    """
    Non-zero iterator to return when iterating through points or
    features. The iteration axis is dependent on how the internal data
    is sorted before instantiation.
    """
    def __init__(self, source):
        self._source = source
        self._index = 0

    def __iter__(self):
        return self

    def next(self):
        """
        Get next non zero value.
        """
        while self._index < len(self._source.data.data):
            value = self._source.data.data[self._index]

            self._index += 1
            if value != 0:
                return value

        raise StopIteration

    def __next__(self):
        return self.next()
