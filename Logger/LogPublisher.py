# -*- coding: utf-8 -*-

import logging
import pika
import json
import uuid

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')


class RemoteLogConsumerDispacher(object):

    def __init__(self, amqp_url, exchange, exchange_type, queue, routing_key, logger):
        self._amqp_url       = amqp_url
        self._exchange       = exchange
        self._exchange_type  = exchange_type
        self._queue          = queue
        self._routing_key    = routing_key
        self._logger         = logger
        self._connection     = pika.BlockingConnection(pika.ConnectionParameters(host=amqp_url))
        self._channel        = self._connection.channel()
        result               = self._channel.queue_declare(exclusive=True)
        self._callback_queue = result.method.queue
        self._channel.basic_consume(self.on_response, no_ack=True, queue=self._callback_queue)

    def on_response(self, ch, method, props, body):
        if self._correlation_id == props.correlation_id:
            self._logger.info("Dispatch response: %r" % body)
            self.response = body

    def dispatch(self, exchange, exchange_type, queue, routing_key):
        self.response = None
        message = json.dumps({'exchange':exchange, 'exchange_type':exchange_type, 'queue':queue, 'routing_key':routing_key})
        self._correlation_id = str(uuid.uuid4())
        self._channel.basic_publish(exchange=self._exchange,
                                   routing_key=self._routing_key,
                                   properties=pika.BasicProperties(
                                         reply_to = self._callback_queue,
                                         correlation_id = self._correlation_id,
                                         ),
                                   body=message)
        self._logger.info("Dispatch consumer on: %r" % message)
        while self.response is None:
            self._connection.process_data_events()
        return self.response

class LogPublisher(object):

    def __init__(self, amqp_url, exchange, exchange_type, queue, routing_key, logger):
        self._connection     = None
        self._channel        = None
        self._deliveries     = []
        self._acked          = 0
        self._nacked         = 0
        self._message_number = 0
        self._stopping       = False
        self._closing        = False

        self._url            = amqp_url
        self._exchange       = exchange
        self._exchange_type  = exchange_type
        self._queue          = queue
        self._routing_key    = routing_key
        self._logger         = logger
        self._dispatcher     = RemoteLogConsumerDispacher('127.0.0.1', '', '', '', 'rpc_queue', logger)

    def connect(self):
        self._logger.info('Connecting to %s', self._url)
        self._dispatcher.dispatch(self._exchange, self._exchange_type, self._queue, self._routing_key)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        self._logger.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        self._logger.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self._logger.warning('Connection closed, reopening in 5 seconds: (%s) %s', reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._connection.ioloop.stop()
        self._connection = self.connect()
        self._connection.ioloop.start()

    def open_channel(self):
        self._logger.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self._logger.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self._exchange)

    def add_on_channel_close_callback(self):
        self._logger.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        self._logger.warning('Channel was closed: (%s) %s', reply_code, reply_text)
        if not self._closing:
            self._connection.close()

    def setup_exchange(self, exchange_name):
        self._logger.info('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self._exchange_type)

    def on_exchange_declareok(self, unused_frame):
        self._logger.info('Exchange declared')
        self.setup_queue(self._queue)

    def setup_queue(self, queue_name):
        self._logger.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name)


    def on_queue_declareok(self, method_frame):
        self._logger.info('Binding %s to %s with %s', self._exchange, self._queue, self._routing_key)
        self._channel.queue_bind(self.on_bindok, self._queue, self._exchange, self._routing_key)

    def on_bindok(self, unused_frame):
        self._logger.info('Queue bound')
        self.start_publishing()

    def start_publishing(self):
        self._logger.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()

    def enable_delivery_confirmations(self):
        self._logger.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        self._logger.info('Received %s for delivery tag: %i', confirmation_type, method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        self._logger.info('Published %i messages, %i have yet to be confirmed, %i were acked and %i were nacked',
                            self._message_number, len(self._deliveries), self._acked, self._nacked)

    def publish_message(self, message):
        if self._stopping:
            return

        properties = pika.BasicProperties(app_id='remotelogger-cli', content_type='application/json', headers=message)

        self._channel.basic_publish(self._exchange, self._routing_key,json.dumps(message, ensure_ascii=False), properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        self._logger.info('Published message # %i: %s', self._message_number, message)

    def close_queue(self):
        self._logger.info('Closing the queue')
        self._channel.queue_delete(queue=self._queue, if_unused=False, if_empty=True)

    def close_exchange(self):
        self._logger.info('Closing the exchange')
        self._channel.exchange_delete(exchange=self._exchange, if_unused=False)

    def close_channel(self):
        self._logger.info('Closing the channel')
        if self._channel:
            self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        self._logger.info('Stopping')
        self._stopping = True
        self.close_queue()
        self.close_exchange()
        self.close_channel()
        self.close_connection()
        self._connection.ioloop.stop()
        self._logger.info('Stopped')

    def close_connection(self):
        self._logger.info('Closing connection')
        self._closing = True
        self._connection.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)#, format=LOG_FORMAT)
    publisher = LogPublisher('amqp://guest:guest@localhost:5672/%2F?connection_attempts=3&heartbeat_interval=3600',
                            'logs', 'direct', 'logs', 'logs', logging.getLogger(__name__))
    try:
        publisher.run()
    except KeyboardInterrupt:
        publisher.stop()
