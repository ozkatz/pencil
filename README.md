What is Pencil?
===============

A non blocking statsd-like UDP proxy to the Graphite graphing server.
This is more than just a python implementation of statsd. the differences are:

1. Support for gauges (arbitrary numbers) in addition to aggregated counters and timers.
2. No forced name spaces. up to the client to determine the prefixes for his data.
3. Well, built in python. so no dependency on node.js if it isn't part of your stack.

Installation
------------

dependencies are described requirements.txt (pip installable).
but basically you need only python > 2.5 (tested against python 2.6 and python 2.7)
and the gevent (http://gevent.org) library for the nifty async I/O stuff.
in order to build gevent (latest version in pypi is too old), you need Cython installed.

Howto
-----
For most projects, installing dependecies and running `./pencil.py &` is sufficient.
A log file will be created in the local directory, with minimal information being logged.
pencil is compatible with most current statsd clients, although the pencil-client library is good reference
in case you also want gauges.

Changing settings:
Simply run `./pencil.py /path/to/settings.json &`

Available settings
------------------
     
+ **bind_adress** - Where to listen for incoming requests. this is a UDP port. 
  default value: `"127.0.0.1:8125"`  
+ **management_address** - For the telnet-like TCP interface. useful for stats and debugging.
  default value: `"127.0.0.1:8126"`
+ **flush_interval** - Time in seconds between flushes to Graphite.
  default value: `10`
+ **graphite_address** - Where graphite is listening to (127.0.0.1:2003 is the default for graphite).
  default value: `"127.0.0.1:2003"`
+ **log_name** - Path to the log file for the server.
  default value: `"pencil.log"`
+ **log_level** - How much information should be printed to the log file.
  default is `"info"`. possible values are: `"debug","info","warning","error"`.
  Choose `"error"` if you don't care and just want the minimum amount of logging done.