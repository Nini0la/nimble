"""
Implementations and helpers specific to performing axis-generic
operations on a UML DataFrame object.
"""
from __future__ import absolute_import
from abc import abstractmethod

import numpy

import UML
from UML.exceptions import ArgumentException
from .axis import Axis
from .base import cmp_to_key

class DataFrameAxis(Axis):
    """
    Differentiate how DataFrame methods act dependent on the axis.

    Also provides abstract methods which will be required to perform
    axis-specific operations.

    Parameters
    ----------
    axis : str
        The axis ('point' or 'feature') which the function will be
        applied to.
    source : UML data object
        The object containing point and feature data.
    """
    def __init__(self, axis, source, **kwds):
        self.axis = axis
        self.source = source
        kwds['axis'] = self.axis
        kwds['source'] = self.source
        super(DataFrameAxis, self).__init__(**kwds)

    def _setName_implementation(self, oldIdentifier, newName):
        super(DataFrameAxis, self)._setName_implementation(oldIdentifier,
                                                           newName)
        #update the index or columns in self.data
        self._updateName()

    def _setNamesFromList(self, assignments, count):
        super(DataFrameAxis, self)._setNamesFromList(assignments, count)
        self._updateName()

    def _setNamesFromDict(self, assignments, count):
        super(DataFrameAxis, self)._setNamesFromDict(assignments, count)
        self._updateName()

    def _updateName(self):
        """
        update self.data.index or self.data.columns
        """
        if self.axis == 'point':
            self.source.data.index = range(len(self.source.data.index))
        else:
            self.source.data.columns = range(len(self.source.data.columns))

    ##############################
    # Structural implementations #
    ##############################

    def _structuralBackend_implementation(self, structure, targetList):
        """
        Backend for points/features.extract points/features.delete,
        points/features.retain, and points/features.copy. Returns a new
        object containing only the members in targetList and performs
        some modifications to the original object if necessary. This
        function does not perform all of the modification or process how
        each function handles the returned value, these are managed
        separately by each frontend function.
        """
        df = self.source.data

        if self.axis == 'point':
            ret = df.iloc[targetList, :]
            axis = 0
            name = 'pointNames'
            nameList = [self.source.points.getName(i) for i in targetList]
            otherName = 'featureNames'
            otherNameList = self.source.features.getNames()
        elif self.axis == 'feature':
            ret = df.iloc[:, targetList]
            axis = 1
            name = 'featureNames'
            nameList = [self.source.features.getName(i) for i in targetList]
            otherName = 'pointNames'
            otherNameList = self.source.points.getNames()

        if structure.lower() != "copy":
            df.drop(targetList, axis=axis, inplace=True)

        if axis == 0:
            df.index = numpy.arange(len(df.index), dtype=df.index.dtype)
        else:
            df.columns = numpy.arange(len(df.columns), dtype=df.columns.dtype)

        return UML.data.DataFrame(ret, **{name: nameList,
                                          otherName: otherNameList})

    def _sort_implementation(self, sortBy, sortHelper):
        if self.axis == 'point':
            test = self.source.pointView(0)
            viewIter = self.source.points
            indexGetter = self.source.points.getIndex
            nameGetter = self.source.points.getName
            names = self.source.points.getNames()
        else:
            test = self.source.featureView(0)
            viewIter = self.source.features
            indexGetter = self.source.features.getIndex
            nameGetter = self.source.features.getName
            names = self.source.features.getNames()

        if isinstance(sortHelper, list):
            if self.axis == 'point':
                self.source.data = self.source.data.iloc[sortHelper, :]
            else:
                self.source.data = self.source.data.iloc[:, sortHelper]
            newNameOrder = [names[idx] for idx in sortHelper]
            return newNameOrder

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
            msg = "sortHelper is neither a scorer or a comparator"
            raise ArgumentException(msg)

        if comparator is not None:
            # make array of views
            viewArray = []
            for v in viewIter:
                viewArray.append(v)

            viewArray.sort(key=cmp_to_key(comparator))
            indexPosition = []
            for i in range(len(viewArray)):
                viewAxis = getattr(viewArray[i], self.axis + 's')
                index = indexGetter(getattr(viewAxis, 'getName')(0))
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

        # use numpy indexing to change the ordering
        if self.axis == 'point':
            self.source.data = self.source.data.iloc[indexPosition, :]
        else:
            self.source.data = self.source.data.iloc[:, indexPosition]

        # convert indices of their previous location into their feature names
        newNameOrder = []
        for i in range(len(indexPosition)):
            oldIndex = indexPosition[i]
            newName = nameGetter(oldIndex)
            newNameOrder.append(newName)
        return newNameOrder

    ####################
    # Abstract Methods #
    ####################

    @abstractmethod
    def _add_implementation(self, toAdd, insertBefore):
        pass

    @abstractmethod
    def _flattenToOne_implementation(self):
        pass

    @abstractmethod
    def _unflattenFromOne_implementation(self, divideInto):
        pass

    @abstractmethod
    def _transform_implementation(self, function, limitTo):
        pass
