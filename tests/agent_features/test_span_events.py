import pytest

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task

from newrelic.api.database_trace import DatabaseTrace
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.function_trace import FunctionTrace, function_trace
from newrelic.api.memcache_trace import MemcacheTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.solr_trace import SolrTrace

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)


@pytest.mark.parametrize('dt_enabled', (True, False))
@pytest.mark.parametrize('span_events_enabled', (True, False))
@pytest.mark.parametrize('txn_sampled', (True, False))
def test_span_events(dt_enabled, span_events_enabled, txn_sampled):
    guid = 'dbb536c53b749e0b'
    sentinel_guid = '0687e0c371ea2c4e'
    function_guid = '482439c52de807ee'
    priority = 0.5

    @function_trace(name='child')
    def child():
        pass

    @function_trace(name='function')
    def function():
        txn = current_transaction()
        txn.current_node.guid = function_guid
        child()

    _settings = {
        'distributed_tracing.enabled': dt_enabled,
        'span_events.enabled': span_events_enabled
    }

    count = 0
    if dt_enabled and span_events_enabled and txn_sampled:
        count = 1

    exact_intrinsics_common = {
        'type': 'Span',
        'transactionId': guid,
        'sampled': txn_sampled,
        'priority': priority,
        'category': 'generic',
    }
    expected_intrinsics = ('timestamp', 'duration')

    exact_intrinsics_root = exact_intrinsics_common.copy()
    exact_intrinsics_root['name'] = 'Function/transaction'
    exact_intrinsics_root['nr.entryPoint'] = True

    exact_intrinsics_function = exact_intrinsics_common.copy()
    exact_intrinsics_function['name'] = 'Function/function'
    exact_intrinsics_function['parentId'] = sentinel_guid

    exact_intrinsics_child = exact_intrinsics_common.copy()
    exact_intrinsics_child['name'] = 'Function/child'
    exact_intrinsics_child['parentId'] = function_guid

    @validate_span_events(count=count,
            expected_intrinsics=['nr.entryPoint'])
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_root,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_function,
            expected_intrinsics=expected_intrinsics)
    @validate_span_events(count=count,
            exact_intrinsics=exact_intrinsics_child,
            expected_intrinsics=expected_intrinsics)
    @override_application_settings(_settings)
    @background_task(name='transaction')
    def _test():
        # Force intrinsics
        txn = current_transaction()
        txn.current_node.guid = sentinel_guid
        txn.guid = guid
        txn._priority = priority
        txn._sampled = txn_sampled

        function()

    _test()


@pytest.mark.parametrize('trace_type,args', (
    (DatabaseTrace, ('select * from foo', )),
    (DatastoreTrace, ('db_product', 'db_target', 'db_operation')),
    (ExternalTrace, ('lib', 'url')),
    (FunctionTrace, ('name', )),
    (MemcacheTrace, ('command', )),
    (MessageTrace, ('lib', 'operation', 'dst_type', 'dst_name')),
    (SolrTrace, ('lib', 'command')),
))
def test_each_span_type(trace_type, args):
    @validate_span_events(count=2)
    @override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    })
    @background_task(name='test_each_span_type')
    def _test():

        transaction = current_transaction()
        transaction._sampled = True

        with trace_type(transaction, *args):
            pass

    _test()


@pytest.mark.parametrize('sql,sql_format,expected', (
    pytest.param(
            'a' * 2001,
            'raw',
            ''.join(['a'] * 1997 + ['...']),
            id='truncate'),
    pytest.param(
            'a' * 2000,
            'raw',
            ''.join(['a'] * 2000),
            id='no_truncate'),
    pytest.param(
            'select * from %s' % ''.join(['?'] * 2000),
            'obfuscated',
            'select * from %s...' % (
                    ''.join(['?'] * (2000 - len('select * from ') - 3))),
            id='truncate_obfuscated'),
    pytest.param('select 1', 'off', ''),
    pytest.param('select 1', 'raw', 'select 1'),
    pytest.param('select 1', 'obfuscated', 'select ?'),
))
def test_database_db_statement_format(sql, sql_format, expected):
    @validate_span_events(count=1, exact_intrinsics={
        'db.statement': expected,
    })
    @override_application_settings({
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
        'transaction_tracer.record_sql': sql_format,
    })
    @background_task(name='test_database_db_statement_format')
    def _test():
        transaction = current_transaction()
        transaction._sampled = True

        with DatabaseTrace(transaction, sql):
            pass

    _test()


@validate_span_events(
    count=1,
    exact_intrinsics={
        'name': 'External/example.com/library/get',
        'type': 'Span',
        'sampled': True,

        'category': 'http',
        'span.kind': 'client',
        'http.url': 'http://example.com/foo',
        'component': 'library',
        'http.method': 'get',
    },
    expected_intrinsics=('priority',),
)
@override_application_settings({
    'distributed_tracing.enabled': True,
    'span_events.enabled': True,
})
@background_task(name='test_external_spans')
def test_external_spans():
    transaction = current_transaction()
    transaction._sampled = True

    with ExternalTrace(
            transaction,
            library='library',
            url='http://example.com/foo?secret=123',
            method='get'):
        pass