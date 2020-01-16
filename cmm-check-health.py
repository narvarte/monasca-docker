#!/usr/bin/env python3

import json
import subprocess
import sys

from time import localtime, gmtime, strftime

# Run this script only with Python 3
if sys.version_info.major != 3:
    sys.stdout.write("Sorry, requires Python 3.x\n")
    sys.exit(1)

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
        print(f"\n{CRED}❌{CEND} There is problem with {service_name}\n")
    else:
        print(f"{CGREEN}✔{CEND} {service_name} is fine")


###############################################################################
#
# Metrics services
#
###############################################################################

def test_memcached():
    try:
        resp = subprocess.run(docker_exec + ["memcached", "ash", "-c", "echo stats | nc -w 1 127.0.0.1 11211"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, check=True).stdout
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
        dbs = subprocess.run(docker_exec + ["influxdb", "influx", "-execute", "SHOW DATABASES"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, check=True).stdout
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
        resp = subprocess.run(docker_exec + ["cadvisor", "wget", "--tries=1", "--spider", "http://127.0.0.1:8080/healthz"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, check=True).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "200 OK" not in resp:
        print("cAdvisor did not returned properly")
        return 2

    return 0


def test_zookeeper():
    try:
        resp = subprocess.run(docker_exec + ["zookeeper", "bash", "-c", "echo mntr | nc -w 1 127.0.0.1 2181"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, check=True).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "zk_avg_latency" not in resp:
        print("Zookeeper did not returned properly")
        return 2

    return 0


def test_kafka():
    try:
        resp = subprocess.run(
            docker_exec + ["kafka", "ash", "-c",
                           "kafka-topics.sh --list --zookeeper zookeeper:2181"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "metrics" not in resp:
        print("'metrics' not found in Kafka topics")
        return 2

    return 0


def test_mysql():
    mysql_conn = "MYSQL_PWD=secretmysql mysql --silent --skip-column-names "

    try:
        resp = subprocess.run(
            docker_exec + ["mysql", "bash", "-c", mysql_conn + "-e 'show databases;'"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "mon" not in resp:
        print("'mon' database not found in MySQL")
        return 2

    try:
        max_conn = subprocess.run(
            docker_exec + ["mysql", "bash", "-c", mysql_conn + "-e 'select @@max_connections;'"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        conn = subprocess.run(
            docker_exec + ["mysql", "bash", "-c", mysql_conn +
            "-e 'SHOW STATUS WHERE `variable_name` = \"Threads_connected\";' | cut -f2"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
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
        resp = subprocess.run(
            docker_exec + ["monasca", "ash", "-c",
                           "curl http://localhost:8070/healthcheck"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    jresp = json.loads(resp)
    if jresp["error"]["title"] != "Unauthorized":
        print("Monasca API did not returned properly")
        return 2

    return 0


def test_grafana():
    try:
        resp = subprocess.run(
            docker_exec + ["grafana", "ash", "-c",
                           "wget -qO- http://localhost:3000/api/health"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "database" not in resp:
        print("Grafana did not returned properly")
        return 2

    jresp = json.loads(resp)
    if jresp["database"] != "ok":
        print(f"Grafana reported problem with database: {jresp['database']}")
        return 3

    return 0


###############################################################################
#
# Logs services
#
###############################################################################

def test_elasticsearch():
    try:
        resp = subprocess.run(
            docker_exec + ["elasticsearch", "ash", "-c",
                           "curl -XGET 'localhost:9200/_cluster/health?pretty'"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
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
        resp = subprocess.run(
            docker_exec + ["elasticsearch-curator", "ash", "-c",
                           "curator --dry-run --config /config.yml /action.yml"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, check=True
        ).stdout
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
