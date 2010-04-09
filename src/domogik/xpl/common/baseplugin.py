#!/usr/bin/python
# -*- coding: utf-8 -*-                                                                           

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Base class for all clients

Implements
==========

- BasePlugin

@author: Maxence Dunnewind <maxence@dunnewind.net>
@copyright: (C) 2007-2009 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

import threading

from domogik.common import logger
from optparse import OptionParser
from domogik.common.daemonize import createDaemon

class BasePlugin():
    """ Basic plugin class, manage common part of all plugins.
    For all xPL plugins, the xPLPlugin class must be use as a basis, not this one.
    This class is a Singleton
    """

    __instance = None 

    def __init__(self, name = None, stop_cb = None, parser = None, daemonize = True):
        """ @param name : Name of current plugin 
            @param parser : An instance of OptionParser. If you want to add extra options to the generic option parser,
            create your own optionparser instance, use parser.addoption and then pass your parser instance as parameter.
            Your options/params will then be available on self.options and self.params
            @param daemonize : If set to False, force the instance *not* to daemonize, even if '-f' is not passed 
            on the command line. If set to True (default), will check if -f was added.
        """
        if BasePlugin.__instance is None:
            BasePlugin.__instance = BasePlugin.__Singl_BasePlugin(name, stop_cb, parser, daemonize)

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        try:
            return getattr(self.__instance, attr)
        except:
            pass

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)

    class __Singl_BasePlugin:

        def __init__(self, name, stop_cb = None, p = None, daemonize = True):
            ''' singleton instance
            @param p : An instance of OptionParser. If you want to add extra options to the generic option parser,
            create your own optionparser instance, use parser.addoption and then pass your parser instance as parameter.
            Your options/params will then be available on self.options and self.params
            @param daemonize : If set to False, force the instance *not* to daemonize, even if '-f' is not passed 
            on the command line. If set to True (default), will check if -f was added.
            '''
            print "create Base plugin instance"
            if p is not None and isinstance(p, OptionParser):
                parser = p
            else:
                parser = OptionParser()
            parser.add_option("-f", action="store_true", dest="run_in_foreground", default=False, \
                    help="Run the plugin in foreground, default to background.")
            (self.options, self.args) = parser.parse_args()
            if not self.options.run_in_foreground and daemonize:
                createDaemon()
                l = logger.Logger(name)
                self._log = l.get_logger()
                self._log.info("Daemonize plugin %s" % name)
                self.is_daemon = True
            else:
                l = logger.Logger(name)
                self._log = l.get_logger()
                self.is_daemon = False
            self._threads = []
            self._timers = []
            if name is not None:
                self._plugin_name = name
            self._stop = threading.Event()
            self._lock_add_thread = threading.Semaphore()
            self._lock_add_timer = threading.Semaphore()
            self._lock_add_cb = threading.Semaphore()
            if stop_cb is not None:
                self._stop_cb = [stop_cb]
            else:
                self._stop_cb = []

        def get_my_logger(self):
            """
            Returns the associated logger instance
            """
            return self._log

        def should_stop(self):
            '''
            Check if the plugin should stop
            This method should be called to check loop condition in threads
            '''
            return self._stop.isSet()

        def get_stop(self):
            '''
            Returns the Event instance
            '''
            return self._stop

        def get_plugin_name(self):
            """
            Returns the name of the current plugin
            """
            return self._plugin_name

        def register_thread(self, thread):
            '''
            Register a thread in the current instance
            Should be called by each thread at start
            @param thread : the thread to add
            '''
            self._lock_add_thread.acquire()
           # self._log.debug('New thread registered : %s' % thread)
            self._threads.append(thread)
            self._lock_add_thread.release()

        def unregister_thread(self, thread):
            '''
            Unregister a thread in the current instance
            Should be the last action of each thread
            @param thread : the thread to remove
            '''
            self._lock_add_thread.acquire()
            if thread in self._threads:
                self._log.debug('Unregister thread')
                self._threads.remove(thread)
            self._lock_add_thread.release()

        def register_timer(self, timer):
            '''
            Register a time in the current instance
            Should be called by each timer
            @param timer : the timer to add
            '''
            self._lock_add_timer.acquire()
            self._log.debug('New timer registered : %s' % timer)
            self._timers.append(timer)
            self._lock_add_timer.release()

        def unregister_timer(self, timer):

            '''
            Unregister a timer in the current instance
            Should be the last action of each timer
            @param timer : the timer to remove
            '''
            self._lock_add_timer.acquire()
            if timer in self._timers:
                self._log.debug('Unregister timer')
                self._timers.remove(timer)
            self._lock_add_timer.release()

        def add_stop_cb(self, cb):
            '''
            Add an additionnal callback to call when a stop request is received
            '''
            self._lock_add_cb.acquire()
            self._stop_cb.append(cb)
            self._lock_add_cb.release()

        def __del__(self):
            self._log.debug("__del__ baseplugin")

