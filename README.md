# VLC Fuzz
This is a simple RTSP protocol fuzzer for the VLC media player, completed as my
final project for CS 460. 

##Usage
Output of `python vlcfuzz.py -h` is as follows:

	Usage: vlcfuzz.py [options]
 		Options:  
  		-h, --help                    show this help message and exit
      
  		-t TARGET, --target=TARGET    IP of target machine
                        
  		-p PORT, --port=PORT          Streaming port on target machine
  
  		--min=MIN                     Minimum bytes of data
  
  		--max=MAX                     Maximum bytes of data
  
  		-s STEP, --step=STEP          Step size between min and max
  
 		 -f FILE, --file=FILE        Path to stream file on hostile
 		 
Of all these options, only the file is required. Example usage:

`python vlcfuzz.py -t 192.168.3.100 -p 8554 --min 30 --max 400 -s 20 -f streams/dogsex`

`python vlcfuzz.py -f streams/backdoor_sluts_9`

`python vlcfuzz.py -p 552 --min 10`

If you want to use the grammar fuzzing feature, use `-g` or `--grammar`. **Be warned**, this attempt almost always succeeds in screwing up VLC, so the script might hang. Watch the logs to see if this happens when running with the grammar flag set.

##Testing
I used an Ubuntu machine with the latest version of VLC. I set up an RTSP stream via the stream dialogue on many ports (default is 8554) and paths, then ran the script. With the grammar flag set, the stream always crashes.

##Methodology
My approach to fuzzing was nothing too fancy. First vlcfuzz tries junk requests, which VLC safely rejects, for the most part. Then vlcfuzz uses RTSP corner cases to generate valid requests, which succeeded in crashing VLC many times. Then vlcfuzz interfaces with the [Blab](https://code.google.com/p/ouspg/wiki/Blab) tool to create valid requests from the EBNF grammar for RTSP requests given in the [RTSP RFC](http://www.ietf.org/rfc/rfc2326.txt). These, sent in the right order, were the best at screwing VLC up. After sending valid requests, this process is repeated but with requests mutated according to historically effective methods (ie, methods that have tripped up VLC in the past). This includes random spacing and switching of method headers. However, VLC was surprisingly good at rejecting bad sequences/requests (with a  405 return code). Most sequences of fuzzer output result in either a reject or accept (OK, code 200). Every so often a sequence in the right order would cause the stream to stop, skip, record, or even crash VLC

##Documentation
Some very pretty documentation of the code, in literate programming style, is available under the `docs` directory. Please open the files in a browser after a `git pull` for the full effect.
##Results
The results were sadly not exciting. I didn't find any glaring security holes, but managed to crash VLC many times. These crashes, if my inspection of the VLC logs are correct, are *not* due to overloading the server but due to VLC's inability to handle some sequences of valid/invalid requests. 
##Further work
If I had more time, I would take a look at how the [Peach fuzzer](http://peachfuzzer.com/) uses grammars to create 100% valid inputs, then replicate that