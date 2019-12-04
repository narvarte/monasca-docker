#!/bin/bash

# Uncomment for verbose logging in bash
#set -x

set -eo pipefail  # Exit the script if any statement returns error.

# set DEBUG option: 1=DEBUG output, 0=no DEBUG output
DEBUG=0

dockerStart="start"
dockerStop="stop"
dockerServiceInfluxDb="influxdb"
dockerServicePersister="monasca-persister"

function execCmd {
  dockerComposeCmd=$1
  dockerMode=$2
  dockerService=$3
  echo "+++ $dockerMode $dockerService +++"
  cmd=$dockerComposeCmd' '$dockerMode' '$dockerService
  echo "Execute: $cmd"
  if ! $cmd; then
    echo "Execution of cmd $cmd failed with non-zero returncode $?, exiting now"
    exit 1
  fi
}

echo ""
echo "====================================================================="
echo "+++++ $(date): Check RAM usage of influxdb +++++"
echo "====================================================================="

######### handle input params ##############
if [ $# -ne 2 ]; then
   echo "illegal number of parameters, expected format: $0 <directory docker-compose yml files> <max. RAM usage (%) of influxdb"
   exit 1;
fi
if [ $DEBUG == 1 ]; then
  echo "params: directory f. yml-files: $1";
  echo "params: max RAM usagefiles: $2";
fi

# read location of yml-files from input param
dockerYmlFileDir=$1
maxRam=$2

# check if yml-files exist in this location
if [ ! -d "$dockerYmlFileDir" ]; then
  echo "ERROR: Specified directory $dockerYmlFileDir  doesn't exist!"
  exit 1
fi

if [ ! -f "$dockerYmlFileDir/docker-compose.yml" ]; then
  # check if docker-compose-metric.yml exists
  if [ ! -f "$dockerYmlFileDir/docker-compose-metric.yml" ]; then
    echo "ERROR: Specified directory $dockerYmlFileDir  doesn't contain docker-compose-metric.yml!"
    exit 1;
  else
    composeMetricFn="docker-compose-metric.yml"
  fi
else
  composeMetricFn="docker-compose.yml"
fi

if [ ! -f "$dockerYmlFileDir/docker-compose-log.yml" ]; then
  echo "ERROR: Specified directory $dockerYmlFileDir  doesn't contain docker-compose-log.yml!"
  exit 1
fi

if [ ! -f "$dockerYmlFileDir/.env" ]; then
  echo "ERROR: Specified directory $dockerYmlFileDir  doesn't contain .env!"
  exit 1
fi

# ----------- check 2nd param: max RAM for integer -------------------
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
  echo "ERROR: max. RAM usage must be specified as integer percentage value: 0-100"
  exit 1
fi
# -----------------------------------------------------------------------

#change to monasca-docker directory
cd "$dockerYmlFileDir"

# set command for execution of docker-compose
dockerComposeCmd="docker-compose -f $dockerYmlFileDir/$composeMetricFn -f $dockerYmlFileDir/docker-compose-log.yml"

# get memory consumption of influxdb container
cmd=$(docker stats "$(docker ps | grep influxdb | awk '{print $1}')" --format "{{.MemPerc}}" --no-stream)
res=$cmd
# eliminate percent char from string
memPercent=${res::-1}
#truncate floating num
memPercentTrunc=${memPercent%.*}

if [ $DEBUG == 1 ]; then
  echo "Result from docker stats: memory consumption: $res, $memPercent, $memPercentTrunc"
fi

# check if 0 <= memPercentTrunc <= 100
if [ "$memPercentTrunc" -ge 0 ] && [ "$memPercentTrunc" -le 100 ];
  then
    if [ $DEBUG == 1 ]; then
      echo "memPercentTrunc is a valid percentage value";
    fi
  else
    echo "invalid value of memory usage retrieved with docker stats: $memPercentTrunc%; please check"
    exit 1;
fi

echo "RAM usage of service $dockerServiceInfluxDb: $memPercentTrunc%"
if [ "$memPercentTrunc" -lt "$maxRam" ];
  then
    echo "RAM used by influxdb service - $memPercentTrunc% - is lower than max. allowed value $maxRam%: no action required";
  else
    echo "RAM used by influxdb service - $memPercentTrunc% - is equal or higher than max. allowed value $maxRam%: stop influxdb and monasca-persister";
    echo "###### Stop docker services #####"
    execCmd "$dockerComposeCmd" "$dockerStop" "$dockerServicePersister"
    execCmd "$dockerComposeCmd" "$dockerStop" "$dockerServiceInfluxDb"

    echo "###### Start docker services again #####"
    execCmd "$dockerComposeCmd" "$dockerStart" "$dockerServiceInfluxDb"
    execCmd "$dockerComposeCmd" "$dockerStart" "$dockerServicePersister"
fi
