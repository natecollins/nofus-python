"""
****************************************************************************************
NOFUS Logger for Python
****************************************************************************************
Copyright 2019 Nathan Collins. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY Nathan Collins ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Nathan Collins OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Nathan Collins.

*****************************************************************************************

****************************************
* Use examples
****************************************

# Initialize built-in file logger; default level logs all except TRACE
Logger.initialize('/path/to/file.log')

# Initialize built-in file logger with customize logger levels
Logger.initialize('/path/to/file.log', Logger.LOG_ERROR | Logger.LOG_CRITICAL | Logger.LOG_WARNING)

# Disable logger
Logger.disable()

# Register custom logger instance which implements LoggingInterface
class CustomLogger(LoggingInterface):
    ..

Logger.register( CustomLogger() )

# Make log entries
Logger.trace("Trace!")
Logger.debug("Debug!")
Logger.info("Info!")
Logger.notice("Notice!")
Logger.warning("Warning!")
Logger.error("Error!")
Logger.critical("Critical!")
"""
import os
import time
import threading

class LoggingInterface:
    """
    Interface required for creating custom logger
    """
    def make_log(self, entry, log_level):
        raise NotImplementedError("Custom Logger class must override make_log()")


class Logger(LoggingInterface):
    """
    Logger class and default file logging implementation
    """
    LOG_CRITICAL  = 0x00000001
    LOG_ERROR     = 0x00000002
    LOG_WARNING   = 0x00000004
    LOG_NOTICE    = 0x00000008
    LOG_INFO      = 0x00000010
    LOG_DEBUG     = 0x00000020
    LOG_TRACE     = 0x00000040

    LOG_NONE      = 0x00000000
    LOG_LOW       = 0x00000003  # CRITICAL & HIGH
    LOG_MED       = 0x0000000F  # LOW + WARNING & NOTICE
    LOG_HIGH      = 0x0000003F  # MED + INFO & DEBUG
    LOG_ALL       = 0xFFFFFFFF

    # Instance of class implementing LoggingInterface
    logger = None
    # Threading lock
    nofus_lock = threading.Lock()

    def __init__(self, log_file=None, log_level=None):
        if log_level is None:
            log_level = Logger.LOG_HIGH
        self.log_file = log_file
        self.log_level = log_level

    @staticmethod
    def register(logger):
        """
        Register a custom logger instead of using the built-in one
        :param logger An instance of a class that implements LoggingInterface
        """
        if not issubclass(logger.__class__, LoggingInterface):
            raise TypeError("Logger failure. Can only register classes which implement LoggingInterface.")
        Logger.logger = logger

    @staticmethod
    def disable():
        Logger.logger = False

    @staticmethod
    def initialize(log_file, log_level=None):
        if log_level is None:
            log_level = Logger.LOG_HIGH

        file_writable = os.path.isfile(log_file) and os.access(log_file, os.W_OK)
        can_create_file = not os.path.isfile(log_file) and os.access(os.path.dirname(log_file), os.W_OK)
        if file_writable or can_create_file:
            Logger.logger = Logger(log_file, log_level)
        else:
            raise IOError("Logger failure. Can not initialize; log file not writable.")

    def make_log(self, entry, log_level):
        if (self.log_level & log_level) != Logger.LOG_NONE:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            level = "CUSTOM"
            if log_level == Logger.LOG_CRITICAL:
                level = "CRITICAL"
            elif log_level == Logger.LOG_ERROR:
                level = "ERROR"
            elif log_level == Logger.LOG_WARNING:
                level = "WARNING"
            elif log_level == Logger.LOG_NOTICE:
                level = "NOTICE"
            elif log_level == Logger.LOG_INFO:
                level = "INFO"
            elif log_level == Logger.LOG_DEBUG:
                level = "DEBUG"
            elif log_level == Logger.LOG_TRACE:
                level = "TRACE"

            entry = "[{0}] [{1}] {2}".format(timestamp, level, entry) + os.linesep
            Logger.nofus_lock.acquire()
            with open(self.log_file, 'a+') as appendlog:
                appendlog.write(entry)
            Logger.nofus_lock.release()

    @staticmethod
    def _process_log(entry, log_level):
        if Logger.logger is None:
            raise RuntimeError("Logger failure. Logger not initialized.")
        elif Logger.logger is not False:
            Logger.logger.make_log(entry, log_level)

    @staticmethod
    def is_enabled(log_level):
        try:
            return (Logger.logger.log_level & log_level) != Logger.LOG_NONE
        except Exception as e:
            return None

    @staticmethod
    def critical(entry):
        Logger._process_log(entry, Logger.LOG_CRITICAL)

    @staticmethod
    def error(entry):
        Logger._process_log(entry, Logger.LOG_ERROR)

    @staticmethod
    def warning(entry):
        Logger._process_log(entry, Logger.LOG_WARNING)

    @staticmethod
    def notice(entry):
        Logger._process_log(entry, Logger.LOG_NOTICE)

    @staticmethod
    def info(entry):
        Logger._process_log(entry, Logger.LOG_INFO)

    @staticmethod
    def debug(entry):
        Logger._process_log(entry, Logger.LOG_DEBUG)

    @staticmethod
    def trace(entry):
        Logger._process_log(entry, Logger.LOG_TRACE)
