import MySQLdb
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
        override_application_settings, validate_database_trace_inputs)
from testing_support.settings import mysql_multiple_settings
from testing_support.util import instance_hostname

from newrelic.agent import background_task

DB_MULTIPLE_SETTINGS = mysql_multiple_settings()

# Settings

_enable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': True,
}
_disable_instance_settings = {
    'datastore_tracer.instance_reporting.enabled': False,
}

# Metrics

_base_scoped_metrics = [
        ('Function/MySQLdb:Connect', 2),
        ('Function/MySQLdb.connections:Connection.__enter__', 2),
        ('Function/MySQLdb.connections:Connection.__exit__', 2),
        ('Datastore/operation/MySQL/select', 2),
        ('Datastore/operation/MySQL/commit', 4),
]

_base_rollup_metrics = [
        ('Datastore/all', 8),
        ('Datastore/allOther', 8),
        ('Datastore/MySQL/all', 8),
        ('Datastore/MySQL/allOther', 8),
        ('Datastore/operation/MySQL/select', 2),
        ('Datastore/operation/MySQL/commit', 4),
]

_enable_scoped_metrics = list(_base_scoped_metrics)
_enable_rollup_metrics = list(_base_rollup_metrics)

_disable_scoped_metrics = list(_base_scoped_metrics)
_disable_rollup_metrics = list(_base_rollup_metrics)

if len(DB_MULTIPLE_SETTINGS) > 1:
    mysql_1 = DB_MULTIPLE_SETTINGS[0]
    host_1 = instance_hostname(mysql_1['host'])
    port_1 = mysql_1['port']

    mysql_2 = DB_MULTIPLE_SETTINGS[1]
    host_2 = instance_hostname(mysql_2['host'])
    port_2 = mysql_2['port']

    instance_metric_name_1 = 'Datastore/instance/MySQL/%s/%s' % (
            host_1, port_1)
    instance_metric_name_2 = 'Datastore/instance/MySQL/%s/%s' % (
            host_2, port_2)

    _enable_rollup_metrics.extend([
            (instance_metric_name_1, 3),
            (instance_metric_name_2, 3),
    ])
    _disable_rollup_metrics.extend([
            (instance_metric_name_1, None),
            (instance_metric_name_2, None),
    ])

# Query

def exercise_mysql(connection):
    with connection as cursor:
        cursor.execute('SELECT version();')
    connection.commit()

# Tests

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics('test_multiple_dbs:test_multi_dbs_enable_instance',
        scoped_metrics=_enable_scoped_metrics,
        rollup_metrics=_enable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@override_application_settings(_enable_instance_settings)
@background_task()
def test_multi_dbs_enable_instance():
    mysql_1 = DB_MULTIPLE_SETTINGS[0]
    mysql_2 = DB_MULTIPLE_SETTINGS[1]

    connection_1 = MySQLdb.connect(db=mysql_1['name'],
            user=mysql_1['user'], passwd=mysql_1['password'],
            host=mysql_1['host'], port=mysql_1['port'])
    exercise_mysql(connection_1)

    connection_2 = MySQLdb.connect(db=mysql_2['name'],
            user=mysql_2['user'], passwd=mysql_2['password'],
            host=mysql_2['host'], port=mysql_2['port'])
    exercise_mysql(connection_2)

@pytest.mark.skipif(len(DB_MULTIPLE_SETTINGS) < 2,
        reason='Test environment not configured with multiple databases.')
@validate_transaction_metrics('test_multiple_dbs:test_multi_dbs_disable_instance',
        scoped_metrics=_disable_scoped_metrics,
        rollup_metrics=_disable_rollup_metrics,
        background_task=True)
@validate_database_trace_inputs(sql_parameters_type=tuple)
@override_application_settings(_disable_instance_settings)
@background_task()
def test_multi_dbs_disable_instance():
    mysql_1 = DB_MULTIPLE_SETTINGS[0]
    mysql_2 = DB_MULTIPLE_SETTINGS[1]

    connection_1 = MySQLdb.connect(db=mysql_1['name'],
            user=mysql_1['user'], passwd=mysql_1['password'],
            host=mysql_1['host'], port=mysql_1['port'])
    exercise_mysql(connection_1)

    connection_2 = MySQLdb.connect(db=mysql_2['name'],
            user=mysql_2['user'], passwd=mysql_2['password'],
            host=mysql_2['host'], port=mysql_2['port'])
    exercise_mysql(connection_2)