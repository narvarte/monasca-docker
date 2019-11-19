#!/bin/bash

# This script is used for gathering data about CMM services and machine that
# this services are running on.
# To run this script it needs to be located in the same folder as all
# configuration files for properly running CMM 2.0.
# This script needs `root` privileges so that it's capable of getting
# data from all services that are capable of influencing stability of running
# CMM.
#
# In the folder containing script `cmm-collect-info.sh` run following command:
#   $ sudo ./cmm-collect-info.sh
#
# Collecting all data could take several minutes but should not be longer than
# 15 minutes.
# If collecting information was successful you should see information with path
# to archive file, like:
#   `INFO: Successfully compressed data to file /tmp/CMM-info.2019-07-29_14:26:53.tar.gz`
# Attach this archive to all reports about problems with CMM.

# Uncomment for debugging
# set -o xtrace

set -eo pipefail  # Exit the script if any statement returns error.
set -E # Export trap to functions.

log() { echo -e "$(date --iso-8601=seconds)" "$1"; }
error() { log "ERROR: $1"; }
warn() { log "WARNING: $1"; }
inf() { log "INFO: $1"; }

DATE="$(date +%Y-%m-%d_%H%M%S)"
HOSTPATH="/tmp/CMM-info.$DATE"
SERVER_DATA_DIR="data-server"
DOCKER_DATA_DIR="data-docker"

# Create directory for all data
mkdir "$HOSTPATH"

{
    # Path for logs of containers
    LOGPATH="/var/lib/docker/containers"

    ###################################################################
    # Folders for gathering specific info
    mkdir "$HOSTPATH/$SERVER_DATA_DIR"
    mkdir "$HOSTPATH/$DOCKER_DATA_DIR"

    inf "All data is written to: $HOSTPATH"

    #####################################
    # Exit trap functions
    function early_exit {
        local rc=$?
        local lc
        lc=$(eval echo \""$BASH_COMMAND\"")
        error "Command '$lc' exited with code: $rc"
        error "Something went wrong, not all data were gathered in $HOSTPATH"
        error "Early exit of the script"
        exit $rc
    }
    trap early_exit HUP INT QUIT TERM ERR

    # function finish {
    #     rc=$?
    #     echo "EXIT (rc: $?)"
    #     inf "Data gathered in $HOSTPATH"
    #     exit $rc
    # }
    # trap finish EXIT

    #####################################
    # Retrieve log information
    #   $1: short name for service
    #   $2: container ID
    function collectLogs() {
        local serviceShortName=$1
        local containerId=$2

        # Get log info directly via docker
        inf "Container: $containerId, service: $serviceShortName, "`
            `"write standard logs to: $serviceShortName/container.log"
        docker logs "$containerId" &> "$HOSTPATH/$serviceShortName/container.log"

        # Get long container ID in order to access container info
        longId=$(docker inspect --format="{{.Id}}" "$containerId")
        # Get all log info from fs
        containerLogPath=$LOGPATH/$longId
        inf "Container: $containerId, service: $serviceShortName, "`
            `"copy json logs from $LOGPATH"
        for entry in "$containerLogPath"/"$longId"-json.log*
        do
            cp "$entry" "$HOSTPATH/$serviceShortName"
        done
    }

    #####################################
    # Retrieve influxdb retention policies
    #   $1: id of influxdb container
    #   $2: output directory
    function collectRetentionPolicies() {
        local containerId=$1
        local outputFile="$2/influxdb/influxdb-retention-policies.txt"
        mkdir -p "$2/influxdb/"
        inf "Get influxdb retention policies, write to: influxdb/influxdb-retention-policies.txt"
        {
            docker exec -it "$containerId" /usr/bin/influx -execute 'SHOW RETENTION POLICIES' -database=mon
            docker exec -it "$containerId" /usr/bin/influx -execute 'SHOW SHARDS' -database=mon
        } >> "$outputFile"
    }

    #####################################
    # Retrieve kafka consumer lags
    #   $1: id of kafka container
    #   $2: output directory
    function collectKafkaLags() {
        local containerId=$1
        local outputFile="$2/kafka/kafka-consumer-lags.txt"
        mkdir -p "$2/kafka/"
        inf "Get kafka consumer lags, write to: kafka/kafka-consumer-lags.txt"
        {
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic events --group thresh-event
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic log --group log-transformer
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic log-transformed --group log-persister
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic log-transformed --group log-metric
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic metrics --group 1_metrics
            docker exec -it "$containerId" kafka-consumer-offset-checker.sh --zookeeper zookeeper:2181 --topic metrics --group thresh-metric
        } >> "$outputFile"
    }

    influxdbContainerId=""
    kafkaContainerId=""
    mysqlContainerId=""

    declare -A SERVICES=(
        [agent-collector]='/etc/monasca/agent/agent.yaml'
        [agent-forwarder]='/etc/monasca/agent/agent.yaml'
        [elasticsearch]='/usr/share/elasticsearch/config'
        [elasticsearch-curator]='/config.yml'
        [grafana]='/etc/grafana/grafana.ini'
        [influxdb]='/etc/influxdb/influxdb.conf'
        [kafka]='/kafka/config'
        [kibana]='/opt/kibana/config/kibana.yml'
        [log-agent]='/monasca-log-agent.conf'
        [log-api]='/etc/monasca'
        [log-metrics]='/etc/monasca/log-metrics.conf'
        [log-persister]='/etc/monasca/log-persister.conf'
        [log-transformer]='/etc/monasca/log-transformer.conf'
        [logspout]='/src/modules.go'
        [monasca]='/etc/monasca'
        [monasca-notification]='/config/notification.yaml'
        [monasca-persister]='/etc/monasca-persister/persister.conf;/etc/monasca/persister-logging.conf'
        [mysql]='/etc/mysql'
        [thresh]='/storm/conf'
        [zookeeper]='/conf'
        # Nothing done for these components
        [elasticsearch-init]=''
        [grafana-init]=''
        [influxdb-init]=''
        [kafka-init]=''
        [kafka-log-init]=''
        [mysql-init]=''
        [cadvisor]=''
        [memcached]=''
        [horizon]=''
        [keystone]=''
    )

    # Sort service names by name length decreasing, avoid trying to get monasca
    # config from monasca-notification etc.
    SERVICES_SORTED=($(for k in "${!SERVICES[@]}"; do echo "${#k}" "$k"; done | sort -rn | cut -f2 -d" "))

    # Get what's added by docker-compose to the start of service names
    # Check for running cadvisor container
    PREFIX=$(docker ps --format '{{.Names}}' | grep 'cadvisor' | sed -e 's/cadvisor.*$//');

    for container in $(docker ps -aq); do
        name=$(docker inspect --format='{{.Name}}' "$container" | sed -e 's/^[/]//');
        # Parse short name out of long name
        SHORTNAME="$(echo "$name" | sed -e "s/$PREFIX//" | sed -e "s/[/_0-9]*$//")"

        # Special handling for influxdb: save id for later usage
        if [[ "$SHORTNAME" =~ "influxdb" ]]; then
            # Check if found container contain influxdb config files
            if docker cp "$container:/etc/influxdb/" - &> /dev/null; then
                influxdbContainerId=$container
            fi
        fi

        # Special handling for Kafka: save id for later usage
        if [[ "$SHORTNAME" =~ "kafka" ]]; then
            # Check if found container contain Kafka config files
            if docker cp "$container:/kafka/config" - &> /dev/null; then
                kafkaContainerId=$container
            fi
        fi

        # Special handling for MySQL: save id for later usage
        if [[ "$SHORTNAME" =~ "mysql" ]]; then
            # Check if found container contain MySQL config files
            if docker cp "$container:/etc/mysql" - &> /dev/null; then
                mysqlContainerId=$container
            fi
        fi

        TRGDIR="$HOSTPATH/$SHORTNAME/"
        mkdir "$TRGDIR"

        # Collect logs from container
        collectLogs "$SHORTNAME" "$container"

        # Find service to get config files from
        for srcService in "${SERVICES_SORTED[@]}"; do
            # We are not getting any config files from unknown or init containers
            if [[ ! "$SHORTNAME" =~ $srcService || "$SHORTNAME" =~ "-init" ]]
            then
                continue
            fi

            # Split string to array of config locations
            IFS=';' read -r -a config_files <<< "${SERVICES[$srcService]}"
            if [ ${#config_files[@]} -eq 0 ]
            then
                # No config file, skip copying
                break
            fi
            # Iterate over all configs
            for conf in "${!config_files[@]}"; do
                inf "Container: $container, service: $SHORTNAME, "`
                    `"copy config file ${config_files[$conf]}"
                if ! docker cp "$container:${config_files[$conf]}" "$TRGDIR"
                then
                    warn "Problem with copying config file from $name"
                    continue
                fi
                # If container is running get env from it
                if [ "$(docker inspect -f '{{.State.Running}}' "${container}" 2>/dev/null)" = "true" ]
                then
                    docker exec -it "$container" env | sort &> "$TRGDIR/env"
                fi
            done
            break
        done
    done

    inf "Save status of all containers to: $DOCKER_DATA_DIR/docker-all-processes.txt"
    docker ps -a > "$HOSTPATH/$DOCKER_DATA_DIR"/docker-all-processes.txt

    inf "Save statistics about all Docker containers to: $DOCKER_DATA_DIR/docker-stats.txt"
    docker stats --all --no-stream > "$HOSTPATH/$DOCKER_DATA_DIR"/docker-stats.txt

    inf "Copy CMM configuration files to: $DOCKER_DATA_DIR/"
    cp .env "$HOSTPATH/$DOCKER_DATA_DIR"
    cp docker-compose-metric.yml "$HOSTPATH/$DOCKER_DATA_DIR"
    cp docker-compose-log.yml "$HOSTPATH/$DOCKER_DATA_DIR"

    inf "Save Docker versions to: $DOCKER_DATA_DIR/docker-versions.txt"
    docker --version > "$HOSTPATH/$DOCKER_DATA_DIR"/docker-versions.txt
    docker-compose --version >> "$HOSTPATH/$DOCKER_DATA_DIR"/docker-versions.txt

    inf "Save Docker service status to: $DOCKER_DATA_DIR/docker-status.txt"
    systemctl -l status docker > "$HOSTPATH/$DOCKER_DATA_DIR"/docker-status.txt

    if [ "$(docker inspect -f '{{.State.Running}}' "${mysqlContainerId}" 2>/dev/null)" = "true" ]
    then
        mkdir -p "$HOSTPATH/mysql"
        TABLES_STATUS="cmm-mysql-tables-status-$(hostname -s).txt"
        ALARM_DEFS="cmm-mysql-alarm_definitions-$(hostname -s).txt"
        inf "Save information about tables status to: mysql/$TABLES_STATUS"
        docker exec -it "${mysqlContainerId}" mysql -uroot -psecretmysql mon \
            -e "show table status" > "$HOSTPATH/mysql/$TABLES_STATUS"
        inf "Save information about alarm_definitions to: mysql/$ALARM_DEFS"
        docker exec -it "${mysqlContainerId}" mysql -uroot -psecretmysql mon \
            -e "select * from alarm_definition" > "$HOSTPATH/mysql/$ALARM_DEFS"
    else
        warn "MySQL container is not running"
    fi

    # Get retention policies and shards info from influxdb
    if [ "$influxdbContainerId" != "" ]; then
        collectRetentionPolicies "$influxdbContainerId" "$HOSTPATH"
    fi

    # Get consumer lags for topics from kafka
    if [ "$kafkaContainerId" != "" ]; then
        collectKafkaLags "$kafkaContainerId" "$HOSTPATH"
    fi

    inf "Save server environment variables to: $SERVER_DATA_DIR/environment-variables.txt"
    printenv > "$HOSTPATH/$SERVER_DATA_DIR"/environment-variables.txt

    fn="/etc/docker/daemon.json"
    if [ -e $fn ]
    then
        inf "Copy $fn to $SERVER_DATA_DIR"
        cp "$fn" "$HOSTPATH/$SERVER_DATA_DIR"
    fi

    inf "Save all running processes to: $SERVER_DATA_DIR/running-processes.txt"
    ps aux > "$HOSTPATH/$SERVER_DATA_DIR"/running-processes.txt

    inf "Save Top 10 by memory to: $SERVER_DATA_DIR/running-processes-top10-memory.txt"
    ps aux --sort=-pmem | head -n 11 > "$HOSTPATH/$SERVER_DATA_DIR"/running-processes-top10-memory.txt
    inf "Save Top 10 by CPU to: $SERVER_DATA_DIR/running-processes-top10-cpu.txt"
    ps aux --sort=-pcpu | head -n 11 > "$HOSTPATH/$SERVER_DATA_DIR"/running-processes-top10-cpu.txt

    inf "Save memory usage to: $SERVER_DATA_DIR/free-memory.txt"
    free -h > "$HOSTPATH/$SERVER_DATA_DIR"/free-memory.txt

    inf "Save disk usage to: $SERVER_DATA_DIR/disk-usage.txt"
    df -h > "$HOSTPATH/$SERVER_DATA_DIR"/disk-usage.txt

    inf "Track usage over time over 150 seconds to: $SERVER_DATA_DIR/tracked-usage.txt"
    top -b -d 5 -n 30 -c > "$HOSTPATH/$SERVER_DATA_DIR"/tracked-usage.txt

    inf "Save NTP synchronization status (ntpq) to: $SERVER_DATA_DIR/ntp-status.txt"
    if [ -x "$(command -v ntpq)" ]; then
        ntpq -pn > "$HOSTPATH/$SERVER_DATA_DIR"/ntp-status.txt
    else
        warn "ntpq not found"
    fi
    inf "Save NTP synchronization status (timedatectl) to: $SERVER_DATA_DIR/ntp-status.txt"
    if [ -x "$(command -v timedatectl)" ]; then
        timedatectl status >> "$HOSTPATH/$SERVER_DATA_DIR"/ntp-status.txt
    else
        warn "timedatectl not found"
    fi

    inf "Successfully gathered data in $HOSTPATH"

    ARCHIVE_FILE="${HOSTPATH}.tar.gz"
    inf "Compressing gathered data to $ARCHIVE_FILE"
    tar -zcf "$ARCHIVE_FILE" "$HOSTPATH"
    inf "Successfully compressed data to file $ARCHIVE_FILE"

} 2>&1 | tee -a "$HOSTPATH/cmm-collect-info.log"
