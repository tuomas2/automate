"""
Watch file changes in this directory
"""

from automate import *


class mysys(System):
    fs = FileChangeSensor(filename="./", silent=True)
    p = Program(
        triggers=[fs],
        update_condition=Value(True),
        on_update=Run(Log(ToStr(fs)))
    )

s = mysys()
