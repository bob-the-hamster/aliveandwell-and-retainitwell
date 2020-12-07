# aliveandwell and retainitwell

A pair of tools to monitor a website and write the results into a Kafka
topic, and then separately to read those same metrics from Kafka and
store them into Postgres

aliveandwell is the Kafka producer. It does the website monitoring.
retainitwell is the Kafka consumer. It stores the metrics in postgres.

# Instructions

The tools are named aliveandwell and retainitwell and they can be installed
with pip3, or you can directly run the aliveandwell/aliveandwell.py or
retainitwell/retainitwell.py scripts

Run with --help for command-line arguments.
Run with --init to write a sample configuration file into the current directory

```
pip3 install aliveandwell_and_retainitwell
aliveandwell --init
retainitwell --init
```

Edit the configuration files with your Kafka and Postgres connection info

## Running tests
Integration tests require configuration to communicate with instances of
kafka and Postgres. The first time you run the tests you will be prompted
with instructions
```
python3 -m unittest discover -s tests
```

# Wishlist
* More tests! Better tests! :D
* Add InfluxDB write support in addition to Postgres
* Figure out how to make the Grafana Postgres Datasource work for
  visualization
* Support scraping multiple websites in parallel
* Support for optional http auth for the websites being checked
* Decide if I want to enable retries for failed sends
* Support more Kafka connection options besides just PLAINTEXT and SSL
* Support other time specifications besides seconds for delay argument
* More vigorous command-line argument checking for better error messages
  on wrong arguments
* More vigorous minimum-require-version testing for requirements.txt
* Support for understanding json payload responses, and for extracting
  metrics from it
* Support for multiple regexes as different values in the kafka data
* Support for regex extraction of a substring match as a metric
* Generalize some of the looping/retry logic into a shared parent class
* Create a slightly more high-level convenience wrapper for postgres
* Add a minimum-delay option for the looping logic

# Tested with
* Python 3.5 on Debian 9
* Kafka 2.6 on Aiven.io
* Postgres 12.5 on Aiven.io

# Thanks to the authors of

* https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html
* https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html
* https://help.aiven.io/en/articles/489572-getting-started-with-aiven-kafka
* https://www.postgresqltutorial.com/postgresql-json/
* https://help.aiven.io/en/articles/489573-getting-started-with-aiven-postgresql
