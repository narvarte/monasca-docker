#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function

import csv
import json
import subprocess
import sys

from time import localtime, gmtime, strftime

###############################################################################
#
# Global values
#
###############################################################################

# Report warning when Kafka lag jump over this value
KAFKA_PROBLEM_LAG = 20000

# String for using docker-compose to exec commands in all services
DOCKER_EXEC = ["docker-compose",
               "-f", "docker-compose-metric.yml",
               "-f", "docker-compose-log.yml",
               "exec"]


print("Running simple tests of running Monasca services")
print("Local time {}".format(strftime("%Y-%m-%d %H:%M:%S", localtime())))
print("UTC time   {}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))

def check_print(func):
    def func_wrapper():
        # Print func name with "test_" stripped
        print("Checking '{}'".format(func.__name__[5:]))
        return func()
    return func_wrapper

def print_info(service_name, test_function):
    CGREEN = '\033[92m'
    CRED = '\033[91m'
    CEND = '\033[0m'
    if test_function != 0:
        print("\n{}❌{} There is problem with {}\n".format(CRED, CEND, service_name))
    else:
        print("{}✔{} {} is fine".format(CGREEN, CEND, service_name))


###############################################################################
#
# Metrics services
#
###############################################################################

@check_print
def test_memcached():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["memcached",
                           "ash", "-c", "echo stats | nc -w 1 127.0.0.1 11211"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "get_hits" not in resp:
        print("There is problem with Memcached")
        return 2

    return 0


@check_print
def test_influxdb():
    try:
        dbs = subprocess.check_output(
            DOCKER_EXEC + ["influxdb",
                           "influx", "-execute", "SHOW DATABASES"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "mon" not in dbs:
        print("Database 'mon' was not found in InfluxDB")
        return 2

    return 0


@check_print
def test_cadvisor():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["cadvisor",
                           "wget", "--tries=1", "--spider", "http://127.0.0.1:8080/healthz"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "200 OK" not in resp:
        print("cAdvisor did not return properly")
        return 2

    return 0


@check_print
def test_zookeeper():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["zookeeper",
                           "bash", "-c", "echo mntr | nc -w 1 127.0.0.1 2181"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "zk_avg_latency" not in resp:
        print("Zookeeper did not return properly")
        return 2

    return 0


@check_print
def test_kafka():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["kafka",
                           "ash", "-c", "kafka-topics.sh --list --zookeeper zookeeper:2181"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "metrics" not in resp:
        print("'metrics' not found in Kafka topics")
        return 2

    cons_cmd = "kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --group {} --topic {}"

    groups_topics = [
        ("thresh-event", "events"),
        ("log-transformer", "log"),
        ("log-persister", "log-transformed"),
        ("log-metric", "log-transformed"),
        ("1_metrics", "metrics"),
        ("thresh-metric", "metrics")
    ]
    bad_lag = False
    for row in groups_topics:
        check_cmd = cons_cmd.format(row[0], row[1])
        try:
            resp = subprocess.check_output(
                DOCKER_EXEC + ["kafka",
                               "ash", "-c", check_cmd],
                stderr=subprocess.STDOUT, universal_newlines=True
            )
        except subprocess.CalledProcessError as exc:
            print(exc.output)
            print(exc)
            return 1

        # Parse output from listing partitions
        reader = csv.reader(resp.split('\n'), delimiter=' ', skipinitialspace=True)
        # Remove depreciation waring and row with column titles
        partition_list = list(reader)[2:]

        lags = []
        for partition in partition_list:
            if len(partition) > 1:
                # Take values only form `Lag` column
                lags.append(int(partition[5]))
        biggest_lag = sorted(lags, reverse=True)[0]
        if biggest_lag > KAFKA_PROBLEM_LAG:
            print("Lag for group `{}`, topic `{}` grow over {}. Biggest found lag {}".format(
                  row[0], row[1], KAFKA_PROBLEM_LAG, biggest_lag))
            print("You can print all lags with: `{} kafka ash -c '{}'`".format(
                  " ".join(DOCKER_EXEC), check_cmd))
            bad_lag = True

    if bad_lag:
        # If too big lag was found return with error
        return 3

    return 0


@check_print
def test_mysql():
    mysql_conn = "MYSQL_PWD=${MYSQL_ROOT_PASSWORD} mysql --silent --skip-column-names "

    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["mysql",
                           "bash", "-c", mysql_conn + "-e 'show databases;'"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "mon" not in resp:
        print("'mon' database not found in MySQL")
        return 2

    try:
        max_conn = subprocess.check_output(
            DOCKER_EXEC + ["mysql",
                           "bash", "-c", mysql_conn + "-e 'select @@max_connections;'"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        conn = subprocess.check_output(
            DOCKER_EXEC + ["mysql",
                           "bash", "-c", mysql_conn +
                           "-e 'SHOW STATUS WHERE `variable_name` = \"Threads_connected\";' | cut -f2"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if int(conn) == int(max_conn):
        print("MySQL database is using all available connections")
        return 3

    if int(conn) == 0:
        print("No one is connecting to MySQL database, is metrics API working properly?")
        return 4

    return 0


@check_print
def test_monasca():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["monasca",
                           "ash", "-c", "curl http://localhost:8070/healthcheck"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    jresp = json.loads(resp)
    if jresp["error"]["title"] != "Unauthorized":
        print("Monasca API did not return properly")
        return 2

    return 0


@check_print
def test_grafana():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["grafana",
                           "ash", "-c", "wget -qO- http://localhost:3000/api/health"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "database" not in resp:
        print("Grafana did not return properly")
        return 2

    jresp = json.loads(resp)
    if jresp["database"] != "ok":
        print("Grafana reported problem with database: {}".format(jresp['database']))
        return 3

    return 0


###############################################################################
#
# Logs services
#
###############################################################################

@check_print
def test_elasticsearch():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["elasticsearch",
                           "ash", "-c", "curl -XGET 'localhost:9200/_cluster/health?pretty'"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "monasca" not in resp:
        print("Elasticsearch did not have 'monasca' cluster")
        return 2

    jresp = json.loads(resp)
    if jresp["status"] == "red":
        print("Elasticsearch health check reports problem with cluster")
        return 2

    return 0


@check_print
def test_elasticsearch_curator():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["elasticsearch-curator",
                           "ash", "-c", "curator --dry-run --config /config.yml /action.yml"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "delete_indices" not in resp:
        print("Elasticsearch Curator did not run properly")
        return 2

    return 0


# Metrics services
print_info("Memcached", test_memcached())
print_info("InfluxDB", test_influxdb())
print_info("cAdvisor", test_cadvisor())
# print_info("Monasca Agent Forwarder", test_agent_forwarder())
# print_info("Monasca Agent Collector", test_agent-collector())
print_info("Zookeeper", test_zookeeper())
print_info("Kafka", test_kafka())
print_info("MySQL", test_mysql())
print_info("Monasca API", test_monasca())
# print_info("Monasca Persister", test_monasca_persister())
# print_info("Monasca Thresh", test_thresh())
# print_info("Monasca Notification", test_monasca_notification())
print_info("Grafana", test_grafana())


# Logs services
# print_info("Monasca Log Metrics", test_log_metrics())
# print_info("Monasca Log Persister", test_log_persister())
# print_info("Monasca Log Transformer", test_log_transformer())
print_info("Elasticsearch", test_elasticsearch())
print_info("Elasticsearch Curator", test_elasticsearch_curator())
# print_info("Kibana", test_kibana())
# print_info("Monasca Log API", test_log_api())
# print_info("Monasca Log Agent", test_log_agent())
# print_info("Monasca Logspout", test_logspout())
