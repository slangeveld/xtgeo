# -*- coding: utf-8 -*-
"""
Module for basic XTGeo dialog, basic interaction with user,
including logging for debugging.

Logging is enabled by setting a environment variable::

  export XTG_LOGGING_LEVEL=INFO   # if bash; will set logging to INFO level
  setenv XTG_LOGGING_LEVEL INFO   # if tcsh; will set logging to INFO level

Other levels are DEBUG and CRITICAL. CRITICAL is default (cf. Pythons logging)

Usage of logging in scripts::

  import xtgeo
  xtg = xtgeo.common.XTGeoDialog()
  logger = xtg.basiclogger(__name__)
  logger.info('This is logging of %s', something)

Other than logging, there is also a template for user interaction, which shall
be used in client scripts::

  xtg.echo('This is a message')
  xtg.warn('This is a warning')
  xtg.error('This is an error, will continue')
  xtg.critical('This is a big error, will exit')

How it should works:

Enviroment variable XTG_VERBOSE_LEVEL will steer the output from lowelevel
C routines; normally they are quiet

XTG_VERBOSE_LEVEL is undefined: xtg.say works to screen

XTG_VERBOSE_LEVEL > 1 starts to print C messages

XTG_VERBOSE_LEVEL < 0 skip also xtg.say

XTG_LOGGING_LEVEL is for Python logging (string, as INFO)

XTG_LOGGING_FORMAT is for Python logging (number, 0 ,1, 2, ...)

The system here is:
syslevel is the actual level when code is executed:

-1: quiet dialog, no warnings only errors and critical

0 : quiet dialog, only warnings and errors will be displayed

In addition there are other classes:

* XTGShowProgress()

* XTGDescription()

"""

from __future__ import division, absolute_import
from __future__ import print_function

import os
import sys
from datetime import datetime as dtime
import getpass
import platform
import inspect
import logging
import warnings
import timeit

import xtgeo
import xtgeo.cxtgeo.cxtgeo as _cxtgeo



UNDEF = _cxtgeo.UNDEF
UNDEF_LIMIT = _cxtgeo.UNDEF_LIMIT
VERYLARGENEGATIVE = _cxtgeo.VERYLARGENEGATIVE
VERYLARGEPOSITIVE = _cxtgeo.VERYLARGEPOSITIVE
MLS = 10000000.0


HEADER = "\033[1;96m"
OKBLUE = "\033[94m"
OKGREEN = "\033[92m"
WARN = "\033[93;43m"
ERROR = "\033[93;41m"
CRITICAL = "\033[1;91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"


class XTGShowProgress(object):
    """Class for showing progress of a computation to the terminal.

    Example::

        # assuming 30 steps in calculation
        theprogress = XTGShowProgress(30, info='Compute stuff')
        for i in range(30):
            do_slow_computation()
            theprogress.flush(i)
        theprogress.finished()
    """

    def __init__(self, maxiter, info="", leadtext="", skip=1, show=True):
        self._max = maxiter
        self._info = info
        self._show = show
        self._leadtext = leadtext
        self._skip = skip
        self._next = 0

    def flush(self, step):
        if not self._show:
            return
        progress = int(float(step) / float(self._max) * 100.0)
        if progress >= self._next:
            print("{0}{1}% {2}".format(self._leadtext, progress, self._info))
            self._next += self._skip

    def finished(self):
        if not self._show:
            return
        print("{0}{1}% {2}".format(self._leadtext, 100, self._info))


class XTGDescription(object):
    """Class for making desciptions of object instances"""

    def __init__(self):
        self._txt = []

    def title(self, atitle):
        fmt = "=" * 99
        self._txt.append(fmt)
        fmt = "{}".format(atitle)
        self._txt.append(fmt)
        fmt = "=" * 99
        self._txt.append(fmt)

    def txt(self, *atxt):
        atxt = list(atxt)
        fmt = self._smartfmt(atxt)
        self._txt.append(fmt)

    def flush(self):
        fmt = "=" * 99
        self._txt.append(fmt)

        for line in self._txt:
            print(line)

    def astext(self):
        thetext = ""
        fmt = "=" * 99
        self._txt.append(fmt)

        for line in self._txt:
            thetext += line + "\n"

        return thetext[:-1]

    @staticmethod
    def _smartfmt(atxt):
        alen = len(atxt)
        atxt.insert(1, "=>")
        if alen == 1:
            fmt = "{:40s}".format(*atxt)
        elif alen == 2:
            fmt = "{:40s} {:>2s} {}".format(*atxt)
        elif alen == 3:
            fmt = "{:40s} {:>2s} {}  {}".format(*atxt)
        elif alen == 4:
            fmt = "{:40s} {:>2s} {}  {}  {}".format(*atxt)
        elif alen == 5:
            fmt = "{:40s} {:>2s} {}  {}  {}  {}".format(*atxt)
        elif alen == 6:
            fmt = "{:40s} {:>2s} {}  {}  {}  {}  {}".format(*atxt)
        elif alen == 7:
            fmt = "{:40s} {:>2s} {}  {}  {}  {}  {}  {}".format(*atxt)
        return fmt


class _TimeFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """handling difftimes in logging..."""

    # cf https://stackoverflow.com/questions/31521859/
    # python-logging-module-time-since-last-log

    def filter(self, record):
        # pylint: disable=access-member-before-definition
        # pylint: disable=attribute-defined-outside-init
        try:
            last = self.last
        except AttributeError:
            last = record.relativeCreated

        dlt = dtime.fromtimestamp(
            record.relativeCreated / 1000.0
        ) - dtime.fromtimestamp(last / 1000.0)

        record.relative = "{0:.2f}".format(dlt.seconds + dlt.microseconds / MLS)

        self.last = record.relativeCreated
        return True


class XTGeoDialog(object):  # pylint: disable=too-many-public-methods
    """System for handling dialogs and messages in XTGeo.

    This module cooperates with Python logging module.

    """

    def __init__(self):

        self._callclass = None
        self._caller = None
        self._rootlogger = logging.getLogger()
        self._lformat = None
        self._lformatlevel = 1
        self._logginglevel = "CRITICAL"
        self._logginglevel_fromenv = None
        self._loggingname = ""
        self._syslevel = 1
        self._test_env = True
        self._tmpdir = "TMP"
        self._testpath = None
        self._bigtests = None
        self._showrtwarnings = True

        # a string, for Python logging:
        self._logginglevel_fromenv = os.environ.get("XTG_LOGGING_LEVEL", None)

        # a number, for format, 1 is simple, 2 is more info etc
        loggingformat = os.environ.get("XTG_LOGGING_FORMAT")

        if self._logginglevel_fromenv:
            self.logginglevel = self._logginglevel_fromenv

        if loggingformat is not None:
            self._lformatlevel = int(loggingformat)

        # a number, for C routines
        envsyslevel = os.environ.get("XTG_VERBOSE_LEVEL")
        if envsyslevel is None:
            self._syslevel = 0
        else:
            self._syslevel = int(envsyslevel)

        # # a string, for Python logging:
        # logginglevel = os.environ.get('XTG_LOGGING_LEVEL')

        # # a number, for format, 1 is simple, 2 is more info etc
        # loggingformat = os.environ.get('XTG_LOGGING_FORMAT')

        # if logginglevel is None:
        #     self._logginglevel = 'CRITICAL'
        # else:
        #     self._logginglevel = str(logginglevel)

        # if loggingformat is None:
        #     self._lformatlevel = 1
        # else:
        #     self._lformatlevel = int(loggingformat)

    # @staticmethod
    # def UNDEF():
    #     return UNDEF

    # @staticmethod
    # def UNDEF_LIMIT():
    #     return UNDEF_LIMIT

    @property
    def bigtests(self):
        """Return bigtests status"""
        return self._bigtests

    @property
    def bigtest(self):
        """Return bigtest(s) status (alt)"""
        return self._bigtests

    @property
    def tmpdir(self):
        """Return tmpdir value"""
        return self._tmpdir

    @property
    def testpath(self):
        """Return or setting up testpath"""
        return self._testpath

    @testpath.setter
    def testpath(self, newtestpath):

        if not os.path.isdir(newtestpath):
            raise RuntimeError(
                "Proposed test path is not valid: {}".format(newtestpath)
            )

        self._testpath = newtestpath

    @property
    def syslevel(self):
        """This is about logging from the C compiled parts"""
        return self._syslevel

    @syslevel.setter
    def syslevel(self, mylevel):
        if 5 > mylevel >= 0:
            self._syslevel = mylevel
        else:
            print("Invalid range for syslevel")

        envsyslevel = os.environ.get("XTG_VERBOSE_LEVEL")

        if envsyslevel is None:
            pass
        else:
            self._syslevel = int(envsyslevel)

    # for backward compatibility (to be phased out)
    def get_syslevel(self):
        return self._syslevel

    # @property
    # def logginglevel(self):
    #     """Will return a logging level property, e.g. logging.CRITICAL"""
    #     ll = logging.CRITICAL
    #     if self._logginglevel == 'INFO':
    #         ll = logging.INFO
    #     elif self._logginglevel == 'WARNING':
    #         ll = logging.WARNING
    #     elif self._logginglevel == 'DEBUG':
    #         ll = logging.DEBUG

    #     return ll

    @property
    def logginglevel(self):
        """Set or return a logging level property, e.g. logging.CRITICAL"""

        return self._logginglevel

    @logginglevel.setter
    def logginglevel(self, level):
        # pylint: disable=pointless-statement

        validlevels = ("INFO", "WARNING", "DEBUG", "CRITICAL")
        if level in validlevels:
            self._logginglevel = level
        else:
            raise ValueError(
                "Invalid level given, must be " "in {}".format(validlevels)
            )

    @property
    def numericallogginglevel(self):
        """Return a numerical logging level (read only)"""
        llo = logging.CRITICAL
        if self._logginglevel == "INFO":
            llo = logging.INFO
        elif self._logginglevel == "WARNING":
            llo = logging.WARNING
        elif self._logginglevel == "DEBUG":
            llo = logging.DEBUG

        return llo

    @property
    def loggingformatlevel(self):
        return self._lformatlevel

    @property
    def loggingformat(self):
        """Returns the format string to be used in logging"""

        if self._lformatlevel <= 1:
            fmt = logging.Formatter(fmt="%(levelname)8s: (%(relative)ss) \t%(message)s")

        elif self._lformatlevel == 2:
            fmt = logging.Formatter(
                fmt="%(levelname)8s (%(relative)ss) %(name)44s "
                "[%(funcName)40s()] %(lineno)4d >> \t%(message)s"
            )

        else:
            fmt = logging.Formatter(
                fmt="%(asctime)s Line: %(lineno)4d %(name)44s "
                "(Delta=%(relative)ss) "
                "[%(funcName)40s()]"
                "%(levelname)8s:"
                "\t%(message)s"
            )

        log = self._rootlogger
        _tmp1 = [hndl.addFilter(_TimeFilter()) for hndl in log.handlers]
        _tmp2 = [hndl.setFormatter(fmt) for hndl in log.handlers]

        self._lformat = fmt._fmt  # private attribute in Formatter()
        return self._lformat

    @staticmethod
    def print_xtgeo_header(appname, appversion, info=None):
        """Prints a banner for a XTGeo app to STDOUT.

        Args:
            appname (str): Name of application.
            appversion (str): Version of application on form '3.2.1'
            info (str, optional): More info, e.g. if beta release

        Example::

            xtg.print_xtgeo_header('myapp', '0.2.1', info='Beta release!')
        """

        cur_version = "Python " + str(sys.version_info[0]) + "."
        cur_version += str(sys.version_info[1]) + "." + str(sys.version_info[2])

        app = appname + ", version " + str(appversion)
        if info:
            app = app + " (" + info + ")"
        print("")
        print(HEADER)
        print("#" * 79)
        print("#{}#".format(app.center(77)))
        print("#" * 79)
        nowtime = dtime.now().strftime("%Y-%m-%d %H:%M:%S")
        ver = "Using XTGeo version " + xtgeo.__version__
        cur_version += " @ {} on {} by {}".format(
            nowtime, platform.node(), getpass.getuser()
        )
        print("#{}#".format(ver.center(77)))
        print("#{}#".format(cur_version.center(77)))
        print("#" * 79)
        print(ENDC)
        print("")

    def basiclogger(self, name, logginglevel=None, loggingformat=None, info=False):
        """Initiate the logger by some default settings."""

        if logginglevel is not None and self._logginglevel_fromenv is None:
            self.logginglevel = logginglevel

        if loggingformat is not None and isinstance(loggingformat, int):
            self._lformatlevel = loggingformat

        logging.basicConfig(stream=sys.stdout)
        fmt = self.loggingformat
        self._loggingname = name
        if info:
            print(
                "Logginglevel is {}, formatlevel is {}, and format is {}".format(
                    self.logginglevel, self._lformatlevel, fmt
                )
            )
        self._rootlogger.setLevel(self.numericallogginglevel)

        logging.captureWarnings(True)

        return logging.getLogger(self._loggingname)

    @staticmethod
    def functionlogger(name):
        """Get the logger for functions (not top level)."""

        logger = logging.getLogger(name)
        logger.addHandler(logging.NullHandler())
        return logger

    def testsetup(self):
        """Basic setup for XTGeo testing (private; only relevant for tests)"""

        tmppath = "TMP"
        try:
            os.makedirs(tmppath)
        except OSError:
            if not os.path.isdir(tmppath):
                raise

        tstpath = os.environ.get("XTG_TESTPATH", "../xtgeo-testdata")
        if not os.path.isdir(tstpath):
            raise RuntimeError("Test path is not valid: {}".format(tstpath))

        bigtst1 = os.environ.get("XTG_BIGTESTS", None)
        bigtst2 = os.environ.get("XTG_BIGTEST", None)

        if bigtst1 is not None or bigtst2 is not None:
            self._bigtests = True

        self._test_env = True
        self._tmpdir = tmppath
        self._testpath = tstpath

        return True

    @staticmethod
    def timer(*args):
        """Without args; return the time, with a time as arg return the
        difference.
        """
        time1 = timeit.default_timer()

        if args:
            return time1 - args[0]

        return time1

    def show_runtimewarnings(self, flag=True):
        """Show warnings issued by xtg.warn, if flag is True."""
        self._showrtwarnings = flag

    def insane(self, string):
        level = 4
        idx = 0

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    def trace(self, string):
        level = 3
        idx = 0

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    def debug(self, string):
        level = 2
        idx = 0

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    def speak(self, string):
        level = 1
        idx = 1

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    info = speak

    def say(self, string):
        level = -5
        idx = 3

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    def warn(self, string):
        """Show warnings at Runtime (pure user info/warns)."""
        level = 0
        idx = 6

        if self._showrtwarnings:
            caller = sys._getframe(1).f_code.co_name
            frame = inspect.stack()[1][0]
            self.get_callerinfo(caller, frame)

            self._output(idx, level, string)

    warning = warn

    @staticmethod
    def warndeprecated(string):
        """Show Deprecation warnings"""

        def warnoneliner(message, category, filename, lineno):

            return "%s: %s: (%s:%s)\n" % (category.__name__, message, filename, lineno)

        warnings.formatwarning = warnoneliner
        warnings.simplefilter("default", DeprecationWarning)
        warnings.warn(string, DeprecationWarning, stacklevel=2)

    @staticmethod
    def warnuser(string):
        """Show User warnings, using Python warnings"""

        def warnoneliner(message, category):
            return "%s: %s\n" % (category.__name__, message)

        warnings.formatwarning = warnoneliner
        warnings.simplefilter("default", UserWarning)
        warnings.warn(string, UserWarning, stacklevel=2)

    def error(self, string):
        level = -8
        idx = 8

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)

    def critical(self, string, sysexit=True):
        level = -9
        idx = 9

        caller = sys._getframe(1).f_code.co_name
        frame = inspect.stack()[1][0]
        self.get_callerinfo(caller, frame)

        self._output(idx, level, string)
        if sysexit:
            raise SystemExit("STOP!")

    def get_callerinfo(self, caller, frame):
        the_class = self._get_class_from_frame(frame)

        # just keep the last class element
        x = str(the_class)
        x = x.split(".")
        the_class = x[-1]

        self._caller = caller
        self._callclass = the_class

        return (self._caller, self._callclass)

    # =============================================================================
    # Private routines
    # =============================================================================

    @staticmethod
    def _get_class_from_frame(fr):
        # pylint: disable=deprecated-method
        args, _, _, value_dict = inspect.getargvalues(fr)

        # we check the first parameter for the frame function is
        # named 'self'
        if args and args[0] == "self":
            instance = value_dict.get("self", None)
            if instance:
                # return its class
                return getattr(instance, "__class__", None)
        # return None otherwise
        return None

    def _output(self, idx, level, string):

        prefix = ""
        endfix = ""

        if idx == 0:
            prefix = "++"
        elif idx == 1:
            prefix = "**"
        elif idx == 3:
            prefix = ">>"
        elif idx == 6:
            prefix = WARN + "##"
            endfix = ENDC
        elif idx == 8:
            prefix = ERROR + "!#"
            endfix = ENDC
        elif idx == 9:
            prefix = CRITICAL + "!!"
            endfix = ENDC

        prompt = False
        if level <= self._syslevel:
            prompt = True

        if prompt:
            if self._syslevel <= 1:
                print("{} {}{}".format(prefix, string, endfix))
            else:
                ulevel = str(level)
                if level == -5:
                    ulevel = "M"
                if level == -8:
                    ulevel = "E"
                if level == -9:
                    ulevel = "W"
                print(
                    "{0} <{1}> [{2:23s}->{3:>33s}] {4}{5}".format(
                        prefix, ulevel, self._callclass, self._caller, string, endfix
                    )
                )
