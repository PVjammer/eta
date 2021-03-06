'''
Core data structures for representing data and containers of data.

Copyright 2017-2018, Voxel51, Inc.
voxel51.com

Brian Moore, brian@voxel51.com
Jason Corso, jason@voxel51.com
'''
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

from collections import defaultdict
import os

from eta.core.config import no_default
import eta.core.serial as etas
import eta.core.utils as etau


class DataContainer(etas.Container):
    '''Abstract base class for containers that store lists of `Serializable`
    data class instances.

    This class cannot be instantiated directly. Instead a subclass should
    be created for each type of data to be stored. Subclasses MUST set the
    following members:
        -  `_ELE_CLS`: the class of the element stored in the container

    In addition, sublasses MAY override the following members:
        - `_ELE_CLS_FIELD`: the name of the private attribute that will store
            the class of the elements in the container
        - `_ELE_ATTR`: the name of the attribute that will store the elements
            in the container

    DataContainer subclasses embed their class names and underlying data
    instance class names in their JSON representations, so they can be read
    reflectively from disk.

    Examples:
        ```
        from eta.core.data import DataContainer
        from eta.core.geometry import LabeledPointContainer

        tags = LabeledPointContainer(...)
        tags.write_json("tags.json")

        tags2 = DataContainer.from_json("tags.json")
        print(tags2.__class__)  # LabeledPointContainer, not DataContainer
        ```

    Attributes:
        <data>: a list of data instances. The field name <data> is specified by
            the `_ELE_ATTR` member of the DataContainer subclass, and the class
            of the data instances is specified by the `_ELE_CLS` member
    '''

    #
    # The class of the data stored in the container
    #
    # Subclasses MUST set this field
    #
    _ELE_CLS = None

    #
    # The name of the private attribute that will store the class of the
    # data in the container
    #
    # Subclasses MAY override this field
    #
    _ELE_CLS_FIELD = "_DATA_CLS"

    #
    # The name of the attribute that will store the data in the container
    #
    # Subclasses MAY override this field
    #
    _ELE_ATTR = "data"

    @classmethod
    def get_data_class(cls):
        '''Gets the class of data stored in this container.'''
        return cls._ELE_CLS

    @classmethod
    def get_data_class_name(cls):
        '''Returns the fully-qualified class name string of the data instances
        in this container.
        '''
        return etau.get_class_name(cls._ELE_CLS)


class DataFileSequence(etas.Serializable):
    '''Class representing a sequence of data files on disk.

    When a DataFileSequence is created, it must correspond to actual files on
    disk. However, when `immutable_bounds=False`, the `gen_path()` method can
    be used to add files to the beginning or end of the sequence.

    Examples of representable file sequences:
        /path/to/video/%05d.png
        /path/to/objects/%05d.json

    Attributes:
        sequence (str): the sequence pattern
        immutable_bounds (bool): whether the lower and upper bounds of the
            sequence can be modified
        extension (str): the file extension of the pattern
        lower_bound (int): the smallest index in the sequence
        upper_bound (int): the largest index in the sequence (inclusive)
    '''

    def __init__(self, sequence, immutable_bounds=True):
        '''Creates a DataFileSequence instance for the given sequence.

        Args:
            sequence: The printf-style pattern describing the files on disk,
                e.g., `/path/to/frame-%05d.json`
            immutable_bounds: whether the lower and upper bounds of the
                sequence should be immutable. By default, this is True

        Raises:
            DataFileSequenceError: if the sequence did not match any files on
                disk
        '''
        self.sequence = sequence
        self.immutable_bounds = immutable_bounds
        self._extension = os.path.splitext(self.sequence)[1]
        self._lower_bound, self._upper_bound = etau.parse_bounds_from_pattern(
            self.sequence)
        self._iter_index = None

        if self._lower_bound is None or self._upper_bound is None:
            raise DataFileSequenceError(
                "Sequence '%s' did not match any files on disk" % sequence)

    def __getitem__(self, index):
        return self.gen_path(index)

    def __iter__(self):
        self._iter_index = self._lower_bound - 1
        return self

    def __next__(self):
        self._iter_index += 1
        if not self.check_bounds(self._iter_index):
            self._iter_index = None
            raise StopIteration
        return self.gen_path(self._iter_index)

    @property
    def extension(self):
        return self._extension

    @property
    def lower_bound(self):
        return self._lower_bound

    @property
    def upper_bound(self):
        return self._upper_bound

    @lower_bound.setter
    def lower_bound(self, value):
        if self.immutable_bounds:
            raise DataFileSequenceError(
                "Cannot set bounds of an immutable sequence.")
        self._lower_bound = min(value, self.upper_bound)

    @upper_bound.setter
    def upper_bound(self, value):
        if self.immutable_bounds:
            raise DataFileSequenceError(
                "Cannot set bounds of an immutable sequence.")
        self._upper_bound = max(value, self.lower_bound)

    @property
    def starts_at_zero(self):
        return self._lower_bound == 0

    @property
    def starts_at_one(self):
        return self._lower_bound == 1

    def check_bounds(self, index):
        '''Checks if the index is within the bounds for this sequence.

        Args:
            index: a sequence index

        Returns:
            True/False
        '''
        if index < self.lower_bound or index > self.upper_bound:
            return False
        return True

    def gen_path(self, index):
        '''Generates the path for the file with the given sequence index.

        If the sequence has mutable bounds, the index can extend the sequence
        consecutively (i.e., by one index) above or below the current bounds.

        Args:
            index: a sequence index

        Returns:
            the generated path for the given index
        '''
        if self.immutable_bounds:
            if not self.check_bounds(index):
                raise DataFileSequenceError(
                    "Index %d out of bounds [%d, %d]" %
                    (index, self.lower_bound, self.upper_bound))
        elif index < 0:
            raise DataFileSequenceError("Indices must be nonnegative")
        elif index == self.lower_bound - 1:
            self._lower_bound = index
        elif index == self.upper_bound + 1:
            self._upper_bound = index
        elif not self.check_bounds(index):
            raise DataFileSequenceError(
                "Index %d out of bounds [%d, %d]; mutable sequences can be "
                "extended at most one index above/below." %
                (index, self.lower_bound, self.upper_bound))

        return self.sequence % index

    @classmethod
    def build_for_dir(cls, dir_path):
        '''Builds a `DataFileSequence` for the given directory.'''
        return cls(etau.parse_dir_pattern(dir_path)[0])

    @classmethod
    def from_dict(cls, d):
        '''Builds a `DataFileSequence` from a JSON dictioanry.'''
        return cls(d["sequence"], immutable_bounds=d["immutable_bounds"])


class DataFileSequenceError(Exception):
    '''Error raised when an invalid DataFileSequence is encountered.'''
    pass


class DataRecords(DataContainer):
    '''Container class for data records.

    DataRecords is a generic container of records each having a value for
    a certain set of fields.
    '''

    _ELE_ATTR = "records"
    _ELE_CLS_FIELD = "_RECORD_CLS"
    _ELE_CLS = None  # this is set per-instance for DataRecords

    def __init__(self, record_cls, **kwargs):
        '''Creates a `DataRecords` instance.

        Args:
            record_cls: the records class to use for this container
            records: an optional list of records to add to the container
        '''
        self._ELE_CLS = record_cls
        super(DataRecords, self).__init__(**kwargs)

    @property
    def record_cls(self):
        '''Returns the class of records in the container.'''
        return self._ELE_CLS

    def add_dict(self, d, record_cls=None):
        '''Adds the records in the dictionary to the container.

        Args:
            d: a DataRecords dictionary
            record_cls: an optional records class to use when parsing the
                records dictionary. If None, the _ELE_CLS class of this
                instance is used

        Returns:
            the number of elements in the container
        '''
        rc = record_cls or self._ELE_CLS
        self.add_container(self.from_dict(d, record_cls=rc))
        return len(self)

    def add_json(self, json_path, record_cls=None):
        '''Adds the records in the JSON file to the container.

        Args:
            json_path: the path to a DataRecords JSON file
            record_cls: an optional records class to use when parsing the
                records dictionary. If None, the _ELE_CLS class of this
                instance is used

        Returns:
            the number of elements in the container
        '''
        rc = record_cls or self._ELE_CLS
        self.add_container(self.from_json(json_path, record_cls=rc))
        return len(self)

    def build_keyset(self, field):
        '''Returns a list of unique values of `field` across the records in
        the container.
        '''
        keys = set()
        for r in self.__elements__:
            keys.add(getattr(r, field))
        return list(keys)

    def build_lookup(self, field):
        '''Builds a lookup dictionary indexed by `field` whose values are lists
        of indices of the records whose `field` attribute matches the
        corresponding key.
        '''
        lud = defaultdict(list)
        for i, r in enumerate(self.__elements__):
            lud[getattr(r, field)].append(i)
        return dict(lud)

    def build_subsets(self, field):
        '''Builds a dictionary indexed by `field` whose values are lists of
        records whose `field` attribute matches the corresponding key.
        '''
        sss = defaultdict(list)
        for r in self.__elements__:
            sss[getattr(r, field)].append(r)
        return dict(sss)

    def cull(self, field, keep_values=None, remove_values=None):
        '''Cull records from the container based on `field`.

        Args:
            field: the field to process
            keep_values: an optional list of field values to keep
            remove_values: an optional list of field values to remove

        Returns:
            the number of elements in the container
        '''
        lud = self.build_lookup(field)

        # Determine values to keep
        if remove_values:
            keep_values = set(lud.keys()) - set(remove_values)
        if not keep_values:
            raise DataRecordsError(
                "Either keep_values or remove_values must be provided")

        # Cull records
        inds = []
        for v in keep_values:
            inds += lud[v]
        self.keep_inds(inds)

        return len(self)

    def slice(self, field):
        '''Returns a list of `field` values for the records in the
        container.
        '''
        return [getattr(r, field) for r in self.__elements__]

    def subset_from_indices(self, indices):
        '''Creates a new DataRecords instance containing only the subset of
        records in this container with the specified indices.
        '''
        return self.extract_inds(indices)

    @classmethod
    def from_dict(cls, d, record_cls=None):
        '''Constructs a DataRecords instance from a dictionary.

        Args:
            d: a DataRecords dictionary
            record_cls: an optional records class to use when parsing the
                records dictionary. If not provided, the DataRecord dictionary
                must define it

        Returns:
            a DataRecords instance
        '''
        rc = record_cls or d.get(cls._ELE_CLS_FIELD, None)
        if rc is None:
            raise DataRecordsError(
                "Need record_cls to parse the DataRecords dictionary")

        return DataRecords(
            record_cls=rc,
            records=[rc.from_dict(r) for r in d[cls._ELE_ATTR]])

    @classmethod
    def from_json(cls, json_path, record_cls=None):
        '''Constructs a DataRecords object from a JSON file.

        Args:
            json_path: the path to a DataRecords JSON file
            record_cls: an optional records class to use when parsing the
                records file. If not provided, the DataRecords JSON file must
                define it

        Returns:
            a DataRecords instance
        '''
        return cls.from_dict(etas.read_json(json_path), record_cls=record_cls)


class DataRecordsError(Exception):
    '''Exception raised for invalid DataRecords invocations.'''
    pass


DEFAULT_DATA_RECORDS_FILENAME = "records.json"


class BaseDataRecord(etas.Serializable):
    '''Base class for all data records.

    Data records are flexible containers that function as dictionary-like
    classes that define the required, optional, and excluded keys that they
    support.

    @todo excluded is redundant. We should only serialize required and optional
    attributes; all others should be excluded by default.
    '''

    def __init__(self):
        '''Base constructor for all data records.'''
        self.clean_optional()

    def __getitem__(self, key):
        '''Provides dictionary-style `[key]` access to the attributes of the
        data record.
        '''
        return getattr(self, key)

    def attributes(self):
        '''Returns the list of attributes of the data record that are to be
        serialized.

        All private attributes (those starting with "_") and attributes in
        `excluded()` are omitted from this list.

        Returns:
            the list of attributes to be serialized
        '''
        attr = super(BaseDataRecord, self).attributes()
        return [a for a in attr if a not in self.excluded()]

    def clean_optional(self):
        '''Deletes any optional attributes from the data record that are not
        set, i.e., those that are `no_default`.

        Note that `None` is a valid value for an attribute.
        '''
        for o in self.optional():
            if hasattr(self, o) and getattr(self, o) is no_default:
                delattr(self, o)

    @classmethod
    def from_dict(cls, d):
        '''Constructs a data record from a JSON dictionary. All required
        attributes must be present in the dictionary, and any optional
        attributes that are present will also be stored.

        Args:
            a JSON dictonary containing (at minimum) all of the required
                attributes for the data record

        Returns:
            an instance of the data record

        Raises:
            KeyError: if a required attribute was not found in the input
                dictionary
        '''
        kwargs = {k: d[k] for k in cls.required()}                  # required
        kwargs.update({k: d[k] for k in cls.optional() if k in d})  # optional
        return cls(**kwargs)

    @classmethod
    def required(cls):
        '''Returns a list of attributes that are required by all instances of
        the data record. By default, an empty list is returned.
        '''
        return []

    @classmethod
    def optional(cls):
        '''Returns a list of attributes that are optionally included in the
        data record if they are present in the data dictionary. By default,
        an empty list is returned.
        '''
        return []

    @classmethod
    def excluded(cls):
        '''Return a list of attributes that should always be excluded when the
        data record is serialized. By default, an empty list is returned.
        '''
        return []


class LabeledVideoRecord(BaseDataRecord):
    '''A simple, reusable DataRecord for a labeled video.

    Args:
        video_path: the path to the video
        label: the label of the video
        group: an optional group attribute that provides additional information
            about the video. For example, if multiple video clips were sampled
            from a single video, this attribute can be used to specify the
            parent video
    '''
    def __init__(self, video_path, label, group=no_default):
        '''Creates a new LabeledVideoRecord instance.'''
        self.video_path = video_path
        self.label = label
        self.group = group
        super(LabeledVideoRecord, self).__init__()

    @classmethod
    def optional(cls):
        return ["group"]

    @classmethod
    def required(cls):
        return ["video_path", "label"]
