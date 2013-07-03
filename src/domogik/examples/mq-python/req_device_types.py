#!/usr/bin/python

import zmq
from zmq.eventloop.ioloop import IOLoop
from domogik.mq.reqrep.client import MQSyncReq
from domogik.mq.message import MQMessage

cli = MQSyncReq(zmq.Context())
msg = MQMessage()
msg.set_action('device_types.get')
msg.add_data('device_type', 'diskfree.disk_usage')
print cli.request('manager', msg.get(), timeout=10).get()

