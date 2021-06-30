'''
Copyright (C) 2021 S[&]T, The Netherlands.
'''
import datetime
import io
import unittest
from unittest.mock import patch

from procsim.core.logger import Logger

node_name = 'ipf1ws1'
processor_name = 'IPF1'
processor_version = '01.04'
task_name = 'Preproc'
message = 'Processor starting'

log_msg = {
    'DEBUG': '2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 Preproc [0000013875]: [D] Processor starting\n',
    'INFO': '2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 Preproc [0000013875]: [I] Processor starting\n',
    'PROGRESS': '2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 Preproc [0000013875]: [P] Processor starting\n',
    'WARNING': '2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 Preproc [0000013875]: [W] Processor starting\n',
    'ERROR': '2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 Preproc [0000013875]: [E] Processor starting\n'
}


class LoggerTest(unittest.TestCase):

    def _call_log(self, logger, level, msg, expected_stdout_msg, expected_stderr_msg):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.log(level, msg)
                self.assertEqual(mock_out.getvalue(), expected_stdout_msg)
                self.assertEqual(mock_err.getvalue(), expected_stderr_msg)

    @patch('procsim.core.logger.os')
    @patch('procsim.core.logger.datetime')
    def testOutputMessage(self, mock_datetime, mock_os):
        mock_os.getpid.return_value = 13875
        mock_datetime.datetime.now.return_value = datetime.datetime(2004, 2, 24, 4, 2, 7, 458000)

        stdout_levels = Logger.LEVELS
        stderr_levels = Logger.LEVELS
        logger = Logger(
            node_name,
            processor_name,
            processor_version,
            stdout_levels,
            stderr_levels,
            task_name
        )
        for level in Logger.LEVELS:
            self._call_log(logger, level, message, log_msg[level], log_msg[level])

    @patch('procsim.core.logger.os')
    @patch('procsim.core.logger.datetime')
    def testLevelFiltering(self, mock_datetime, mock_os):
        mock_os.getpid.return_value = 13875
        mock_datetime.datetime.now.return_value = datetime.datetime(2004, 2, 24, 4, 2, 7, 458000)

        levels = ['DEBUG', 'INFO', 'PROGRESS', 'WARNING', 'ERROR']
        for idx in range(len(Logger.LEVELS) + 1):
            stdout_levels = levels[:idx]
            stderr_levels = levels[idx:]
            logger = Logger(
                node_name,
                processor_name,
                processor_version,
                stdout_levels,
                stderr_levels,
                task_name
            )
            for level in Logger.LEVELS:
                exp_out = log_msg[level] if level in stdout_levels else ''
                exp_err = log_msg[level] if level in stderr_levels else ''
                self._call_log(logger, level, message, exp_out, exp_err)

    @patch('procsim.core.logger.os')
    @patch('procsim.core.logger.datetime')
    def testNamedLogMethods(self, mock_datetime, mock_os):
        mock_os.getpid.return_value = 13875
        mock_datetime.datetime.now.return_value = datetime.datetime(2004, 2, 24, 4, 2, 7, 458000)

        stdout_levels = Logger.LEVELS
        stderr_levels = Logger.LEVELS
        logger = Logger(
            node_name,
            processor_name,
            processor_version,
            stdout_levels,
            stderr_levels,
            task_name
        )
        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.debug(message)
                self.assertEqual(mock_out.getvalue(), log_msg['DEBUG'])
                self.assertEqual(mock_err.getvalue(), log_msg['DEBUG'])

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.info(message)
                self.assertEqual(mock_out.getvalue(), log_msg['INFO'])
                self.assertEqual(mock_err.getvalue(), log_msg['INFO'])

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.progress(message)
                self.assertEqual(mock_out.getvalue(), log_msg['PROGRESS'])
                self.assertEqual(mock_err.getvalue(), log_msg['PROGRESS'])

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.warning(message)
                self.assertEqual(mock_out.getvalue(), log_msg['WARNING'])
                self.assertEqual(mock_err.getvalue(), log_msg['WARNING'])

        with patch('sys.stdout', new_callable=io.StringIO) as mock_out:
            with patch('sys.stderr', new_callable=io.StringIO) as mock_err:
                logger.error(message)
                self.assertEqual(mock_out.getvalue(), log_msg['ERROR'])
                self.assertEqual(mock_err.getvalue(), log_msg['ERROR'])


if __name__ == '__main__':
    unittest.main()
