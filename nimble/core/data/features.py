"""
Define methods of the features attribute for Base objects.

All user-facing, feature axis functions are contained here. Functions
specific to only the feature axis will provide their functionality here.
However, most functions are applicable to either axis so only the
signatures and docstrings specific to the features axis are provided
here. The functionality of axis generic methods are defined in axis.py,
with a leading underscore added to the method name. Additionally, the
wrapping of function calls for the logger takes place in here.
"""

from abc import ABC, abstractmethod
from collections import Counter

import numpy as np

import nimble
from nimble.core.logger import handleLogging
from nimble.exceptions import InvalidArgumentType, InvalidArgumentValue
from nimble.exceptions import InvalidArgumentValueCombination
from nimble._utility import prettyListString
from ._dataHelpers import limitedTo2D

class Features(ABC):
    """
    Methods that apply to the features axis of a Base object.
    """
    def __init__(self, base):
        """
        Parameters
        ----------
        base : Base
            The Base instance that will be queried and modified.
        """
        self._base = base
        super().__init__()

    @limitedTo2D
    def __iter__(self):
        return self._iter()

    @limitedTo2D
    def __getitem__(self, key):
        return self._getitem(key)

    ########################
    # Low Level Operations #
    ########################

    def getName(self, index):
        """
        The name of the feature at the provided index.

        Parameters
        ----------
        index : int

        Returns
        -------
        str

        See Also
        --------
        getNames, setName, setNames

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.getName(1)
        'b'
        """
        return self._getName(index)

    def getNames(self):
        """
        The feature names ordered by index.

        Returns
        -------
        lst

        See Also
        --------
        getName, setName, setNames

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.getNames()
        ['a', 'b', 'c', 'd']
        """
        return self._getNames()

    def setName(self, oldIdentifier, newName, useLog=None):
        """
        Set or change a featureName.

        Set the name of the feature at ``oldIdentifier`` with the value
        of ``newName``.

        Parameters
        ----------
        oldIdentifier : str, int
            A string or integer, specifying either a current featureName
            or the index of a current featureName.
        newName : str
            May be either a string not currently in the featureName set,
            or None for an default featureName. newName cannot begin
            with the default prefix.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        setNames

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.setName('b', 'new')
        >>> data.features.getNames()
        ['a', 'new', 'c', 'd']
        """
        self._setName(oldIdentifier, newName, useLog)

    def setNames(self, assignments, useLog=None):
        """
        Set or rename all of the feature names of this object.

        Set the feature names of this object according to the values
        specified by the ``assignments`` parameter. If assignments is
        None, then all feature names will be given new default values.

        Parameters
        ----------
        assignments : iterable, dict, None
            * iterable - Given a list-like container, the mapping
              between names and array indices will be used to define the
              feature names.
            * dict - The mapping for each feature name in the format
              {name:index}
            * None - remove names from this object
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        setName

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.setNames(['1', '2', '3', '4'])
        >>> data.features.getNames()
        ['1', '2', '3', '4']
        """
        self._setNames(assignments, useLog)

    def getIndex(self, identifier):
        """
        The index of a feature.

        Return the index location of the feature ``identifier``. The
        ``identifier`` can be a feature name or integer (including
        negative integers).

        Parameters
        ----------
        name : str
            The name of a feature.

        Returns
        -------
        int

        See Also
        --------
        getIndices

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.getIndex('c')
        2
        >>> data.features.getIndex(-1)
        3
        """
        return self._getIndex(identifier)

    def getIndices(self, names):
        """
        The indices of a list of feature names.

        Return a list of the the index locations of the provided feature
        ``names``.

        Parameters
        ----------
        names : list
            The names of features.

        Returns
        -------
        list

        See Also
        --------
        getIndex

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.getIndices(['c', 'a', 'd'])
        [2, 0, 3]
        """
        return self._getIndices(names)

    def hasName(self, name):
        """
        Determine if feature name exists.

        Parameters
        ----------
        names : str
            The name of a feature.

        Returns
        -------
        bool

        Examples
        --------
        >>> data = nimble.identity('Matrix', 4,
        ...                        featureNames=['a', 'b', 'c', 'd'])
        >>> data.features.hasName('a')
        True
        >>> data.features.hasName('e')
        False
        """
        return self._hasName(name)

    #########################
    # Structural Operations #
    #########################
    @limitedTo2D
    def copy(self, toCopy=None, start=None, end=None, number=None,
             randomize=False, useLog=None):
        """
        Return a copy of certain features of this object.

        A variety of methods for specifying the features to copy based
        on the provided parameters. If toCopy is not None, start and end
        must be None. If start or end is not None, toCopy must be None.

        Parameters
        ----------
        toCopy : identifier, list of identifiers, function, query
            * identifier - a name or index
            * list of identifiers - an iterable container of identifiers
            * function - accepts a feature as its only argument and
              returns a boolean value to indicate if the feature should
              be copied
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.
        start, end : identifier
            Parameters indicating range based copying. Begin the copying
            at the location of ``start``. Finish copying at the
            inclusive ``end`` location. If only one of start and end are
            non-None, the other default to 0 and the number of values in
            each feature, respectively.
        number : int
            The quantity of features that are to be copied, the default
            None means unrestricted copying. This can be provided on its
            own (toCopy, start and end are None) to the first ``number``
            of features, or in conjuction with toCopy or  start and end,
            to limit their output.
        randomize : bool
            Indicates whether random sampling is to be used in
            conjunction with the number parameter. If randomize is
            False, the chosen features are determined by feature order,
            otherwise it is uniform random across the space of possible
            features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Returns
        -------
        nimble Base object

        See Also
        --------
        Base.copy

        Examples
        --------
        >>> raw = [[1, 2, 3, 4],
        ...        [1, 2, 3, 4],
        ...        [1, 2, 3, 4],
        ...        [1, 2, 3, 4]]
        >>> data = nimble.data('Matrix', raw,
        ...                    pointNames=['a', 'b', 'c', 'd'],
        ...                    featureNames=['1', '2', '3', '4'])
        >>> single = data.features.copy('1')
        >>> single
        Matrix(
            [[1]
             [1]
             [1]
             [1]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'1':0}
            )
        >>> multiple = data.features.copy(['1', 3])
        >>> multiple
        Matrix(
            [[1 4]
             [1 4]
             [1 4]
             [1 4]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'1':0, '4':1}
            )
        >>> func = data.features.copy(lambda ft: sum(ft) < 10)
        >>> func
        Matrix(
            [[1 2]
             [1 2]
             [1 2]
             [1 2]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'1':0, '2':1}
            )
        >>> strFunc = data.features.copy("a >= 3")
        >>> strFunc
        Matrix(
            [[3 4]
             [3 4]
             [3 4]
             [3 4]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'3':0, '4':1}
            )
        >>> startEnd = data.features.copy(start=1, end=2)
        >>> startEnd
        Matrix(
            [[2 3]
             [2 3]
             [2 3]
             [2 3]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'2':0, '3':1}
            )
        >>> numberNoRandom = data.features.copy(number=2)
        >>> numberNoRandom
        Matrix(
            [[1 2]
             [1 2]
             [1 2]
             [1 2]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'1':0, '2':1}
            )
        >>> nimble.random.setSeed(42)
        >>> numberRandom = data.features.copy(number=2, randomize=True)
        >>> numberRandom
        Matrix(
            [[1 4]
             [1 4]
             [1 4]
             [1 4]]
            pointNames={'a':0, 'b':1, 'c':2, 'd':3}
            featureNames={'1':0, '4':1}
            )
        """
        return self._copy(toCopy, start, end, number, randomize, useLog)

    @limitedTo2D
    def extract(self, toExtract=None, start=None, end=None, number=None,
                randomize=False, useLog=None):
        """
        Move certain features of this object into their own object.

        A variety of methods for specifying the features to extract
        based on the provided parameters. If toExtract is not None,
        start and end must be None. If start or end is not None,
        toExtract must be None.

        Parameters
        ----------
        toExtract : identifier, list of identifiers, function, query
            * identifier - a name or index
            * list of identifiers - an iterable container of identifiers
            * function - accepts a feature as its only argument and
              returns a boolean value to indicate if the feature should
              be extracted
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.
        start, end : identifier
            Parameters indicating range based extraction. Begin the
            extraction at the location of ``start``. Finish extracting
            at the inclusive ``end`` location. If only one of start and
            end are non-None, the other default to 0 and the number of
            values in each feature, respectively.
        number : int
            The quantity of features that are to be extracted, the
            default None means unrestricted extraction. This can be
            provided on its own (toExtract, start and end are None) to
            the first ``number`` of features, or in conjuction with
            toExtract or  start and end, to limit their output.
        randomize : bool
            Indicates whether random sampling is to be used in
            conjunction with the number parameter. If randomize is
            False, the chosen features are determined by feature order,
            otherwise it is uniform random across the space of possible
            features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Returns
        -------
        nimble Base object

        See Also
        --------
        retain, delete

        Examples
        --------
        Extract a single feature.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> single = data.features.extract('a')
        >>> single
        List(
            [[1.000]
             [0.000]
             [0.000]]
            featureNames={'a':0}
            )
        >>> data
        List(
            [[0.000 0.000]
             [1.000 0.000]
             [0.000 1.000]]
            featureNames={'b':0, 'c':1}
            )

        Extract multiple features.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> multiple = data.features.extract(['a', 2])
        >>> multiple
        List(
            [[1.000 0.000]
             [0.000 0.000]
             [0.000 1.000]]
            featureNames={'a':0, 'c':1}
            )
        >>> data
        List(
            [[0.000]
             [1.000]
             [0.000]]
            featureNames={'b':0}
            )

        Extract feature when the function returns True.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> func = data.features.extract(lambda ft: ft[2] == 1)
        >>> func
        List(
            [[0.000]
             [0.000]
             [1.000]]
            featureNames={'c':0}
            )
        >>> data
        List(
            [[1.000 0.000]
             [0.000 1.000]
             [0.000 0.000]]
            featureNames={'a':0, 'b':1}
            )

        Extract feature when the query string returns True.

        >>> data = nimble.identity('List', 3,
        ...                        featureNames=['a', 'b', 'c'],
        ...                        pointNames=['p1', 'p2', 'p3'])
        >>> strFunc = data.features.extract("p2 != 0")
        >>> strFunc
        List(
            [[0.000]
             [1.000]
             [0.000]]
            pointNames={'p1':0, 'p2':1, 'p3':2}
            featureNames={'b':0}
            )
        >>> data
        List(
            [[1.000 0.000]
             [0.000 0.000]
             [0.000 1.000]]
            pointNames={'p1':0, 'p2':1, 'p3':2}
            featureNames={'a':0, 'c':1}
            )

        Extract features from the inclusive start to the inclusive end.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> startEnd = data.features.extract(start=1, end=2)
        >>> startEnd
        List(
            [[0.000 0.000]
             [1.000 0.000]
             [0.000 1.000]]
            featureNames={'b':0, 'c':1}
            )
        >>> data
        List(
            [[1.000]
             [0.000]
             [0.000]]
            featureNames={'a':0}
            )

        Select a set number to extract, starting from the first feature.

        >>> nimble.random.setSeed(42)
        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> numberNoRandom = data.features.extract(number=2)
        >>> numberNoRandom
        List(
            [[1.000 0.000]
             [0.000 1.000]
             [0.000 0.000]]
            featureNames={'a':0, 'b':1}
            )
        >>> data
        List(
            [[0.000]
             [0.000]
             [1.000]]
            featureNames={'c':0}
            )

        Select a set number to extract, choosing features at random.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> numberRandom = data.features.extract(number=2,
        ...                                      randomize=True)
        >>> numberRandom
        List(
            [[0.000 1.000]
             [0.000 0.000]
             [1.000 0.000]]
            featureNames={'c':0, 'a':1}
            )
        >>> data
        List(
            [[0.000]
             [1.000]
             [0.000]]
            featureNames={'b':0}
            )
        """
        return self._extract(toExtract, start, end, number, randomize, useLog)

    @limitedTo2D
    def delete(self, toDelete=None, start=None, end=None, number=None,
               randomize=False, useLog=None):
        """
        Remove certain features from this object.

        A variety of methods for specifying features to delete based on
        the provided parameters. If toDelete is not None, start and end
        must be None. If start or end is not None, toDelete must be
        None.

        Parameters
        ----------
        toDelete : identifier, list of identifiers, function, query
            * identifier - a name or index
            * list of identifiers - an iterable container of identifiers
            * function - accepts a feature as its only argument and
              returns a boolean value to indicate if the feature should
              be deleted
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.
        start, end : identifier
            Parameters indicating range based deletion. Begin the
            deletion at the location of ``start``. Finish deleting at
            the inclusive ``end`` location. If only one of start and
            end are non-None, the other default to 0 and the number of
            values in each feature, respectively.
        number : int
            The quantity of features that are to be deleted, the
            default None means unrestricted deletion. This can be
            provided on its own (toDelete, start and end are None) to
            the first ``number`` of features, or in conjuction with
            toDelete or  start and end, to limit their output.
        randomize : bool
            Indicates whether random sampling is to be used in
            conjunction with the number parameter. If randomize is
            False, the chosen features are determined by feature order,
            otherwise it is uniform random across the space of possible
            features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        extract, retain

        Examples
        --------
        Delete a single feature.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete('a')
        >>> data
        List(
            [[0.000 0.000]
             [1.000 0.000]
             [0.000 1.000]]
            featureNames={'b':0, 'c':1}
            )

        Delete multiple features.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete(['a', 2])
        >>> data
        List(
            [[0.000]
             [1.000]
             [0.000]]
            featureNames={'b':0}
            )

        Delete feature when the function returns True.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete(lambda ft: ft[2] == 1)
        >>> data
        List(
            [[1.000 0.000]
             [0.000 1.000]
             [0.000 0.000]]
            featureNames={'a':0, 'b':1}
            )

        Delete feature when the query string returns True.

        >>> data = nimble.identity('List', 3,
        ...                        featureNames=['a', 'b', 'c'],
        ...                        pointNames=['p1', 'p2', 'p3'])
        >>> data.features.delete("p2 != 0")
        >>> data
        List(
            [[1.000 0.000]
             [0.000 0.000]
             [0.000 1.000]]
            pointNames={'p1':0, 'p2':1, 'p3':2}
            featureNames={'a':0, 'c':1}
            )

        Delete features from the inclusive start to the inclusive end.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete(start=1, end=2)
        >>> data
        List(
            [[1.000]
             [0.000]
             [0.000]]
            featureNames={'a':0}
            )

        Select a set number to delete, starting from the first feature.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete(number=2)
        >>> data
        List(
            [[0.000]
             [0.000]
             [1.000]]
            featureNames={'c':0}
            )

        Select a set number to delete, choosing features at random.

        >>> nimble.random.setSeed(42)
        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.delete(number=2,  randomize=True)
        >>> data
        List(
            [[0.000]
             [1.000]
             [0.000]]
            featureNames={'b':0}
            )
        """
        self._delete(toDelete, start, end, number, randomize, useLog)

    @limitedTo2D
    def retain(self, toRetain=None, start=None, end=None, number=None,
               randomize=False, useLog=None):
        """
        Keep only certain features of this object.

        A variety of methods for specifying features to delete based on
        the provided parameters. If toRetain is not None, start and end
        must be None. If start or end is not None, toRetain must be
        None.

        Parameters
        ----------
        toRetain : identifier, list of identifiers, function, query
            * identifier - a name or index
            * list of identifiers - an iterable container of identifiers
            * function - accepts a feature as its only argument and
              returns a boolean value to indicate if the feature should
              be retained
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.
        start, end : identifier
            Parameters indicating range based retention. Begin the
            retention at the location of ``start``. Finish retaining at
            the inclusive ``end`` location. If only one of start and
            end are non-None, the other default to 0 and the number of
            values in each feature, respectively.
        number : int
            The quantity of features that are to be retained, the
            default None means unrestricted retained. This can be
            provided on its own (toRetain, start and end are None) to
            the first ``number`` of features, or in conjuction with
            toRetain or  start and end, to limit their output.
        randomize : bool
            Indicates whether random sampling is to be used in
            conjunction with the number parameter. If randomize is
            False, the chosen features are determined by feature order,
            otherwise it is uniform random across the space of possible
            features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        extract, delete

        Examples
        --------
        Retain a single feature.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain('a')
        >>> data
        List(
            [[1.000]
             [0.000]
             [0.000]]
            featureNames={'a':0}
            )

        Retain multiple features.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain(['a', 2])
        >>> data
        List(
            [[1.000 0.000]
             [0.000 0.000]
             [0.000 1.000]]
            featureNames={'a':0, 'c':1}
            )

        Retain feature when the function returns True.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain(lambda ft: ft[2] == 1)
        >>> data
        List(
            [[0.000]
             [0.000]
             [1.000]]
            featureNames={'c':0}
            )

        Retain feature when the query string returns True.

        >>> data = nimble.identity('List', 3,
        ...                        featureNames=['a', 'b', 'c'],
        ...                        pointNames=['p1', 'p2', 'p3'])
        >>> data.features.retain("p2 != 0")
        >>> data
        List(
            [[0.000]
             [1.000]
             [0.000]]
            pointNames={'p1':0, 'p2':1, 'p3':2}
            featureNames={'b':0}
            )

        Retain features from the inclusive start to the inclusive end.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain(start=1, end=2)
        >>> data
        List(
            [[0.000 0.000]
             [1.000 0.000]
             [0.000 1.000]]
            featureNames={'b':0, 'c':1}
            )

        Select a set number to retain, starting from the first feature.

        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain(number=2)
        >>> data
        List(
            [[1.000 0.000]
             [0.000 1.000]
             [0.000 0.000]]
            featureNames={'a':0, 'b':1}
            )

        Select a set number to retain, choosing features at random.

        >>> nimble.random.setSeed(42)
        >>> data = nimble.identity('List', 3)
        >>> data.features.setNames(['a', 'b', 'c'])
        >>> data.features.retain(number=2, randomize=True)
        >>> data
        List(
            [[0.000 1.000]
             [0.000 0.000]
             [1.000 0.000]]
            featureNames={'c':0, 'a':1}
            )
        """
        self._retain(toRetain, start, end, number, randomize, useLog)

    @limitedTo2D
    def count(self, condition):
        """
        The number of features which satisfy the condition.

        Parameters
        ----------
        condition : function, query
            * function - accepts a feature as its only argument and
              returns a boolean value to indicate if the feature should
              be counted
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.

        Returns
        -------
        int

        See Also
        --------
        Base.countElements, Base.countUniqueElements

        Examples
        --------
        Count using a python function.

        >>> def sumIsOne(ft):
        ...     return sum(ft) == 1
        >>> data = nimble.identity('Matrix', 3)
        >>> data.features.count(sumIsOne)
        3

        Count when the query string returns True.

        >>> data = nimble.identity('Matrix', 3,
        ...                        pointNames=['pt1', 'pt2', 'pt3'])
        >>> data.features.count("pt1 == 0")
        2
        """
        return self._count(condition)

    @limitedTo2D
    def sort(self, by=None, reverse=False, useLog=None):
        """
        Arrange the features in this object.

        This sort is stable, meaning the initial feature order is
        retained for features that evaluate as equal.

        Parameters
        ----------
        by : identifier(s), function, None
            Based on the parameter type:

            * identifier(s) - a single point index or name or a list
              of point indices and/or names. For lists, sorting occurs
              according to the first index with ties being broken in the
              order of the subsequent indices. Sort follows the natural
              ordering of the values in the identifier(s).
            * function - a scorer or comparator function. Must take
              either one or two positional arguments accepting feature
              views.
            * None - sort by the feature names.
        reverse : bool
            Reverse the sorted order.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Examples
        --------
        Sort by feature names.

        >>> raw = [[64, 67, 64],
        ...        [68, 71, 66],
        ...        [73, 71, 70],
        ...        [45, 40, 51]]
        >>> fts = ['Denver', 'Boulder', 'Fort Collins']
        >>> highTemps = nimble.data('Matrix', raw, featureNames=fts)
        >>> highTemps.features.sort()
        >>> highTemps
        Matrix(
            [[67 64 64]
             [71 68 66]
             [71 73 70]
             [40 45 51]]
            featureNames={'Boulder':0, 'Denver':1, 'Fort Col...':2}
            )

        Sort by points.

        >>> raw = [[3, 1, 2, 0, 2],
        ...        [100, 1, 10, 0, 11],
        ...        [200, 2, 20, 0, 21],
        ...        [300, 3, 30, 0, 31]]
        >>> orders = nimble.data('Matrix', raw)
        >>> orders.features.sort(0)
        >>> orders
        Matrix(
            [[0 1 2  2   3 ]
             [0 1 10 11 100]
             [0 2 20 21 200]
             [0 3 30 31 300]]
            )

        Sort using function.

        >>> raw = [[64, 67, 64],
        ...        [68, 71, 66],
        ...        [73, 71, 70],
        ...        [45, 40, 51]]
        >>> fts = ['Denver', 'Boulder', 'Fort Collins']
        >>> highTemps = nimble.data('Matrix', raw, featureNames=fts)
        >>> def averageHighTemp(ft):
        ...     return nimble.calculate.mean(ft)
        >>> highTemps.features.sort(averageHighTemp, reverse=True)
        >>> highTemps
        Matrix(
            [[64 64 67]
             [66 68 71]
             [70 73 71]
             [51 45 40]]
            featureNames={'Fort Col...':0, 'Denver':1, 'Boulder':2}
            )
        """
        self._sort(by, reverse, useLog)

    @limitedTo2D
    def transform(self, function, features=None, useLog=None):
        """
        Modify this object by applying a function to each feature.

        Perform an inplace modification of the data in this object
        through the application of the provided ``function`` to the
        features or subset of features in this object.

        Parameters
        ----------
        function
            Must accept the view of a feature as an argument.
        features : identifier, list of identifiers
            May be a single feature name or index, an iterable,
            container of feature names and/or indices. None indicates
            application to all features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        calculate

        Examples
        --------
        Transform all features; apply to all points.

        >>> data = nimble.ones('Matrix', 3, 5)
        >>> data.features.transform(lambda ft: ft + 2)
        >>> data
        Matrix(
            [[3.000 3.000 3.000 3.000 3.000]
             [3.000 3.000 3.000 3.000 3.000]
             [3.000 3.000 3.000 3.000 3.000]]
            )

        Transform all features; apply to certain points. Note that the
        function recieves a read-only view of each feature, so we need
        to make a copy in order to modify any specific data.

        >>> def transformMiddlePoint(ft):
        ...     ftList = ft.copy(to='python list', outputAs1D=True)
        ...     ftList[1] += 4
        ...     return ftList
        >>> data = nimble.ones('Matrix', 3, 5)
        >>> data.features.transform(transformMiddlePoint)
        >>> data
        Matrix(
            [[1.000 1.000 1.000 1.000 1.000]
             [5.000 5.000 5.000 5.000 5.000]
             [1.000 1.000 1.000 1.000 1.000]]
            )

        Transform a subset of features.

        >>> data = nimble.ones('Matrix', 3, 5)
        >>> data.features.transform(lambda ft: ft + 6, features=[1, 3])
        >>> data
        Matrix(
            [[1.000 7.000 1.000 7.000 1.000]
             [1.000 7.000 1.000 7.000 1.000]
             [1.000 7.000 1.000 7.000 1.000]]
            )
        """
        self._transform(function, features, useLog)

    ###########################
    # Higher Order Operations #
    ###########################
    @limitedTo2D
    def calculate(self, function, features=None, useLog=None):
        """
        Return a new object with a calculation applied to each feature.

        Calculates the results of the given function on the specified
        features in this object, with output values collected into a new
        object that is returned upon completion.

        Parameters
        ----------
        function : function
            Accepts a view of a feature as an argument and returns the
            new values in that feature.
        features : feature, list of features
            The subset of features to limit the calculation to. If None,
            the calculation will apply to all features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Returns
        -------
        nimble Base object

        See Also
        --------
        transform

        Examples
        --------
        Apply calculation to all features; apply to all points.

        >>> data = nimble.ones('Matrix', 3, 5)
        >>> addTwo = data.features.calculate(lambda ft: ft + 2)
        >>> addTwo
        Matrix(
            [[3.000 3.000 3.000 3.000 3.000]
             [3.000 3.000 3.000 3.000 3.000]
             [3.000 3.000 3.000 3.000 3.000]]
            )

        Apply calculation to all features; function modifies a specific
        point. Note that the function recieves a read-only view of each
        feature, so a copy is necessary to modify any specific data.

        >>> def changeMiddlePoint(ft):
        ...     ftList = ft.copy(to='python list', outputAs1D=True)
        ...     ftList[1] += 4
        ...     return ftList
        >>> data = nimble.ones('Matrix', 3, 5)
        >>> middleChange = data.features.calculate(changeMiddlePoint)
        >>> middleChange
        Matrix(
            [[1.000 1.000 1.000 1.000 1.000]
             [5.000 5.000 5.000 5.000 5.000]
             [1.000 1.000 1.000 1.000 1.000]]
            )

        Apply calculation to a subset of features.

        >>> ftNames = ['f1', 'f2', 'f3']
        >>> data = nimble.identity('Matrix', 3, featureNames=ftNames)
        >>> calc = data.features.calculate(lambda ft: ft + 6,
        ...                                features=[2, 0])
        >>> calc
        Matrix(
            [[6.000 7.000]
             [6.000 6.000]
             [7.000 6.000]]
            featureNames={'f3':0, 'f1':1}
            )
        """
        return self._calculate(function, features, useLog)

    @limitedTo2D
    def matching(self, function, useLog=None):
        """
        Return a boolean value object identifying matching features.

        Apply a function returning a boolean value for each feature in
        this object. Common any/all matching functions can be found in
        nimble's match module. Note that the pointName in the returned
        object will be set to the ``__name__`` attribute of ``function``
        unless it is a ``lambda`` function.

        Parameters
        ----------
        function : function
            * function - in the form of function(featureView) which
              returns True, False, 0 or 1.
            * query - string in the format 'POINTNAME OPERATOR VALUE'
              (i.e "pt1 < 10", "id4 == yes", or "row4 is nonZero") where
              OPERATOR is separated from the POINTNAME and VALUE by
              whitespace characters. See ``nimble.match.QueryString``
              for string requirements.

        Returns
        -------
        nimble Base object
            A point vector of boolean values.

        Examples
        --------
        >>> from nimble import match
        >>> raw = [[1, -1, 1], [-3, 3, 3]]
        >>> data = nimble.data('Matrix', raw)
        >>> allPositiveFts = data.features.matching(match.allPositive)
        >>> allPositiveFts
        Matrix(
            [[False False True]]
            pointNames={'allPositive':0}
            )

        >>> from nimble import match
        >>> raw = [[1, float('nan'), 1], [-3, 3, 3]]
        >>> data = nimble.data('Matrix', raw)
        >>> ftHasMissing = data.features.matching(match.anyMissing)
        >>> ftHasMissing
        Matrix(
            [[False True False]]
            pointNames={'anyMissing':0}
            )
        """
        return self._matching(function, useLog)

    @limitedTo2D
    def insert(self, insertBefore, toInsert, useLog=None):
        """
        Insert more features into this object.

        Expand this object by inserting the features of ``toInsert``
        prior to the ``insertBefore`` identifier. The points in
        ``toInsert`` do not need to be in the same order as in the
        calling object; the data will automatically be placed using the
        calling object's point order if there is an unambiguous mapping.
        ``toInsert`` will be unaffected by calling this method.

        Parameters
        ----------
        insertBefore : identifier
            The index or feature name prior to which the data from
            toInsert will be inserted.
        toInsert : nimble Base object
            The nimble Base object whose contents we will be including
            in this object. Must have the same point names as the
            calling object, but not necessarily in the same order. Must
            not share any feature names with the calling object.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        append

        Examples
        --------
        Insert data; default names.

        >>> data = nimble.zeros('Matrix', 3, 2)
        >>> toInsert = nimble.ones('Matrix', 3, 2)
        >>> data.features.insert(1, toInsert)
        >>> data
        Matrix(
            [[0.000 1.000 1.000 0.000]
             [0.000 1.000 1.000 0.000]
             [0.000 1.000 1.000 0.000]]
            )

        Insert before another point; mixed object types.

        >>> rawData = [[1, 4], [5, 8]]
        >>> data = nimble.data('Matrix', rawData,
        ...                    featureNames=['1', '4'])
        >>> rawInsert = [[2, 3], [6, 7]]
        >>> toInsert = nimble.data('List', rawInsert,
        ...                        featureNames=['2', '3'])
        >>> data.features.insert('4', toInsert)
        >>> data
        Matrix(
            [[1 2 3 4]
             [5 6 7 8]]
            featureNames={'1':0, '2':1, '3':2, '4':3}
            )

        Reorder names.

        >>> rawData = [[1, 2], [5, 6]]
        >>> data = nimble.data('Matrix', rawData, pointNames=['a', 'b'])
        >>> rawInsert = [[7, 8], [3, 4]]
        >>> toInsert = nimble.data('Matrix', rawInsert,
        ...                        pointNames=['b', 'a'])
        >>> data.features.insert(2, toInsert)
        >>> data
        Matrix(
            [[1 2 3 4]
             [5 6 7 8]]
            pointNames={'a':0, 'b':1}
            )
        """
        self._insert(insertBefore, toInsert, False, useLog)

    @limitedTo2D
    def append(self, toAppend, useLog=None):
        """
        Append features to this object.

        Expand this object by appending the features of ``toAppend``
        to the end of this object. The points in ``toAppend`` do not
        need to be in the same order as in the calling object; the data
        will automatically be placed using the calling object's point
        order if there is an unambiguous mapping. ``toAppend`` will be
        unaffected by calling this method.

        Parameters
        ----------
        toAppend : nimble Base object
            The nimble Base object whose contents we will be including
            in this object. Must have the same point names as the
            calling object, but not necessarily in the same order. Must
            not share any feature names with the calling object.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        See Also
        --------
        insert

        Examples
        --------
        Append data; default names.

        >>> data = nimble.zeros('Matrix', 3, 2)
        >>> toAppend = nimble.ones('Matrix', 3, 2)
        >>> data.features.append(toAppend)
        >>> data
        Matrix(
            [[0.000 0.000 1.000 1.000]
             [0.000 0.000 1.000 1.000]
             [0.000 0.000 1.000 1.000]]
            )

        Append mixed object types.

        >>> rawData = [[1, 2], [5, 6]]
        >>> data = nimble.data('Matrix', rawData,
        ...                    featureNames=['1', '2'])
        >>> rawAppend = [[3, 4], [7, 8]]
        >>> toAppend = nimble.data('List', rawAppend,
        ...                        featureNames=['3', '4'])
        >>> data.features.append(toAppend)
        >>> data
        Matrix(
            [[1 2 3 4]
             [5 6 7 8]]
            featureNames={'1':0, '2':1, '3':2, '4':3}
            )

        Reorder names.

        >>> rawData = [[1, 2], [5, 6]]
        >>> data = nimble.data('Matrix', rawData,
        ...                    pointNames=['a', 'b'])
        >>> rawAppend = [[7, 8], [3, 4]]
        >>> toAppend = nimble.data('Matrix', rawAppend,
        ...                        pointNames=['b', 'a'])
        >>> data.features.append(toAppend)
        >>> data
        Matrix(
            [[1 2 3 4]
             [5 6 7 8]]
            pointNames={'a':0, 'b':1}
            )
        """
        self._insert(None, toAppend, True, useLog)

    @limitedTo2D
    def replace(self, data, features=None, useLog=None, **dataKwds):
        """
        Replace the data in one or more of the features in this object.

        If ``features=None``, the data must be a nimble data object with
        matching featureNames, matching featureNames must be specified
        as a ``dataKwds`` argument or the data must replace all
        features. Otherwise, the shape of the ``data`` object must align
        with the ``features`` parameter. Index values in ``features``
        will take priority over matching featureNames.

        Parameters
        ----------
        data
            The object containing the data to use as a replacement. This
            can be any ``source`` accepted by ``nimble.data``.
        features : identifier, list, None
            The feature (name or index) or list of features to replace
            with the provided data.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.
        dataKwds
            Any keyword arguments accepted by ``nimble.data`` to use
            to construct a nimble data object from ``data``. These only
            apply when ``data`` is not already a nimble data object.

        Examples
        --------
        >>> obj = nimble.zeros('Matrix', 3, 3,
        ...                    featureNames=['a', 'b', 'c'])
        >>> newFt = nimble.ones('Matrix', 3, 1, featureNames=['b'])
        >>> obj.features.replace(newFt, features='b')
        >>> obj
        Matrix(
            [[0.000 1.000 0.000]
             [0.000 1.000 0.000]
             [0.000 1.000 0.000]]
            featureNames={'a':0, 'b':1, 'c':2}
            )

        >>> obj = nimble.zeros('Sparse', 3, 4)
        >>> replacement = [[1, 9], [2, 8], [3, 7]]
        >>> obj.features.replace(replacement, [1, 2])
        >>> obj
        Sparse(
            [[0.000 1.000 9.000 0.000]
             [0.000 2.000 8.000 0.000]
             [0.000 3.000 7.000 0.000]]
            )

        >>> obj = nimble.zeros('DataFrame', 3, 3,
        ...                    featureNames=['a', 'b', 'c'])
        >>> obj.features.replace(['Y', 'N', 'Y'], featureNames=['b'])
        >>> obj
        DataFrame(
            [[0.000 Y 0.000]
             [0.000 N 0.000]
             [0.000 Y 0.000]]
            featureNames={'a':0, 'b':1, 'c':2}
            )
        """
        return self._replace(data, features, useLog, **dataKwds)

    @limitedTo2D
    def mapReduce(self, mapper, reducer, useLog=None):
        """
        Apply a mapper and reducer function to this object.

        Return a new object containing the results of the given mapper
        and reducer functions

        Parameters
        ----------
        mapper : function
            Input a feature and output an iterable containing
            two-tuple(s) of mapping identifiers and feature values.
        reducer : function
            Input the ``mapper`` output and output a two-tuple
            containing the identifier and the reduced value.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Examples
        --------
        mapReduce the counts of data types in the features.

        >>> def typeMapper(ft):
        ...     ftType = str(type(ft[0]))
        ...     return [(ftType, 1)]
        >>> def typeReducer(ftType, totals):
        ...     return (ftType, sum(totals))
        >>> raw = [[61500, 'Open', 'Chicago Bears'],
        ...        [71228, 'Dome', 'Atlanta Falcons'],
        ...        [77000, 'Open', 'Kansas City Chiefs'],
        ...        [72968, 'Dome', 'New Orleans Saints'],
        ...        [76500, 'Open', 'Miami Dolphins']]
        >>> ftNames = ['CAPACITY', 'ROOF_TYPE', 'TEAM']
        >>> data = nimble.data('Matrix', raw, featureNames=ftNames)
        >>> data.features.mapReduce(typeMapper, typeReducer)
        Matrix(
            [[<class 'int'> 1]
             [<class 'str'> 2]]
            )
        """
        return self._mapReduce(mapper, reducer, useLog)

    @limitedTo2D
    def permute(self, order=None, useLog=None):
        """
        Permute the indexing of the features.

        Change the arrangement of features in the object. A specific
        permutation can be provided as the ``order`` argument. If
        ``order`` is None, the permutation will be random. Note: a
        random permutation may be the same as the current permutation.

        Parameters
        ----------
        order : list, None
            A list of identifiers indicating the new permutation order.
            If None, the permutation will be random.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Notes
        -----
        Random permutation relies on python's random.shuffle() which may
        not be sufficiently random for large number of features.
        See random.shuffle()'s documentation.

        Examples
        --------
        >>> nimble.random.setSeed(42)
        >>> raw = [[1, 2, 3, 4],
        ...        [1, 2, 3, 4],
        ...        [1, 2, 3, 4],
        ...        [1, 2, 3, 4]]
        >>> data = nimble.data('DataFrame', raw)
        >>> data.features.permute()
        >>> data
        DataFrame(
            [[3 2 4 1]
             [3 2 4 1]
             [3 2 4 1]
             [3 2 4 1]]
            )

        Permute with a list of identifiers.

        >>> raw = [['home', 81, 3],
        ...        ['gard', 98, 10],
        ...        ['home', 14, 1],
        ...        ['home', 11, 3]]
        >>> cols = ['dept', 'ID', 'quantity']
        >>> orders = nimble.data('DataFrame', raw, featureNames=cols)
        >>> orders.features.permute(['ID', 'quantity', 'dept'])
        >>> orders
        DataFrame(
            [[81 3  home]
             [98 10 gard]
             [14 1  home]
             [11 3  home]]
            featureNames={'ID':0, 'quantity':1, 'dept':2}
            )
        """
        self._permute(order, useLog)

    @limitedTo2D
    def fillMatching(self, fillWith, matchingElements, features=None,
                     useLog=None, **kwarguments):
        """
        Replace given values in each feature with other values.

        Fill matching values within each feature with a specified value
        based on the values in that feature. The ``fill`` value can be
        a constant or a determined based on unmatched values in the
        feature. The match and fill modules in nimble offer common
        functions for these operations.

        Parameters
        ----------
        fillWith : value or function
            * value - a value to fill each matching value in each
              feature
            * function - must be in the format:
              fillWith(feature, matchingElements) or
              fillWith(feature, matchingElements, \*\*kwarguments)
              and return the transformed feature as a list of values.
              Certain fill methods can be imported from nimble's fill
              module.
        matchingElements : value, list, or function
            * value - a value to locate within each feature
            * list - values to locate within each feature
            * function - must accept a single value and return True if
              the value is a match. Certain match types can be imported
              from nimble's match module.
            * query - string in the format 'OPERATOR VALUE' representing
              a function (i.e "< 10", "== yes", or "is missing"). See
              ``nimble.match.QueryString`` for string requirements.
        features : identifier or list of identifiers
            Select specific features to apply fill to. If features is
            None, the fill will be applied to all features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.
        kwarguments
            Provide additional parameters to a ``fillWith`` function.

        See Also
        --------
        nimble.fill, nimble.match

        Examples
        --------
        Fill a value with another value.

        >>> raw = [[1, 1, 1],
        ...        [1, 1, 1],
        ...        [1, 1, 'na'],
        ...        [2, 2, 2],
        ...        ['na', 2, 2]]
        >>> data = nimble.data('Matrix', raw)
        >>> data.features.fillMatching(-1, 'na')
        >>> data
        Matrix(
            [[1  1 1 ]
             [1  1 1 ]
             [1  1 -1]
             [2  2 2 ]
             [-1 2 2 ]]
            )

        Fill using nimble's match and fill modules; limit to first
        feature. Note: None is converted to np.nan in nimble.

        >>> from nimble import match
        >>> from nimble import fill
        >>> raw = [[1, 1, 1],
        ...        [1, 1, 1],
        ...        [1, 1, None],
        ...        [2, 2, 2],
        ...        [None, 2, 2]]
        >>> data = nimble.data('Matrix', raw)
        >>> data.features.fillMatching(fill.mean, match.missing, features=0)
        >>> data
        Matrix(
            [[1.000 1.000 1.000]
             [1.000 1.000 1.000]
             [1.000 1.000  nan ]
             [2.000 2.000 2.000]
             [1.250 2.000 2.000]]
            )
        """
        return self._fillMatching(fillWith, matchingElements, features,
                                  useLog, **kwarguments)

    @limitedTo2D
    def normalize(self, function, applyResultTo=None, features=None,
                  useLog=None):
        """
        Modify all features in this object using the given function.

        Normalize the data by a function that adjusts each feature
        based on the provided function. If the function allows, the
        normalization can also be applied to a second object.

        Parameters
        ----------
        function
            The function applying the normalization. Functions must
            accept a feature view and output the normalized feature
            data. When ``applyResultTo`` is not None, the function must
            accept a second feature view and return a two-tuple
            (normalized feature from the calling object,
            normalized feature from applyResultTo).
            Common normalizations can be found in nimble.calculate.
        applyResultTo : nimble Base object, None
            The secondary object to apply the the normalization to.
            Must have the same number of features as the calling object.
        features : identifier, list of identifiers, None
            Select specific features to apply the normalization to. If
            features is None, the normalization will be applied to all
            features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Examples
        --------
        Calling object only.

        >>> from nimble.calculate import range0to1Normalize
        >>> rawTrain = [[5, 9.8, 92],
        ...             [3, 6.2, 58],
        ...             [2, 3.0, 29]]
        >>> pts = ['movie1', 'movie2', 'movie3']
        >>> fts = ['review1', 'review2', 'review3']
        >>> train = nimble.data('Matrix', rawTrain, pts, fts)
        >>> train.features.normalize(range0to1Normalize)
        >>> train
        Matrix(
            [[1.000 1.000 1.000]
             [0.333 0.471 0.460]
             [0.000 0.000 0.000]]
            pointNames={'movie1':0, 'movie2':1, 'movie3':2}
            featureNames={'review1':0, 'review2':1, 'review3':2}
            )

        With applyResultTo.

        >>> from nimble.calculate import meanStandardDeviationNormalize
        >>> rawTrain = [[5, 9.8, 92],
        ...             [3, 6.2, 58],
        ...             [2, 3.0, 10]]
        >>> rawTest = [[4, 9.1, 43],
        ...            [3, 5.1, 88]]
        >>> fts = ['review1', 'review2', 'review3']
        >>> trainPts = ['movie1', 'movie2', 'movie3']
        >>> train = nimble.data('Matrix', rawTrain, trainPts, fts)
        >>> testPts = ['movie4', 'movie5']
        >>> test = nimble.data('Matrix', rawTest, testPts, fts)
        >>> train.features.normalize(meanStandardDeviationNormalize,
        ...                          applyResultTo=test)
        >>> train
        Matrix(
            [[1.336  1.248  1.149 ]
             [-0.267 -0.048 0.139 ]
             [-1.069 -1.200 -1.288]]
            pointNames={'movie1':0, 'movie2':1, 'movie3':2}
            featureNames={'review1':0, 'review2':1, 'review3':2}
            )
        >>> test
        Matrix(
            [[0.535  0.996  -0.307]
             [-0.267 -0.444 1.031 ]]
            pointNames={'movie4':0, 'movie5':1}
            featureNames={'review1':0, 'review2':1, 'review3':2}
            )
        """
        if not callable(function):
            raise InvalidArgumentType('function must be callable')
        if applyResultTo is None:
            self.transform(function, features=features, useLog=False)
        elif isinstance(applyResultTo, nimble.core.data.Base):
            if len(self) != len(applyResultTo.features):
                msg = 'applyResultTo must have the same number of features as '
                msg += 'the calling object'
                raise InvalidArgumentValue(msg)
            selfNames = self._getNamesNoGeneration()
            applyToNames = applyResultTo.features._getNamesNoGeneration()
            if ((selfNames is not None and applyToNames is not None)
                    and selfNames != applyToNames):
                msg = 'applyResultTo featureNames do not match the '
                msg += 'featureNames of the calling object'
                raise InvalidArgumentValue(msg)
            if features is not None:
                features = list(map(self._getIndex, features))
            zipFeatures = zip(self, applyResultTo.features)
            for i, (ft1, ft2) in enumerate(zipFeatures):
                if features is None or i in features:
                    # pylint: disable=cell-var-from-loop
                    norm1, norm2 = function(ft1, ft2)
                    self.transform(lambda _: norm1, features=i, useLog=False)
                    applyResultTo.features.transform(lambda _: norm2,
                                                     features=i,
                                                     useLog=False)
        else:
            msg = 'applyResultTo must be None or an instance of Base'
            raise InvalidArgumentType(msg)

        handleLogging(useLog, 'prep', 'features.normalize',
                      self._base.getTypeString(), Features.normalize,
                      function, applyResultTo, features)

    @limitedTo2D
    def splitByParsing(self, feature, rule, resultingNames, useLog=None):
        """
        Split a feature into multiple features.

        Parse an existing feature and divide it into separate parts.
        Each value must split into a number of values equal to the
        length of ``resultingNames``.

        Parameters
        ----------
        feature : indentifier
            The name or index of the feature to parse and split.
        rule : str, int, list, function
            * string - split the value at any instance of the character
              string. This works in the same way as python's built-in
              split() function; removing this string.
            * integer - the index position where the split will occur.
              Unlike a string, no characters will be removed when using
              integer. All characters before the index will be split
              from characters at and after the index.
            * list - may contain integer and/or string values
            * function - any function accepting a value as input,
              splitting the  value and returning a list of the split
              values.
        resultingNames : list
            Strings defining the names of the split features.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.

        Notes
        -----
        Visual representations of the Examples::

            locations.splitFeatureByParsing('location', ', ',
                                            ['city', 'country'])

                locations (before)                locations (after)
            +-------------------------+    +-----------+--------------+
            | location                |    | city      | country      |
            +-------------------------+    +-----------+--------------+
            | Cape Town, South Africa |    | Cape Town | South Africa |
            +-------------------------+ -> +-----------+--------------+
            | Lima, Peru              |    | Lima      | Peru         |
            +-------------------------+    +-----------+--------------+
            | Moscow, Russia          |    | Moscow    | Russia       |
            +-------------------------+    +-----------+--------------+

            inventory.splitFeatureByParsing(0, 3, ['category', 'id'])

              inventory (before)                  inventory (after)
            +---------+----------+        +----------+-----+----------+
            | product | quantity |        | category | id  | quantity |
            +---------+----------+        +----------+-----+----------+
            | AGG932  | 44       |        | AGG      | 932 | 44       |
            +---------+----------+        +----------+-----+----------+
            | AGG734  | 11       |   ->   | AGG      | 734 | 11       |
            +---------+----------+        +----------+-----+----------+
            | HEQ892  | 1        |        | HEQ      | 892 | 1        |
            +---------+----------+        +----------+-----+----------+
            | LEQ331  | 2        |        | LEQ      | 331 | 2        |
            +---------+----------+        +----------+-----+----------+

        This function was inspired by the separate function from the
        tidyr library created by Hadley Wickham [1]_ in the R
        programming language.

        References
        ----------
        .. [1] Wickham, H. (2014). Tidy Data. Journal of Statistical
           Software, 59(10), 1 - 23.
           doi:http://dx.doi.org/10.18637/jss.v059.i10

        Examples
        --------
        Split with a string for ``rule``.

        >>> raw = [['Cape Town, South Africa'],
        ...        ['Lima, Peru'],
        ...        ['Moscow, Russia']]
        >>> fts = ['location']
        >>> locations = nimble.data('Matrix', raw, featureNames=fts)
        >>> locations.features.splitByParsing('location', ', ',
        ...                                   ['city', 'country'])
        >>> locations
        Matrix(
            [[Cape Town South Africa]
             [   Lima       Peru    ]
             [  Moscow     Russia   ]]
            featureNames={'city':0, 'country':1}
            )

        Split with an index for ``rule``.

        >>> raw = [['AGG932', 44],
        ...        ['AGG734', 11],
        ...        ['HEQ892', 1],
        ...        ['LEQ331', 2]]
        >>> fts = ['product', 'quantity']
        >>> inventory = nimble.data('List', raw, featureNames=fts)
        >>> inventory.features.splitByParsing(0, 3, ['category', 'id'])
        >>> inventory
        List(
            [[AGG 932 44]
             [AGG 734 11]
             [HEQ 892 1 ]
             [LEQ 331 2 ]]
            featureNames={'category':0, 'id':1, 'quantity':2}
            )
        """
        if not (isinstance(rule, (int, np.integer, str))
                or hasattr(rule, '__iter__')
                or hasattr(rule, '__call__')):
            msg = "rule must be an integer, string, iterable of integers "
            msg += "and/or strings, or a function"
            raise InvalidArgumentType(msg)

        splitList = []
        numResultingFts = len(resultingNames)
        for i, value in enumerate(self._base[:, feature]):
            if isinstance(rule, str):
                splitList.append(value.split(rule))
            elif isinstance(rule, (int, np.number)):
                splitList.append([value[:rule], value[rule:]])
            elif hasattr(rule, '__iter__'):
                split = []
                startIdx = 0
                for item in rule:
                    if isinstance(item, str):
                        split.append(value[startIdx:].split(item)[0])
                        # find index of value from startIdx on, o.w. will only
                        # ever return first instance. Add len of previous
                        # values to get actual index and add one to bypass this
                        # item in next iteration
                        startIdx = (value[startIdx:].index(item) +
                                    len(value[:startIdx]) + 1)
                    elif isinstance(item, (int, np.integer)):
                        split.append(value[startIdx:item])
                        startIdx = item
                    else:
                        msg = "A list of items for rule may only contain "
                        msg += " integers and strings"
                        raise InvalidArgumentType(msg)
                split.append(value[startIdx:])
                splitList.append(split)
            else:
                splitList.append(rule(value))
            if len(splitList[-1]) != numResultingFts:
                msg = "The value at index {0} split into ".format(i)
                msg += "{0} values, ".format(len(splitList[-1]))
                msg += "but resultingNames contains "
                msg += "{0} features".format(numResultingFts)
                raise InvalidArgumentValueCombination(msg)

        featureIndex = self.getIndex(feature)
        numRetFeatures = len(self) - 1 + numResultingFts

        self._splitByParsing_implementation(featureIndex, splitList,
                                            numRetFeatures, numResultingFts)

        fNames = self.getNames()[:featureIndex]
        fNames.extend(resultingNames)
        fNames.extend(self.getNames()[featureIndex + 1:])
        self._base._shape[1] = numRetFeatures
        self.setNames(fNames, useLog=False)

        handleLogging(useLog, 'prep', 'features.splitByParsing',
                      self._base.getTypeString(), Features.splitByParsing,
                      feature, rule, resultingNames)

    @limitedTo2D
    def repeat(self, totalCopies, copyFeatureByFeature):
        """
        Create an object using copies of this object's features.

        Copies of this object will be stacked horizontally. The returned
        object will have the same number of points as this object and
        the number of features will be equal to the number of features
        in this object times ``totalCopies``. If this object contains
        featureNames, each feature name will have "_#" appended, where #
        is the number of the copy made.

        Parameters
        ----------
        totalCopies : int
            The number of times a copy of the data in this object will
            be present in the returned object.
        copyFeatureByFeature : bool
            When False, copies are made as if iterating through the
            features in this object ``totalCopies`` times. When True,
            copies are made as if the object is only iterated once,
            making ``totalCopies`` copies of each feature before
            iterating to the next feature.

        Returns
        -------
        nimble Base object
            Object containing the copied data.

        Examples
        --------
        Single feature

        >>> data = nimble.data('Matrix', [[1], [2], [3]])
        >>> data.features.setNames(['a'])
        >>> data.features.repeat(totalCopies=3,
        ...                      copyFeatureByFeature=False)
        Matrix(
            [[1 1 1]
             [2 2 2]
             [3 3 3]]
            featureNames={'a_1':0, 'a_2':1, 'a_3':2}
            )

        Two-dimensional, copyFeatureByFeature is False

        >>> data = nimble.data('Matrix', [[1, 2], [3, 4], [5, 6]])
        >>> data.features.setNames(['a', 'b'])
        >>> data.features.repeat(totalCopies=2,
        ...                      copyFeatureByFeature=False)
        Matrix(
            [[1 2 1 2]
             [3 4 3 4]
             [5 6 5 6]]
            featureNames={'a_1':0, 'b_1':1, 'a_2':2, 'b_2':3}
            )

        Two-dimensional, copyFeatureByFeature is True

        >>> data = nimble.data('Matrix', [[1, 2], [3, 4], [5, 6]])
        >>> data.features.setNames(['a', 'b'])
        >>> data.features.repeat(totalCopies=2,
        ...                      copyFeatureByFeature=True)
        Matrix(
            [[1 1 2 2]
             [3 3 4 4]
             [5 5 6 6]]
            featureNames={'a_1':0, 'a_2':1, 'b_1':2, 'b_2':3}
            )
        """
        return self._repeat(totalCopies, copyFeatureByFeature)

    ###################
    # Query functions #
    ###################
    @limitedTo2D
    def unique(self):
        """
        Only the unique features from this object.

        Any repeated features will be removed from the returned object.
        If feature names are present, the feature name of the first
        instance of the unique feature in this object will be assigned.

        Returns
        -------
        nimble Base object
            The object containing only unique features.

        Examples
        --------
        >>> raw = [['a', 1, 3, 'a'],
        ...        ['a', 5, 6, 'a'],
        ...        ['b', 7, 1, 'b'],
        ...        ['c', 2, 9, 'c']]
        >>> ftNames = ['f1', 'f2', 'f3', 'f1_copy']
        >>> data = nimble.data('Matrix', raw, featureNames=ftNames)
        >>> uniqueFeatures = data.features.unique()
        >>> uniqueFeatures
        Matrix(
            [[a 1 3]
             [a 5 6]
             [b 7 1]
             [c 2 9]]
            featureNames={'f1':0, 'f2':1, 'f3':2}
            )
        """
        return self._unique()

    @limitedTo2D
    def report(self, basicStatistics=True, extraStatisticFunctions=(),
               useLog=None):
        """
        Report containing a summary and statistics for each feature.

        Produce a report, as a nimble List object, containing statistic
        and summary information about each feature in this object. The
        default will include mean, mode, minimum, Q1, median, Q3,
        maximum, uniqueCount, count, and standardDeviation.

        Parameters
        ----------
        basicStatistics : bool, list
            True will include mean, mode, minimum, Q1, median, Q3,
            maximum, uniqueCount, count, and standardDeviation. False
            will only use functions in ``extraStatisticFunctions``. To
            limit the report to a selection of basic statistics, a list
            of strings can be provided, e.g.
            ['mean', 'standardDeviation', 'minimum', 'maximum']
        extraStatisticFunctions : list
            A list of functions to include in the report. Functions must
            accept a feature view as the only input and output a single
            value.
        useLog : bool, None
            Local control for whether to send object creation to the
            logger. If None (default), use the value as specified in the
            "logger" "enabledByDefault" configuration option. If True,
            send to the logger regardless of the global option. If
            False, do **NOT** send to the logger, regardless of the
            global option.
        """
        allow = ['mean', 'mode', 'minimum', 'Q1', 'median', 'Q3', 'maximum',
                 'uniqueCount', 'count', 'standardDeviation']
        if basicStatistics is True:
            stats = allow
        elif basicStatistics:
            if any(stat not in allow for stat in basicStatistics):
                allowed = prettyListString(allow, True, itemStr="'{}'".format)
                msg = 'Invalid value found in basicStatistics. Allowed '
                msg += 'values are {}'.format(allowed)
                raise InvalidArgumentValue(msg)
            stats = basicStatistics
        else:
            stats = []

        fnames = ['index']
        for stat in stats:
            fnames.append(stat)
        fnames.extend(func.__name__ for func in extraStatisticFunctions)

        counter = Counter(fnames)
        remaining = dict(counter)
        # extra function names could conflict
        if len(set(fnames)) != len(fnames):
            editedNames = []
            # add a unique integer to any duplicate names
            for val in fnames:
                if counter[val] > 1:
                    diff = counter[val] - remaining[val]
                    editedNames.append('{} ({})'.format(val, diff))
                    remaining[val] -= 1
                else:
                    editedNames.append(val)
            fnames = editedNames

        pnames = self._getNamesNoGeneration()

        results = []
        quartiles = {'Q1': 0, 'median': 1, 'Q3': 2}
        for i, ft in enumerate(self):
            row = [i]
            quartileCalcs = None
            for stat in stats:
                if stat in quartiles:
                    if quartileCalcs is None:
                        quartileCalcs = nimble.calculate.quartiles(ft)
                    row.append(quartileCalcs[quartiles[stat]])
                else:
                    func = getattr(nimble.calculate, stat)
                    row.append(func(ft))

            for func in extraStatisticFunctions:
                row.append(func(ft))
            results.append(row)

        report = nimble.data('List', results, pnames, fnames, useLog=False)

        handleLogging(useLog, 'data', "feature", str(report))

        return report

    #########################
    # Statistical functions #
    #########################
    @limitedTo2D
    def similarities(self, similarityFunction):
        """
        Calculate similarities between features.

        Return a new object containing the results of the
        ``similarityFunction``.

        Parameters
        ----------
        similarityFunction: str
            The name of the function. The accepted strings include:
            'correlation', 'covariance', 'sample covariance',
            'population covariance' and, 'dot product'. Pearson
            correlation coefficients are used for 'correlation'.

        Returns
        -------
        nimble Base object
        """
        return self._similarities(similarityFunction)

    @limitedTo2D
    def statistics(self, statisticsFunction, groupByFeature=None):
        """
        Calculate feature statistics.

        Parameters
        ----------
        statisticsFunction: str
            The name of the function. The accepted strings include:
            'max', 'mean', 'median', 'min', 'population std',
            'population standard deviation', 'proportion missing',
            'proportion zero', 'sample standard deviation',
            'sample std', 'standard deviation', 'std', 'unique count'

        Returns
        -------
        nimble Base object
        """
        return self._statistics(statisticsFunction, groupByFeature)


    ############
    # plotting #
    ############

    @limitedTo2D
    def plot(self, features=None, horizontal=False, outPath=None,
             show=True, figureName=None, title=True, xAxisLabel=True,
             yAxisLabel=True, legendTitle=None, **kwargs):
        """
        Bar chart comparing features.

        Each value in the object is considered to be the height of a
        bar in the chart. Bars will be grouped by each feature and bar
        colors indicate each point. If multiple bar colors are
        necessary, a legend mapping the pointName (when available) or
        point index to its bar color will be added.

        Parameters
        ----------
        features : list of identifiers, None
            List of feature names and/or indices to plot. None will
            apply to all features.
        horizontal : bool
            False, the default, draws plot bars vertically. True will
            draw bars horizontally.
        outPath : str, None
            A string of the path to save the current figure.
        show : bool
            If True, display the plot. If False, the figure will not
            display until a plotting function with show=True is called.
            This allows for future plots to placed on the figure with
            the same ``figureName`` before being shown.
        figureName : str, None
            A new figure will be generated when None or a new name,
            otherwise the figure with that name will be activated to
            draw the plot on an existing figure.
        title : str, bool
            The title of the plot. If True, a title will automatically
            be generated.
        xAxisLabel : str, bool
            A label for the x axis. If True, a label will automatically
            be generated.
        yAxisLabel : str, bool
            A label for the y axis. If True, a label will automatically
            be generated.
        legendTitle : str, None
            A title for the legend. A legend is only added when multiple
            bar colors are necessary, otherwise this parameter is
            ignored. None will not add a title to the legend.
        kwargs
            Any keyword arguments accepted by matplotlib.pyplot's
            ``bar`` function.

        See Also
        --------
            matplotlib.pyplot.bar
        """
        self._plotComparison(
            None, features, None, horizontal, outPath, show, figureName, title,
            xAxisLabel, yAxisLabel, legendTitle, **kwargs)

    @limitedTo2D
    def plotMeans(self, features=None, horizontal=False, outPath=None,
                  show=True, figureName=None, title=True, xAxisLabel=True,
                  yAxisLabel=True, **kwargs):
        """
        Plot feature means with 95% confidence interval bars.

        The 95% confidence interval for each feature is calculated using
        the critical value from the two-sided Student's t-distribution.

        Parameters
        ----------
        features : list of identifiers, None
            List of feature names and/or indices to plot. None will
            apply to all features.
        horizontal : bool
            False, the default, draws plot bars vertically. True will
            draw bars horizontally.
        outPath : str, None
            A string of the path to save the current figure.
        show : bool
            If True, display the plot. If False, the figure will not
            display until a plotting function with show=True is called.
            This allows for future plots to placed on the figure with
            the same ``figureName`` before being shown.
        figureName : str, None
            A new figure will be generated when None or a new name,
            otherwise the figure with that name will be activated to
            draw the plot on an existing figure.
        title : str, bool
            The title of the plot. If True, a title will automatically
            be generated.
        xAxisLabel : str, bool
            A label for the x axis. If True, a label will automatically
            be generated.
        yAxisLabel : str, bool
            A label for the y axis. If True, a label will automatically
            be generated.
        kwargs
            Any keyword arguments accepted by matplotlib.pyplot's
            ``errorbar`` function.

        See Also
        --------
            matplotlib.pyplot.errorbar
        """
        self._plotComparison(
            nimble.calculate.mean, features, True, horizontal, outPath,
            show, figureName, title, xAxisLabel, yAxisLabel, None, **kwargs)

    @limitedTo2D
    def plotStatistics(
            self, statistic, features=None, horizontal=False, outPath=None,
            show=True, figureName=None, title=True, xAxisLabel=True,
            yAxisLabel=True, legendTitle=None, **kwargs):
        """
        Bar chart comparing an aggregate statistic between features.

        The bars in the plot represent the output of the ``statistic``
        function applied to each feature. Typically, functions return a
        single numeric value, however, the function may return a feature
        vector. In that case, each point in the object returned by
        ``statistic`` is considered to be the heights of separate bars
        for that feature. Bars will be grouped by each feature and
        bar colors indicate each point. If multiple bar colors are
        necessary, a legend mapping the pointName (when available) or
        point index to its bar color will be added.

        Parameters
        ----------
        statistic : function
            Functions take a feature view the only required argument.
            Common statistic functions can be found in nimble.calculate.
        features : list of identifiers, None
            List of feature names and/or indices to plot. None will
            apply to all features.
        horizontal : bool
            False, the default, draws plot bars vertically. True will
            draw bars horizontally.
        outPath : str, None
            A string of the path to save the current figure.
        show : bool
            If True, display the plot. If False, the figure will not
            display until a plotting function with show=True is called.
            This allows for future plots to placed on the figure with
            the same ``figureName`` before being shown.
        figureName : str, None
            A new figure will be generated when None or a new name,
            otherwise the figure with that name will be activated to
            draw the plot on an existing figure.
        title : str, bool
            The title of the plot. If True, a title will automatically
            be generated.
        xAxisLabel : str, bool
            A label for the x axis. If True, a label will automatically
            be generated.
        yAxisLabel : str, bool
            A label for the y axis. If True, a label will automatically
            be generated.
        legendTitle : str, None
            A title for the legend. A legend is only added when multiple
            bar colors are necessary, otherwise this parameter is
            ignored. None will not add a title to the legend.
        kwargs
            Any keyword arguments accepted by matplotlib.pyplot's
            ``bar`` function.

        See Also
        --------
            matplotlib.pyplot.bar
        """
        self._plotComparison(
            statistic, features, False, horizontal, outPath, show, figureName,
            title, xAxisLabel, yAxisLabel, legendTitle, **kwargs)

    ####################
    # Abstract Methods #
    ####################

    @abstractmethod
    def _iter(self):
        pass

    @abstractmethod
    def _getitem(self, key):
        pass

    @abstractmethod
    def _getName(self, index):
        pass

    @abstractmethod
    def _getNames(self):
        pass

    @abstractmethod
    def _setName(self, oldIdentifier, newName, useLog):
        pass

    @abstractmethod
    def _setNames(self, assignments, useLog):
        pass

    @abstractmethod
    def _getIndex(self, identifier, allowFloats=False):
        pass

    @abstractmethod
    def _getIndices(self, names):
        pass

    @abstractmethod
    def _hasName(self, name):
        pass

    @abstractmethod
    def _copy(self, toCopy, start, end, number, randomize, useLog=None):
        pass

    @abstractmethod
    def _extract(self, toExtract, start, end, number, randomize, useLog=None):
        pass

    @abstractmethod
    def _delete(self, toDelete, start, end, number, randomize, useLog=None):
        pass

    @abstractmethod
    def _retain(self, toRetain, start, end, number, randomize, useLog=None):
        pass

    @abstractmethod
    def _count(self, condition):
        pass

    @abstractmethod
    def _sort(self, by, reverse, useLog=None):
        pass

    @abstractmethod
    def _transform(self, function, limitTo, useLog=None):
        pass

    @abstractmethod
    def _calculate(self, function, limitTo, useLog=None):
        pass

    @abstractmethod
    def _matching(self, function, useLog=None):
        pass

    @abstractmethod
    def _insert(self, insertBefore, toInsert, append=False, useLog=None):
        pass

    @limitedTo2D
    def _replace(self, data, locations, useLog=None):
        pass

    @abstractmethod
    def _mapReduce(self, mapper, reducer, useLog=None):
        pass

    @abstractmethod
    def _permute(self, order=None, useLog=None):
        pass

    @abstractmethod
    def _fillMatching(self, match, fill, limitTo, useLog=None, **kwarguments):
        pass

    @abstractmethod
    def _splitByParsing_implementation(self, featureIndex, splitList,
                                       numRetFeatures, numResultingFts):
        pass

    @abstractmethod
    def _repeat(self, totalCopies, copyVectorByVector):
        pass

    @abstractmethod
    def _unique(self):
        pass

    @abstractmethod
    def _similarities(self, similarityFunction):
        pass

    @abstractmethod
    def _statistics(self, statisticsFunction, groupByFeature):
        pass

    @abstractmethod
    def _plotComparison(self, statistic, identifiers, confidenceIntervals,
                        horizontal, outPath, show, figureName, title,
                        xAxisLabel, yAxisLabel, legendTitle, **kwargs):
        pass

    @abstractmethod
    def _getNamesNoGeneration(self):
        pass
