"""
コネクターファクトリー
USE_MOCK=true のとき自動的にモック実装を返す
"""
from __future__ import annotations

from ceo_system.config import get_config


def get_calendar_connector():
    if get_config().use_mock:
        from ceo_system.mock.connectors import MockGoogleCalendarConnector
        return MockGoogleCalendarConnector()
    from ceo_system.connectors.google_calendar import GoogleCalendarConnector
    return GoogleCalendarConnector()


def get_docs_connector(credentials=None):
    if get_config().use_mock:
        from ceo_system.mock.connectors import MockGoogleDocsConnector
        return MockGoogleDocsConnector()
    if credentials is None:
        return None
    from ceo_system.connectors.google_docs import GoogleDocsConnector
    return GoogleDocsConnector(credentials)


def get_gmail_connector(credentials=None):
    if get_config().use_mock:
        from ceo_system.mock.connectors import MockGmailConnector
        return MockGmailConnector()
    if credentials is None:
        return None
    from ceo_system.connectors.gmail import GmailConnector
    return GmailConnector(credentials)


def get_line_works_connector():
    if get_config().use_mock:
        from ceo_system.mock.connectors import MockLineWorksConnector
        return MockLineWorksConnector()
    from ceo_system.connectors.line_works import LineWorksConnector
    return LineWorksConnector()


def get_sakumiru_connector():
    if get_config().use_mock:
        from ceo_system.mock.connectors import MockSakumiruConnector
        return MockSakumiruConnector()
    from ceo_system.connectors.sakumiru import SakumiruConnector
    return SakumiruConnector()
