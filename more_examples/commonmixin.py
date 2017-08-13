from automate import *
import psutil

def meminfo():
    return psutil.virtual_memory().percent


def cpu_usage_():
    return psutil.cpu_percent()


class CommonMixin:
    class SystemInfo(Group):
        tags = 'web,analog'
        cpu_usage = PollingSensor(interval=10, status_updater=Func(cpu_usage_))
        memory = PollingSensor(interval=10, status_updater=Func(meminfo))