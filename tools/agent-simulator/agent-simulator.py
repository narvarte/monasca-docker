import time
import random

from monascaclient import client

import config


def create_simple_metrics():
    metrics = []
    for metric_name_index in range(config.simple_metrics['number_of_metrics_names']):
        for metric_index in range(config.simple_metrics['number_of_metrics']):
            metric = {'name': 'rand.metric' + str(metric_name_index),
                      'dimensions': create_dimensions(metric_index,
                                                      config.simple_metrics['number_of_dimensions']),
                      'timestamp': time.time() * 1000,
                      'value': random.randint(0, 100)}
            metrics.append(metric)
    return metrics


def create_complex_metrics():
    metrics = []
    for metric_info in config.complex_metric:
        for metric_index in range(metric_info['number_of_metrics']):
            metric = {'name': 'rand.commetric' + str(metric_index),
                      'dimensions': create_dimensions(metric_index,
                                                      metric_info['number_of_dimensions']),
                      'timestamp': time.time() * 1000,
                      'value': random.randint(0, 100)}
            if 'value_meta' in metric_info.keys():
                metric['value-meta'] = metric_info['value_meta']
            metrics.append(metric)
    return metrics


def create_dimensions(metric_index, number_of_dimensions):
    dimensions = {}
    for dimension_index in range(number_of_dimensions):
        dimensions['test_name_' + chr(97 + dimension_index)] = \
            'test_dimension_' + chr(97 + metric_index)
    return dimensions


def update_value_and_timestamp(metrics):
    for metric in metrics:
        metric['timestamp'] = time.time() * 1000
        metric['value'] = random.randint(0, 100)


def send_metric(mon_client, metrics):
    mon_client.metrics.create(jsonbody=metrics)


def main():
    metrics = create_simple_metrics() + create_complex_metrics()
    mon_client = client.Client('2_0', **config.keystone_credential)
    while True:
        start_time = time.time()
        print(metrics)
        send_metric(mon_client, metrics)
        update_value_and_timestamp(metrics)
        time.sleep(config.frequency - (start_time - time.time()))

if __name__ == "__main__":
    main()

