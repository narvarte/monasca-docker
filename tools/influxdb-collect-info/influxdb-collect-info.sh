#!/bin/bash

# (C) Copyright 2020 Fujitsu Enabling Software Technology GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

################################
# influxdb-collect-info v1.0.1 #
################################

# Set DEBUG option: 1=DEBUG output, 0=no DEBUG output
DEBUG=0

# Uncomment for verbose logging in bash
#set -x

# Set the max ram perc. threshold. Integer 0-100
maxRam=30

# Set the output directory
outputDataDir="/opt/cmm-server/cmm-influx-data"

# Set the monasca containers directory
monascaContainersDir="/opt/cmm-server/monasca-containers"

# Set the amount of past days for collecting metrics
amountDays=40

# Set the metrics list
declare -a metricNames=("container.io.read_bytes"
                        "container.io.read_bytes_sec"
                        "container.io.write_bytes"
                        "container.io.write_bytes_sec"
                        "container.mem.cache"
                        "container.mem.rss"
                        "container.mem.swap"
                        "container.mem.used_perc"
                       )

#####################################
# Don't edit below this line
#####################################

set -eo pipefail  # Exit the script if any statement returns error.

log() { echo -e "$(date --iso-8601=seconds)" "$1"; }
error() { log "ERROR: $1"; }
warn() { log "WARNING: $1"; }
inf() { log "INFO: $1"; }
debg() { if [ $DEBUG == 1 ]; then
           log "DEBUG: $1";
         fi
       }


#####################################
# Retrieve metrics querying Influxdb
#   $1: metric name
#   $2: metric day
function collectMetrics() {
    local metricName=$1
    local metricDay=$2
    metricDayDec=$((metricDay - 1))
    debg "Getting metric $metricName from $metricDay days ago to $metricDayDec days ago"
    influx_query="'SELECT * FROM \"$metricName\" where image =~ /influx/ and time > now() -${metricDay}d and time < now() -${metricDayDec}d' -database=mon"
    cmd_f="docker exec $(docker ps | grep influxdb | awk '{print $1}') /usr/bin/influx -execute $influx_query"
    eval "$cmd_f" &> "$outputDataDir"/metrics/"$metricName"_"$metricDay".txt
}


inf "v1.0.1 ==========================================================================="
inf "=                           Influxdb Collect Info                                ="
inf "=================================================================================="

# check if RAM value is valid: it's an integer, 0-100
parErr=false
if [ "$maxRam" -eq "$maxRam" ] 2>/dev/null; then
  if [ "$maxRam" -lt 0 ] || [ "$maxRam" -gt 100 ]; then
    parErr=true
  fi
else
  parErr=true
fi

if $parErr -eq true; then
  error "ERROR: max. RAM usage must be specified as integer percentage value: 0-100"
  exit 1
fi

# get memory consumption of influxdb container
cmd=$(docker stats "$(docker ps | grep influxdb | awk '{print $1}')" --format "{{.MemPerc}}" --no-stream)
res=$cmd
# eliminate percent char from string
memPercent=${res::-1}
#truncate floating num
memPercentTrunc=${memPercent%.*}

debg "Result from docker stats: memory consumption: $res, $memPercent, $memPercentTrunc"

# check if 0 <= memPercentTrunc <= 100
if [ "$memPercentTrunc" -ge 0 ] && [ "$memPercentTrunc" -le 100 ];
  then
      debg "memPercentTrunc is a valid percentage value";
  else
      error "invalid value of memory usage retrieved with docker stats: $memPercentTrunc%; please check"
    exit 1;
fi

debg "RAM usage of service Influxdb: $memPercentTrunc%"
if [ "$memPercentTrunc" -lt "$maxRam" ];
  then
    inf "RAM used by influxdb service $memPercentTrunc% is lower than max. value $maxRam%: no action required";
  else
    warn "RAM used by influxdb service $memPercentTrunc% is equal or higher than max. value $maxRam% !!!";

    mkdir -p $outputDataDir/metrics

    inf "Getting inspect info from Influxdb container..."
    debg "Executing: docker inspect <Influxdb-ID>"
    docker inspect "$(docker ps | grep influxdb | awk '{print $1}')" > "$outputDataDir"/influx_inspect.txt

    inf "Getting stats info from Influxdb container..."
    debg "Executing: docker stats <Influxdb-ID> --no-stream"
    docker stats "$(docker ps | grep influxdb | awk '{print $1}')" --no-stream > "$outputDataDir"/influx_stats.txt

    inf "Getting process info from Influxdb container"
    debg "Executing inside of the Influxdb container: ps aux"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" ps aux > "$outputDataDir"/inspect_ps_aux.txt

    inf "Getting shards from Influxdb..."
    debg "Executing inside of the Influxdb container: influx -execute 'SHOW SHARDS' -database=mon"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" /usr/bin/influx -execute 'SHOW SHARDS' -database=mon > "$outputDataDir"/influx_shards.txt

    inf "Getting retention policies from Influxdb..."
    debg "Executing inside of the Influxdb container: influx -execute 'SHOW RETENTION POLICIES' -database=mon"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" /usr/bin/influx -execute 'SHOW RETENTION POLICIES' -database=mon > "$outputDataDir"/influx_retention.txt

    inf "Getting the list of empty wal files..."
    debg "find /<monasca-containers-dir>/influxdb/wal -size 0 -type f -print | wc -l"
    find $monascaContainersDir/influxdb/wal -size 0 -type f -print | wc -l > "$outputDataDir"/influx_empty_wal.txt
    debg "find /<monasca-containers-dir>/influxdb/wal -size 0 -type f -print"
    find $monascaContainersDir/influxdb/wal -size 0 -type f -print >> "$outputDataDir"/influx_empty_wal.txt

    inf "Getting Influxdb network information..."
    inf "Command: netstat -r" > "$outputDataDir"/influx_netstat.txt
    debg "Executing inside of the Influxdb container: netstat -r"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" netstat -r >> "$outputDataDir"/influx_netstat.txt
    inf "Command: netstat -aeWp" >> "$outputDataDir"/influx_netstat.txt
    debg "Executing inside of the Influxdb container: netstat -aeWp"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" netstat -aeWp >> "$outputDataDir"/influx_netstat.txt

    inf "Getting Influxdb memory information..."
    inf "Command: cat /proc/1/status" > "$outputDataDir"/influx_memory_status.txt
    debg "Executing inside of the Influxdb container: cat /proc/1/status"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" cat /proc/1/status >> "$outputDataDir"/influx_memory_status.txt
    inf "Command: cat /proc/1/maps" > "$outputDataDir"/influx_memory_maps.txt
    debg "Executing inside of the Influxdb container: cat /proc/1/maps"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" cat /proc/1/maps >> "$outputDataDir"/influx_memory_maps.txt
    inf "Command: cat /proc/1/smaps" > "$outputDataDir"/influx_memory_smaps.txt
    debg "Executing inside of the Influxdb container: cat /proc/1/smaps"
    docker exec "$(docker ps | grep influxdb | awk '{print $1}')" cat /proc/1/smaps >> "$outputDataDir"/influx_memory_smaps.txt

    for metricName in "${metricNames[@]}"; do
        inf "Getting the metric values: $metricName from Influxdb container..."
        for metricDay in $(eval echo "{$amountDays..1}"); do
            collectMetrics "$metricName" "$metricDay"
        done
    done
    DATE="$(date +%Y-%m-%d_%H%M%S)"
    ARCHIVE_FILE="${outputDataDir}_$DATE.tar.gz"
    inf "Compressing gathered data to $ARCHIVE_FILE"
    tar -zcf "$ARCHIVE_FILE" "$outputDataDir"
    inf "Successfully compressed data to file $ARCHIVE_FILE"

fi
