# ####An RTSP protocol fuzzer for the VLC media player
import logging
import os
import random
import socket
import sys
import string

from optparse import OptionParser

# RTSP linebreak format, mandated by RTSP RFC whitepaper
CRLF = '\r\n'
# The different RTSP methods, similar to HTTP methods. Must appear at the
# beginning of requests
methods = ['OPTIONS', 'DESCRIBE', 'SETUP', 'PLAY', 'GET_PARAMETER',
    'TEARDOWN', 'PAUSE']
# Settings, changeable as user sees fit
log_file = 'vlcfuzz.log'
user_agent_str = 'User-Agent: VLC media player (LIVE555 Streaming Media v2010.02.10)'
protocol_str = 'AVP;unicast;client_port=36142-36143'
session_str = '98q2y3bkkjhgier2'
# The scale factor determines number of mutations (defined below) per request.
# 10% of a request string will be mutated. Increase this to increase mutations
mutate_scale_factor = .1
# File with basic EBNF grammar for an RTSP request. Requires Blab tool
grammar_file = 'rtsp_grammar.blab'

# Deletes contents of log file on every run, so the log file is fresh
def clear_log():
    with open(log_file, 'w') as f:
        f.write('')

# Generates a random string of the lenght SIZE, for use in do_random_fuzz
def gen_data(size):
    # String contains only uppercase letters and numbers, change if other
    # behavior is desired
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))

# Sends DATA (a list of request strings) to specified IP and PORT
def send(data, ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
    except socket.error, (value, msg):
        if s:
            s.close()
        logger.error('Could not connect to target\n %s' % msg, exc_info=True)
        # If connection is not possible, quit gracefully
        sys.exit(1)

    for packet in data:
        logger.info('Sending %s' % packet)
        r = None
        try:
            s.send(packet)
            r = s.recv(1024)
        except:
            logger.error('Could not send packet:\n%s' % packet)
        logger.info('Recieved %s' % r)
    s.close()

# First fuzzer function, simply creates bad requests that look like:
# > PAUSEJHGJSHFJGUY873687YQTWTDSHG376T38
# > PLAY8784YR8REYFUFHUYRIBDSH CHGBYEUYYTBB

def junk_fuzz(min, max, step):
    # The length of the requests starts at MIN and increases to MAX by increments of
    # size STEP
    size = min
    requests = []
    for method in methods:
        for i in xrange(max/step):
            # We craft the request with a method, a random string, and a
            # linebreak
            req = '%s%s%s' % (method, gen_data(size), CRLF)
            requests.append(req)
            # Increase request size for next request
            size += step
    return requests

# Takes an incomplete request from `do_randomized_fuzz`, fills out the missing
# pieces (the method and the random string data of length SIZE), and creates a
# request for every method
def structured_fuzz(min, max, step, target, path, data):
    size = min
    requests = []
    for method in methods:
        for i in xrange(max/step):
            req = '%s rtsp://%s/%s%s%s%s%s%s%s%s' % flesh_out_data(data,method,
                                                                    size)
            requests.append(req)
            size += step
    return requests

# Fuzzes with random strings as data (permissable under the RTSP RFC)
def do_randomized_fuzz(options, mutator_func):
    # `structured_formats` contains data sequences that are RTSP request corner
    # cases. The first `None` is filled in with a method, and the second with a
    # random string
    structured_formats = [
    # Normal, though minimal, format
    (None, options.target, options.file, None, ' RTSP/1.0', CRLF, 'CSeq: 1',
        CRLF, user_agent_str, CRLF+'\n'),

    # Another normal and minimal format with the order of data and user agent
    # string switched
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 1', CRLF,
        user_agent_str, None, CRLF+'\n'),

    # Same as above, but without a sequence number
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: ', None,
        CRLF, user_agent_str, CRLF+'\n'),

    # Added Accept string
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 2', CRLF,
        'Accept: application/sdp', None, CRLF+user_agent_str+CRLF+'\n'),

    # Added protocol version
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 3', CRLF,
        'Transport: ', None, '/'+ protocol_str+CRLF+user_agent_str+CRLF+'\n'),

    # Protocol version with extra data and semicolon
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 3', CRLF,
      'Transport: RTP/', None, ';'+protocol_str+CRLF+user_agent_str+CRLF+'\n'),

    # Even more protocol data
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 3',CRLF,
      'Transport: RTP/AVP',None,';'+protocol_str+CRLF+user_agent_str+CRLF+'\n'),

    # Request with session key but no value
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 6', CRLF,
        'Session: ', None, CRLF+user_agent_str+CRLF+'\n'),

    # Request with session key and session value
    (None, options.target, options.file, ' RTSP/1.0', CRLF, 'CSeq: 7', CRLF,
        'Session: '+session_str+CRLF+'Range: npt=', None,
        CRLF+user_agent_str+CRLF+'\n')]

    logger.info('Starting Junk Fuzz')
    junk_fuzz_output = junk_fuzz(options.min, options.max, options.step)
    send(junk_fuzz_output, options.target, options.port)

    s = 0
    for format in structured_formats:
        logger.info('Starting Structured Fuzz Seq %s' % str(s))
        # Create list of requests that match the current format
        structured_fuzz_output = structured_fuzz(options.min, options.max,
                options.step, options.target, options.file, format)
        # Mutate the requests according to the passed in MUTATOR_FUNC
        if mutator_func is not None:
            structured_fuzz_output = mutator_func(structured_fuzz_output)
        # Send to the target
        send(structured_fuzz_output, options.target, options.port)
        s += 1

# Replaces the `None`s in the structured request formats with valid headers and
# data
def flesh_out_data(data_tuple, method, size):
    lst = list(data_tuple)
    # The first `None` is always a method
    lst[0] = method
    # This list comprehension replaces the remaining `None`s with data
    return tuple([gen_data(size) if e is None else e for e in lst])

# This function implements more intelligent fuzzing based on a subset of the
# EBNF grammar for an RTSP request given in the RTSP RFC whitepaper. **This
# requires the installation of the
# [Blab](https://code.google.com/p/ouspg/wiki/Blab) tool **
def do_grammar_fuzz(options, mutator_func, num):
    requests = []
    # `setup_sent` makes sure a play request is not sent before a setup request,
    # which is illegal
    setup_sent = False
    logger.info('Starting grammar fuzz')
    for i in xrange(num):
        # First, get the basic request
        request = os.popen("cat %s | blab" % grammar_file).read()
        # Add the URI to the target
        request = request.replace('URI', 'rtsp://%s/%s' % (options.target,
                                options.file))
        # Add a sequence number, which increases by one for every request
        body = 'CSeq: %s%s' % (str(i+1), CRLF)
        setup_sent = setup_sent or 'SETUP' in request
        # Continue if a PLAY is seen before a setup
        if not setup_sent and 'PLAY' in request:
            continue
        # If there is a setup, we must add additional protocol information
        if 'SETUP' in request:
            body += 'Transport: RTP/%s;%s' % (protocol_str, CRLF)
        # If the request is to play, we need to add session info
        elif 'PLAY' in request:
            body += 'Range: npt=5-20%sSession=%s%s' % (CRLF, session_str, CRLF)
        # Likewise with a pause
        elif 'PAUSE' in request or 'RECORD' in request or 'TEARDOWN' in request:
            body += 'Session=%s%s' % (session_str, CRLF)
        # Replace the body of the request with the body we just generated
        request = request.replace("BODY", body)
        requests.append(request)
    # Mutate the requests if a mutator function is given
    if mutator_func is not None:
        grammar_fuzz_output = mutator_func(requests)
    send(grammar_fuzz_output, options.target, options.port)

# #####Mutators
# These functions change requests in ways that historically have lead to
# exploits in VLC and other media players

# Replaces characters with spaces at random, which is the source of a past known
# exploit in VLC
def random_mutate(requests):
    mutated_requests = []
    for request in requests:
        request = list(request)
        # We only mutate `scale_factor * len(request)` times, which by default
        # is 10% of the request string
        for i in xrange(int(mutate_scale_factor * len(request))):
            request[random.randint(0,len(request)-1)] = ' '
        request = "".join(request)
        mutated_requests.append(request)
    return mutated_requests

# Replaces the method with another method (for example, PAUSE to PLAY)
def method_mutate(requests):
    mutated_requests = []
    for request in requests:
        for method in methods:
            if method in request:
                new_method = methods[random.randint(0,len(methods)-1)]
                request = request.replace(method, new_method)
        mutated_requests.append(request)
    return mutated_requests

# Simply adds a space to he beginning of requests, another known exploit in a
# past version of VLC
def offset_mutate(requests):
    mutated_requests = []
    for request in requests:
        request = ' ' + request
        mutated_requests.append(request)
    return mutated_requests

if __name__ == '__main__':
    # ####Set up script flags and options
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

    # The only required command line parameter is the path to the streaming file
    # on the target
    parser.add_option('-f', '--file', dest='file',
            help='Path to stream file on host')

    # Get options
    options, args = parser.parse_args()

    # Set up logging
    clear_log()
    logging.basicConfig(filename=log_file, level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Quit if there is no path on target machine
    if options.file is None:
        logger.error('ERROR: Remote stream file not specified, quitting')
        sys.exit(1)
    # Display current script settings
    print 'Script running with these options:'
    print options

    # We'll set up an array such that each fuzzing method is run with no
    # mutation random mutation, method switching, and offset addition
    mutators = [None, random_mutate, method_mutate, offset_mutate]

    for mutate_func in mutators:
        logger.info('Doing randomized fuzzing with mutator:%s' % mutate_func)
        do_randomized_fuzz(options, mutate_func)
    for mutate_func in mutators:
        logger.info('Doing grammar fuzzing with mutator:%s' % mutate_func)
        do_grammar_fuzz(options, mutate_func, 0)

    # ####And we're done!
    print 'Done! Check out the log file'
