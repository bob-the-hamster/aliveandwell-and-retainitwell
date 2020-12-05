# aliveandwell and retainitwell

A pair of tools to monitor a website and write the results into a Kafka
topic, and then separately to read those same metrics from Kafka and
store them into Postgres


# Wishlist

* Read a configuration file as an alternative to command-line arguments
* Support scraping multiple websites in parallel
* Support for optional http auth for the websites being checked
* Exponential backoff and retry for catch-all exceptions
* Support more Kafka connection options besides just PLAINTEXT and SSL
* Support other time specifications besides seconds for delay argument
* More vigorous command-line argument checking for better error messages
  on wrong arguments
* More vigorous minimum-require-version testing for requirements.txt
