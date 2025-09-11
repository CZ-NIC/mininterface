from mininterface import Mininterface
from configs import ConflictingEnv, SimpleEnv
from mininterface._lib.cli_flags import CliFlags
from mininterface._lib.run import run
from shared import TestAbstract


import logging
from unittest.mock import patch


class TestLog(TestAbstract):
    @staticmethod
    def log(object=SimpleEnv, add_verbose=True, add_quiet=False, args=None):
        run(object, add_verbose=add_verbose, add_quiet=add_quiet, args=args, interface=Mininterface)
        logger = logging.getLogger(__name__)
        logger.debug("debug level")
        logger.info("info level")
        logger.warning("warning level")
        logger.error("error level")

    @patch("logging.basicConfig")
    def test_run_verbosity0(self, mock_basicConfig):
        self.sys("-v")
        with self.assertRaises(SystemExit):
            run(SimpleEnv, add_verbose=False, interface=Mininterface)
        mock_basicConfig.assert_not_called()

    @patch("logging.basicConfig")
    def test_run_verbosity1(self, mock_basicConfig):
        self.log()
        # NOTE I do not like tests need force=True here.
        mock_basicConfig.assert_called_once_with(level=logging.WARNING, format="%(message)s", force=True)
        # mock_basicConfig.assert_not_called()

    @patch("logging.basicConfig")
    def test_run_verbosity2(self, mock_basicConfig):
        self.sys("-v")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format="%(message)s", force=True)

    @patch("logging.basicConfig")
    def test_run_verbosity2b(self, mock_basicConfig):
        self.sys("--verbose")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.INFO, format="%(message)s", force=True)

    @patch("logging.basicConfig")
    def test_run_verbosity3(self, mock_basicConfig):
        self.sys("-vv")
        self.log()
        mock_basicConfig.assert_called_once_with(level=logging.DEBUG, format="%(message)s", force=True)

    @patch("logging.basicConfig")
    def test_custom_verbosity(self, mock_basicConfig):
        """We use an object, that has verbose attribute too. Which interferes with the one injected."""
        self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()

        self.sys("-v")
        with (
            self.assertStderr(contains="running-tests: error: unrecognized arguments: -v"),
            self.assertRaises(SystemExit),
        ):
            self.log(ConflictingEnv)
        mock_basicConfig.assert_not_called()

    def test_quiet(self):
        with self.assertStderr("warning level\nerror level"):
            self.log()

        with self.assertStderr("warning level\nerror level"):
            self.log(add_quiet=True)

        with self.assertStderr("error level"):
            self.log(add_quiet=True, args=["-q"])

    def test_log_level(self):
        test_cases = [
            (True, 0, logging.WARNING),
            (True, 1, logging.INFO),
            (True, 2, logging.DEBUG),
            (True, 3, logging.NOTSET),
            (logging.INFO, 0, logging.INFO),
            (logging.INFO, 1, logging.DEBUG),
            (logging.INFO, 2, logging.NOTSET),
            (logging.INFO, 3, logging.NOTSET),
            (logging.ERROR, 1, logging.WARNING),
            # quiet flag
            (logging.WARNING, -1, logging.ERROR),
            # NOTE quiet might correspond to `verbose`
            # (logging.INFO, -1, logging.WARNING),
            # NOTE quiet might be used multiple times
            # (logging.INFO, -2, logging.ERROR),
        ]
        for base, count, expected in test_cases:
            cf = CliFlags(base)
            with self.subTest(count=count):
                self.assertEqual(cf.get_log_level(count), expected)

    def test_quiet_int(self):
        with self.assertStderr("error level"):
            self.log(add_quiet=True, args=["--quiet"])

    def test_verbose_int(self):
        with self.assertStderr("info level\nwarning level\nerror level"):
            self.log(add_verbose=logging.INFO, args=[])

    def test_verbose_int_param(self):
        with self.assertStderr("debug level\ninfo level\nwarning level\nerror level"):
            self.log(add_verbose=logging.INFO, args=["--verbose"])

    def test_verbose_sequence_1(self):
        with self.assertStderr("error level"):
            self.log(add_verbose=(35, 30, 25, 20, 15), args=[])

    def test_verbose_sequence_2(self):
        with self.assertStderr("warning level\nerror level"):
            self.log(add_verbose=(35, 30, 25, 20, 15), args=["-v"])

    def test_verbose_sequence_3(self):
        with self.assertStderr("warning level\nerror level"):
            self.log(add_verbose=(35, 30, 25, 20, 15), args=["-vv"])

    def test_verbose_sequence_4(self):
        with self.assertStderr("info level\nwarning level\nerror level"):
            self.log(add_verbose=(35, 30, 25, 20, 15), args=["-vvv"])
