import asyncio
import pytest
from testing_support.fixtures import (
    dt_enabled,
    validate_transaction_metrics,
)
from testing_support.validators.validate_span_events import validate_span_events
from newrelic.api.background_task import background_task

from test_application import is_graphql_2


@pytest.fixture(scope="session")
def graphql_run_async():
    from graphql import graphql, __version__ as version

    major_version = int(version.split(".")[0])
    if major_version == 2:

        def graphql_run(*args, **kwargs):
            return graphql(*args, return_promise=True, **kwargs)

        return graphql_run
    else:
        return graphql


@dt_enabled
def test_query_and_mutation_async(app, graphql_run_async, is_graphql_2):
    from graphql import __version__ as version

    FRAMEWORK_METRICS = [
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]
    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/GraphQL/storage", 1),
        ("GraphQL/resolve/GraphQL/storage_add", 1),
        ("GraphQL/operation/GraphQL/query/<anonymous>/storage", 1),
        ("GraphQL/operation/GraphQL/mutation/<anonymous>/storage_add", 1),
    ]
    _test_mutation_unscoped_metrics = [
        ("OtherTransaction/all", 1),
        ("GraphQL/all", 2),
        ("GraphQL/GraphQL/all", 2),
        ("GraphQL/allOther", 2),
        ("GraphQL/GraphQL/allOther", 2),
    ] + _test_mutation_scoped_metrics

    _expected_mutation_operation_attributes = {
        "graphql.operation.type": "mutation",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.name": "storage_add",
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
        "graphql.field.returnType": "[String]" if is_graphql_2 else "String",
    }
    _expected_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_query_resolver_attributes = {
        "graphql.field.name": "storage",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
        "graphql.field.returnType": "[String]",
    }

    @validate_transaction_metrics(
        "query/<anonymous>/storage",
        "GraphQL",
        scoped_metrics=_test_mutation_scoped_metrics,
        rollup_metrics=_test_mutation_unscoped_metrics + FRAMEWORK_METRICS,
        background_task=True,
    )
    @validate_span_events(exact_agents=_expected_mutation_operation_attributes)
    @validate_span_events(exact_agents=_expected_mutation_resolver_attributes)
    @validate_span_events(exact_agents=_expected_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_query_resolver_attributes)
    @background_task()
    def _test():
        async def coro():
            response = await graphql_run_async(
                app, 'mutation { storage_add(string: "abc") }'
            )
            assert not response.errors
            response = await graphql_run_async(app, "query { storage }")
            assert not response.errors

            # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
            assert "storage" in str(response.data)
            assert "abc" in str(response.data)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(coro())

    _test()
