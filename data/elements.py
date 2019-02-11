"""
Methods and helpers responsible for determining how each function
will operate over each element.
"""
from __future__ import absolute_import
from abc import abstractmethod

import numpy
import six

import UML
from UML.exceptions import ArgumentException, ImproperActionException
from UML.logger import enableLogging
from . import dataHelpers
from .dataHelpers import valuesToPythonList
from .dataHelpers import logCaptureFactory

logCapture = logCaptureFactory('elements')

class Elements(object):
    """
    Differentiate how methods act on each element.

    Also includes abstract methods which will be required to perform
    data-type specific operations.

    Parameters
    ----------
    source : UML data object
        The object containing the elements.
    kwds
        Included due to best practices so args may automatically be
        passed further up into the hierarchy if needed.
    """
    def __init__(self, source, **kwds):
        self._source = source
        self._ptPosition = 0
        self._ftPosition = 0
        super(Elements, self).__init__(**kwds)

    def __iter__(self):
        return self

    def next(self):
        """
        Get next item
        """
        while self._ptPosition < len(self._source.points):
            while self._ftPosition < len(self._source.features):
                value = self._source[self._ptPosition, self._ftPosition]
                self._ftPosition += 1
                return value
            self._ptPosition += 1
            self._ftPosition = 0
        raise StopIteration

    def __next__(self):
        return self.next()

    #########################
    # Structural Operations #
    #########################

    def transform(self, toTransform, points=None, features=None,
                  preserveZeros=False, skipNoneReturnValues=False,
                  useLog=None):
        """
        Modify each element using a function or mapping.

        Perform an inplace modification of the elements or subset of
        elements in this object.

        Parameters
        ----------
        toTransform : function, dict
            * function - in the form of toTransform(elementValue)
              or toTransform(elementValue, pointNum, featureNum)
            * dictionary -  map the current element [key] to the
              transformed element [value].
        points : identifier, list of identifiers
            May be a single point name or index, an iterable,
            container of point names and/or indices. None indicates
            application to all points.
        features : identifier, list of identifiers
            May be a single feature name or index, an iterable,
            container of feature names and/or indices. None indicates
            application to all features.
        preserveZeros : bool
            If True it does not apply toTransform to elements in the
            data that are 0, and that 0 is not modified.
        skipNoneReturnValues : bool
            If True, any time toTransform() returns None, the value
            originally in the data will remain unmodified.

        See Also
        --------
        points.transform, features.transform

        Examples
        --------
        TODO
        """
        if enableLogging(useLog):
            wrapped = logCapture(self.transform)
            return wrapped(toTransform, points, features, preserveZeros,
                           skipNoneReturnValues, useLog=False)

        if points is not None:
            points = self._source._constructIndicesList('point', points)
        if features is not None:
            features = self._source._constructIndicesList('feature', features)

        self._transform_implementation(toTransform, points, features,
                                       preserveZeros, skipNoneReturnValues)

        self._source.validate()

    ###########################
    # Higher Order Operations #
    ###########################

    def calculate(self, function, points=None, features=None,
                  preserveZeros=False, skipNoneReturnValues=False,
                  outputType=None, useLog=None):
        """
        Return a new object with a calculation applied to each element.

        Calculates the results of the given function on the specified
        elements in this object, with output values collected into a new
        object that is returned upon completion.

        Parameters
        ----------
        function : function
            Take a value as input and return the desired value.
        points : point, list of points
            The subset of points to limit the calculation to. If None,
            the calculation will apply to all points.
        features : feature, list of features
            The subset of features to limit the calculation to. If None,
            the calculation will apply to all features.
        preserveZeros : bool
            Bypass calculation on zero values
        skipNoneReturnValues : bool
            Bypass values when ``function`` returns None. If False, the
            value None will replace the value if None is returned.
        outputType: UML data type
            Return an object of the specified type. If None, the
            returned object will have the same type as the calling
            object.

        Returns
        -------
        UML object

        See also
        --------
        transform : calculate inplace

        Examples
        --------
        TODO
        """
        if enableLogging(useLog):
            wrapped = logCapture(self.calculate)
            return wrapped(function, points, features, preserveZeros,
                           skipNoneReturnValues, useLog=False)

        oneArg = False
        try:
            function(0, 0, 0)
        except TypeError:
            oneArg = True

        if points is not None:
            points = self._source._constructIndicesList('point', points)
        if features is not None:
            features = self._source._constructIndicesList('feature', features)

        if outputType is not None:
            optType = outputType
        else:
            optType = self._source.getTypeString()

        # Use vectorized for functions with oneArg
        if oneArg:
            if not preserveZeros:
                # check if the function preserves zero values
                try:
                    preserveZeros = function(0) == 0
                except Exception:
                    preserveZeros = False
            def functionWrap(value):
                if preserveZeros and value == 0:
                    return 0
                currRet = function(value)
                if skipNoneReturnValues and currRet is None:
                    return value

                return currRet

            vectorized = numpy.vectorize(functionWrap)
            ret = self._calculate_implementation(vectorized, points, features,
                                                 preserveZeros, optType)

        else:
            # if unable to vectorize, iterate over each point
            if not points:
                points = list(range(len(self._source.points)))
            if not features:
                features = list(range(len(self._source.features)))
            valueArray = numpy.empty([len(points), len(features)])
            p = 0
            for pi in points:
                f = 0
                for fj in features:
                    value = self._source[pi, fj]
                    if preserveZeros and value == 0:
                        valueArray[p, f] = 0
                    else:
                        if oneArg:
                            currRet = function(value)
                        else:
                            currRet = function(value, pi, fj)
                        if skipNoneReturnValues and currRet is None:
                            valueArray[p, f] = value
                        else:
                            valueArray[p, f] = currRet
                    f += 1
                p += 1

            ret = UML.createData(optType, valueArray, useLog=False)

        ret._absPath = self._source.absolutePath
        ret._relPath = self._source.relativePath

        self._source.validate()

        return ret

    def count(self, condition):
        """
        The number of values which satisfy the condition.

        Parameters
        ----------
        condition : function
            function - may take two forms:
            a) a function that accepts an element value as input and
            will return True if it is to be counted
            b) a filter function, as a string, containing a comparison
            operator and a value

        Returns
        -------
        int

        See Also
        --------
        points.count, features.count

        Examples
        --------
        TODO
        """
        if callable(condition):
            ret = self.calculate(function=condition, outputType='Matrix')
        elif isinstance(condition, six.string_types):
            func = lambda x: eval('x'+condition)
            ret = self.calculate(function=func, outputType='Matrix')
        else:
            msg = 'function can only be a function or str, not else'
            raise ArgumentException(msg)
        return int(numpy.sum(ret.data))

    def countUnique(self, points=None, features=None):
        """
        Count of each unique value in the data.

        Parameters
        ----------
        points : identifier, list of identifiers
            May be None indicating application to all points, a single
            name or index or an iterable of points and/or indices.
        features : identifier, list of identifiers
            May be None indicating application to all features, a single
            name or index or an iterable of names and/or indices.

        Returns
        -------
        dict
            Each unique value as keys and the number of times that
            value occurs as values.

        See Also
        --------
        calculate.uniqueCount

        Examples
        --------
        TODO
        """
        uniqueCount = {}
        if points is None:
            points = [i for i in range(len(self._source.points))]
        if features is None:
            features = [i for i in range(len(self._source.features))]
        points = valuesToPythonList(points, 'points')
        features = valuesToPythonList(features, 'features')
        for i in points:
            for j in features:
                val = self._source[i, j]
                temp = uniqueCount.get(val, 0)
                uniqueCount[val] = temp + 1

        return uniqueCount

    ########################
    # Numerical Operations #
    ########################

    def multiply(self, other, useLog=None):
        """
        Multiply objects element-wise.

        Perform element-wise multiplication of this UML data object
        against the provided ``other`` UML data object, with the result
        being stored in-place in the calling object. Both objects must
        contain only numeric data. The pointCount and featureCount of
        both objects must be equal. The types of the two objects may be
        different.

        Parameters
        ----------
        other : UML object
            The object containing the elements to multiply with the
            elements in this object.

        Examples
        --------
        TODO
        """
        if enableLogging(useLog):
            wrapped = logCapture(self.multiply)
            return wrapped(other, useLog=False)

        if not isinstance(other, UML.data.Base):
            msg = "'other' must be an instance of a UML data object"
            raise ArgumentException(msg)

        if len(self._source.points) != len(other.points):
            msg = "The number of points in each object must be equal."
            raise ArgumentException(msg)
        if len(self._source.features) != len(other.features):
            msg = "The number of features in each object must be equal."
            raise ArgumentException(msg)

        if len(self._source.points) == 0 or len(self._source.features) == 0:
            msg = "Cannot do elements.multiply with empty points or features"
            raise ImproperActionException(msg)

        self._source._validateEqualNames('point', 'point',
                                         'elements.multiply', other)
        self._source._validateEqualNames('feature', 'feature',
                                         'elements.multiply', other)

        try:
            self._multiply_implementation(other)
        except Exception as e:
            #TODO: improve how the exception is catch
            self._source._numericValidation()
            other._numericValidation()
            raise e

        retNames = dataHelpers.mergeNonDefaultNames(self._source, other)
        retPNames = retNames[0]
        retFNames = retNames[1]
        self._source.points.setNames(retPNames)
        self._source.features.setNames(retFNames)
        self._source.validate()

    def power(self, other, useLog=None):
        """
        Raise the elements of this object to a power.

        The power to raise each element to can be either a UML object or
        a single numerical value. If ``other`` is an object, both must
        contain only numeric data. The pointCount and featureCount of
        both objects must be equal. The types of the two objects may be
        different.

        Parameters
        ----------
        other : numerical value, UML object
            * numerical value - the power to raise each element to
            * The object containing the elements to raise the elements
              in this object to

        Examples
        --------
        TODO
        """
        if enableLogging(useLog):
            wrapped = logCapture(self.power)
            return wrapped(other, useLog=False)

        # other is UML or single numerical value
        singleValue = dataHelpers._looksNumeric(other)
        if not singleValue and not isinstance(other, UML.data.Base):
            msg = "'other' must be an instance of a UML data object "
            msg += "or a single numeric value"
            raise ArgumentException(msg)

        if isinstance(other, UML.data.Base):
            # same shape
            if len(self._source.points) != len(other.points):
                msg = "The number of points in each object must be equal."
                raise ArgumentException(msg)
            if len(self._source.features) != len(other.features):
                msg = "The number of features in each object must be equal."
                raise ArgumentException(msg)

        if len(self._source.points) == 0 or len(self._source.features) == 0:
            msg = "Cannot do elements.power when points or features is emtpy"
            raise ImproperActionException(msg)

        if isinstance(other, UML.data.Base):
            def powFromRight(val, pnum, fnum):
                try:
                    return val ** other[pnum, fnum]
                except Exception as e:
                    self._source._numericValidation()
                    other._numericValidation()
                    raise e
            self._source.elements.transform(powFromRight)
        else:
            def powFromRight(val, pnum, fnum):
                try:
                    return val ** other
                except Exception as e:
                    self._source._numericValidation()
                    other._numericValidation()
                    raise e
            self._source.elements.transform(powFromRight)

        self._source.validate()

    ########################
    # Higher Order Helpers #
    ########################

    def _calculate_genericVectorized(
            self, function, points, features, outputType):
        # need points/features as arrays for indexing
        if points:
            points = numpy.array(points)
        else:
            points = numpy.array(range(len(self._source.points)))
        if features:
            features = numpy.array(features)
        else:
            features = numpy.array(range(len(self._source.features)))
        toCalculate = self._source.copyAs('numpyarray')
        # array with only desired points and features
        toCalculate = toCalculate[points[:, None], features]
        try:
            values = function(toCalculate)
            # check if values has numeric dtype
            if numpy.issubdtype(values.dtype, numpy.number):
                return UML.createData(outputType, values, useLog=False)

            return UML.createData(outputType, values,
                                  elementType=numpy.object_, useLog=False)
        except Exception:
            # change output type of vectorized function to object to handle
            # nonnumeric data
            function.otypes = [numpy.object_]
            values = function(toCalculate)
            return UML.createData(outputType, values,
                                  elementType=numpy.object_, useLog=False)

    #####################
    # Abstract Methods  #
    #####################

    @abstractmethod
    def _calculate_implementation(self, function, points, features,
                                  preserveZeros, outputType):
        pass

    @abstractmethod
    def _multiply_implementation(self, other):
        pass

    @abstractmethod
    def _transform_implementation(self, toTransform, points, features,
                                  preserveZeros, skipNoneReturnValues):
        pass