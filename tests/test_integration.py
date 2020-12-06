import unittest
import os
import sys
import configparser

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
    
    def test_sanity(self):
        alive = aliveandwell.Application(
            website="https://google.com",
            bootstrap=self._bootstrap.split(","),
            topic=self._topic,
            cafile=self._cafile,
            cert=self._cert,
            key=self._key,
            delay=-1,
            )
        retain = retainitwell.Application(
            postgres_uri=self._postgres_uri,
            table=self._table,
            bootstrap=self._bootstrap.split(","),
            topic=self._topic,
            group_id=self._group,
            cafile=self._cafile,
            cert=self._cert,
            key=self._key,
            delay=-1,
            )
        


#-----------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
