#!/usr/bin/env python
# coding=utf-8

import csv
import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from shlex import shlex
from time import localtime, gmtime, strftime

###############################################################################
#
# Global values
#
###############################################################################

# Script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get out of tools dir to root dir with docker-compose yaml files
root_dir = os.path.normpath(os.path.join(script_dir, os.path.pardir, os.path.pardir))

prog_desc = "Cloud Monitoring Manager health check script."
parser = ArgumentParser(description=prog_desc)

parser.add_argument(
    "-m", "--metrics", action="store_true",
    help="Check metrics pipeline")
parser.add_argument(
    "-l", "--logs", action="store_true",
    help="Check logs pipeline")

parser.add_argument(
    "-k", "--kafka-lag", default=20000, type=int,
    help="Report warning when Kafka lag jump over this value")
parser.add_argument(
    "-r", "--max-restarts", default=-1, type=int,
    help="After this number of restarts of one service issue warning")

parser.add_argument(
    "-f", "--folder", default=root_dir,
    help="Folder with `.env` and docker-compose yaml config files")

ARGS = parser.parse_args()

dot_env_path =  os.path.join(ARGS.folder, ".env")
compose_metrics_path = os.path.join(ARGS.folder, "docker-compose-metric.yml")
compose_logs_path = os.path.join(ARGS.folder, "docker-compose-log.yml")

# String for using docker-compose to exec commands in all services
DOCKER_EXEC = ["docker-compose",
               "--project-directory", ARGS.folder,
               "--file", compose_metrics_path,
               "--file", compose_logs_path,
               "exec"]

# No arguments provided, check both pipelines
if not ARGS.metrics and not ARGS.logs:
    ARGS.metrics = True
    ARGS.logs = True

print("Running simple tests of running Monasca services")
print("Local time {}".format(strftime("%Y-%m-%d %H:%M:%S", localtime())))
print("UTC time   {}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))


def print_info(service_name, test_function):
    CGREEN = '\033[92m'
    CRED = '\033[91m'
    CEND = '\033[0m'

    print("Checking '{}'".format(service_name))

    if test_function() is not None:
        print("\n{}❌{} There is problem with {}\n".format(CRED, CEND, service_name))
    else:
        print("{}✔{} {} looks fine".format(CGREEN, CEND, service_name))


###############################################################################
#
# Environment tests
#
###############################################################################

try:
    resp = subprocess.check_output(["docker-compose", "--version"],
        stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
    )
except subprocess.CalledProcessError as exc:
    print(exc.output)
    print(exc)
    sys.exit(1)
print(resp)

print("Looking for `.env` and configuration files in: {}".format(ARGS.folder))
if not os.path.isdir(ARGS.folder):
    print("Folder does not exists: {}".format(ARGS.folder))
    print("Exiting")
    sys.exit(1)

config_files = [
    dot_env_path,
    compose_metrics_path,
    compose_logs_path
]
for cfile in config_files:
    if not os.path.exists(cfile):
        print("File does not exists: {}".format(cfile))
        print("Exiting")
        sys.exit(1)


###############################################################################
#
# Metrics services
#
###############################################################################

def test_memcached():
    try:
        # Memcached does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["memcached",
                           "ash", "-c", "echo stats | nc -w 1 127.0.0.1 11211"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "get_hits" not in resp:
        print("There is problem with Memcached")
        return 1


def test_influxdb():
    try:
        dbs = subprocess.check_output(
            DOCKER_EXEC + ["influxdb",
                           "influx", "-execute", "SHOW DATABASES"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "mon" not in dbs:
        print("Database 'mon' was not found in InfluxDB")
        return 1


def test_cadvisor():
    try:
        # cAdvisor does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["cadvisor",
                           "wget", "--tries=1", "--spider", "http://127.0.0.1:8080/healthz"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "200 OK" not in resp:
        print("cAdvisor did not return properly")
        return 1


def test_zookeeper():
    try:
        # Zookeeper does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["zookeeper",
                           "bash", "-c", "echo mntr | nc -w 1 127.0.0.1 2181"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "zk_avg_latency" not in resp:
        print("Zookeeper did not return properly")
        return 1


def test_mysql():
    mysql_conn = "MYSQL_PWD=${MYSQL_ROOT_PASSWORD} mysql --silent --skip-column-names "

    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["mysql",
                           "bash", "-c", mysql_conn + "-e 'show databases;'"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "mon" not in resp:
        print("'mon' database not found in MySQL")
        return 1

    try:
        max_conn = subprocess.check_output(
            DOCKER_EXEC + ["mysql",
                           "bash", "-c", mysql_conn + "-e 'select @@max_connections;'"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
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
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if int(conn) == int(max_conn):
        print("MySQL database is using all available connections")
        return 1

    if int(conn) == 0:
        print("No one is connecting to MySQL database, is metrics API working properly?")
        return 1


def test_monasca():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["monasca",
                           "ash", "-c",
                           "curl http://localhost:$MONASCA_CONTAINER_API_PORT/healthcheck"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        jresp = json.loads(resp)
    except ValueError as ex:
        print("Monasca API returned wrong JSON response: {}".format(resp))
        return 1

    if jresp["error"]["title"] != "Unauthorized":
        print("Monasca API did not return properly")
        return 1


def test_grafana():
    try:
        # Grafana does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["grafana",
                           "ash", "-c", "wget -qO- http://localhost:3000/api/health"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "database" not in resp:
        print("Grafana did not return properly")
        return 1

    try:
        jresp = json.loads(resp)
    except ValueError as ex:
        print("Grafana returned wrong JSON response: {}".format(resp))
        return 1

    if ("database" not in jresp) or (jresp["database"] != "ok"):
        print("Grafana reported problem with database: {}".format(jresp))
        return 1


###############################################################################
#
# Logs services
#
###############################################################################

def test_elasticsearch():
    try:
        # Elasticsearch does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["elasticsearch",
                           "ash", "-c", "curl -XGET 'localhost:9200/_cluster/health?pretty'"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "monasca" not in resp:
        print("Elasticsearch did not have 'monasca' cluster")
        return 1

    try:
        jresp = json.loads(resp)
    except ValueError as ex:
        print("Elasticsearch returned wrong JSON response: {}".format(resp))
        return 1

    if jresp["status"] == "red":
        print("Elasticsearch health check reports problem with cluster")
        return 1


def test_elasticsearch_curator():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["elasticsearch-curator",
                           "ash", "-c", "curator --dry-run --config /config.yml /action.yml"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    if "delete_indices" not in resp:
        print("Elasticsearch Curator did not run properly")
        return 1


def test_kibana():
    try:
        # Kibana does not allow to change PORT inside the container
        resp = subprocess.check_output(
            DOCKER_EXEC + ["kibana",
                           "sh", "-c", "wget -qO- http://localhost:5601/api/status"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        jresp = json.loads(resp)
    except ValueError as ex:
        print("Kibana returned wrong JSON response: {}".format(resp))
        return 1

    if jresp["status"]["overall"]["state"] != "green":
        print("Kibana health check reports problem")
        return 1


def test_log_api():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["log-api",
                           "sh", "-c",
                           "curl http://localhost:$MONASCA_CONTAINER_LOG_API_PORT/healthcheck"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    try:
        jresp = json.loads(resp)
    except ValueError as ex:
        print("Monasca LOG API returned wrong JSON response: {}".format(resp))
        return 1

    if ("kafka" not in jresp) or (jresp["kafka"] != "OK"):
        print("Monasca LOG API did not return properly: {}".format(jresp))
        return 1


###############################################################################
#
# Cross pipeline services
#
###############################################################################

def test_kafka():
    try:
        resp = subprocess.check_output(
            DOCKER_EXEC + ["kafka",
                           "ash", "-c", "kafka-topics.sh --list --zookeeper $ZOOKEEPER_CONNECTION_STRING"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    kafka_topics = []
    if ARGS.metrics:
        kafka_topics.extend([
            "60-seconds-notifications",
            "alarm-notifications",
            "alarm-state-transitions",
            "events",
            "metrics",
            "retry-notifications"
        ])
    if ARGS.logs:
        kafka_topics.extend([
            "log",
            "log-transformed"
        ])

    for topic in kafka_topics:
        if topic not in resp:
            print("'{}' not found in Kafka topics".format(topic))
            return 1

    cons_cmd = "kafka-consumer-offset-checker.sh --zookeeper $ZOOKEEPER_CONNECTION_STRING --group {} --topic {}"

    groups_topics = []
    if ARGS.metrics:
        groups_topics.extend([
            ("thresh-event", "events"),
            ("1_metrics", "metrics"),
            ("thresh-metric", "metrics")
        ])
    if ARGS.logs:
        groups_topics.extend([
            ("log-transformer", "log"),
            ("log-persister", "log-transformed"),
            ("log-metric", "log-transformed")
        ])
    bad_lag = False
    for row in groups_topics:
        check_cmd = cons_cmd.format(row[0], row[1])
        try:
            resp = subprocess.check_output(
                DOCKER_EXEC + ["kafka",
                               "ash", "-c", check_cmd],
                stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
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
                # Take values only from `Lag` column
                lags.append(int(partition[5]))
        biggest_lag = sorted(lags, reverse=True)[0]
        if biggest_lag > ARGS.kafka_lag:
            print("Lag for group `{}`, topic `{}` grow over {}. Biggest lag found: {}".format(
                  row[0], row[1], ARGS.kafka_lag, biggest_lag))
            print("You can print all lags with: `{} kafka ash -c '{}'`".format(
                  " ".join(DOCKER_EXEC), check_cmd))
            bad_lag = True

    if bad_lag:
        # If too big lag was found return with error
        return 1


###############################################################################
#
# Global Docker checks
#
###############################################################################

# TODO: Not working properly with 20 Docker containers on one machine.
# Docker events provide only last 256 events and even health checks are logged
# so with all our services working on one machine it's provide us with events
# only from the last 4 minutes...
def test_docker_events():
    try:
        resp = subprocess.check_output(
            ["docker", "events",
                "--filter", "event=die", "--filter", "event=oom",
                "--since=24h", "--until=1s"],
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    filtered_list = {}

    return_error = None
    for row in resp.splitlines():

        tags = row[row.find('(')+1:-1]
        lexer = shlex(tags, posix=True)
        # Separate words
        lexer.whitespace = ", "
        # Split only on whitespace chars
        lexer.whitespace_split = True
        # "=" is part of the word
        lexer.wordchars += "="
        # Separate key=value pairs to dict, split each pair only on first "="
        parsed_row = dict(word.split("=", 1) for word in lexer)
        service = parsed_row["com.docker.compose.service"]

        # Check for out of memory errors
        if "container oom" in row:
            print("  Service '{}' got killed in the last 24 hours because "
                  "of out of memory error, please check"
                  .format(service))
            return_error = 1

        if service not in filtered_list:
            filtered_list[service] = {"restarts": 0}
        filtered_list[service]["restarts"] += 1

    for key in filtered_list:
        if filtered_list[key]["restarts"] > ARGS.max_restarts:
            print("  Service '{}' restarted at least {} times in last "
                  "24 hours, please check"
                  .format(key, filtered_list[key]["restarts"]))
            return_error = 1

    return return_error


# test_docker_restarts will report number of Docker container restarts from
# the time it was created/started (like with `docker-compose up`).
def test_docker_restarts():
    try:
        resp = subprocess.check_output(
            ["docker inspect --format \
                'ID={{.ID}} CREATED={{.Created}} RESTARTS={{.RestartCount}} \
                    OOM={{.State.OOMKilled}} NAME={{.Name}}' \
                $(docker ps -aq)"], shell=True,
            stderr=subprocess.STDOUT, universal_newlines=True, cwd=ARGS.folder
        )
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        print(exc)
        return 1

    return_error = None
    for row in resp.splitlines():
        lexer = shlex(row, posix=True)
        # Separate words
        lexer.whitespace = ", "
        # Split only on whitespace chars
        lexer.whitespace_split = True
        # "=" is part of the word
        lexer.wordchars += "="
        # Separate key=value pairs to dict, split each pair only on first "="
        parsed_row = dict(word.split("=", 1) for word in lexer)

        # Check for number of restarts
        if int(parsed_row["RESTARTS"]) > ARGS.max_restarts:
            print("  Service '{}' restarted at least {} times from the time "
                  "it was started: {}, please check"
                  .format(parsed_row["NAME"],
                          parsed_row["RESTARTS"],
                          # Remove milliseconds from creation time
                          parsed_row["CREATED"].split(".", 1)[0],
                  ))
            return_error = 1

        # Check if service got out of memory error
        if parsed_row["OOM"] != "false":
            print("  Service '{}' was restarted because of out of memory error, "
                  "please check"
                  .format(parsed_row["NAME"]))
            return_error = 1

    return return_error

###############################################################################
#
# Run checks
#
###############################################################################

# Metrics services
if ARGS.metrics:
    print_info("Memcached", test_memcached)
    print_info("InfluxDB", test_influxdb)
    print_info("cAdvisor", test_cadvisor)
    # print_info("Monasca Agent Forwarder", test_agent_forwarder)  // no healthcheck
    # print_info("Monasca Agent Collector", test_agent-collector)  // no healthcheck
    print_info("Zookeeper", test_zookeeper)
    print_info("MySQL", test_mysql)
    print_info("Monasca API", test_monasca)
    # print_info("Monasca Persister", test_monasca_persister)  // no healthcheck
    # print_info("Monasca Thresh", test_thresh)  // no healthcheck
    # print_info("Monasca Notification", test_monasca_notification)  // no healthcheck
    print_info("Grafana", test_grafana)


# Logs services
if ARGS.logs:
    # print_info("Monasca Log Metrics", test_log_metrics)  // no healthcheck
    # print_info("Monasca Log Persister", test_log_persister)  // no healthcheck
    # print_info("Monasca Log Transformer", test_log_transformer)  // no healthcheck
    print_info("Elasticsearch", test_elasticsearch)
    print_info("Elasticsearch Curator", test_elasticsearch_curator)
    print_info("Kibana", test_kibana)
    print_info("Monasca Log API", test_log_api)
    # print_info("Monasca Log Agent", test_log_agent)  // no healthcheck
    # print_info("Monasca Logspout", test_logspout)  // no healthcheck

# Cross pipeline services
if ARGS.metrics or ARGS.logs:
    print_info("Kafka", test_kafka)

# TODO: Not working properly with running 20 Docker containers on one machine.
# print_info("Docker events", test_docker_events)

# Check number of restarts only if user request for it himself.
if ARGS.max_restarts > 0:
    print_info("Docker restarts", test_docker_restarts)
