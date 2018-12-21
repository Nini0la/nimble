"""
Method implementations and helpers acting specifically on each element
Matrix object.
"""
from __future__ import absolute_import
import itertools

import numpy

import UML
from .elements import Elements

class MatrixElements(Elements):
    """
    Matrix method implementations performed on each element.

    Parameters
    ----------
    source : UML data object
        The object containing features data.
    """
    def __init__(self, source, **kwds):
        self.source = source
        kwds['source'] = source
        super(MatrixElements, self).__init__(**kwds)

    ##############################
    # Structural implementations #
    ##############################

    def _transform_implementation(self, toTransform, points, features,
                                  preserveZeros, skipNoneReturnValues):
        oneArg = False
        try:
            toTransform(0, 0, 0)
        except TypeError:
            if isinstance(toTransform, dict):
                oneArg = None
            else:
                oneArg = True

        IDs = itertools.product(range(len(self.source.points)),
                                range(len(self.source.features)))
        for (i, j) in IDs:
            currVal = self.source.data[i, j]

            if points is not None and i not in points:
                continue
            if features is not None and j not in features:
                continue
            if preserveZeros and currVal == 0:
                continue

            if oneArg is None:
                if currVal in toTransform.keys():
                    currRet = toTransform[currVal]
                else:
                    continue
            elif oneArg:
                currRet = toTransform(currVal)
            else:
                currRet = toTransform(currVal, i, j)

            if skipNoneReturnValues and currRet is None:
                continue

            self.source.data[i, j] = currRet

    ################################
    # Higher Order implementations #
    ################################

    def _calculate_implementation(self, function, points, features,
                                  preserveZeros, outputType):
        return self._calculate_genericVectorized(
            function, points, features, outputType)

    #############################
    # Numerical implementations #
    #############################

    def _multiply_implementation(self, other):
        """
        Perform element wise multiplication of this UML data object
        against the provided other UML data object. Both objects must
        contain only numeric data. The pointCount and featureCount of
        both objects must be equal. The types of the two objects may be
        different, but the returned object will be the inplace
        modification of the calling object.
        """
        if isinstance(other, UML.data.Sparse):
            result = other.data.multiply(self.source.data)
            if hasattr(result, 'todense'):
                result = result.todense()
            self.source.data = numpy.matrix(result)
        else:
            self.source.data = numpy.multiply(self.source.data, other.data)
