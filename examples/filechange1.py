"""
Watch file changes in this directory
"""

from automate import *


class mysys(System):
    fs = FileChangeSensor(filename="/storage/", silent=True)
    p = Program(
        triggers=[fs],
        # update_condition = Equal(Shell("cat file.txt"),Value("dodi")),
        #update_condition=Changed(Equal(Eval("open('file.txt').read().strip()"), Value("dodi"))),
        #update_condition = Equal(Eval("open('file.txt').read().strip()"),Value("dodi")),
        #on_update = Log(Changed(Equal(Eval("open('file.txt').read().strip()"),Value("dodi")))),
        update_condition=Value(True),
        on_update=Run(Log(ToStr(fs)))  # , Exec("import traceback; print ''.join(traceback.format_stack())")),
    )

s = mysys()
