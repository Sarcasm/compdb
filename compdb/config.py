from __future__ import print_function, unicode_literals, absolute_import

import configparser
import os
import sys


def _xdg_config_home():
    """Return a path under XDG_CONFIG_HOME directory (defaults to '~/.config').

    https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
    """
    return os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))


def _win32_config_dir():
    """Return resource under APPDATA directory.

    https://technet.microsoft.com/en-us/library/cc749104(v=ws.10).aspx
    """
    # Purposefully use a syntax that triggers an error
    # if the APPDATA environment variable does not exists.
    # It's not clear what should be the default.
    return os.environ['APPDATA']


def _macos_config_dir():
    """Return path under macOS specific configuration directory.
    """
    # What should the directory be?
    # ~/Library/Application Support/
    #   https://developer.apple.com/library/content/documentation/General/Conceptual/MOSXAppProgrammingGuide/AppRuntime/AppRuntime.html#//apple_ref/doc/uid/TP40010543-CH2-SW13
    # ~/Library/Preferences/
    #   Someone said so stackoverflow.
    # ~/.config/:
    #   Same as Linux when XDG_CONFIG_HOME is not defined.
    #
    # Choose the Linux way until someone with more knowledge complains.
    return os.path.expanduser('~/.config')


def get_user_conf():
    if sys.platform.startswith('win32'):
        config_dir = _win32_config_dir()
    elif sys.platform.startswith('darwin'):
        config_dir = _macos_config_dir()
    else:
        # Assume Linux-like behavior for other platforms,
        # platforms like FreeBSD should have the same behavior as Linux.
        #
        # A few platforms would be nice to test:
        # - cygwin
        # - msys2
        config_dir = _xdg_config_home()
    return os.path.join(config_dir, 'compdb', 'config')


def locate_dominating_file(name, start_dir='.'):
    curdir = os.path.abspath(start_dir)
    olddir = None
    while not curdir == olddir:
        if os.path.exists(os.path.join(curdir, name)):
            return curdir
        olddir = curdir
        curdir = os.path.dirname(curdir)
    return None


def get_local_conf():
    compdb_dir = locate_dominating_file('.compdb')
    if compdb_dir:
        return os.path.join(compdb_dir, '.compdb')
    return None


class OptionInvalidError(ValueError):
    '''Raise when a key string of the form '<section>.<option>' is malformed'''

    def __init__(self, message, key, *args):
        self.message = message
        self.key = key
        super(OptionInvalidError, self).__init__(message, key, *args)


def parse_key(key):
    section, sep, var = key.partition('.')
    if section and sep and var:
        return section, var
    else:
        raise OptionInvalidError(
            'invalid key, should be of the form <section>.<variable>', key)


class SectionSchema(object):
    def __init__(self):
        self.schemas = {}
        self.depends = []

    def add_dependency(self, other_section):
        self.depends.append(other_section)

    def register_string(self, name, desc):
        # type('') is a hack to get the unicode string type in a portable way
        # both in Python 3 and 2, when unicode_literals for the latter
        self.schemas[name] = type('')

    def register_int(self, name, desc):
        self.schemas[name] = int

    def register_path(self, name, desc):
        self.schemas[name] = 'path_magic'


class ConfigSchema(object):
    def __init__(self):
        self._section_to_schemas = {}

    def sections(self):
        return self._section_to_schemas.keys()

    def get_section_schema(self, section):
        self._section_to_schemas[section] = SectionSchema()
        return self._section_to_schemas[section]


class LazyTypedSection():
    def __init__(self, section_schema, sections):
        self._section_schema = section_schema
        self._sections = sections

    def __getattr__(self, unsafe_option_name):
        option = unsafe_option_name.replace('_', '-')
        if option not in self._section_schema.schemas:
            # requesting an unspecified attribute is an error
            raise AttributeError(option)
        cls = self._section_schema.schemas[option]
        for section, path in self._sections:
            if option in section:
                value = section[option]
                if cls == 'path_magic':
                    return os.path.normpath(
                        os.path.join(os.path.dirname(path or ''), value))
                return cls(value)
        return None


class LazyTypedConfig():
    def __init__(self, config_schema):
        self._config_schema = config_schema
        self._filenames = []
        self._configs = []
        self._sections = {}
        self._overrides = []

    def options(self):
        for section_name, section_schema in \
                self._config_schema._section_to_schemas.items():
            for key in section_schema.schemas.keys():
                yield '{}.{}'.format(section_name, key)

    def get_effective_configuration(self):
        conf = configparser.ConfigParser()
        self._get_configs()  # load self._filenames
        for config_path in self._filenames:
            if config_path:
                conf.read(config_path)
            else:
                self._apply_overrides(conf)
        return conf

    def set_overrides(self, overrides):
        for key, value in overrides:
            section, opt = parse_key(key)
            if section not in self._config_schema._section_to_schemas or \
               opt not in \
               self._config_schema._section_to_schemas[section].schemas:
                # overriding an unspecified attribute is an error
                raise AttributeError(key)
            # check type of key, if the type is wrong an error will be
            # reported, even if the config override is not given by the command
            # there is no reason for the user to specify any wrong values
            cls = self._config_schema._section_to_schemas[section].schemas[opt]
            if cls == 'path_magic':
                cls = type('')
            cls(value)
            self._overrides.append((section, opt, value))

    def _apply_overrides(self, config):
        for section, option, value in self._overrides:
            config.set(section, option, value)

    def _make_configs(self):
        user_conf = get_user_conf()
        if os.path.isfile(user_conf):
            self._filenames.append(user_conf)
        local_conf = get_local_conf()
        if local_conf:
            self._filenames.append(local_conf)
        if self._overrides:
            # none is a special value for the overrides
            self._filenames.append(None)
        for config_path in self._filenames:
            conf = configparser.ConfigParser()
            # initialize all the sections,
            # this avoid having to check for them later on
            for section in self._config_schema.sections():
                conf.add_section(section)
            if config_path:
                conf.read(config_path)
            else:
                self._apply_overrides(conf)
            self._configs.append(conf)

    def _get_configs(self):
        if not self._configs:
            self._make_configs()
        return self._configs

    def _make_section(self, name):
        schema = self._config_schema._section_to_schemas[name]
        sections = [config[name] for config in self._get_configs()]
        return LazyTypedSection(schema,
                                reversed(list(zip(sections, self._filenames))))

    def __getattr__(self, unsafe_section_name):
        section = unsafe_section_name.replace('_', '-')
        if section not in self._sections:
            self._sections[section] = self._make_section(section)
        return self._sections[section]
