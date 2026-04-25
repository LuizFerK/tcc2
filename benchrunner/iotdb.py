from benchrunner import iot_benchmark


def run(test_type):
    iot_benchmark.run(test_type)


def write():
    run('write')


def read():
    run('read')
