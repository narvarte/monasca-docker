#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function

import json
import subprocess
import sys

from time import localtime, gmtime, strftime


print("Running simple tests of running Monasca services")
print("Local time {}".format(strftime("%Y-%m-%d %H:%M:%S", localtime())))
print("UTC time   {}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))

docker_exec = ["docker-compose",
               "-f", "docker-compose-metric.yml",
               "-f", "docker-compose-log.yml",
               "exec"]


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

def test_memcached():
    try:
        resp = subprocess.check_output(
            docker_exec + ["memcached",
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

def test_influxdb():
    try:
        dbs = subprocess.check_output(
            docker_exec + ["influxdb",
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


def test_cadvisor():
    try:
        resp = subprocess.check_output(
            docker_exec + ["cadvisor",
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


def test_zookeeper():
    try:
        resp = subprocess.check_output(
            docker_exec + ["zookeeper",
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


def test_kafka():
    try:
        resp = subprocess.check_output(
            docker_exec + ["kafka",
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

    return 0


def test_mysql():
    mysql_conn = "MYSQL_PWD=${MYSQL_ROOT_PASSWORD} mysql --silent --skip-column-names "

    try:
        resp = subprocess.check_output(
            docker_exec + ["mysql",
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
            docker_exec + ["mysql",
                           "bash", "-c", mysql_conn + "-e 'select @@max_connections;'"],
            stderr=subprocess.STDOUT, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        conn = subprocess.check_output(
            docker_exec + ["mysql",
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


def test_monasca():
    try:
        resp = subprocess.check_output(
            docker_exec + ["monasca",
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


def test_grafana():
    try:
        resp = subprocess.check_output(
            docker_exec + ["grafana",
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

def test_elasticsearch():
    try:
        resp = subprocess.check_output(
            docker_exec + ["elasticsearch",
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


def test_elasticsearch_curator():
    try:
        resp = subprocess.check_output(
            docker_exec + ["elasticsearch-curator",
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
