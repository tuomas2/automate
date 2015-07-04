import sys
from xmlrpclib import ServerProxy
host = (len(sys.argv) == 2 and sys.argv[1]) or 'http://raspi2:8080/'
server = ServerProxy(host)
import sys
import termios
import tty
import string


def onechar(prompt):
    print prompt,
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rv = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print
    return rv

chars = list(string.ascii_lowercase)
for i in 'qlas':
    chars.remove(i)

while True:
    server.flush()
    websensors = server.get_websensors()
    d = {}
    print
    print 'Web sensors'
    for i, name in enumerate(websensors.keys()):
        print '%s %20.20s: %s' % (chars[i], name, websensors[name])
        d[chars[i]] = name
    print

    print 'l  -> log'
    print 'a  -> actuators'
    print 's  -> sensors'
    print 'q  -> quit'
    cmd = onechar('\ntoggle?')
    if cmd == 'q':
        break
    if cmd == 'l':
        print server.log()
    if cmd == 'a':
        for name, value in server.get_actuators().iteritems():
            print '%20.20s: %s' % (name, value)
    if cmd == 's':
        for name, value in server.get_sensors().iteritems():
            print '%20.20s: %s' % (name, value)
    elif cmd in d:
        server.toggle_object_status(d[cmd])
