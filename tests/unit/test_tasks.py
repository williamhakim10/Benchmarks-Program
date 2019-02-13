import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, ANY, call
import json
import pytest
import pandas as pd
from app.tasks import (
    send_activated_email, import_analyze_store_list, generate_summary_stats,
    send_report, extract_stats, init_list_analysis, update_stored_data,
    send_monthly_reports, generate_diffs)
from app.lists import MailChimpImportError
from app.models import ListStats

def test_send_activated_email(mocker):
    """Tests the send_activated_email function."""
    mocked_send_email = mocker.patch('app.tasks.send_email')
    send_activated_email('foo@bar.com', 'foo')
    mocked_send_email.assert_called_with(
        ANY,
        ['foo@bar.com'],
        'activated-email.html',
        {'title': ANY,
         'email_hash': 'foo'})

@pytest.mark.xfail(raises=MailChimpImportError, strict=True)
@pytest.mark.parametrize('user_email', [(None), ('foo@bar.com')])
def test_import_analyze_store_list_maichimpimporterror(mocker, user_email):
    """Tests that the import_analyze_store_list function fails gracefully when
    a MailChimpImportError occurs."""
    mocker.patch('app.tasks.MailChimpList')
    mocked_do_async_import = mocker.patch('app.tasks.do_async_import')
    mocked_do_async_import.side_effect = MailChimpImportError('foo', 'bar')
    mocked_send_email = mocker.patch('app.tasks.send_email')
    mocked_os = mocker.patch('app.tasks.os')
    mocked_os.environ.get.side_effect = ['admin@foo.com']
    import_analyze_store_list(
        {'list_id': 'foo', 'total_count': 'bar', 'key': 'foo-bar1',
         'data_center': 'bar1'}, 1, user_email=user_email)
    if user_email:
        mocked_send_email.assert_called_with(
            ANY,
            ['foo@bar.com', 'admin@foo.com'],
            'error-email.html',
            {'title': ANY,
             'error_details': 'bar'})
    else:
        mocked_send_email.assert_not_called()

def test_import_analyze_store_list(
        mocker, fake_list_data, fake_calculation_results, mocked_mailchimp_list):
    """Tests the import_analyze_store_list method."""
    mocked_mailchimp_list_instance = mocked_mailchimp_list.return_value
    mocked_do_async_import = mocker.patch('app.tasks.do_async_import')
    mocked_list_stats = mocker.patch('app.tasks.ListStats', spec=ListStats)
    list_stats = import_analyze_store_list(
        fake_list_data, fake_list_data['org_id'])
    mocked_mailchimp_list.assert_called_with(
        fake_list_data['list_id'], fake_list_data['total_count'],
        fake_list_data['key'], fake_list_data['data_center'])
    mocked_do_async_import.assert_has_calls(
        mocked_mailchimp_list_instance.import_list_members.return_value,
        mocked_mailchimp_list_instance.import_sub_activity.return_value)
    mocked_mailchimp_list_instance.flatten.assert_called()
    mocked_mailchimp_list_instance.calc_list_breakdown.assert_called()
    mocked_mailchimp_list_instance.calc_open_rate.assert_called_with(
        fake_list_data['open_rate'])
    mocked_mailchimp_list_instance.calc_frequency.assert_called_with(
        fake_list_data['creation_timestamp'], fake_list_data['campaign_count'])
    mocked_mailchimp_list_instance.calc_histogram.assert_called()
    mocked_mailchimp_list_instance.calc_high_open_rate_pct.assert_called()
    mocked_mailchimp_list_instance.calc_cur_yr_stats.assert_called()
    assert isinstance(list_stats, ListStats)
    mocked_list_stats.assert_called_with(
        **{k: (v if k != 'hist_bin_counts' else json.dumps(v))
           for k, v in fake_calculation_results.items()},
        list_id=fake_list_data['list_id'])

def test_import_analyze_store_list_store_results_in_db( # pylint: disable=unused-argument
        mocker, fake_list_data, mocked_mailchimp_list):
    """Tests the import_analyze_store_list function when data
    is stored in the db."""
    mocker.patch('app.tasks.do_async_import')
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_db = mocker.patch('app.tasks.db')
    fake_list_data['monthly_updates'] = True
    import_analyze_store_list(fake_list_data, 'foo')
    mocked_email_list.assert_called_with(
        list_id=fake_list_data['list_id'],
        creation_timestamp=fake_list_data['creation_timestamp'],
        list_name=fake_list_data['list_name'],
        api_key=fake_list_data['key'],
        data_center=fake_list_data['data_center'],
        store_aggregates=fake_list_data['store_aggregates'],
        monthly_updates=fake_list_data['monthly_updates'],
        org_id='foo')
    mocked_db.session.merge.assert_called_with(mocked_email_list.return_value)
    mocked_db.session.add.assert_called_with(mocked_list_stats.return_value)
    mocked_db.session.commit.assert_called()

def test_import_analyze_store_list_store_results_in_db_exception( # pylint: disable=unused-argument
        mocker, fake_list_data, mocked_mailchimp_list):
    """Tests the import_analyze_store_list function when data
    is stored in the db and an exception occurs."""
    mocker.patch('app.tasks.do_async_import')
    mocker.patch('app.tasks.ListStats')
    mocker.patch('app.tasks.EmailList')
    mocked_db = mocker.patch('app.tasks.db')
    mocked_db.session.commit.side_effect = Exception()
    fake_list_data['monthly_updates'] = True
    with pytest.raises(Exception):
        import_analyze_store_list(fake_list_data, 'foo')
    mocked_db.session.rollback.assert_called()

def test_generate_summary_stats_single_analysis(
        mocker, fake_list_stats_query_result_as_df,
        fake_list_stats_query_result_means):
    """Tests the generate_summary_stats function when passed a single analysis."""
    mocked_extract_stats = mocker.patch('app.tasks.extract_stats')
    mocked_extract_stats.return_value = {'foo': 1, 'bar': 2}
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_db = mocker.patch('app.tasks.db')
    mocked_pd_read_sql = mocker.patch('app.tasks.pd.read_sql')
    mocked_pd_read_sql.return_value = fake_list_stats_query_result_as_df
    list_stats, agg_stats = generate_summary_stats(['foo'])
    mocked_extract_stats.assert_called_once()
    mocked_pd_read_sql.assert_called_with(
        mocked_list_stats.query.filter.return_value.order_by.return_value
        .distinct.return_value.statement,
        mocked_db.session.bind)
    assert list_stats == {'foo': [1], 'bar': [2]}
    assert agg_stats == fake_list_stats_query_result_means

def test_generate_summary_stats_multiple_analyses(
        mocker, fake_list_stats_query_result_as_df,
        fake_list_stats_query_result_means):
    """Tests the generate_summary_stats function when passed two sets of analysis."""
    mocked_extract_stats = mocker.patch('app.tasks.extract_stats')
    mocked_extract_stats.return_value = {'foo': 1, 'bar': 2}
    mocked_db = mocker.patch('app.tasks.db')
    mocked_pd_read_sql = mocker.patch('app.tasks.pd.read_sql')
    fake_list_stats_query_result_as_df = pd.concat([
        fake_list_stats_query_result_as_df.assign(row_number=1),
        fake_list_stats_query_result_as_df.assign(row_number=2)])
    mocked_pd_read_sql.return_value = fake_list_stats_query_result_as_df
    list_stats, agg_stats = generate_summary_stats(['foo', 'bar'])
    mocked_extract_stats.assert_has_calls([call('foo'), call('bar')])
    mocked_pd_read_sql.assert_called_with(ANY, mocked_db.session.bind)
    assert list_stats == {'foo': [1, 1], 'bar': [2, 2]}
    assert agg_stats == {
        k: [*v, *v] for k, v in
        fake_list_stats_query_result_means.items()
    }

def test_generate_diffs():
    """Tests the generate_diffs function."""
    fake_list_stats = {
        'subscribers': [1, 2],
        'open_rate': [0, 0.5]
    }
    fake_agg_stats = {
        'subscribers': [10, 5],
        'open_rate': [0.3, 0.4]
    }
    diffs = generate_diffs(fake_list_stats, fake_agg_stats)
    assert diffs == {
        'subscribers': ['+100.0%', '-50.0%'],
        'open_rate': ['+0.0%', '+33.3%']
    }

def test_send_report_no_prev_month(mocker, fake_calculation_results):
    """Tests the send_report function when list_stats and agg_stats only contain
    one set of results."""
    mocked_generate_diffs = mocker.patch('app.tasks.generate_diffs')
    mocker.patch('app.tasks.draw_bar')
    mocker.patch('app.tasks.draw_stacked_horizontal_bar')
    mocker.patch('app.tasks.draw_histogram')
    mocker.patch('app.tasks.draw_donuts')
    mocker.patch('app.tasks.send_email')
    fake_stats = {k: [v] for k, v in fake_calculation_results.items()}
    send_report(fake_stats, fake_stats, '1', 'foo', ['foo@bar.com'])
    mocked_generate_diffs.assert_not_called()

def test_send_report_has_prev_month(mocker, fake_calculation_results):
    """Tests the send_report function when list_stats and agg_stats contain two
    sets of results."""
    mocked_generate_diffs = mocker.patch('app.tasks.generate_diffs')
    mocker.patch('app.tasks.draw_bar')
    mocker.patch('app.tasks.draw_stacked_horizontal_bar')
    mocker.patch('app.tasks.draw_histogram')
    mocker.patch('app.tasks.draw_donuts')
    mocker.patch('app.tasks.send_email')
    fake_stats = {k: [v, v] for k, v in fake_calculation_results.items()}
    send_report(fake_stats, fake_stats, '1', 'foo', ['foo@bar.com'])
    mocked_generate_diffs.assert_called_with(fake_stats, fake_stats)

def test_send_report(mocker, fake_calculation_results):
    """Tests the send_report function."""
    mocked_generate_diffs = mocker.patch('app.tasks.generate_diffs')
    mocked_generate_diffs.return_value = {
        k: [v, v] for k, v in fake_calculation_results.items()
    }
    mocked_draw_bar = mocker.patch('app.tasks.draw_bar')
    mocked_draw_stacked_horizontal_bar = mocker.patch(
        'app.tasks.draw_stacked_horizontal_bar')
    mocked_draw_histogram = mocker.patch('app.tasks.draw_histogram')
    mocked_draw_donuts = mocker.patch('app.tasks.draw_donuts')
    mocked_send_email = mocker.patch('app.tasks.send_email')
    mocker.patch('app.tasks.os.environ.get', return_value='bar')
    fake_stats = {k: [v, v] for k, v in fake_calculation_results.items()}
    send_report(fake_stats, fake_stats, '1', 'foo', ['foo@bar.com'])
    mocked_draw_bar.assert_has_calls([
        call(ANY, [2, 2, 2, 2], [2, 2], ANY, ANY),
        call(ANY, [0.5, 0.5, 0.5, 0.5], [0.5, 0.5], ANY, ANY, percentage_values=True)
    ])
    mocked_draw_stacked_horizontal_bar.assert_called_with(
        ANY,
        [('Subscribed %', [0.2, 0.2, 0.2, 0.2]),
         ('Unsubscribed %', [0.2, 0.2, 0.2, 0.2]),
         ('Cleaned %', [0.2, 0.2, 0.2, 0.2]),
         ('Pending %', [0.1, 0.1, 0.1, 0.1])],
        [0.2, 0.2], ANY, ANY)
    mocked_draw_histogram.assert_called_with(
        ANY, {'title': 'Subscribers', 'vals': [0.1, 0.2, 0.3]}, ANY, ANY, ANY)
    mocked_draw_donuts.assert_has_calls([
        call(ANY,
             [(ANY, [0.1, 0.9]), (ANY, [0.1, 0.9]),
              (ANY, [0.1, 0.9]), (ANY, [0.1, 0.9])],
             [0.1, 0.1], ANY, ANY),
        call(ANY,
             [(ANY, [0.1, 0.9]), (ANY, [0.1, 0.9]),
              (ANY, [0.1, 0.9]), (ANY, [0.1, 0.9])],
             [0.1, 0.1], ANY, ANY)
    ])
    mocked_send_email.assert_called_with(
        ANY, ['foo@bar.com'], ANY, {
            'title': 'We\'ve analyzed the foo list!',
            'list_id': '1',
            'epoch_time': ANY
        }, configuration_set_name='bar')

def test_extract_stats(fake_calculation_results):
    """Tests the extract_stats function."""
    fake_calculation_results.pop('frequency')
    fake_list_object = MagicMock(
        **{k: (json.dumps(v) if k == 'hist_bin_counts' else v)
           for k, v in fake_calculation_results.items()}
    )
    stats = extract_stats(fake_list_object)
    assert stats == fake_calculation_results

def test_init_list_analysis_existing_list_update_privacy_options(
        mocker, fake_list_data):
    """Tests the init_list_analysis function when the list exists in
    the database. Also tests that monthly_updates and store_aggregates
    are updated if they differ from that stored in the database."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_recent_analyses = (
        mocked_list_stats.query.filter_by.return_value.order_by
        .return_value.limit.return_value.all.return_value)
    mocked_desc = mocker.patch('app.tasks.desc')
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_list_object = (
        mocked_email_list.query.filter_by.return_value.first.return_value)
    mocked_list_object.monthly_updates = True
    mocked_list_object.store_aggregates = False
    mocked_db = mocker.patch('app.tasks.db')
    mocked_generate_summary_stats = mocker.patch(
        'app.tasks.generate_summary_stats')
    mocked_generate_summary_stats.return_value = 'foo', 'bar'
    mocked_send_report = mocker.patch('app.tasks.send_report')
    init_list_analysis({'email': 'foo@bar.com'}, fake_list_data, 1)
    mocked_list_stats.query.filter_by.assert_called_with(
        list_id=fake_list_data['list_id'])
    mocked_list_stats.query.filter_by.return_value.order_by.assert_called_with(
        mocked_desc.return_value)
    mocked_email_list.query.filter_by.assert_called_with(
        list_id=fake_list_data['list_id'])
    mocked_db.session.merge.assert_called_with(mocked_list_object)
    mocked_db.session.commit.assert_called()
    mocked_generate_summary_stats.assert_called_with(mocked_recent_analyses)
    mocked_send_report.assert_called_with(
        'foo', 'bar', fake_list_data['list_id'], fake_list_data['list_name'],
        ['foo@bar.com'])

def test_init_analysis_existing_list_db_error(mocker, fake_list_data):
    """Tests the init_list_analysis function when the list exists in the
    database and a database error occurs."""
    mocker.patch('app.tasks.ListStats')
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_list_object = (
        mocked_email_list.query.filter_by.return_value.first.return_value)
    mocked_list_object.monthly_updates = True
    mocked_list_object.store_aggregates = False
    mocked_db = mocker.patch('app.tasks.db')
    mocked_db.session.commit.side_effect = Exception()
    with pytest.raises(Exception):
        init_list_analysis({'email': 'foo@bar.com'}, fake_list_data, 1)
        mocked_db.session.rollback.assert_called()

def test_init_list_analysis_new_list_no_store(mocker, fake_list_data):
    """Tests the init_list_analysis function when the list does not exist
    in the database and the user chose not to store their data."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    (mocked_list_stats.query.filter_by.return_value.order_by
     .return_value.limit.return_value.all.return_value) = None
    mocked_import_analyze_store_list = mocker.patch(
        'app.tasks.import_analyze_store_list')
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_email_list.query.filter_by.return_value.first.return_value = None
    mocker.patch('app.tasks.generate_summary_stats', return_value=(
        'foo', 'bar'))
    mocker.patch('app.tasks.send_report')
    init_list_analysis({'email': 'foo@bar.com'}, fake_list_data, 1)
    mocked_import_analyze_store_list.assert_called_with(
        fake_list_data, 1, 'foo@bar.com')

def test_init_list_analysis_new_list_monthly_updates(mocker, fake_list_data):
    """Tests the init_list_analysis function when the list does not
    exist in the database and the user chose to store their data and
    requested monthly updates."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    (mocked_list_stats.query.filter_by.return_value.order_by
     .return_value.limit.return_value.all.return_value) = None
    mocker.patch('app.tasks.import_analyze_store_list')
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_list_object = (
        mocked_email_list.query.filter_by.return_value.first.return_value)
    mocked_list_object.monthly_updates = True
    mocked_list_object.store_aggregates = False
    mocked_associate_user_with_list = mocker.patch(
        'app.tasks.associate_user_with_list')
    mocker.patch('app.tasks.generate_summary_stats', return_value=(
        'foo', 'bar'))
    mocker.patch('app.tasks.send_report')
    fake_list_data['monthly_updates'] = True
    init_list_analysis(
        {'email': 'foo@bar.com', 'user_id': 2}, fake_list_data, 1)
    mocked_associate_user_with_list.assert_called_with(2, mocked_list_object)

def test_update_stored_data_empty_db(mocker, caplog):
    """Tests the update_stored_data function when there are no lists stored in
    the database."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    (mocked_list_stats.query.order_by.return_value.distinct
     .return_value.all.return_value) = None
    update_stored_data()
    assert 'No lists in the database!' in caplog.text

def test_update_stored_data_no_old_analyses(mocker, caplog):
    """Tests the update_stored_data function when there are no analyses older
    than 30 days."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_analysis = MagicMock(
        analysis_timestamp=datetime.now(timezone.utc))
    (mocked_list_stats.query.order_by.return_value.distinct
     .return_value.all.return_value) = [mocked_analysis]
    caplog.set_level(logging.INFO)
    update_stored_data()
    assert 'No old lists to update' in caplog.text


def test_update_stored_data(mocker, fake_list_data):
    """Tests the update_stored_data function."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_list_to_update = MagicMock(
        **{('api_key' if k == 'key' else k): v
           for k, v in fake_list_data.items()}
    )
    mocked_analysis = MagicMock(
        analysis_timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc),
        list=mocked_list_to_update,
        list_id=fake_list_data['list_id'])
    (mocked_list_stats.query.order_by.return_value.distinct
     .return_value.all.return_value) = [mocked_analysis]
    mocked_requests = mocker.patch('app.tasks.requests')
    mocked_import_analyze_store_list = mocker.patch(
        'app.tasks.import_analyze_store_list')
    mocked_requests.get.return_value.json.return_value = {
        'stats': {
            'member_count': 5,
            'unsubscribe_count': 6,
            'cleaned_count': 7,
            'open_rate': 1,
            'campaign_count': 10
        }
    }
    update_stored_data()
    mocked_requests.get.assert_called_with(
        'https://bar1.api.mailchimp.com/3.0/lists/foo',
        params=(
            ('fields', 'stats.member_count,'
                       'stats.unsubscribe_count,'
                       'stats.cleaned_count,'
                       'stats.open_rate,'
                       'stats.campaign_count'),
        ),
        auth=('shorenstein', 'foo-bar1'))
    mocked_import_analyze_store_list.assert_called_with(
        {'list_id': 'foo',
         'list_name': 'bar',
         'key': 'foo-bar1',
         'data_center': 'bar1',
         'monthly_updates': False,
         'store_aggregates': False,
         'total_count': 18,
         'open_rate': 1,
         'creation_timestamp': 'quux',
         'campaign_count': 10},
        1)

def test_update_stored_data_keyerror(mocker, fake_list_data, caplog):
    """Tests the update_stored_data function when the list raises a KeyError."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_list_to_update = MagicMock(
        **{('api_key' if k == 'key' else k): v
           for k, v in fake_list_data.items()}
    )
    mocked_analysis = MagicMock(
        analysis_timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc),
        list=mocked_list_to_update,
        list_id=fake_list_data['list_id'])
    (mocked_list_stats.query.order_by.return_value.distinct
     .return_value.all.return_value) = [mocked_analysis]
    mocked_requests = mocker.patch('app.tasks.requests')
    mocked_requests.get.return_value.json.return_value = {}
    with pytest.raises(MailChimpImportError):
        update_stored_data()
    assert ('Error updating list foo. API key is no longer valid or list '
            'no longer exists.') in caplog.text

def test_update_stored_data_import_error(mocker, fake_list_data, caplog):
    """Tests the update_stored_data function when the list import raises an error."""
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_list_to_update = MagicMock(
        **{('api_key' if k == 'key' else k): v
           for k, v in fake_list_data.items()}
    )
    mocked_analysis = MagicMock(
        analysis_timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc),
        list=mocked_list_to_update,
        list_id=fake_list_data['list_id'])
    (mocked_list_stats.query.order_by.return_value.distinct
     .return_value.all.return_value) = [mocked_analysis]
    mocked_requests = mocker.patch('app.tasks.requests')
    mocked_import_analyze_store_list = mocker.patch(
        'app.tasks.import_analyze_store_list')
    mocked_import_analyze_store_list.side_effect = MailChimpImportError(
        'foo', 'bar')
    mocked_requests.get.return_value.json.return_value = {
        'stats': {
            'member_count': 5,
            'unsubscribe_count': 6,
            'cleaned_count': 7,
            'open_rate': 1,
            'campaign_count': 10
        }
    }
    with pytest.raises(MailChimpImportError):
        update_stored_data()
    assert 'Error importing new data for list foo.' in caplog.text

def test_send_monthly_reports(mocker, fake_list_data, caplog):
    """Tests the send_monthly_reports function."""
    mocked_email_list = mocker.patch('app.tasks.EmailList')
    mocked_list = MagicMock(**fake_list_data)
    mocked_list.monthly_update_users = [MagicMock(email='foo@bar.com')]
    mocked_email_list.query.filter_by.return_value.all.return_value = [mocked_list]
    caplog.set_level(logging.INFO)
    mocked_list_stats = mocker.patch('app.tasks.ListStats')
    mocked_stats_object = (
        mocked_list_stats.query.filter_by.return_value.order_by
        .return_value.limit.return_value.all.return_value)
    mocked_list_stats = MagicMock()
    mocked_agg_stats = MagicMock()
    mocked_generate_summary_stats = mocker.patch(
        'app.tasks.generate_summary_stats',
        return_value=(mocked_list_stats, mocked_agg_stats))
    mocked_send_report = mocker.patch('app.tasks.send_report')
    send_monthly_reports()
    assert ('Emailing foo@bar.com an updated report. List: bar (foo).'
            in caplog.text)
    mocked_generate_summary_stats.assert_called_with(mocked_stats_object)
    mocked_send_report.assert_called_with(
        mocked_list_stats, mocked_agg_stats, 'foo', 'bar', ['foo@bar.com'])
