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


class SectionSpec(object):
    def __init__(self):
        self.specs = {}
        self.depends = []

    def add_dependency(self, other_section):
        self.depends.append(other_section)

    def register_string(self, name, desc):
        if sys.version_info[0] < 3:
            exec('self.specs[name] = unicode')
            self.specs[name] = unicode  # noqa: F821
        else:
            self.specs[name] = str

    def register_int(self, name, desc):
        self.specs[name] = int


class ConfigSpec(object):
    def __init__(self):
        self._section_to_specs = {}

    def get_section_spec(self, section):
        self._section_to_specs[section] = SectionSpec()
        return self._section_to_specs[section]


class LazyTypedSection():
    def __init__(self, section, section_spec):
        self._section = section
        self._section_spec = section_spec

    def __getattr__(self, name):
        if name not in self._section_spec.specs:
            # requesting an unspecified attribute is an error
            raise AttributeError
        if name not in self._section:
            return None
        return self._section_spec.specs[name](self._section[name])


class LazyTypedConfig():
    def __init__(self, config_spec):
        self._config = None
        self._config_spec = config_spec
        self._sections = {}

    def __getattr__(self, name):
        human_name = name.replace('_', '-')
        if not self._config:
            self._config = make_conf()
        if human_name not in self._sections:
            if human_name not in self._config:
                # use the empty-dict as a configuration,
                # this will make the LazyTypedSection return a default value
                self._sections[human_name] = LazyTypedSection(
                    {}, self._config_spec._section_to_specs[human_name])
            else:
                self._sections[human_name] = LazyTypedSection(
                    self._config[human_name],
                    self._config_spec._section_to_specs[human_name])
        return self._sections[human_name]