import os
import sys
import signal
import time
from subprocess import \
    check_output, \
    CalledProcessError

from State import State
from Client import Client
from Command import Command
from daemonize import Daemonize
from PackageInfo import PackageInfo
from ClientOption import ClientOption
from ClientLogger import ClientLogger
from LoggedRequest import LoggedRequest
from CommandExecutor import CommandExecutor


# noinspection PyClassHasNoInit
class ClientDaemon:

    @staticmethod
    def start(opts, args):
        logger = ClientLogger.setup()
        if not ClientDaemon.__status(opts, args):
            try:
                pid_file = opts.get(ClientOption.PID_FILE)
                foreground = opts.get(ClientOption.DEBUG)

                def start():
                    Client.run(opts, args)

                daemon = Daemonize(
                    app=PackageInfo.pip_package_name,
                    pid=pid_file,
                    action=start,
                    foreground=foreground,
                    verbose=True,
                    logger=logger,
                    auto_close_fds=False
                )
                daemon.start()
            except Exception as e:
                logger.debug('%s start failed.', PackageInfo.pip_package_name)
                logger.exception(e)
                raise e
        else:
            sys.stdout.write('{0} is already running...\n'.format(PackageInfo.pip_package_name))
            sys.stdout.flush()
            sys.exit(1)

    @staticmethod
    def stop(opts, args):
        logger = ClientLogger.setup()
        pid_file = opts.get(ClientOption.PID_FILE)
        logout_coast_time = opts.get(ClientOption.LOGOUT_COAST_TIME)
        max_power_down_timeout = opts.get(ClientOption.MAX_POWER_DOWN_TIMEOUT)

        try:
            for process_id in ClientDaemon.__get_process_ids():
                try:
                    os.kill(process_id, signal.SIGTERM)
                except Exception as e:
                    logger.exception(e)
        except CalledProcessError:
            pass

        # Wait for what we assume will be a graceful exit,
        # this will exit early if the pid file is removed as expected.
        current = time.time()
        max_wait_time = max_power_down_timeout + logout_coast_time + 5
        while time.time() - current < max_wait_time and os.path.isfile(pid_file):
            time.sleep(0.1)

        # This should never happen, but... if the pid file still exist at this point, we will nuke it from orbit!
        # Otherwise it will prevent the client daemon from starting again...
        if os.path.isfile(pid_file):
            try:
                os.remove(pid_file)
            except Exception as e:
                logger.exception(e)

    @staticmethod
    def update(opts, args):

        if not ClientDaemon.__is_in_use(opts, args):
            logger = ClientLogger.setup()

            try:
                requested_version = args[1] if len(args) >= 2 else None
                if ClientDaemon.__should_update(opts, requested_version):
                    ClientDaemon.stop(opts, args)

                    requested_package = PackageInfo.pip_package_name

                    if requested_version:
                        requested_package = '{0}=={1}'.format(requested_package, requested_version)

                    CommandExecutor().execute_commands([
                        'pip install --upgrade --force-reinstall --ignore-installed --no-cache-dir {0}'
                        .format(requested_package)
                    ])
                else:
                    version = 'current' if not requested_version else 'requested'

                    sys.stdout.write(
                        '{0} v{1} already matches the {2} version. \n'
                        'Use the --force-update option to bypass the version check and re-install.\n'.format(
                            PackageInfo.pip_package_name,
                            PackageInfo.version,
                            version
                        ))
                    sys.stdout.flush()
                    sys.exit(1)
            except Exception as e:
                logger.debug('%s update failed, remediation maybe required!', PackageInfo.pip_package_name)
                logger.exception(e)
                raise e
            finally:
                if not ClientDaemon.__status(opts, args):
                    ClientDaemon.restart(opts, args)

        else:
            sys.stdout.write('{0} is currently in use, try again later...\n'.format(PackageInfo.pip_package_name))
            sys.stdout.flush()
            sys.exit(1)

    @staticmethod
    def __should_update(opts, requested_version=None):
        if opts.get(ClientOption.FORCE_UPDATE):
            return True

        response = LoggedRequest.get('https://pypi.python.org/pypi/{0}/json'.format(PackageInfo.pip_package_name))
        response.raise_for_status()
        data = response.json()

        current_version = PackageInfo.version
        latest_version = data.get('info', {}).get('version', '0.0.0')
        latest_version = '.'.join([s.zfill(2) for s in latest_version.split('.')])
        if not requested_version:
            return current_version != latest_version

        requested_version = '.'.join([s.zfill(2) for s in requested_version.split('.')])
        return current_version != requested_version

    @staticmethod
    def restart(opts, args):
        logger = ClientLogger.setup()
        reboot_delay = opts.get(ClientOption.REBOOT_DELAY)
        try:
            args[0] = Command.STOP.get('command')
            ClientDaemon.stop(opts, args)
            logger.debug('Restarting in %s seconds...', reboot_delay)
            time.sleep(reboot_delay)
            args[0] = Command.START.get('command')
            ClientDaemon.start(opts, args)
        except Exception as e:
            logger.debug('%s restart failed.', PackageInfo.pip_package_name)
            logger.exception(e)
            raise e

    @staticmethod
    def status(opts, args):
        status = ClientDaemon.__status(opts, args)
        if status:
            sys.stdout.write('{0}\n'.format(status))
            sys.stdout.flush()
            sys.exit(0)
        else:
            sys.stdout.write('{0}\n'.format(State.TERMINATED))
            sys.stdout.flush()
            sys.exit(1)

    @staticmethod
    def __status(opts, _):
        process_ids = ClientDaemon.__get_process_ids()
        status_file = opts.get(ClientOption.STATUS_FILE)

        status = terminated = State.TERMINATED
        if os.path.isfile(status_file):
            with open(status_file, 'r') as f:
                status = f.readline().strip()

        return status if status is not terminated and len(process_ids) > 0 else None

    @staticmethod
    def __is_in_use(opts, args):
        status = ClientDaemon.__status(opts, args)
        return status == State.IN_USE or status == State.IN_TRAINING

    @staticmethod
    def __get_process_ids():
        process_ids = []

        cmd = ['pgrep', '-f', '(/{0}\s+(start|restart|update))'.format(PackageInfo.pip_package_name)]
        for process_id in check_output(cmd).splitlines():
            process_id = int(process_id)
            is_current_process = process_id == int(os.getpid())
            if not is_current_process:
                process_ids.append(process_id)

        return process_ids
