import abc
import re

from . import mysql_settings
_ = str


class DatastoreModelsBase(object):
    """Base model for the datastore schema and user models."""

    def serialize(self):
        return self.__dict__

    def _deserialize(self, obj):
        self.__dict__ = obj

    def __repr__(self):
        return str(self.serialize())

    @classmethod
    def deserialize(cls, value, verify=True):
        item = cls(deserializing=True)
        item._deserialize(value)
        if verify:
            item.verify_dict()
        return item

    @abc.abstractmethod
    def verify_dict(self):
        """Validate the object's data dictionary.
        :returns:            True if dictionary is valid.
        """

    @staticmethod
    def check_string(value, desc):
        """Check if the value is a string/unicode.
        :param value:        Value to check.
        :param desc:         Description for exception message.
        :raises:             ValueError if not a string/unicode.
        """
        if not isinstance(value, str):
            raise ValueError(_("%(desc)s is not a string. Type = %(t)s.")
                             % {'desc': desc, 't': type(value)})


class DatastoreSchema(DatastoreModelsBase):
    """Represents a database schema."""

    def __init__(self, name=None, deserializing=False):
        self._name = None
        self._collate = None
        self._character_set = None
        # If both or neither are passed in this is a bug.
        if bool(deserializing) == bool(name):
            raise RuntimeError(_("Bug in DatastoreSchema()"))
        if not deserializing:
            self.name = name

    def __str__(self):
        return str(self.name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._validate_schema_name(value)
        self._name = value

    def _validate_schema_name(self, value):
        """Perform checks on a given schema name.
        :param value:        Validated schema name.
        :type value:         string
        :raises:             ValueError On validation errors.
        """
        if not value:
            raise ValueError(_("Schema name empty."))
        self.check_string(value, 'Schema name')
        if self._max_schema_name_length and (len(value) >
                                             self._max_schema_name_length):
            raise ValueError(_("Schema name '%(name)s' is too long. "
                               "Max length = %(max_length)d.")
                             % {'name': value,
                                'max_length': self._max_schema_name_length})
        elif not self._is_valid_schema_name(value):
            raise ValueError(_("'%s' is not a valid schema name.") % value)

    @property
    def _max_schema_name_length(self):
        """Return the maximum valid schema name length if any.
        :returns:            Maximum schema name length or None if unlimited.
        """
        return None

    def _is_valid_schema_name(self, value):
        """Validate a given schema name.
        :param value:        Validated schema name.
        :type value:         string
        :returns:            TRUE if valid, FALSE otherwise.
        """
        return True

    def verify_dict(self):
        """Check that the object's dictionary values are valid by reloading
        them via the property setters. The checkers should raise the
        ValueError exception if invalid. All mandatory fields should be
        checked.
        """
        self.name = self._name

    @property
    def ignored_dbs(self):
        return []

    def is_ignored(self):
        return self.name in self.ignored_dbs

    def check_reserved(self):
        """Check if the name is on the ignore_dbs list, meaning it is
        reserved.
        :raises:             ValueError if name is on the reserved list.
        """
        if self.is_ignored():
            raise ValueError(_('Database name "%(name)s" is on the reserved '
                               'list: %(reserved)s.')
                             % {'name': self.name,
                                'reserved': self.ignored_dbs})

    def _create_checks(self):
        """Checks to be performed before database can be created."""
        self.check_reserved()

    def check_create(self):
        """Check if the database can be created.
        :raises:             ValueError if the schema is not valid for create.
        """
        try:
            self._create_checks()
        except ValueError as e:
            raise ValueError(_('Cannot create database: %(error)s')
                             % {'error': str(e)})

    def _delete_checks(self):
        """Checks to be performed before database can be deleted."""
        self.check_reserved()

    def check_delete(self):
        """Check if the database can be deleted.
        :raises:             ValueError if the schema is not valid for delete.
        """
        try:
            self._delete_checks()
        except ValueError as e:
            raise ValueError(_('Cannot delete database: %(error)s')
                             % {'error': str(e)})


class DatastoreUser(DatastoreModelsBase):
    """Represents a datastore user."""

    _HOSTNAME_WILDCARD = '%'
    root_username = 'root'

    def __init__(self, name=None, password=None, host=None, databases=None,
                 deserializing=False):
        self._name = None
        self._password = None
        self._host = self._HOSTNAME_WILDCARD
        self._databases = []
        self._is_root = False
        if not deserializing:
            self.name = name
            if password:
                self.password = password
            if host:
                self.host = host
            if databases:
                self.databases = databases

    @classmethod
    def root(cls, name=None, password=None, *args, **kwargs):
        if not name:
            name = cls.root_username
        if not password:
            password = 'superuser'
        user = cls(name, password, *args, **kwargs)
        user.make_root()
        return user

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._validate_user_name(value)
        self._name = value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self.check_string(value, "User password")
        if self._is_valid_password(value):
            self._password = value
        else:
            raise ValueError(_("'%s' is not a valid password.") % value)

    def _add_database(self, value):
        serial_db = self._build_database_schema(value).serialize()
        if self._is_valid_database(serial_db):
            self._databases.append(serial_db)

    @property
    def databases(self):
        return self._databases

    @databases.setter
    def databases(self, value):
        if isinstance(value, list):
            for dbname in value:
                self._add_database(dbname)
        else:
            self._add_database(value)

    @property
    def host(self):
        if self._host is None:
            return self._HOSTNAME_WILDCARD
        return self._host

    @host.setter
    def host(self, value):
        self.check_string(value, "User host name")
        if self._is_valid_host_name(value):
            self._host = value
        else:
            raise ValueError(_("'%s' is not a valid hostname.") % value)

    def _build_database_schema(self, name):
        """Build a schema for this user.
        :type name:             string
        """
        return self.schema_model(name)

    def deserialize_schema(self, value):
        """Deserialize a user's databases value.
        :type value:            dict
        """
        return self.schema_model.deserialize(value)

    def _validate_user_name(self, value):
        """Perform validations on a given user name.
        :param value:        Validated user name.
        :type value:         string
        :raises:             ValueError On validation errors.
        """
        if not value:
            raise ValueError(_("User name empty."))
        self.check_string(value, "User name")
        if self._max_user_name_length and (len(value) >
                                           self._max_user_name_length):
            raise ValueError(_("User name '%(name)s' is too long. "
                               "Max length = %(max_length)d.")
                             % {'name': value,
                                'max_length': self._max_user_name_length})
        elif not self._is_valid_user_name(value):
            raise ValueError(_("'%s' is not a valid user name.") % value)

    @property
    def _max_user_name_length(self):
        """Return the maximum valid user name length if any.
        :returns:            Maximum user name length or None if unlimited.
        """
        return None

    def _is_valid_user_name(self, value):
        """Validate a given user name.
        :param value:        User name to be validated.
        :type value:         string
        :returns:            TRUE if valid, FALSE otherwise.
        """
        return True

    def _is_valid_host_name(self, value):
        """Validate a given host name.
        :param value:        Host name to be validated.
        :type value:         string
        :returns:            TRUE if valid, FALSE otherwise.
        """
        return True

    def _is_valid_password(self, value):
        """Validate a given password.
        :param value:        Password to be validated.
        :type value:         string
        :returns:            TRUE if valid, FALSE otherwise.
        """
        return True

    def _is_valid_database(self, value):
        """Validate a given database (serialized schema object).
        :param value:        The database to be validated.
        :type value:         dict
        :returns:            TRUE if valid, FALSE otherwise.
        :raises:             ValueError if operation not allowed.
        """
        return value not in self.databases

    def verify_dict(self):
        """Check that the object's dictionary values are valid by reloading
        them via the property setters. The checkers should raise the
        ValueError exception if invalid. All mandatory fields should be
        checked.
        """
        self.name = self._name
        if self.__dict__.get('_password'):
            self.password = self._password
        else:
            self._password = None
        if self.__dict__.get('_host'):
            self.host = self._host
        else:
            self._host = self._HOSTNAME_WILDCARD
        if self.__dict__.get('_databases'):
            for database in self._databases:
                # Create the schema for validation only
                self.deserialize_schema(database)
        else:
            self._databases = []
        if not self.__dict__.get('_is_root'):
            self._is_root = False

    @property
    def schema_model(self):
        return DatastoreSchema

    @property
    def ignored_users(self):
        if self._is_root:
            return []
        return []

    @property
    def is_ignored(self):
        return self.name in self.ignored_users

    def make_root(self):
        self._is_root = True

    def check_reserved(self):
        """Check if the name is on the ignore_users list, meaning it is
        reserved.
        :raises:             ValueError if name is on the reserved list.
        """
        if self.is_ignored:
            raise ValueError(_('User name "%(name)s" is on the reserved '
                               'list: %(reserved)s.')
                             % {'name': self.name,
                                'reserved': self.ignored_users})

    def _create_checks(self):
        """Checks to be performed before user can be created."""
        self.check_reserved()

    def check_create(self):
        """Check if the user can be created.
        :raises:             ValueError if the user is not valid for create.
        """
        try:
            self._create_checks()
        except ValueError as e:
            raise ValueError(_('Cannot create user: %(error)s')
                             % {'error': str(e)})

    def _delete_checks(self):
        """Checks to be performed before user can be created."""
        self.check_reserved()

    def check_delete(self):
        """Check if the user can be deleted.
        :raises:             ValueError if the user is not valid for delete.
        """
        try:
            self._delete_checks()
        except ValueError as e:
            raise ValueError(_('Cannot delete user: %(error)s')
                             % {'error': str(e)})


class MySQLSchema(DatastoreSchema):
    """Represents a MySQL database and its properties."""

    # Defaults
    __charset__ = "utf8mb3"
    __collation__ = "utf8mb3_general_ci"
    dbname = re.compile(r"^[A-Za-z0-9_-]+[\s\?\#\@]*[A-Za-z0-9_-]+$")

    # Complete list of acceptable values
    collation = mysql_settings.collation
    charset = mysql_settings.charset

    def __init__(self, name=None, collate=None, character_set=None,
                 deserializing=False):
        super(MySQLSchema, self).__init__(name=name,
                                          deserializing=deserializing)
        if not deserializing:
            if collate:
                self.collate = collate
            if character_set:
                self.character_set = character_set

    @property
    def _max_schema_name_length(self):
        return 64

    def _is_valid_schema_name(self, value):
        # must match the dbname regex, and
        # cannot contain a '\' character.
        return not any([
            not self.dbname.match(value),
            ("%r" % value).find("\\") != -1
        ])

    @property
    def collate(self):
        """Get the appropriate collate value."""
        if not self._collate and not self._character_set:
            return self.__collation__
        elif not self._collate:
            return self.charset[self._character_set][0]
        else:
            return self._collate

    @collate.setter
    def collate(self, value):
        """Validate the collation and set it."""
        if not value:
            pass
        elif self._character_set:
            if value not in self.charset[self._character_set]:
                msg = (_("%(val)s not a valid collation for charset %(char)s.")
                       % {'val': value, 'char': self._character_set})
                raise ValueError(msg)
            self._collate = value
        else:
            if value not in self.collation:
                raise ValueError(_("'%s' not a valid collation.") % value)
            self._collate = value
            self._character_set = self.collation[value]

    @property
    def character_set(self):
        """Get the appropriate character set value."""
        if not self._character_set:
            return self.__charset__
        else:
            return self._character_set

    @character_set.setter
    def character_set(self, value):
        """Validate the character set and set it."""
        if not value:
            pass
        elif value not in self.charset:
            raise ValueError(_("'%s' not a valid character set.") % value)
        else:
            self._character_set = value

    def verify_dict(self):
        # Also check the collate and character_set values if set, initialize
        # them if not.
        super(MySQLSchema, self).verify_dict()
        if self.__dict__.get('_collate'):
            self.collate = self._collate
        else:
            self._collate = None
        if self.__dict__.get('_character_set'):
            self.character_set = self._character_set
        else:
            self._character_set = None


class MySQLUser(DatastoreUser):
    """Represents a MySQL User and its associated properties."""

    not_supported_chars = re.compile(r"""^\s|\s$|'|"|;|`|,|/|\\""")

    def _is_valid_string(self, value):
        if (not value or
                self.not_supported_chars.search(value) or
                ("%r" % value).find("\\") != -1):
            return False
        else:
            return True

    def _is_valid_user_name(self, value):
        return self._is_valid_string(value)

    def _is_valid_password(self, value):
        return self._is_valid_string(value)

    def _is_valid_host_name(self, value):
        if value in [None, "%"]:
            # % is MySQL shorthand for "everywhere". Always permitted.
            # Null host defaults to % anyway.
            return True
        else:
            # If it wasn't required, anything else goes.
            return True

    def _build_database_schema(self, name):
        return MySQLSchema(name)

    def deserialize_schema(self, value):
        return MySQLSchema.deserialize(value)

    @property
    def _max_user_name_length(self):
        return 16

    @property
    def schema_model(self):
        return MySQLSchema
