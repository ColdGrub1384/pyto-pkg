#!/usr/bin/env python3

"""
Python interpreter.

usage: python [-c cmd | -m mod | file] [arg]
"""

import sys
import site
import os
import runpy
import platform
import subprocess
import sysconfig
import platform
from collections import namedtuple
from code import interact

def ios_ver():
    IOSVersion = namedtuple("IOS", ["system", "release", "model", "is_simulator"])
    is_simulator = ("-simulator" in sysconfig.get_config_var('SOABI'))
    match sys.platform:
        case "ios":
            if "macabi" in sysconfig.get_config_var('SOABI'):
                return IOSVersion("macOS", "11.0", "Mac", False)
            else:
                return IOSVersion("iOS", "13.0", "iPhone", is_simulator)
        case "watchos":
            return IOSVersion("watchOS", "6.0", "Apple Watch", is_simulator)
        case "tvos":
            return IOSVersion("watchOS", "6.0", "Apple Watch", is_simulator)

def platform_system():
    return os.environ["PYTHON_SYSTEM"]

def sysconfig_get_platform():
    return os.environ["_PYTHON_HOST_PLATFORM"]

## Interpreter  ##

_usage = "usage: python [-c cmd | -m mod | file | -] [arg]"

def main():

    site_path = os.environ["PYTHON_SITE_PATH"]
    proj_path = os.environ["PYTHON_PROJ_PATH"]
    bin_path = os.environ["PYTHON_BIN_PATH"]
    include_path = os.environ["PYTHON_INCLUDE_PATH"]

    try:
        from pip._internal.locations import base
        base.user_site = site_path
        base.site_packages = site_path
    except ImportError:
        pass

    site.USER_SITE = site_path
    sys.prefix = proj_path
    sys.exec_prefix = proj_path
    sysconfig._PREFIX = sys.prefix
    sysconfig._EXEC_PREFIX = sys.exec_prefix
    sysconfig._INSTALL_SCHEMES["posix_prefix"]["platlib"] = site_path
    sysconfig._INSTALL_SCHEMES["posix_prefix"]["purelib"] = site_path
    sysconfig._INSTALL_SCHEMES["posix_prefix"]["scripts"] = bin_path
    sysconfig._INSTALL_SCHEMES["posix_prefix"]["include"] = include_path
    sysconfig._INSTALL_SCHEMES["posix_prefix"]["data"] = proj_path

    sys.platform = os.environ["PYTHON_PLATFORM"].split("_")[0]
    sys.implementation._multiarch = f"{os.environ["ARCHS"].replace(";", "-")}{os.environ["SDK_NAME"]}"
    platform.system = platform_system
    platform.ios_ver = ios_ver
    sysconfig.get_platform = sysconfig_get_platform
    subprocess._can_fork_exec = True
    sys.argv.pop(0)
    sys.executable = os.environ["PYTHON_SCRIPT_PATH"]
    sys._base_executable = sys.executable
    sys.argv.insert(0, sys.executable)

    if len(sys.argv) > 1 and sys.argv[1] == "-u":
        sys.argv.pop(1)

    sys.path.append(os.getcwd())

    if len(sys.argv) == 1 and sys.stdin.isatty():
        return interact()
    elif len(sys.argv) == 1 and not sys.stdin.isatty():
        if len(sys.argv) > 1:
            sys.argv.pop(0)
        return exec(sys.stdin.read(), globals={})

    try:
        if sys.argv[1] == "--version":
            return print("Python "+sys.version.split(" ")[0])
    except IndexError:
        pass

    if sys.argv[1] == "-c":
        try:
            _code = sys.argv[2] # python -c "import sys; print(sys.argv)" foo bar
            sys.argv.pop(0) # -c "import sys; print(sys.argv)" foo bar
            sys.argv.pop(0) # "import sys; print(sys.argv)" foo bar
            sys.argv[0] = "-c" # -c foo bar
        except IndexError:
            print(_usage, file=sys.stderr)
            sys.exit(1)

        exec(_code, globals={})
    elif sys.argv[1] == "-m" or sys.argv[1].startswith("-m"):
        if sys.argv[1] != "-m":
            mod = sys.argv[1].replace("-m", "")
            sys.argv.pop(1)
            sys.argv.insert(1, mod)
            sys.argv.insert(1, "-m")
        try:
            sys.argv.pop(0)
            sys.argv.pop(0)
        except IndexError:
            print(_usage, file=sys.stderr)
            sys.exit(1)

        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(-1, cwd)
            added = True
        else:
            sys.path.remove(cwd)
            sys.path.insert(-1, cwd)
            added = False

        try:
            runpy.run_module(sys.argv[0], run_name="__main__")
        finally:
            if added and cwd in sys.path:
                sys.path.remove(cwd)

    elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
        print(_usage, file=sys.stderr)
        sys.exit(1)
    else:
        sys.argv.pop(0)

        try:
            script = sys.argv[0]
            script_dir = os.path.abspath(os.path.dirname(script))
            sys.path.append(script_dir)
            runpy.run_path(script, run_name="__main__")
        except Exception as e:
            exc_type, exc, tb = sys.exc_info()
            sys.excepthook(exc_type, exc, tb)
            sys.exit(1)

if __name__ == "__main__":
    main()
