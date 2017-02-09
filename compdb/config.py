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


def make_conf():
    config_paths = [get_user_conf()]
    local_conf = get_local_conf()
    if local_conf:
        config_paths.append(local_conf)
    conf = configparser.ConfigParser()
    conf.read(config_paths)
    return conf


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
        if sys.version_info[0] < 3:
            exec('self.schemas[name] = unicode')
            self.schemas[name] = unicode  # noqa: F821
        else:
            self.schemas[name] = str

    def register_int(self, name, desc):
        self.schemas[name] = int


class ConfigSchema(object):
    def __init__(self):
        self._section_to_schemas = {}

    def get_section_schema(self, section):
        self._section_to_schemas[section] = SectionSchema()
        return self._section_to_schemas[section]


class LazyTypedSection():
    def __init__(self, section, section_schema):
        self._section = section
        self._section_schema = section_schema

    def __getattr__(self, name):
        if name not in self._section_schema.schemas:
            # requesting an unspecified attribute is an error
            raise AttributeError(name)
        if name not in self._section:
            return None
        return self._section_schema.schemas[name](self._section[name])


class LazyTypedConfig():
    def __init__(self, config_schema):
        self._config = None
        self._config_schema = config_schema
        self._sections = {}
        self._overrides = []

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
            self._config_schema._section_to_schemas[section] \
                               .schemas[opt](value)
            self._overrides.append((section, opt, value))

    def get_config(self):
        if not self._config:
            self._config = make_conf()
            self._apply_overrides(self._config)
        return self._config

    def _apply_overrides(self, config):
        for section, option, value in self._overrides:
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, option, value)

    def __getattr__(self, name):
        human_name = name.replace('_', '-')
        self.get_config()  # make sure self._config is loaded
        if human_name not in self._sections:
            if human_name not in self._config:
                # use the empty-dict as a configuration,
                # this will make the LazyTypedSection return a default value
                self._sections[human_name] = LazyTypedSection(
                    {}, self._config_schema._section_to_schemas[human_name])
            else:
                self._sections[human_name] = LazyTypedSection(
                    self._config[human_name],
                    self._config_schema._section_to_schemas[human_name])
        return self._sections[human_name]
