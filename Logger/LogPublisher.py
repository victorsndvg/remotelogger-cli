# -*- coding: utf-8 -*-

import logging
import pika
import json
import uuid

class RemoteLogConsumerDispacher(object):

    def __init__(self, config, exchange, exchange_type, queue, routing_key, logger):
        self._host           = config['host']
        self._port           = config['port']
        self._user           = config['user']
        self._pass           = config['pass']
        self._url            = 'amqp://'+self._user+':'+self._pass+'@'+self._host+':'+str(self._port)+'/'
        self._exchange       = exchange
        self._exchange_type  = exchange_type
        self._queue          = queue
        self._routing_key    = routing_key
        self._logger         = logger

        self._connection     = None
        self._channel        = None
        self._callback_queue = None

    def connect(self):
        self._logger.debug('Connecting: %s' % self._url)
        credentials = pika.PlainCredentials(self._user, self._pass) 
        parameters = pika.ConnectionParameters(host=self._host, port=self._port, credentials=credentials) 
        self._connection = pika.BlockingConnection(parameters)

    def channel_open(self):
        self._logger.debug('Opening channel')
        self._channel = self._connection.channel()

    def exchange_open(self):
        if self._exchange: 
            self._logger.info('Opening exchange: %s (%s)' % (self._exchange, self._exchange_type))
            self._channel.exchange_declare(exchange=self._exchange, exchange_type=self._exchange_type)

    def queue_open(self):
        self._logger.debug('Opening queue: %s' % self._queue)
        self._channel.queue_declare(queue=self._queue)

    def callback_queue_open(self):
        self._logger.debug('Opening callback queue')
        result = self._channel.queue_declare(exclusive=True)
        self._callback_queue = result.method.queue
        self._channel.basic_consume(self.on_response, no_ack=True, queue=self._callback_queue)

    def on_response(self, ch, method, props, body):
        if self._correlation_id == props.correlation_id:
            self._logger.info('Dispatch response: %s' % body)
            self.response = body

    def disconnect(self):
        self._logger.debug('Disconnecting')
        self._connection.close()

    def channel_close(self):
        self._logger.debug('Closing channel')
        self._channel.close()

    def exchange_close(self):
        if self._exchange: 
            self._logger.debug('Closing exchange: %s' % self._exchange)
            self._channel.exchange_delete(exchange=self._exchange)

    def queue_close(self):
        self._logger.debug('Closing queue: %s' % self._queue)
        self._channel.queue_delete(queue=self._queue)

    def callback_queue_close(self):
        self._logger.debug('Clossing callback queue')
        result = self._channel.queue_delete(self._queue)

    def on_response(self, ch, method, props, body):
        if self._correlation_id == props.correlation_id:
            self._logger.info('Dispatch response: %s' % body)
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
        self._logger.info('Dispatch consumer on: %r' % message)
        while self.response is None:
            self._connection.process_data_events()
        return self.response

    def start(self):
        self.connect()
        self.channel_open()
        self.exchange_open()
        self.queue_open()
        self.callback_queue_open()

    def stop(self):
        self.callback_queue_close()
        self.queue_close()
        self.exchange_close()
        self.channel_close()
        self.disconnect()


class LogPublisher(object):

    def __init__(self, config, logger):
        self._connection     = None
        self._channel        = None
        self._deliveries     = []
        self._acked          = 0
        self._nacked         = 0
        self._message_number = 0
        self._stopping       = False
        self._closing        = False

        self._url            = 'amqp://'+config['user']+':'+config['pass']+'@'+config['host']+':'+str(config['port'])+'/'
        self._host           = config['host']
        self._port           = config['port']
        self._user           = config['user']
        self._pass           = config['pass']
        self._exchange       = config['exchange']
        self._exchange_type  = config['exchange_type']
        self._queue          = config['queue']
        self._routing_key    = config['routing_key']
        self._heartbeat      = config['heartbeat']
        self._blocked_timeout= config['blocked_connection_timeout']
        self._logger         = logger

        dispatcher  = RemoteLogConsumerDispacher(config, '', '', '', 'rpc_queue', logger)
        dispatcher.start()
        dispatcher.dispatch(self._exchange, self._exchange_type, self._queue, self._routing_key)
        dispatcher.stop()

    def start(self):
        self.connect()
        self.channel_open()
        self.exchange_open()
        self.queue_open()
        self.queue_bind()

    def stop(self):
        self.queue_unbind()
        self.queue_close()
        self.exchange_close()
        self.channel_close()
        self.disconnect()

    def connect(self):
        self._logger.info('Connecting: %s' % self._url)
        credentials = pika.PlainCredentials(self._user, self._pass) 
        parameters = pika.ConnectionParameters(host=self._host, port=self._port, credentials=credentials, heartbeat_interval=self._heartbeat) 
        self._connection = pika.BlockingConnection(parameters)
        self._connection.add_on_connection_blocked_callback(self.connection_blocked_callback)
        self._connection.add_on_connection_unblocked_callback(self.connection_unblocked_callback)

    def channel_open(self):
        self._logger.info('Opening channel')
        self._channel = self._connection.channel()
        self._channel.confirm_delivery()
        self._channel.add_on_cancel_callback(self.channel_cancel_callback)
        self._channel.add_on_return_callback(self.channel_return_callback)

    def exchange_open(self):
        self._logger.info('Opening exchange: %s (%s)' % (self._exchange, self._exchange_type))
        self._channel.exchange_declare(exchange=self._exchange, exchange_type=self._exchange_type)

    def queue_open(self):
        self._logger.info('Opening queue: %s' % self._queue)
        self._channel.queue_declare(queue=self._queue)

    def queue_bind(self):
        self._logger.info('Binding queue "%s" to exchange "%s" with key "%s"' % (self._queue, self._exchange, self._routing_key))
        self._channel.queue_bind(queue=self._queue, exchange=self._exchange, routing_key=self._routing_key)

    def send(self, message):
        self._logger.info('Sending message: %s' % message)
        delivery = self._channel.basic_publish(exchange=self._exchange, routing_key=self._routing_key, body=message,
                                           properties=pika.BasicProperties(content_type='application/json', delivery_mode=1), mandatory=True)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        self._logger.info('Received %s for delivery tag: %i',confirmation_type, method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        self._logger.info('Published %i messages, %i have yet to be confirmed, %i were acked and %i were nacked', self._message_number, len(self._deliveries), self._acked, self._nacked)

    def channel_close(self):
        self._logger.info('Closing channel')
        self._channel.close()

    def exchange_close(self):
        self._logger.info('Clsing exchange: %s' % self._exchange)
        self._channel.exchange_delete(exchange=self._exchange)

    def queue_close(self):
        self._logger.info('Closing queue: %s' % self._queue)
        self._channel.queue_delete(queue=self._queue)

    def queue_unbind(self):
        self._logger.info('Unbinding queue "%s" from exchange "%s" with key "%s"' % (self._queue, self._exchange, self._routing_key))
        self._channel.queue_unbind(queue=self._queue, exchange=self._exchange, routing_key=self._routing_key)

    def disconnect(self):
        self._logger.info('Disconnecting')
        self._connection.close()

    def connection_blocked_callback(self, unused_frame):
        self._logger.info('Connection blocked callback')

    def connection_unblocked_callback(self, unused_frame):
        self._logger.info('Connection unblocked callback')

    def connection_backpressure_callback(self, unused_frame):
        self._logger.info('Connection backpressure callback')

    def connection_close_callback(self, unused_frame):
        self._logger.info('Connection close callback')

    def connection_open_callback(self, unused_frame):
        self._logger.info('Connection open callback')

    def connection_open_error_callback(self, unused_frame):
        self._logger.info('Connection open_error callback')

    def channel_cancel_callback(self, unused_frame):
        self._logger.info('Channel cancel callback')

    def channel_return_callback(self, unused_frame):
        self._logger.info('Channel return callback')

    def channel_callback(self, unused_frame):
        self._logger.info('Channel callback')

    def channel_close_callback(self, unused_frame):
        self._logger.info('Channel close callback')

    def channel_flow_callback(self, unused_frame):
        self._logger.info('Channel flow callback')









if __name__ == '__main__':
    LOG_FORMAT = ('%(levelname) -10s %(lineno) -5d: %(message)s')
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(__name__)
    url           = 'amqp://guest:guest@localhost:5672/%2F?connection_attempts=3&heartbeat_interval=3600'
    url           = 'localhost'
    exchange      = 'exchange'
    exchange_type = 'direct'
    queue         = 'queue'
    routing_key   = 'routing_key'
#    dispatcher  = RemoteLogConsumerDispacher('localhost', '', '', '', 'rpc_queue', logger)
#    dispatcher.run()

    if True:

        publisher  = LogPublisher(url, exchange, exchange_type, queue, routing_key, logger)
        publisher.connect()
        publisher.channel_open()
        publisher.exchange_open()
        publisher.queue_open()
        publisher.queue_bind()

        for i in range(1,2):
            publisher.send('hola'+str(i))

        publisher.queue_unbind()
        publisher.queue_close()
        publisher.exchange_close()
        publisher.channel_close()
        publisher.disconnect()




#    try:
#        publisher.run()
#    except KeyboardInterrupt:
#        publisher.stop()
