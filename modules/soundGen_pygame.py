# -*- coding: utf-8 -*-
import pygame
#from pygame.locals import *
import math
import numpy
import time
import logging
import track_bola_utils
import sys

logger = logging.getLogger('soundGen')

PROCESS_SLEEP_TIME = 0.035 #in seconds


class multiproc_soundGen():
    toExit = 0;
    soundGenJobList = 0;
    
    
    def checkJobList(self):
        if (self.soundGenJobList.qsize() > 0 or self.soundGenJobList.empty() == False ):
                try:
                        tempvar = self.soundGenJobList.get()
                        self.soundGenJobList.task_done()
                except:
                        return;
                #print str("checkJobList: queue: " + str(tempvar) )
                index = tempvar[0]
                try:
                    argument = tempvar[1]
                except:
                    argument = ""
                    pass
                
                #print "checkJobList: Got a Message:", index
                #print "checkJobList: Message's argument:", argument
#                 try:
#                     a = str(argument)
#                     print "Argument: %s" %a
#                 except:
#                     print "Message's argument cannot be parsed to str."
#                     pass
                if (index == "tone"):
                    #print "Command secondaryInfo received."
                    logger.debug( str(tempvar[1]) )
                    logger.debug( str(tempvar[2]) )
                    self.tone(tempvar[1], tempvar[2])
                    logger.debug('tone..')
                elif (index == "play"):
                    #print "Command exitDisplay received."
                    
                    self.play()
                elif (index == "exit"):
                    #print "Command exitDisplay received."
                    logger.debug('exiting..')
                    self.exit()
                    return;
                else:
                    print "unknown message: %s" % str(index)
                    


    def __init__(self,jobl, freq=None,duration=None,sample_rate=44100, bits=16):
        self.soundGenJobList = jobl
        logger.info('New instance of soundGen')
        pygame.mixer.pre_init(sample_rate, -bits, 2)
        pygame.init()
        self.sample_rate = sample_rate
        self.bits = bits
        if ((duration == None) or (freq == None)) :
            self.duration = 1.0
            self.freq = 1000.0
        else :
            self.duration = duration
            self.freq = freq
        self.sound = self.tone(self.duration,self.freq)
        logger.debug("soundGen(multiproc) instance initialized.")


    def exit(self):
        print "SoundGen exiting."
        self.toExit = 1;
        try:
            pygame.mixer.quit()
            pygame.quit()
            time.sleep(0.2)
            sys.exit()
        except:
            pass
        pass

    def tone(self, duration=1.0, freq=1000.0) :
        self.duration = duration
        self.freq = freq
        logger.info('Tone freq = %s Hz, duration = %s s, sample_rate = %s, bits = %s',self.freq,self.duration,self.sample_rate,self.bits)

        n_samples = int(round(self.duration*self.sample_rate))
        buf = numpy.zeros((n_samples, 2), dtype = numpy.int16)
        max_sample = 2**(self.bits - 1) - 1
        for s in range(n_samples):
            t = float(s)/self.sample_rate    # time in seconds

            buf[s][0] = int(round(max_sample*math.sin(2*math.pi*self.freq*t))) # left
            buf[s][1] = int(round(max_sample*math.sin(2*math.pi*self.freq*t))) # right

        self.sound = pygame.sndarray.make_sound(buf)
        logger.debug(str(self.sound))
        return self.sound

    #TODO add new waveforms

    def play(self):
        
        logger.info('Tone freq = %s Hz, duration = %s s',self.freq,self.duration)
        if (float(self.duration)  < 0.000003571):
            #print "not played because duration is less than audible."
            logger.debug("Not played tone because duration is less than audible.")
        else:
            self.sound.play()
            #print "playing tone %s" % self.freq
            #print self.sound
            logger.debug("playing")
        pass

    def getFrequency(self):
        return self.freq
    
    def getDuration(self):
        return self.duration


class soundGen():
    
    def launch_multiproc(self, jobl, freq, duration, sample_rate, bits):
        a = multiproc_soundGen(jobl, freq, duration, sample_rate, bits)
        time.sleep(0.5)
        while(a.toExit != 1):
            
            a.checkJobList()
            if (a.toExit == 1):
                #del a
                print "Exiting soundGen class."
                a.toExit = 1;
                logger.debug( "exiting launch_multiproc" )
                #self.exit()
                break;
            pass
            #print "loop. %s %d" % (str(a), a.toExit)
            time.sleep(PROCESS_SLEEP_TIME)
    
    def __init__(self,freq=None,duration=None,sample_rate=44100, bits=16):
        
        self.freq = freq
        self.duration = duration
        
        import multiprocessing
        self.soundGenJobList = multiprocessing.JoinableQueue()
        
        self.soundGenProc = multiprocessing.Process(target=self.launch_multiproc, args=(self.soundGenJobList, freq,duration,sample_rate, bits,) )
        self.soundGenProc.start()
        
        logger.debug('soundGen process started')


    def exit(self):
        self.soundGenJobList.put( ( "exit", "" ) )
        logger.debug("soundGen exit message.")
        time.sleep(0.5)
        self.soundGenProc.terminate()
        del self.soundGenProc
        del self.soundGenJobList
        del self.freq
        del self.duration
        #sys.exit()
        pass

    def tone(self, duration=1.0, freq=1000.0) :
        self.soundGenJobList.put( ( "tone" , duration, freq ) )


    #TODO add new waveforms

    def play(self):
        self.soundGenJobList.put( ( "play", "" ) )

    def getFrequency(self):
        return self.freq
    
    def getDuration(self):
        return self.duration

        #there is needed a delay, after the play command.

if __name__ == '__main__':
    # create a logging format
    dateformat = '%Y/%m/%d %H:%M:%S'
    formatter_str = '%(asctime)s.%(msecs)d - %(name)s - %(levelname)s - %(message)s'
    filename_to_log='logs/sound.log'
    
    
    logging.basicConfig(filename=filename_to_log, filemode='w+',
        level=logging.DEBUG, format=formatter_str,
        datefmt=dateformat)
    
    #===========================================================================
    #the following lines are only to ALSO log to stdout, are not strictly necessary
    #===========================================================================
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    formatter = track_bola_utils.formatterWithMillis(fmt=formatter_str,datefmt=dateformat)
    console.setFormatter(formatter)
    logger.addHandler(console)
    #===========================================================================
    
    
    
    logger.info('Start Sound Test')
    s1 = soundGen()
    duration = 3.0 # in seconds
    freq1 = 1440
    freq2 = 1550

    s1.tone(duration, freq1)
    s1.play()
    time.sleep(duration)

    time.sleep(4)

    s1.tone(duration, freq2)
    s1.play()
    time.sleep(duration)

    time.sleep(4)


    s2 = soundGen(3*freq1,2*duration)
    s2.play()
    time.sleep(2*duration)
    logger.info('End Sound Test')
    s1.exit()
    s2.exit()
    sys.exit()
