import unittest
import os
import sys
import configparser
from datetime import datetime
from pprint import pprint

import aliveandwell
import retainitwell

EXAMPLE_TEST_CONFIG="""# For aliveandwell & retainitwell tests.
# Run with: python3 -m unittest discover -s tests
[test]
# Change this to yes when the configuration is ready to use
okay_to_test=no

[kafka]
# You can have multiple bootstrap hosts separated by commas
bootstrap=hostname:port
# NOTE: The topic name must always be prefixed with "test_"
#       or the tests will not run. This is to protect your real topic
topic=test_mytopic
group=test_retainitwell_consumer_group
# These files are for the SSL connection
cafile=kafka_ca.pem
cert=kafka_service.cert
key=kafka_service.key

[postgres]
uri=postgres://user:pass@hostname:portnumber/databasename?sslmode=require
# NOTE: The table name must always be prefixed with "test_"
#       or the tests will not run. This is to protect your real table
table=test_aliveandwell_metrics
"""

#-----------------------------------------------------------------------

class TestAliveAndWellAndRetainItWell(unittest.TestCase):
    
    def setUp(self):
        edit_please = False

        # Create the sample test.ini if it is needed
        if not os.path.exists("test.ini"):
            with open("test.ini", "w") as f:
                f.write(EXAMPLE_TEST_CONFIG)
                os.chmod("test.ini", 0o600)
            edit_please = True
        else:
            # Check if test.ini is ready to use
            config = configparser.ConfigParser()
            with open("test.ini") as f:
                config.read_file(f)
                if config.get("test", "okay_to_test", fallback="no") != "yes":
                    edit_please = True
        
        if edit_please:
            raise Exception("Please edit test.ini with the kafka and postgres connection info for testing")
        
        print("Integration tests will be based on configuration in test.ini")
        self._bootstrap = config.get("kafka", "bootstrap", fallback=None)
        self._topic     = config.get("kafka", "topic", fallback="")
        self._group     = config.get("kafka", "group", fallback="")
        self._cafile    = config.get("kafka", "cafile", fallback=None)
        self._cert      = config.get("kafka", "cert", fallback=None)
        self._key       = config.get("kafka", "key", fallback=None)
        self._postgres_uri = config.get("postgres", "uri", fallback=None)
        self._table     = config.get("postgres", "table", fallback="")
        if not self._topic.startswith("test_"):
            raise Exception("Kafka topic in test.ini must start with test_")
        if not self._table.startswith("test_"):
            raise Exception("Postgres table in test.ini must start with test_")
        self.alive = aliveandwell.Application(
            website="https://google.com",
            bootstrap=self._bootstrap.split(","),
            topic=self._topic,
            cafile=self._cafile,
            cert=self._cert,
            key=self._key,
            delay=-1,
            )
        self.retain = retainitwell.Application(
            postgres_uri=self._postgres_uri,
            table=self._table,
            bootstrap=self._bootstrap.split(","),
            topic=self._topic,
            group_id=self._group,
            cafile=self._cafile,
            cert=self._cert,
            key=self._key,
            delay=-1,
            drop_table=True,
            )
    
    def test_kafka_sanity(self):
        # Run a single retain pass to clear any data in the Kafka topic
        # that might be left over from a previous testing pass
        self.retain.single_poll(store_metrics=False)
        # Now fake a single check
        timestamp = datetime.utcnow().isoformat() + "Z"
        message = {
            "url": "https://fake.website",
            "timestamp": timestamp,
            "status_code": 999,
            "request_time": 0.1234,
            }
        self.alive._send_to_kafka(message)
        # Now see if we can get those metrics back from Kafka
        metrics = self.retain.single_poll(store_metrics=False)
        self.assertEqual(len(metrics), 1)
        m = metrics[0]
        self.assertEqual(m["url"], "https://fake.website")
        self.assertEqual(m["timestamp"], timestamp)
        self.assertEqual(m["status_code"], 999)
        self.assertEqual(m["request_time"], 0.1234)


#-----------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
