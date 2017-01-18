import sys
import unittest
from mock import patch

from tinker_access_client.tinker_access_client.ClientDaemon import ClientDaemon
from tinker_access_client.tinker_access_client.ClientLogger import ClientLogger
from tinker_access_client.tinker_access_client.CommandHandler import CommandHandler
from tinker_access_client.tinker_access_client.ClientOptionParser import ClientOptionParser

#TODO: add test for __enter__, __exit__ and refactor to use context statements with CommandHandler() as etc..

@unittest.skip("temporarily disabled")
class TestCommandHandler(unittest.TestCase):
    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'start')
    def test_startCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['start'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.start.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'stop')
    def test_stopCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['stop'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.stop.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'restart')
    def test_restartCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['restart'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.restart.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'restart')
    def test_restartFromReloadCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['reload'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.restart.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'restart')
    def test_restartFromForReloadCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['force_reload'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.restart.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientOptionParser, '__new__')
    @patch.object(ClientDaemon, 'status')
    def test_statusCommand(self, _, mock_parser, mock_setup):
        mock_parser.return_value.parse_args.return_value = ({}, ['status'])
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(ClientDaemon.status.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @patch.object(sys, 'exit')
    @patch.object(ClientLogger, 'setup')
    @patch.object(ClientDaemon, 'start')
    @patch.object(ClientOptionParser, '__new__')
    def test_logsUnexpectedExceptions(self, mock_parser, mock_start, mock_setup, mock_exit):
        mock_parser.return_value.parse_args.return_value = ({}, ['start'])
        mock_start.side_effect = RuntimeError
        CommandHandler().run()

        logger = mock_setup.return_value
        self.assertEqual(logger.debug.call_count, 2)
        self.assertEqual(logger.exception.call_count, 1)
        mock_exit.assert_called_with(1)