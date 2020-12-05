A pair of tools to monitor a website and write the results into a Kafka
topic, and then separately to read those same metrics from Kafka and
store them into Postgres


# Wishlist

* Read a configuration file as an alternative to command-line arguments
* Support more Kafka connection options besides just PLAINTEXT and SSL
* More vigorous command-line argument checking for better error messages
  on wrong arguments
