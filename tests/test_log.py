from mininterface import Mininterface, run
from configs import ConflictingEnv, SimpleEnv
from shared import TestAbstract


import logging
from unittest.mock import patch


class TestLog(TestAbstract):
    @staticmethod
    def log(object=SimpleEnv):
        run(object, interface=Mininterface)
        logger = logging.getLogger(__name__)
        logger.debug("debug level")
        logger.info("info level")
        logger.warning("warning level")
        logger.error("error level")

    @patch('logging.basicConfig')
    def test_run_verbosity0(self, mock_basicConfig):
        self.sys("-v")
        with self.assertRaises(SystemExit):
            run(SimpleEnv, add_verbose=False, interface=Mininterface)
        mock_basicConfig.assert_not_called()

    @patch('logging.basicConfig')
    def test_run_verbosity1(self, mock_basicConfig):
        self.log()
        mock_basicConfig.assert_not_called()

    @patch('logging.basicConfig')
    def test_run_verbosity2(self, mock_basicConfig):
        self.sys("-v")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format='%(levelname)s - %(message)s')

    @patch('logging.basicConfig')
    def test_run_verbosity2b(self, mock_basicConfig):
        self.sys("--verbose")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format='%(levelname)s - %(message)s')

    @patch('logging.basicConfig')
    def test_run_verbosity3(self, mock_basicConfig):
        self.sys("-vv")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.DEBUG, format='%(levelname)s - %(message)s')

    @patch('logging.basicConfig')
    def test_custom_verbosity(self, mock_basicConfig):
        """ We use an object, that has verbose attribute too. Which interferes with the one injected. """
        self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()

        self.sys("-v")
        with (self.assertStderr(contains="running-tests: error: unrecognized arguments: -v"), self.assertRaises(SystemExit)):
            self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()
