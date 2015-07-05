"""
Watch file changes in this directory

Detects if content of file.txt is "dodi".
"""

from automate import *


class mysys(System):
    fs = FileChangeSensor(filename="./file.txt", silent=True)
    p = Program(
        triggers=[fs],
        update_condition=Changed(Equal(Eval("open('file.txt').read().strip()"), Value("dodi"))),
        on_update=Run(Log(ToStr("Hep!")))
    )

s = mysys()
