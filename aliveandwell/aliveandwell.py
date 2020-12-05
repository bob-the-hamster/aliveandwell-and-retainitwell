#!/usr/bin/env python3
description = "A simple tool to periodically check a website and send metrics to Kafka"

import sys
import argparse

# Pip imports
from kafka import KafkaProducer

#-----------------------------------------------------------------------

class Application():
    
    def __init__(self, bootstrap, topic, cafile=None, cert=None, key=None):
        protocol = "PLAINTEXT"
        if cafile or cert or key:
            protocol = "SSL"
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            security_protocol=protocol,
            ssl_cafile=cafile,
            ssl_certfile=cert,
            ssl_keyfile=key,
            )
        self._topic = topic
    
    def run(self):
        self._producer.send(self._topic, b'LoremIpsumDolorSitAmit')



#-----------------------------------------------------------------------

def aliveandwell_commandline_entrypoint():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-b", "--bootstrap", help="A list of one or more Kafka bootstrap servers, separated by commas")
    parser.add_argument("-t", "--topic", help="The name of the Kafka topic to write to")
    parser.add_argument("--cafile", help="A certificate authority file for SSL connection to Kafka")
    parser.add_argument("--cert", help="A certificate file for SSL connection to Kafka")
    parser.add_argument("--key", help="A certificate key file for SSL connection to Kafka")
    args = parser.parse_args()
    if args.bootstrap is None or args.topic is None:
        print("You must specify at least one kafka bootstrap server and a kafka topic name\n")
        parser.print_help()
        sys.exit()
    app = Application(
        bootstrap=args.bootstrap.split(","),
        topic=args.topic,
        cafile=args.cafile,
        cert=args.cert,
        key=args.key,
        )
    app.run()

#-----------------------------------------------------------------------

if __name__ == "__main__":
    aliveandwell_commandline_entrypoint()
