import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.web_transaction
import newrelic.api.message_transaction

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance(settings.app_name)


@newrelic.api.message_transaction.message_transaction(library='library',
        destination_type='Exchange',
        destination_name='x')
def _test_function_1(message):
    pass


@newrelic.api.message_transaction.message_transaction(library='library',
        destination_type='Exchange',
        destination_name='x',
        application=application)
def _test_function_2():
    pass


class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_message_transaction(self):
        transaction = newrelic.api.message_transaction.MessageTransaction(
                library='library', destination_type='Exchange',
                destination_name='x',
                application=application)
        with transaction:
            pass

    def test_message_transaction_decorator_with_arg(self):
        _test_function_1('hello kitty')

    def test_message_transaction_decorator_no_arg(self):
        _test_function_2()

    def test_message_transaction_decorator_error(self):
        transaction = newrelic.api.message_transaction.MessageTransaction(
                library='library', destination_type='Exchange',
                destination_name='x',
                application=application)

        raises = False
        with transaction:
            try:
                _test_function_1('meow', None)
            except TypeError:
                raises = True
        assert raises

    def test_process_cat_empty_settings(self):

        class FakeApp(newrelic.api.application.Application):
            def activate(self, *args, **kwargs):
                pass

            @property
            def settings(self):
                return None

        transaction = newrelic.api.message_transaction.MessageTransaction(
                library='library', destination_type='Exchange',
                destination_name='x',
                application=FakeApp(settings.app_name))

        with transaction:
            transaction._process_incoming_cat_headers(None, None)

        assert transaction.client_cross_process_id is None
        assert transaction.client_account_id is None
        assert transaction.client_application_id is None


if __name__ == '__main__':
    unittest.main()