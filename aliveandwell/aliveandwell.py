#!/usr/bin/env python3
description = "A simple tool to periodically check a website and send metrics to Kafka. Sibling to the retainitwell tool"

#-----------------------------------------------------------------------

import sys
import os
import argparse
import time
import traceback
import json
import re
from datetime import datetime
import configparser

# Pip imports
import kafka
import requests

#-----------------------------------------------------------------------

# Defaults
DEFAULT_DELAY = 60

#-----------------------------------------------------------------------

class Application():
    
    def __init__(self, website, bootstrap, topic, cafile=None, cert=None, key=None, delay=DEFAULT_DELAY, regex=None):
        self._website = website
        self._delay = delay
        
        # Init Kafka producer
        print("Connecting to Kafka as a producer...")
        protocol = "PLAINTEXT"
        if cafile or cert or key:
            protocol = "SSL"
        self._topic = topic
        # Retry if the broker is not available at first
        self._producer = None
        for i in range(2):
            try:
                self._producer = kafka.KafkaProducer(
                    bootstrap_servers=bootstrap,
                    security_protocol=protocol,
                    ssl_cafile=cafile,
                    ssl_certfile=cert,
                    ssl_keyfile=key,
                    )
            except kafka.errors.NoBrokersAvailable as e:
                print("{} trying again in 10 seconds ({}/3)".format(str(e), i+1))
                time.sleep(10)
        if self._producer is None:
            print("Unable to connect to Kafka broker")
            sys.exit(1)

        self._regex = None
        if regex:
            self._regex = re.compile(regex)
    
    def run(self):
        backoff = self._delay
        while True:
            try:
                t = time.time()
                #raise Exception("Foo") # Fake error for testing backoff
                
                # Perform the actual check-pass
                self.single_check()
                # Handle the delay logic
                elapsed = time.time() - t
                if self._delay == -1:
                    pass
                elif elapsed > self._delay:
                    print("Check cycle took longer than the delay ({:0.1f} > {}), so skipping any delay.".format(elapsed, self._delay))
                else:
                    sleep_by = self._delay - elapsed
                    print("Sleeping {:0.1f} seconds before checking again".format(sleep_by))
                    time.sleep(sleep_by)
                
                # A check pass completed successfully!
                backoff = self._delay
                
            except KeyboardInterrupt:
                print("\nCancelled by user, exiting...")
                sys.exit()
                
            except Exception as e:
                # Any failure in this loop should cause a retry, with a growing backoff
                # (but don't retry less than once every 6 hours)
                traceback.print_exc()
                print("A error occured, trying again in {} seconds".format(backoff))
                try:
                    time.sleep(backoff)
                except KeyboardInterrupt:
                    print("\nCancelled by user, exiting...")
                    sys.exit()
                backoff = min(int(max(backoff, 1) * 2), 60*60*6)
                
            if self._delay == -1:
                "Break after a polling check..."
                break

    def single_check(self, store_metrics=True):
        print("Checking whether {} is alive and well...".format(self._website))
        r = requests.get(self._website)
        message = {
            "url": self._website,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status_code": r.status_code,
            "request_time": r.elapsed.total_seconds(),
            }
        if self._regex:
            message["regex_match"] = bool(self._regex.search(r.text))
        if store_metrics:
            self._send_to_kafka(message)
        return message
    
    def _send_to_kafka(self, message):
        result = self._producer.send(self._topic, json.dumps(message, sort_keys=True).encode("utf-8"))
        self._producer.flush()
        print(message)
        return result



#-----------------------------------------------------------------------

EXAMPLE_CONFIG = """# Configuration file for aliveandwell tool
[monitor]
website=https://put.the.real.url.here/
delay={}
#regex=

[kafka]
# You can have multiple bootstrap hosts separated by commas
bootstrap=hostname:port
topic=mytopic
# These files are for the SSL connection
cafile=kafka_ca.pem
cert=kafka_service.cert
key=kafka_service.key
""".format(DEFAULT_DELAY)

def handle_config_file(args):
    if args.init:
        if os.path.exists(args.config):
            print("--init option was specified but config file {} already exists.".format(args.config))
            sys.exit(1)
        with open(args.config, "w") as f:
            f.write(EXAMPLE_CONFIG)
        os.chmod(args.config, 0o600)
        print("Wrote a sample configuration to {}".format(args.config))
        sys.exit(1)
        
    if os.path.exists(args.config):
        print("Reading configuration file {}".format(args.config))
        config = configparser.ConfigParser()
        with open(args.config) as f:
            config.read_file(f)
        if not args.website:   args.website   = config.get("monitor", "website", fallback=None)
        if not args.delay:     args.delay     = config.get("monitor", "delay", fallback=DEFAULT_DELAY)
        if not args.regex:     args.regex     = config.get("monitor", "regex", fallback=None)
        if not args.bootstrap: args.bootstrap = config.get("kafka", "bootstrap", fallback=None)
        if not args.topic:     args.topic     = config.get("kafka", "topic", fallback=None)
        if not args.cafile:    args.cafile    = config.get("kafka", "cafile", fallback=None)
        if not args.cert:      args.cert      = config.get("kafka", "cert", fallback=None)
        if not args.key:       args.key       = config.get("kafka", "key", fallback=None)
    else:
        print("Configuration file {} does not exist. Use --init if you want to create an example config.".format(args.config))
    return args

#-----------------------------------------------------------------------

def aliveandwell_commandline_entrypoint():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("website", nargs="?", help="The website url to monitor")
    parser.add_argument("-c", "--config", default="aliveandwell.ini", help="A configuration file to read options from. Command-line arguments override options found in the config file.")
    parser.add_argument("--init", action="store_true", help="Create a sample ini file.")
    parser.add_argument("-b", "--bootstrap", help="A list of one or more Kafka bootstrap servers, separated by commas")
    parser.add_argument("-t", "--topic", help="The name of the Kafka topic to write to")
    parser.add_argument("--cafile", help="A certificate authority file for SSL connection to Kafka")
    parser.add_argument("--cert", help="A certificate file for SSL connection to Kafka")
    parser.add_argument("--key", help="A certificate key file for SSL connection to Kafka")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY, help="Number of seconds to wait between each website check. Defaults to {} seconds. -1 means test once and quit immediately".format(DEFAULT_DELAY))
    parser.add_argument("--regex", help="An optional regular expression pattern to search for in the response text. If specified, there will be a regex_match metrics that is True or False")
    args = parser.parse_args()
    args = handle_config_file(args)
    if args.website is None or args.bootstrap is None or args.topic is None:
        parser.print_help()
        print("\nYou must specify the website url, and at least one kafka bootstrap server and a kafka topic name\n")
        sys.exit()
    app = Application(
        website=args.website,
        bootstrap=args.bootstrap.split(","),
        topic=args.topic,
        cafile=args.cafile,
        cert=args.cert,
        key=args.key,
        delay=args.delay,
        regex=args.regex,
        )
    app.run()

#-----------------------------------------------------------------------

if __name__ == "__main__":
    aliveandwell_commandline_entrypoint()
