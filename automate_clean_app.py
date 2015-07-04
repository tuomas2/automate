#!/usr/bin/env python
# encoding: utf-8

from automate import *

config = get_config()

config.set(
    debug=False,
    autosave_interval=10 * 60,
    http_auth=()
)

if __name__ == '__main__':
    import sys

    fname = ""
    if len(sys.argv) == 2:
        fname = sys.argv[1]
    load_state(fname)
    main()
