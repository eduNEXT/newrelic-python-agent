import pytest
import random

from testing_support.fixtures import (
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)
from testing_support.mock_external_grpc_server import MockExternalgRPCServer

_coverage_source = []

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
    "agent_limits.errors_per_harvest": 100,
    "distributed_tracing.enabled": True,
    "mtb.endpoint": "https://nr-internal.aws-us-east-2.tracing.staging-edge.nr-data.net/",
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (backend_mtb)", default_settings=_default_settings
)


@pytest.fixture(scope="module")
def grpc_app_server():
    port = random.randint(50000, 50099)
    with MockExternalgRPCServer(port=port) as server:
        yield server, port


@pytest.fixture(scope="module")
def mock_grpc_server(grpc_app_server):
    from _test_handler import HANDLERS

    server, port = grpc_app_server
    server.add_generic_rpc_handlers(HANDLERS)
    return port


@pytest.fixture(scope="session")
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope="function")
def requires_data_collector(collector_available_fixture):
    pass
