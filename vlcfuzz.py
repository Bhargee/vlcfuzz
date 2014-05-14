import logging
import random
import socket
import sys
import string

from optparse import OptionParser

# Linebreak mandated by RTSP RFC whitepaper
CRLF = '\r\n'
# The different RTSP methods, similar to HTTP methods
methods = ['OPTIONS', 'DESCRIBE', 'SETUP', 'PLAY', 'GET_PARAMETER',
    'TEARDOWN', 'PAUSE']
log_file = 'vlcfuzz.log'
user_agent_str = 'User-Agent: VLC media player (LIVE555 Streaming Media v2010.02.10)'

def add_method_to_data(data_tuple, method):
    lst = list(data_tuple)
    lst[0] = method
    return tuple(lst)

def clear_log():
    with open(log_file, 'w') as f:
        f.write('')

def gen_data(size):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))

def send(data, ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
    except socket.error, (value, msg):
        if s:
            s.close()
        logger.error('Could not connect to target\n %s' % msg, exc_info=True)
        sys.exit(1)

    for packet in data:
        logger.info('Sending %s' % packet)
        try:
            s.send(packet)
        except:
            logger.error('Could not send packet %s' % packet)
        r = s.recv(1024)
        logger.info('Recieved %s' % r)
    s.close()

def junk_fuzz(min, max, step):
    size = min
    requests = []
    for method in methods:
        for i in xrange(max/step):
            req = '%s%s%s' % (method, gen_data(size), CRLF)
            requests.append(req)
            size += step
    return requests

def structured_fuzz(min, max, step, target, path, data):
    size = min
    requests = []
    for method in methods:
        for i in xrange(max/step):
            req = '%s rtsp://%s/%s%s%s%s%s%s%s%s' % add_method_to_data(data,method)
            requests.append(req)
            size += step
    return requests

def random_fuzz():
    pass

def do_fuzz(options):
    structured_formats = []
    structured_formats[0] = (None, options.target, options.file, None,
            ' RTSP/1.0', CRLF, 'CSeq: 1', CRLF, user_agent_str, CRLF+'\n')
    structured_formats[1] = (None, options.target, options.file, ' RTSP/1.0',
            CRLF, 'CSeq: 1', CRLF, user_agent_str, None, CRLF+'\n')
    structured_formats[2] = (None, options.target, options.file, ' RTSP/1.0',
            CRLF, 'CSeq: ', None, CRLF, user_agent_str, CRLF+'\n')
    structured_formats[3] = (None, options.target, options.file, ' RTSP/1.0',
            CRLF, 'CSeq: 2', CRLF, 'Accept: application/sdp', None, CRLF,
            user_agent_str+CRLF+'\n')


    logger.info('Starting Junk Fuzz')
    junk_fuzz_output = junk_fuzz(options.min, options.max, options.step)
    #send(junk_fuzz_output, options.target, options.port)

    for s in len(structured_formats):
        logger.info('Starting Structured Fuzz Seq %s' % str(s))
        structured_fuzz_output = structured_fuzz(options.min, options.max,
                options.step, options.target, options.file,
                structured_formats[s])
        #send(structured_fuzz_output, options.target, options.port)

if __name__ == '__main__':
    # Set up script flags and options
    parser = OptionParser()
    parser.add_option('-t', '--target', dest='target',
            help='IP of target machine',
            default='127.0.0.1')

    parser.add_option('-p', '--port', dest='port',
            help='Streaming port on target machine',
            type=int, default=554)

    parser.add_option('--min', dest='min',
            help='Minimum bytes of data',
            default=20)

    parser.add_option('--max', dest='max',
            help='Maximum bytes of data',
            default=100)

    parser.add_option('-s','--step', dest='step',
            help='Step size between min and max',
            default=20)

    parser.add_option('-f', '--file', dest='file',
            help='Path to stream file on host')

    # Get options
    options, args = parser.parse_args()

    # Set up logging, both to console and to LOG_FILE
    clear_log()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Fuzzing doesn't work without a remote stream file/path
    if options.file is None:
        logger.error('ERROR: Remote stream file not specified, quitting')
        sys.exit(1)

    # goto fuzzing entrypoint
    do_fuzz(options)
