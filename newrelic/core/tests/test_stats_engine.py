import unittest


from newrelic.core.config import (global_settings, SPAN_EVENT_RESERVOIR_SIZE,
    DEFAULT_RESERVOIR_SIZE, apply_server_side_settings)
from newrelic.core.stats_engine import StatsEngine, LimitedDataSet


class TestStatsEngineCustomEvents(unittest.TestCase):

    def setUp(self):
        self.settings = global_settings()

    def test_custom_events_initial_values(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)
        self.assertEqual(stats.custom_events.num_samples, 0)
        self.assertEqual(stats.custom_events.num_seen, 0)

    def test_custom_events_reset_stats_set_capacity(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)

        self.settings.event_harvest_config.harvest_limits.custom_event_data = \
                500
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity, 500)

    def test_custom_events_capacity_same_as_transaction_events(self):
        stats = StatsEngine()

        ce_settings = self.settings.event_harvest_config.harvest_limits
        ce_settings.custom_event_data = DEFAULT_RESERVOIR_SIZE
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity,
                stats.transaction_events.capacity)

    def test_custom_events_reset_stats_after_adding_samples(self):
        stats = StatsEngine()

        stats.custom_events.add('event')
        self.assertEqual(stats.custom_events.num_samples, 1)
        self.assertEqual(stats.custom_events.num_seen, 1)

        stats.reset_stats(self.settings)
        self.assertEqual(stats.custom_events.num_samples, 0)
        self.assertEqual(stats.custom_events.num_seen, 0)


class TestStatsEngineSpanEvents(unittest.TestCase):

    def setUp(self):
        self.settings = global_settings()

    def test_span_events_initial_values(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, 100)
        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)

    def test_span_events_reset_stats_set_capacity_enabled(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, 100)

        original_setting = self.settings.event_harvest_config\
                .harvest_limits.span_event_data
        try:
            self.settings.event_harvest_config\
                    .harvest_limits.span_event_data = 321
            stats.reset_stats(self.settings)

            self.assertEqual(stats.span_events.capacity, 321)
        finally:
            self.settings.event_harvest_config\
                    .harvest_limits.span_event_data = original_setting

    def test_span_events_reset_stats_set_capacity_disabled(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, 100)
        stats.reset_stats(None)
        self.assertEqual(stats.span_events.capacity, 100)

    def test_span_events_reset_stats_after_adding_samples(self):
        stats = StatsEngine()

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)

    def test_span_events_harvest_snapshot(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = stats.harvest_snapshot()
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

    def test_span_events_merge(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = StatsEngine()
        snapshot.span_events.add('event')
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        stats.merge(snapshot)
        self.assertEqual(stats.span_events.num_samples, 2)
        self.assertEqual(stats.span_events.num_seen, 2)

    def test_span_events_rollback(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = StatsEngine()
        snapshot.span_events.add('event')
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        stats.rollback(snapshot)
        self.assertEqual(stats.span_events.num_samples, 2)
        self.assertEqual(stats.span_events.num_seen, 2)

    def test_server_side_config_over_capacity(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        over_capacity_settings = {
            'event_harvest_config.harvest_limits.span_event_data': 2 * SPAN_EVENT_RESERVOIR_SIZE,
        }
        stats.reset_stats(apply_server_side_settings(over_capacity_settings))
        self.assertEqual(
                    stats.span_events.capacity, 2 * SPAN_EVENT_RESERVOIR_SIZE)

    def test_server_side_config_under_capacity(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        under_capacity_settings = {
            'event_harvest_config.harvest_limits.span_event_data': SPAN_EVENT_RESERVOIR_SIZE / 2,
        }
        stats.reset_stats(apply_server_side_settings(under_capacity_settings))
        self.assertEqual(stats.span_events.capacity,
                SPAN_EVENT_RESERVOIR_SIZE / 2)


class TestLimitedDataSet(unittest.TestCase):

    def test_empty_set(self):
        instance = LimitedDataSet()

        self.assertEqual(list(instance.samples), [])
        self.assertEqual(instance.capacity, 200)
        self.assertEqual(instance.num_seen, 0)

        self.assertEqual(instance.sampling_info['reservoir_size'], 200)
        self.assertEqual(instance.sampling_info['events_seen'], 0)

    def test_single_item(self):
        instance = LimitedDataSet()

        instance.add(1)

        self.assertEqual(list(instance.samples), [1])
        self.assertEqual(instance.num_seen, 1)

        self.assertEqual(instance.sampling_info['reservoir_size'], 200)
        self.assertEqual(instance.sampling_info['events_seen'], 1)

    def test_at_capacity(self):
        instance = LimitedDataSet(10)

        for i in range(10):
            instance.add(i)

        self.assertEqual(instance.num_samples, 10)
        self.assertEqual(list(instance.samples), list(range(10)))
        self.assertEqual(instance.num_seen, 10)

        self.assertEqual(instance.sampling_info['reservoir_size'], 10)
        self.assertEqual(instance.sampling_info['events_seen'], 10)

    def test_over_capacity(self):
        instance = LimitedDataSet(10)

        for i in range(20):
            instance.add(i)

        self.assertEqual(instance.num_samples, 10)
        self.assertEqual(list(instance.samples), list(range(10)))
        self.assertEqual(instance.num_seen, 20)

        self.assertEqual(instance.sampling_info['reservoir_size'], 10)
        self.assertEqual(instance.sampling_info['events_seen'], 20)

    def test_should_sample(self):
        instance = LimitedDataSet(10)

        for i in range(10):
            self.assertTrue(instance.should_sample())
            instance.add(i)

        self.assertFalse(instance.should_sample())

    def test_merge_sampled_data_set_under_capacity(self):
        a = LimitedDataSet(capacity=100)
        b = LimitedDataSet(capacity=100)

        count_a = 8
        count_b = 9
        data_a = ['data_a %d' % i for i in range(count_a)]
        data_b = ['data_b %d' % i for i in range(count_b)]

        for i in data_a:
            a.add(i)

        for i in data_b:
            b.add(i)

        a.merge(b)

        self.assertEqual(a.num_seen, count_a + count_b)
        self.assertEqual(a.num_seen, a.num_samples)

        samples = list(a.samples)
        self.assertEqual(len(samples), a.num_seen)
        self.assertEqual(len(samples), count_a + count_b)
        self.assertEqual(samples, data_a + data_b)

        self.assertEqual(a.sampling_info['reservoir_size'], 100)
        self.assertEqual(a.sampling_info['events_seen'], count_a + count_b)

    def test_merge_sampled_data_set_over_capacity(self):
        capacity = 10
        a = LimitedDataSet(capacity=capacity)
        b = LimitedDataSet(capacity=capacity)

        count_a = 11
        count_b = 20
        data_a = ['data_a %d' % i for i in range(count_a)]
        data_b = ['data_b %d' % i for i in range(count_b)]

        for i in data_a:
            a.add(i)

        for i in data_b:
            b.add(i)

        a.merge(b)

        self.assertEqual(a.num_seen, count_a + count_b)
        self.assertEqual(a.num_samples, capacity)

        samples = list(a.samples)
        self.assertEqual(len(samples), capacity)
        self.assertEqual(samples, data_a[:capacity])

        self.assertEqual(a.sampling_info['reservoir_size'], capacity)
        self.assertEqual(a.sampling_info['events_seen'], count_a + count_b)

    def test_size_0(self):
        instance = LimitedDataSet(0)

        instance.add('x')
        self.assertEqual(list(instance.samples), [])

        self.assertEqual(instance.sampling_info['reservoir_size'], 0)
        self.assertEqual(instance.sampling_info['events_seen'], 1)


if __name__ == '__main__':
    unittest.main()
