
keystone_credential = {'auth_url': 'http://192.168.10.6/identity',
                       'username': 'mini-mon',
                       'password': 'password',
                       'project_name': 'mini-mon',
                       'project_domain_name': 'default',
                       'user_domain_name': 'default',
                       'endpoint': 'http://192.168.10.6/metrics/v2.0'}
frequency = 30

simple_metrics = {'number_of_metrics_names': 2,
                  'number_of_metrics': 2,
                  'number_of_dimensions': 1}
complex_metric = [{'number_of_dimensions': 1,
                   'number_of_metrics': 2,
                   'value_meta': 'aaaaaaaa'},
                  {'number_of_dimensions': 1,
                   'number_of_metrics': 3}]

