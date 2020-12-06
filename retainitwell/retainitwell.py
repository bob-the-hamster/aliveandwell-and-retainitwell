#!/usr/bin/env python3
description = "A simple tool to fetch website metrics from Kafka and retain them in PostgreSQL. Sibling to the aliveandwell tool"

#-----------------------------------------------------------------------

import sys
import argparse
import time
import traceback
from datetime import datetime
import platform

# Pip imports
import kafka

#-----------------------------------------------------------------------

# Defaults
DEFAULT_GROUP_ID = "retainitwell_consumer_group"

#-----------------------------------------------------------------------

class Application():
    
    def __init__(self, bootstrap, topic, group_id=DEFAULT_GROUP_ID, cafile=None, cert=None, key=None):
        self._group_id = group_id
        self._client_id = "retainitwell-on-{}".format(platform.node())
        
        # Init Kafka Consumer
        protocol = "PLAINTEXT"
        if cafile or cert or key:
            protocol = "SSL"
        self._topic = topic
        # Retry if the broker is not available at first
        self._consumer = None
        for i in range(2):
            try:
                self._consumer = kafka.KafkaConsumer(
                    topic,
                    auto_offset_reset="earliest",
                    bootstrap_servers=bootstrap,
                    client_id=self._client_id,
                    group_id=self._group_id,
                    security_protocol=protocol,
                    ssl_cafile=cafile,
                    ssl_certfile=cert,
                    ssl_keyfile=key,
                    )
            except kafka.errors.NoBrokersAvailable as e:
                print("{} trying again in 10 seconds ({}/3)".format(str(e), i+1))
                time.sleep(10)
        if self._consumer is None:
            print("Unable to connect to Kafka broker")
            sys.exit(1)
    
    def run(self):
        print("Polling Kafka with group_id={} client_id={}".format(self._group_id, self._client_id))
        for i in range(2): # Poll twice
            raw_messages = self._consumer.poll(timeout_ms=1000)
            for tp, messages in raw_messages.items():
                print(tp)
                for msg in messages:
                    print("Received: {}".format(msg.value))        


#-----------------------------------------------------------------------

def retainitwell_commandline_entrypoint():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-b", "--bootstrap", help="A list of one or more Kafka bootstrap servers, separated by commas")
    parser.add_argument("-t", "--topic", help="The name of the Kafka topic to read from")
    parser.add_argument("-g", "--group", default=DEFAULT_GROUP_ID, help="Optionally override the kafka consumer group id.. The default is {}".format(DEFAULT_GROUP_ID))
    parser.add_argument("--cafile", help="A certificate authority file for SSL connection to Kafka")
    parser.add_argument("--cert", help="A certificate file for SSL connection to Kafka")
    parser.add_argument("--key", help="A certificate key file for SSL connection to Kafka")
    args = parser.parse_args()
    if args.bootstrap is None or args.topic is None:
        parser.print_help()
        print("\nYou must specify the website url, and at least one kafka bootstrap server and a kafka topic name\n")
        sys.exit()
    app = Application(
        bootstrap=args.bootstrap.split(","),
        topic=args.topic,
        group_id=args.group,
        cafile=args.cafile,
        cert=args.cert,
        key=args.key,
        )
    app.run()


#-----------------------------------------------------------------------

if __name__ == "__main__":
    retainitwell_commandline_entrypoint()
