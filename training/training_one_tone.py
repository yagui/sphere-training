# -*- coding: utf-8 -*-

######################################################
#Training 4:
"""
    
    This training creates a 1 sec tone , has an 2 second interval where the subject can
    generate movement or not, and a reward in case there has been detected continous movement. Then follows a 5 second delay
    between this and the next trial.<>
    
"""
######################################################><
import os, sys
lib_path = os.path.abspath('../modules/')
sys.path.append(lib_path)
import time
import timeit
import logging

class gVariables():
    trainingName = "training_one_tone"
    #relevant Training variables
    eventTime1_sound = 1.0 #in seconds. Instant of time when the soundGen ends.
    eventTime2_movement = 3.0 #in seconds. Instant of time when movement ceases to be considered for reward
    eventTime3_trialEnd = 10.0 #in seconds. Instant of time when the trial ends.
    minIdleIntertrialTime = 1.0 #no-movement time in seconds before the start of next trial. If not reached this time with no movement, trial doesn't start
    
    interTrialRandom1Time = 4.0 #intertrial time is random between this value and the random2 value
    interTrialRandom2Time = 7.0 #intertrial time is random between previous value and this value.
    
    maxMovementThreshold = 200
    maxMovementTime = 11 #max amount of movement time (10 means 1000 ms) to give reward. SHould be less than the opportunity duration
    movementTime = 5 # time for a continuous time that should be reached to give reward.
    #ex.: movementTime = 5 means that there should be movement detected over 500 ms at least
    
    soundGenDuration = 1.0
    soundGenFrequency1 = 1000.0 #in Hz
    soundGenFrequency2 = 2000.0 #in Hz
    
    trialCount = 0 #total number of trials
    successTrialCount=0 #total number of succesful trials
    successRate = 0 #success rate = (success trials / total trial count) %
    dropReleased = 0 #0: no drop of water released this trial, 1: drop of water released
    trialExecuting = False #if true, the trial is online and working. Else, it has been stopped or never started
    
    countMovement = 0 #if it reaches 10, there has been detected a sustained movement for 1000 ms => give reward
    countIdleTime = 0 #if it reaches 10, there has NOT been detected a sustained movement for 1000 ms => reset counters
    
    #video Detection:
    videoDet=0 # video Detection object. initialized in the main.
    
    start_time = timeit.default_timer() #time when training with tone started.
    current_trial_start_time = timeit.default_timer() #current trial in execution, absolute time it started
    current_trial_time = timeit.default_timer() #second of the current trial (between 0 and the maximum length of a trial)
    current_trial_paused_time = 0 #to handle pause and resume correctly..
    
    current_trial_number = 0 #0: tone, 1: movement detection, 2: inter-trial, 3: instant before changing to 0

            
    def recalculateTimeIntervals(self):
        print "recalculating time intervals."
        #Should recalculate timeThreshold_0x according to total Time DUration.
        #This should be executed by the program only once, at the beginning of the run.
    
def printInstructions():
    print '\nOptions:'
    print 'o: Open Valve'
    print 'c: Close Valve'
    print 'd: Water Drop'
    print '1: %d Hz tone' % gVariables.soundGenFrequency1
    print '2: %d Hz tone' % gVariables.soundGenFrequency2
    print 't/T: increase/decrease threshold (10 - %d)' % gVariables.maxMovementThreshold
    print 'e/E: increase/decrease Movement Time needed for reward (100 ms - %d ms)' % (gVariables.maxMovementTime * 100)
    print 'k: start or stop tone training'
    print 'p: pause or resume tone training'
    print 'l/L: recalibrate video input with/without noise filtering.'
    print 'q or ESC: quit\n'

def initDisplay():
    import trainingDisplay #display for showing different variables of interest
    gVariables.display = trainingDisplay.trainingDisplay()
    gVariables.display.addImportantInfo(("Trials", 0))
    gVariables.display.addImportantInfo(("Succesful Trials", 0))
    gVariables.display.addImportantInfo(("Time", 0))
    gVariables.display.addSecondaryInfo(("% s/t",0.0))
    gVariables.display.addSecondaryInfo(("Trial Time","0 - 10"))
    
    gVariables.display.renderAgain()

def updateDisplayInfo():
    if (gVariables.trialExecuting == True):
                    now = timeit.default_timer()
                    b = getFormattedTime(int(now - gVariables.start_time) )
                    gVariables.display.updateInfo("Time", b )
    gVariables.display.updateInfo("Trials", gVariables.trialCount)
    gVariables.display.updateInfo("Succesful Trials", gVariables.successTrialCount)
    if (gVariables.trialCount > 0):
                    temp =  (1.0*gVariables.successTrialCount/ gVariables.trialCount)
                    tempH = temp*100.0
                    tempString = str(tempH)
                    if (len(tempString) > 3):
                        tempS = str(tempH)[:4]
                    else:
                        tempS = str(tempH)[:3]
                    gVariables.successRate = tempS
                    gVariables.display.updateInfo("% s/t", gVariables.successRate)
                    a = str(gVariables.current_trial_time)[:4] + " - " + str(gVariables.eventTime3_trialEnd)
                    gVariables.display.updateInfo("Trial Time", a)
    gVariables.display.renderAgain()

def loopFunction():
    print gVariables.trainingName
    import sphereVideoDetection
    gVariables.videoDet = sphereVideoDetection.sphereVideoDetection(VIDEOSOURCE, CAM_WIDTH, CAM_HEIGHT)
    #Display initialization.
    initDisplay()
    try:
        while(True):
                trialLoop() #
                time.sleep(0.05)
                #####################
                updateDisplayInfo()
                #gVariables.logger.debug('Movement Vector: %s',gVariables.movementVector)
                #####################
                if (gVariables.trialExecuting == True):
                    if (gVariables.videoDet.getMovementStatus() == True and 
                        gVariables.videoDet.getMovementTime() >= (gVariables.movementTime / 10.0) ):
                        giveReward()
                    #print "Continuous total time: %r"%gVariables.videoDet.getMovementTime()
    finally:
        return


def trialLoop():
            #This function controls all events that defines a trial: Tone at a given time, reward opportunity, etc.
            
            if (gVariables.trialExecuting == True):
                #Update Trial Time. Important since this is where events happen at certain moments in this line.
                gVariables.current_trial_start_time += gVariables.current_trial_paused_time
                gVariables.start_time += gVariables.current_trial_paused_time #we consider that training time has not passed in the pause state.
                gVariables.current_trial_paused_time = 0
                gVariables.current_trial_time = (timeit.default_timer() - gVariables.current_trial_start_time)
                
                if (gVariables.current_trial_number == 3 and 
                    gVariables.videoDet.getIdleTime() > gVariables.minIdleIntertrialTime and
                    gVariables.videoDet.getMovementStatus() == False):
                    gVariables.logger.info('Starting trial:%d' % gVariables.trialCount)
                    gVariables.trialCount+=1
                    gVariables.dropReleased = 0
                    gVariables.current_trial_start_time = timeit.default_timer()
                    gVariables.logger.info('tone 1: 1 kHz')
                    gVariables.s1.play()
                    gVariables.current_trial_number = 0
                    gVariables.current_trial_paused_time = 0
                    
                    #add random factor to the intertrial time in the next one:
                    from random import randint
                    i = randint(0,10)
                    scaleF = (gVariables.interTrialRandom2Time - gVariables.interTrialRandom1Time) / 10
                    gVariables.eventTime3_trialEnd = gVariables.eventTime2_movement + gVariables.interTrialRandom1Time + (i * scaleF)
                    
                if ( int(gVariables.current_trial_time) >= gVariables.eventTime1_sound and 
                     int(gVariables.current_trial_time) <= gVariables.eventTime2_movement 
                     and gVariables.current_trial_number == 0):
                    gVariables.logger.info('Start trial movement detection')
                    gVariables.videoDet.resetMovementTime()
                    gVariables.current_trial_number = 1
                elif (int(gVariables.current_trial_time) >= gVariables.eventTime2_movement and 
                      gVariables.current_trial_number == 1):
                    gVariables.logger.info('End trial movement detection')
                    gVariables.logger.info('Start inter-trial delay')
                    gVariables.current_trial_number = 2
                elif (int(gVariables.current_trial_time) >= gVariables.eventTime3_trialEnd and
                      gVariables.current_trial_number == 2):
                    gVariables.logger.info('End trial:%d' % gVariables.trialCount)
                    if(gVariables.dropReleased==1):
                        gVariables.logger.info('Trial succesful')
                    else:
                        gVariables.logger.info('Trial not succesful')
                    gVariables.logger.info('Success rate:%r' % (gVariables.successRate))
                    gVariables.current_trial_number = 3


def restartTraining():
        #print "Restarting."
        try:
            import timeit
            gVariables.start_time = timeit.default_timer()
            gVariables.current_trial_start_time = timeit.default_timer()
        except:
            pass
        gVariables.current_trial_number = 3
        gVariables.trialCount = 0
        gVariables.successTrialCount=0
        gVariables.trialExecuting = True
        gVariables.logger.info('Variables set. Starting %s' % gVariables.trainingName)
    
def stopTraining():
        gVariables.trialExecuting = False
        gVariables.logger.info('%s stopped.' % gVariables.trainingName)

def pauseTraining():
    gVariables.trialExecuting = False
    gVariables.current_trial_paused_time = timeit.default_timer()
    gVariables.logger.info('%s paused.' % gVariables.trainingName)

def resumeTraining():
    gVariables.trialExecuting = True
    gVariables.current_trial_paused_time = (timeit.default_timer() - gVariables.current_trial_paused_time)
    print gVariables.current_trial_paused_time
    gVariables.logger.info('%s resumed.' % gVariables.trainingName)

def giveReward():
    if (gVariables.dropReleased == 0):
        if (gVariables.current_trial_number == 1):
            #print "Release drop of water."
            gVariables.valve1.drop()
            gVariables.logger.debug("Release drop of water.")
            gVariables.successTrialCount+=1
            gVariables.dropReleased = 1

def getFormattedTime(a):
    try:
        hours = int (int(a) / 3600)  #hours
        minutes = int((int(a) - hours*3600) / 60) #minutes
        seconds = int(int(a) - hours*3600 - minutes*60 )
        if hours >0:
            hours = str(hours) + " h   "
            minutes = str(minutes) + " m   "
        else:
            hours = ""
            if (int(minutes) > 0):
                
                minutes = str(minutes) + " m   "
            else:
                minutes = ''  
        
        seconds  = str(int(seconds) ) + " s   " 
        return str(hours)+ str(minutes) + str(seconds)
    except:
        return str(a) + ' s   '

def trainingInit():
    #logging
    formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    dateformat = '%Y/%m/%d %I:%M:%S %p'
    import logging
    logging.basicConfig(filename='logs/%s_%s.log' % (gVariables.trainingName,time.strftime("%Y-%m-%d")), filemode='a',
    level=logging.DEBUG, format=formatter, datefmt = dateformat)
    gVariables.logger = logging.getLogger('main')
    gVariables.logger.info('===============================================')
    gVariables.logger.info('Start %s' % gVariables.trainingName)
    #valve:
    import valve
    gVariables.valve1 = valve.Valve()
    #soundGen
    import soundGen
    gVariables.s1 = soundGen.soundGen(gVariables.soundGenFrequency1, gVariables.soundGenDuration)
    gVariables.s2 = soundGen.soundGen(gVariables.soundGenFrequency2, gVariables.soundGenDuration)
    gVariables.trialExecuting = False #boolean, if a 8 second with tone trial is wanted, this shoulb de set to 1
    # Create thread for executing detection tasks without interrupting user input.
    import threading
    fred1 = threading.Thread(target=loopFunction)
    fred1.start()
    time.sleep(1.3) #to print Instructions after calibration printings.
    printInstructions()

if __name__ == '__main__':
    ######
    #Input
    ######
    import termios, fcntl, sys, os
    fd = sys.stdin.fileno()
    try:
        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
    
        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
    except:
        print "Error capturing input."
    ####################
    #Video configuration
    ####################
    try:
        from configvideo import *
    except ImportError:
        print "File configvideo.py not found."
    except:
        print "Error importing configvideo" 
    ###############
    trainingInit()
    ###############
    try:
        while(True):
            try:
                key = sys.stdin.read(1)#cv2.waitKey(100) #in miliseconds
                if (key == 'o'): #escape pressed
                    gVariables.logger.info('valve open')
                    gVariables.valve1.open()
                elif (key == 'c'):
                    gVariables.logger.info('valve close')
                    gVariables.valve1.close()
                elif (key == 'd'):
                    gVariables.logger.info('valve drop')
                    gVariables.valve1.drop()
                elif (key == '1'):
                    gVariables.logger.info('tone 1: %d Hz' % gVariables.soundGenFrequency1)
                    gVariables.s1.play()
                elif (key == '2'):
                    gVariables.logger.info('tone 2: %d Hz'% gVariables.soundGenFrequency2)
                    gVariables.s2.play()
                elif (key == 't'):
                    gVariables.videoDet.setMovementThreshold(gVariables.videoDet.getMovementThreshold() + 10)
                    if gVariables.videoDet.getMovementThreshold() > gVariables.maxMovementThreshold:
                        gVariables.videoDet.setMovementThreshold(gVariables.maxMovementThreshold)
                    print "Movement Threshold changed to : " + str(gVariables.videoDet.getMovementThreshold())
                    printInstructions()
                elif (key == 'T'):
                    gVariables.videoDet.setMovementThreshold(gVariables.videoDet.getMovementThreshold() - 10)
                    if gVariables.videoDet.getMovementThreshold() < 10:
                        gVariables.videoDet.setMovementThreshold(10)
                    print "Movement Threshold changed to : " + str(gVariables.videoDet.getMovementThreshold())
                    printInstructions()
                elif (key == 'e'):
                    gVariables.movementTime += 1
                    if gVariables.movementTime > gVariables.maxMovementTime:
                        gVariables.movementTime = gVariables.maxMovementTime
                    print "Movement Time changed to : " + str(gVariables.movementTime * 100) + " ms"
                    printInstructions()
                elif (key == 'E'):
                    gVariables.movementTime -= 1
                    if gVariables.movementTime < 1:
                        gVariables.movementTime = 1
                    print "Movement Time changed to : " + str(gVariables.movementTime * 100) + " ms"
                    printInstructions()
                elif (key == 'l'):
                    gVariables.videoDet.calibrate()
                    gVariables.videoDet.setNoiseFiltering(True)
                    print "Calibrated. Noise Filtering is ON."
                elif (key == 'L'):
                    gVariables.videoDet.calibrate()
                    gVariables.videoDet.setNoiseFiltering(False)
                    print "Calibrated. Noise Filtering is OFF."
                elif (key == 'k'):
                    if gVariables.trialExecuting == False:
                        restartTraining()
                        print "Tone Training started."
                        print "  %d seconds: tone" %gVariables.soundGenDuration
                        print "  %d seconds: detection of movement" % (gVariables.eventTime2_movement -
                                                                       gVariables.eventTime1_sound)
                        print "  (%r - %r) seconds: inter trial delay time" % (gVariables.interTrialRandom1Time , 
                                                                               gVariables.interTrialRandom2Time)
                    else:
                        stopTraining()
                        print "Tone Training stopped."
                        
                elif (key == 'p'):
                    if gVariables.trialExecuting == False:
                        resumeTraining()
                        print "Resuming Tone Training."
                    else:
                        pauseTraining()
                        print "Tone Training paused."
                elif (key=='\x1b' or key=='q'):
                    print "Exiting."
                    gVariables.logger.info('Exit signal key = %s',key)
                    import signal
                    os.kill(os.getpid(), signal.SIGINT)
                    sys.exit()
                else :
                    print "Key not supported: %r" %key
            except IOError: pass
            time.sleep(0.08)
    except:
        print "Closing %s." % gVariables.trainingName
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
        gVariables.logger.info('End %s'% gVariables.trainingName)
        import os
        os._exit(0)