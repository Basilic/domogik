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
=============

Implements
==========

class XplManager(XplPlugin):

@author: Maikel Punie <maikel.punie@gmail.com>
@copyright: (C) 2007-2013 Domogik project
@license: GPL(v3)
@organization: Domogik
"""
from domogik.xpl.common.xplconnector import Listener
from domogik.xpl.common.plugin import XplPlugin
from domogik.common.database import DbHelper
from domogik.xpl.common.xplmessage import XplMessage
from domogik.mq.pubsub.publisher import MQPub
from domogik.mq.pubsub.subscriber import MQSyncSub
from domogik.mq.reqrep.client import MQSyncReq
from domogik.mq.message import MQMessage
import time
import traceback
import calendar
import zmq
import json
from domogik.common.utils import call_package_conversion

################################################################################
class XplManager(XplPlugin):
    """ Statistics manager
    """

    def __init__(self):
        """ Initiate DbHelper, Logs and config
        """
        XplPlugin.__init__(self, 'xplgw')
        self.log.info(u"XPL manager initialisation...")
        self._db = DbHelper()
        self.pub = MQPub(zmq.Context(), 'xplgw')
        self.stats = None
        self.client_xpl_map = {}
        self._load_client_to_xpl_target()
        self.load()
        self.ready()

    def on_mdp_request(self, msg):
	# XplPlugin handles MQ Req/rep also
        XplPlugin.on_mdp_request(self, msg)

        if msg.get_action() == "reload":
            self.load()
            msg = MQMessage()
            msg.set_action( 'reload.result' )
            self.reply(msg.get())
	elif msg.get_action() == "cmd.send":
            self._send_xpl_command(msg)

    def _load_client_to_xpl_target(self):
        cli = MQSyncReq(self.zmq)
        msg = MQMessage()
        msg.set_action('client.list.get')
        response = cli.request('manager', msg.get(), timeout=10)
        if response:
            data = response.get_data()
            for cli in data:
                self.client_xpl_map[cli] = data[cli]['xpl_source']
        else:
            self.log.error(u"Updating client list was not successfull, no response from manager")


    def _send_xpl_command(self, data):
        """ Reply to config.get MQ req
            @param data : MQ req message
                Needed info in data:
                - cmdid         => command id to send
                - cmdparams     => key/value pair of all params needed for this command
        """
	with self._db.session_scope():
	    self.log.info(u"Received new cmd request: {0}".format(data))
            failed = False

            request = data.get_data()
            if 'cmdid' not in request:
                failed = "cmdid not in message data"
            if 'cmdparams' not in request:
                failed = "cmdparams not in message data"
            if not failed:
                # get the command
		cmd = self._db.get_command(request['cmdid'])
		if cmd is not None:
		    if cmd.xpl_command is not None:
		        xplcmd = cmd.xpl_command
			xplstat = self._db.get_xpl_stat(xplcmd.stat_id)
			if xplstat is not None:
			    # get the device from the db
			    dev = self._db.get_device(int(cmd.device_id))
			    msg = XplMessage()
                            # update the client list
                            if not dev['client_id'] in list(self.client_xpl_map.keys()):
                                self._load_client_to_xpl_target()
                            if not dev['client_id'] in list(self.client_xpl_map.keys()):
                                failed = "Can not fincd xpl source for {0} client_id".format(dev['client_id'])
                            else:
                                msg.set_target(self.client_xpl_map[dev['client_id']])
                            msg.set_source(self.myxpl.get_source())
			    msg.set_type("xpl-cmnd")
			    msg.set_schema( xplcmd.schema)
			    # static params
			    for p in xplcmd.params:
			        msg.add_data({p.key : p.value})
			    # dynamic params
			    for p in cmd.params:
				if p.key in request['cmdparams']:
				    value = request['cmdparams'][p.key]
				    # chieck if we need a conversion
				    if p.conversion is not None and p.conversion != '':
				        value = call_package_conversion(\
						self.log, dev['client_id'], \
						p.conversion, value)
				    msg.add_data({p.key : value})
				else:
				    failed = "Parameter ({0}) for device command msg is not provided in the mq message".format(p.key)
                            if not failed:
			        # send out the msg
			        self.log.debug(u"sending xplmessage: {0}".format(msg))
			        self.myxpl.send(msg)
			        ### Wait for answer
			        stat_received = 0
			        if xplstat != None:
				    # get xpl message from queue
				    self.log.debug(u"Command : wait for answer...")
				    sub = MQSyncSub( self.zmq, 'rest-command', ['device-stats'] )
				    stat = sub.wait_for_event()
				    if stat is not None:
				        reply = json.loads(stat['content'])
				        reply_msg = MQMessage()
				        reply_msg.set_action('cmd.send.result')
				        reply_msg.add_data('stat', reply)
				        reply_msg.add_data('status', True)
				        reply_msg.add_data('reason', None)
				        self.log.debug(u"mq reply".format(reply_msg.get()))
				        self.reply(reply_msg.get())
			else:
			    failed = "xplStat {0} does not exists".format(xplcmd.stat_id)
		    else:
                        failed = "Command {0} has no associated xplcommand".format(cmd.id)
		else:
		    failed = "Command {0} does not exists".format(request['cmdid'])

            if failed:
		self.log.error(failed)
     		reply_msg = MQMessage()
                reply_msg.set_action('cmd.send.result')
                reply_msg.add_data('status', False)
                reply_msg.add_data('reason', failed)
                self.log.debug(u"mq reply".format(reply_msg.get()))
                self.reply(reply_msg.get())

    def load(self):
        """ (re)load all xml files to (re)create _Stats objects
        """
        self.log.info(u"Rest Stat Manager loading.... ")
        self._db.open_session()
        try:
            # not the first load : clean
            if self.stats != None:
                self.log.info(u"reloading")
                for stat in self.stats:
                    self.myxpl.del_listener(stat.get_listener())

            ### Load stats
            # key1, key2 = device_type_id, schema
            self.stats = []
            for sen in self._db.get_all_sensor():
                self.log.debug(sen)
                statparam = self._db.get_xpl_stat_param_by_sensor(sen.id)
                if statparam is None:
                    self.log.error( \
                            'Corresponding xpl-stat param can not be found for sensor {0}' \
                            .format(sen))
                    continue
                stat = self._db.get_xpl_stat(statparam.xplstat_id)
                if stat is None:
                    self.log.error( \
                            'Corresponding xpl-stat can not be found for xplstatparam {0}' \
                            .format(statparam))
                    continue
                dev = self._db.get_device(stat.device_id)
                if dev is None:
                    self.log.error(\
                            'Corresponding device can not be found for xpl-stat {0}' \
                            .format(stat))
                    continue
                # xpl-trig
                self.stats.append(self._Stat(self.myxpl, dev, stat, sen, \
                                  "xpl-trig", self.log, self._db, self.pub))
                # xpl-stat
                self.stats.append(self._Stat(self.myxpl, dev, stat, sen, \
                                  "xpl-stat", self.log, self._db, self.pub))
        except:
            self.log.error(u"%s" % traceback.format_exc())
        self._db.close_session()
        self.log.info(u"Loading finished")

    class _Stat:
        """ This class define a statistic parser and logger instance
        Each instance create a Listener and the associated callbacks
        """

        def __init__(self, xpl, dev, stat, sensor, xpl_type, log_stats, dbh, pub):
            """ Initialize a stat instance
            @param xpl : A xpl manager instance
            @param dev : A Device reference
            @param stat : A XplStat reference
            @param sensor: A Sensor reference
            @param xpl-type: what xpl-type to listen for
            """
            ### Rest data
            self._db = dbh
            self._log_stats = log_stats
            self._dev = dev
            self._stat = stat
            self._sen = sensor
            self._pub = pub

            ### build the filter
            params = {'schema': stat.schema, 'xpltype': xpl_type}
            for param in stat.params:
                if param.static:
                    params[param.key] = param.value

            ### start the listener
            self._log_stats.info("creating listener for %s" % (params))
            self._listener = Listener(self._callback, xpl, params)

        def get_listener(self):
            """ getter for lsitener object
            """
            return self._listener

        def _callback(self, message):
            """ Callback for the xpl message
            @param message : the Xpl message received
            """
            self._log_stats.debug("Stat received for device {0}." \
                    .format(self._dev['name']))
            current_date = calendar.timegm(time.gmtime())
            stored_value = None
            try:
                # find what parameter to store
                for param in self._stat.params:
                    # self._log_stats.debug("Checking param {0}".format(param))
                    if param.sensor_id is not None and param.static is False:
                        if param.key in message.data:
                            value = message.data[param.key]
                            # self._log_stats.debug( \
                            #        "Key found {0} with value {1}." \
                            #        .format(param.key, value))
                            store = True
                            if param.ignore_values:
                                if value in eval(param.ignore_values):
                                    self._log_stats.debug( \
                                            "Value {0} is in the ignore list {0}, so not storing." \
                                            .format(value, param.ignore_values))
                                    store = False
                            if store:
                                # check if we need a conversion
                                if self._sen.conversion is not None and self._sen.conversion != '':
                                    value = call_package_conversion(\
                                                self._log_stats, \
                                                self._dev['client_id'], \
                                                self._sen.conversion, \
                                                value)
                                self._log_stats.info( \
                                        "Storing stat for device '{0}' ({1}) and sensor'{2}' ({3}): key '{4}' with value '{5}' after conversion." \
                                        .format(self._dev['name'], self._dev['id'], self._sen.name, self._sen.id, param.key, value))
                                # do the store
                                stored_value = value
                                my_db = DbHelper()
                                with my_db.session_scope():
                                    my_db.add_sensor_history(\
                                            param.sensor_id, \
                                            value, \
                                            current_date)
                                del(my_db)
                            else:
                                self._log_stats.debug("Don't need to store this value")
                        #else:
                        #    self._log_stats.debug("Key not found in message data")
                    #else:
                    #    self._log_stats.debug("No sensor attached")
            except:
                self._log_stats.error(traceback.format_exc())
            # publish the result
            self._pub.send_event('device-stats', \
                          {"timestamp" : current_date, \
                          "device_id" : self._dev['id'], \
                          "sensor_id" : self._sen.id, \
                          "stored_value" : stored_value})

if __name__ == '__main__':
    EVTN = XplManager()
