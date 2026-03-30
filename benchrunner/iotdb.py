from benchrunner import iot_benchmark

def write():
    iot_benchmark.run("insertTest")

def read():
    iot_benchmark.run("queryTest")
