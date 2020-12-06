# aliveandwell and retainitwell

A pair of tools to monitor a website and write the results into a Kafka
topic, and then separately to read those same metrics from Kafka and
store them into Postgres

# Wishlist

* Read a configuration file as an alternative to command-line arguments
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
* Add a minimum-delay option for the looping logic

# Thanks to the authors of

* https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html
* https://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html
* https://help.aiven.io/en/articles/489572-getting-started-with-aiven-kafka
* https://www.postgresqltutorial.com/postgresql-json/
* https://help.aiven.io/en/articles/489573-getting-started-with-aiven-postgresql
