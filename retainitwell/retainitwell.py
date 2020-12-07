#!/usr/bin/env python3
description = "A simple tool to fetch website metrics from Kafka and retain them in PostgreSQL. Sibling to the aliveandwell tool"

#-----------------------------------------------------------------------

import sys
import os
import argparse
import time
import traceback
from datetime import datetime
import json
import platform
from pprint import pprint
import configparser

# Pip imports
import kafka
import psycopg2
from psycopg2.extras import RealDictCursor

#-----------------------------------------------------------------------

# Defaults
DEFAULT_GROUP_ID = "retainitwell_consumer_group"
DEFAULT_DELAY = 15
DEFAULT_TABLE = "aliveandwell_metrics"

#-----------------------------------------------------------------------

class Application():
    
    def __init__(self, postgres_uri, table, bootstrap, topic, group_id=DEFAULT_GROUP_ID, cafile=None, cert=None, key=None, delay=DEFAULT_DELAY, drop_table=False):
        self._table = table
        self._topic = topic
        self._group_id = group_id
        self._client_id = "retainitwell-on-{}".format(platform.node())
        self._delay = delay
        self._drop_table = drop_table
        
        # Postgres connection
        self._init_postgres(postgres_uri)
        
        # Init Kafka Consumer
        print("Connecting to Kafka as a consumer...")
        protocol = "PLAINTEXT"
        if cafile or cert or key:
            protocol = "SSL"
        self._topic = topic
        # Retry if the broker is not available at first
        self._consumer = None
        for i in range(2):
            try:
                self._consumer = kafka.KafkaConsumer(
                    self._topic,
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
    
    def _init_postgres(self, postgres_uri):
        self._pg = psycopg2.connect(postgres_uri)
        # After connecting, make sure the table is created
        if self._drop_table:
            self._do_drop_table()
        with self._cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """)
            table_list = [x["table_name"] for x in cur.fetchall()]
            print("Existing table list: {}".format(",".join(table_list)))
            cur.execute("""
                CREATE TABLE IF NOT EXISTS {} (
                    id    SERIAL PRIMARY KEY,
                    time  TIMESTAMPTZ NOT NULL,
                    data  JSON NOT NULL
                )
                """.format(self._table))
            self._pg.commit()
            
            # Test and see what values are already there
            cur.execute("""
                 SELECT * FROM {}
                 ORDER BY time DESC 
                 LIMIT 3
                 """.format(self._table))
            results = [x for x in reversed(cur.fetchall())]
            if len(results) > 0:
                print("Reading back the most recent metrics from the table...")
                for r in results:
                    print("{} data={}".format(r["id"], r["data"]))

    def _do_drop_table(self):
        with self._cursor() as cur:
            print("Dropping table {} so it can be re-created...".format(self._table))
            cur.execute("""
                DROP TABLE IF EXISTS {}
                """.format(self._table))
        self._pg.commit()
    
    def _cursor(self):
        return self._pg.cursor(cursor_factory=RealDictCursor)

    def run(self):
        backoff = self._delay
        while True:
            try:
                t = time.time()
                #raise Exception("Foo") # Fake error for testing backoff
                
                # Perform the actual polling-pass
                self.single_poll()
                # Handle the delay logic
                elapsed = time.time() - t
                if self._delay == -1:
                    pass
                elif elapsed > self._delay:
                    print("Polling cycle took longer than the delay ({:0.1f} > {}), so skipping any delay.".format(elapsed, self._delay))
                else:
                    sleep_by = self._delay - elapsed
                    print("Sleeping {:0.1f} seconds before polling again".format(sleep_by))
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
    
    def single_poll(self, store_metrics=True):
        print("Polling Kafka topic {} with group_id={} client_id={}".format(self._topic, self._group_id, self._client_id))
        metrics_batch = []
        for i in range(2): # Poll twice
            raw_messages = self._consumer.poll(timeout_ms=1000)
            for tp, messages in raw_messages.items():
                print(tp)
                for msg in messages:
                    try:
                        point = json.loads(msg.value.decode('utf-8'))
                    except Exception:
                        point = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "decode_error": True,
                            }
                    metrics_batch.append(point)
        print("Read {} metrics datapoints".format(len(metrics_batch)))
        if store_metrics:
            self._write_metrics(metrics_batch)
        # Let Kafka know we processed the metrics successfully
        self._consumer.commit()
        # Returning the metrics is not needed by the main applicaiton loop, but makes
        # integration testing easier
        return metrics_batch
    
    def _write_metrics(self, metrics_batch):
        print("Writing {} metrics into Postgresql table {}".format(len(metrics_batch), self._table))
        with self._cursor() as cursor:
            for point in metrics_batch:
                query = """
                    INSERT INTO {} (time, data)
                    VALUES(%s, %s)
                    """.format(self._table)
                time_str = point["timestamp"]
                data_str = json.dumps(point)
                cursor.execute(query, (time_str, data_str))
        self._pg.commit()

#-----------------------------------------------------------------------

EXAMPLE_CONFIG = """# Configuration file for retainitwell tool
[polling]
delay={}

[kafka]
# You can have multiple bootstrap hosts separated by commas
bootstrap=hostname:port
topic=mytopic
group={}
# These files are for the SSL connection
cafile=kafka_ca.pem
cert=kafka_service.cert
key=kafka_service.key

[postgres]
uri=postgres://user:pass@hostname:portnumber/databasename?sslmode=require
table={}

""".format(DEFAULT_DELAY, DEFAULT_GROUP_ID, DEFAULT_TABLE)

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
        if not args.delay:     args.delay     = config.get("polling", "delay", fallback=DEFAULT_DELAY)
        if not args.bootstrap: args.bootstrap = config.get("kafka", "bootstrap", fallback=None)
        if not args.topic:     args.topic     = config.get("kafka", "topic", fallback=None)
        if not args.cafile:    args.cafile    = config.get("kafka", "cafile", fallback=None)
        if not args.cert:      args.cert      = config.get("kafka", "cert", fallback=None)
        if not args.key:       args.key       = config.get("kafka", "key", fallback=None)
        if not args.postgres_uri: args.postgres_uri = config.get("postgres", "uri", fallback=None)
        if not args.table:     args.table     = config.get("postgres", "table", fallback=DEFAULT_TABLE)
    else:
        print("Configuration file {} does not exist. Use --init if you want to create an example config.".format(args.config))
    return args

#-----------------------------------------------------------------------

def retainitwell_commandline_entrypoint():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("postgres_uri", nargs="?", help="Postgres server URI in the format postgres://user:pass@hostname:portnumber/databasename?sslmode=require")
    parser.add_argument("-c", "--config", default="retainitwell.ini", help="A configuration file to read options from. Command-line arguments override options found in the config file.")
    parser.add_argument("--init", action="store_true", help="Create a sample ini file.")
    parser.add_argument("-b", "--bootstrap", help="A list of one or more Kafka bootstrap servers, separated by commas")
    parser.add_argument("-t", "--topic", help="The name of the Kafka topic to read from")
    parser.add_argument("-g", "--group", default=DEFAULT_GROUP_ID, help="Optionally override the kafka consumer group id.. The default is {}".format(DEFAULT_GROUP_ID))
    parser.add_argument("--cafile", help="A certificate authority file for SSL connection to Kafka")
    parser.add_argument("--cert", help="A certificate file for SSL connection to Kafka")
    parser.add_argument("--key", help="A certificate key file for SSL connection to Kafka")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY, help="Number of seconds to wait between each poll from Kafka. Defaults to {} seconds. -1 means poll once and quit immediately".format(DEFAULT_DELAY))
    parser.add_argument("--table", default=DEFAULT_TABLE, help="The name of the Postgres table where the metrics should be written. It will be created if it does not exist already.")
    parser.add_argument("--drop-table", action="store_true", help="Drop the Postgres table, and re-create it. Destructive!")
    args = parser.parse_args()
    args = handle_config_file(args)
    if args.postgres_uri is None or args.bootstrap is None or args.topic is None:
        parser.print_help()
        print("\nYou must specify the porstgres server uri, and at least one kafka bootstrap server and a kafka topic name\n")
        sys.exit()
    if args.drop_table:
        answer = input("You used the --drop-table argument to delete and re-create table {}. Are you sure? (yes/no): ".format(args.table))
        if answer.lower() == "yes":
            print("Okay! You know best!")
        else:
            print("Quitting...")
            sys.exit(1)
    app = Application(
        postgres_uri=args.postgres_uri,
        table=args.table,
        bootstrap=args.bootstrap.split(","),
        topic=args.topic,
        group_id=args.group,
        cafile=args.cafile,
        cert=args.cert,
        key=args.key,
        delay=args.delay,
        drop_table=args.drop_table,
        )
    app.run()


#-----------------------------------------------------------------------

if __name__ == "__main__":
    retainitwell_commandline_entrypoint()
