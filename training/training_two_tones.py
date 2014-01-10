# -*- coding: utf-8 -*-

######################################################
#Training two tones:
"""
    This training creates two tone of different frequency.
    Each tone has one second of duration. After the tone, there is a two second
    interval where the subject must move (first tone) or stand still (second
    tone).
    If the subject succed in the task, gets a reward.
    There 50 % propabilty of ocurrance for each tone. If one tone appears three
    time in a row, the other tone is fixed in the next trial. 
    The inter trial delay is random between 3 to 6 seconds.
 
    
"""
######################################################><
import os, sys
import modulespath
import time
import timeit
import logging

class gVariables():
    import config_training_two_tones as cfgtwotones
    trainingName = cfgtwotones.trainingName
    #relevant Training variables
    eventTime1_sound = cfgtwotones.eventTime1_sound #in seconds. Instant of time when the soundGen ends.
    eventTime2_movement = cfgtwotones.eventTime2_movement #in seconds. Instant of time when movement ceases to be considered for reward
    eventTime3_trialEnd = cfgtwotones.eventTime3_trialEnd #in seconds. Instant of time when the trial ends.
    minIdleIntertrialTime = cfgtwotones.minIdleIntertrialTime #no-movement time in seconds before the start of next trial. If not reached this time with no movement, trial doesn't start
    
    interTrialRandom1Time = cfgtwotones.interTrialRandom1Time #intertrial time is random between this value and the random2 value
    interTrialRandom2Time = cfgtwotones.interTrialRandom2Time #intertrial time is random between previous value and this value.
    
    maxMovementThreshold = cfgtwotones.maxMovementThreshold
    maxMovementTime = cfgtwotones.maxMovementTime #max amount of movement time (10 means 1000 ms) to give reward. SHould be less than the opportunity duration
    maxIdleTime = cfgtwotones.maxIdleTime
    movementTime = cfgtwotones.movementTime # continuous moving time that should be reached to give reward. 0.5 = 500 ms
    #ex.: movementTime = 0.5 means that there should be movement detected over 500 ms at least
    idleTime = cfgtwotones.idleTime # continuous idle time that should be reached to give reward. 10= 1000 ms
    
    soundGenDuration = cfgtwotones.soundGenDuration
    soundGenFrequency1 = cfgtwotones.soundGenFrequency1 #in Hz
    soundGenFrequency2 = cfgtwotones.soundGenFrequency2 #in Hz
    
    trialCount = 0 #total number of trials
    movementTrialCount = 0 #total number of trials which requires the subject to move
    idleTrialCount = 0 #total number of trials which requires the subject to stay idle.
    successTrialCount=0 #total number of succesful trials
    successMovementTrialCount=0 #total number of succesful trials regarding movement state
    successIdleTrialCount=0 #total number of succesful trials regarding idle state
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
    
    current_trial_stage = 0 #0: tone, 1: movement detection, 2: inter-trial, 3: instant before changing to 0

    toneOneProbability = cfgtwotones.toneOneProbability
    history_trial = [1, 2, 1, 2, 1, 2]
    current_trial_type = 0  # 1: for tone one, reward after movement 2: for tone two, reward after standing still
    current_trial_type_str = "" #same as type but with string format.
    
    
def printInstructions():
    print '\nOptions:'
    print 'o: Open Valve'
    print 'c: Close Valve'
    print 'd: Water Drop'
    print 'r: Give Reward manually'
    print '1: %d Hz tone' % gVariables.soundGenFrequency1
    print '2: %d Hz tone' % gVariables.soundGenFrequency2
    print 't/T: increase/decrease threshold (10 - %d)' % gVariables.maxMovementThreshold
    print 'e/E: increase/decrease Movement Time needed for reward (100 ms - %d ms)' % (gVariables.maxMovementTime * 1000)
    print 'i/I: increase/decrease Idle Time needed for reward (100 ms - %d ms)' % (gVariables.maxIdleTime * 1000)
    print 'k: start or stop tone training'
    print 'p: pause or resume tone training'
    print 'l/L: recalibrate video input with/without noise filtering.'
    print 'b/B: increase/decrease one tone probability.'
    print 'q or ESC: quit\n'

def initDisplay():
    import trainingDisplay #display for showing different variables of interest
    gVariables.display = trainingDisplay.trainingDisplay()
    gVariables.display.addImportantInfo(("Trials", 0))
    gVariables.display.addImportantInfo(("Successful Trials", 0))
    gVariables.display.addImportantInfo(("Successful Trials mvnt", 0))
    gVariables.display.addImportantInfo(("Successful Trials idle", 0))
    gVariables.display.addImportantInfo(("Time", 0))
    gVariables.display.addSecondaryInfo(("% s/t",0.0))
    gVariables.display.addSecondaryInfo(("Trial Time","0 - 10"))
    gVariables.display.addSecondaryInfo(("Trial status",""))
    
    gVariables.display.renderAgain()

def updateDisplayInfo():
    if (gVariables.trialExecuting == True):
                    now = timeit.default_timer()
                    b = getFormattedTime(int(now - gVariables.start_time ) )
                    gVariables.display.updateInfo("Time", b )
                    if (gVariables.current_trial_type == 1):
                        sttrial = "move"
                    elif (gVariables.current_trial_type == 2):
                        sttrial = "still"
                    else:
                        sttrial = ""
                    gVariables.current_trial_type_str = sttrial
                    if (gVariables.current_trial_time < gVariables.eventTime2_movement):
                        gVariables.display.updateInfo("Trial status",sttrial+" - "+"running")
                    else:
                        if gVariables.dropReleased == 1:
                             gVariables.display.updateInfo("Trial status",sttrial+" - "+"SUCCESS")
                        else:
                            gVariables.display.updateInfo("Trial status",sttrial+" - "+"FAIL")
    gVariables.display.updateInfo("Trials", gVariables.trialCount)
    gVariables.display.updateInfo("Successful Trials", gVariables.successTrialCount)
    stmvnt = str(gVariables.successMovementTrialCount) + " / " + str(gVariables.movementTrialCount )
    stidle = str(gVariables.successIdleTrialCount) + " / " + str(gVariables.idleTrialCount )
    gVariables.display.updateInfo("Successful Trials mvnt", stmvnt)
    gVariables.display.updateInfo("Successful Trials idle", stidle)
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
    gVariables.videoDet.setMovementTimeWindow(gVariables.movementTime ) #seconds that should be moving.
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
                if (gVariables.trialExecuting == True and gVariables.current_trial_stage == 1):
                    #print gVariables.videoDet.getTrackingStatus()
                    if (gVariables.current_trial_type == 1):
                      if (gVariables.videoDet.getMovementStatus() == True and 
                        (  ( gVariables.videoDet.getMovementTime() >= (gVariables.movementTime) )
                           ) 
                          ):
                        giveReward()
                        #print "Continuous total time: %r"%gVariables.videoDet.getMovementTime()
                    elif (gVariables.current_trial_type == 2):
                      if (gVariables.videoDet.getMovementStatus() == False and 
                        gVariables.videoDet.getIdleTime() >= (gVariables.idleTime ) ):#
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
                if ((gVariables.current_trial_stage == 3 and 
                    gVariables.videoDet.getIdleTime() >= gVariables.minIdleIntertrialTime and
                    gVariables.videoDet.getMovementStatus() == False) or (gVariables.trialCount == 0) ):
                    gVariables.logger.info('Starting trial:%d' % gVariables.trialCount)
                    gVariables.trialCount+=1
                    gVariables.dropReleased = 0
                    gVariables.current_trial_start_time = timeit.default_timer()

                    gVariables.logger.debug(gVariables.history_trial)
                    gVariables.logger.debug(gVariables.toneOneProbability)
                    gVariables.logger.debug(gVariables.current_trial_type)
                    if (gVariables.toneOneProbability < 0.75) and (gVariables.toneOneProbability > 0.25) and (gVariables.history_trial[-1] == gVariables.history_trial[-2]) and (gVariables.history_trial[-2] == gVariables.history_trial[-3]) :
                        # 3 equal trial have past. forced changing trial
                        gVariables.logger.info('fixed tone')
                        if (gVariables.history_trial[-1]) == 2:
                            gVariables.current_trial_type = 1
                        else :
                            gVariables.current_trial_type = 2
                    else :
                        from random import random
                        if (random() < gVariables.toneOneProbability) :
                            gVariables.current_trial_type = 1
                        else :
                            gVariables.current_trial_type = 2
                            
                    if (gVariables.current_trial_type == 1) :
                            gVariables.logger.info('tone 1: 1 kHz')
                            gVariables.s1.play()
                            gVariables.movementTrialCount += 1
                            #a new "time window" should be set for 
                            # some movement analysis methods to work.
                            gVariables.videoDet.setMovementTimeWindow(gVariables.movementTime)
                    else :
                            gVariables.logger.info('tone 2: 8 kHz')
                            gVariables.s2.play()
                            gVariables.idleTrialCount += 1
                            #a new "time window" should be set for 
                            # some movement analysis methods to work.
                            gVariables.videoDet.setMovementTimeWindow(gVariables.idleTime )

                    gVariables.history_trial[0:-1] = gVariables.history_trial[1:]
                    gVariables.history_trial[-1] = gVariables.current_trial_type

                    gVariables.current_trial_stage = 0
                    gVariables.current_trial_paused_time = 0
                    
                    #add random factor to the intertrial time in the next one:
                    from random import randint
                    i = randint(0,10)
                    scaleF = (gVariables.interTrialRandom2Time - gVariables.interTrialRandom1Time) / 10
                    gVariables.eventTime3_trialEnd = gVariables.eventTime2_movement + gVariables.interTrialRandom1Time + (i * scaleF)
                    
                if ( int(gVariables.current_trial_time) >= gVariables.eventTime1_sound and 
                     int(gVariables.current_trial_time) <= gVariables.eventTime2_movement 
                     and gVariables.current_trial_stage == 0):
                    gVariables.logger.info('Start trial movement detection')
                    if (gVariables.current_trial_type == 1) :
                        gVariables.videoDet.resetMovementTime()
                    else:
                        gVariables.videoDet.resetIdleTime()
                    gVariables.current_trial_stage = 1
                elif (int(gVariables.current_trial_time) >= gVariables.eventTime2_movement and 
                      gVariables.current_trial_stage == 1):
                    gVariables.logger.info('End trial movement detection')
                    gVariables.logger.info('Start inter-trial delay')
                    gVariables.current_trial_stage = 2
                elif (int(gVariables.current_trial_time) >= gVariables.eventTime3_trialEnd and
                      gVariables.current_trial_stage == 2):
                    gVariables.logger.info('End trial:%d' % gVariables.trialCount)
                    gVariables.logger.info('Trial type: '+str(gVariables.current_trial_type_str))
                    ##
                    gVariables.videoDet.setMovementTimeWindow(gVariables.minIdleIntertrialTime)
                    if(gVariables.dropReleased==1):
                        gVariables.logger.info('Trial successful')
                    else:
                        gVariables.logger.info('Trial not successful')
                    gVariables.logger.info('Success rate:%r' % (gVariables.successRate))
                    gVariables.current_trial_stage = 3

def restartTraining():
        #print "Restarting."
        try:
            import timeit
            gVariables.start_time = timeit.default_timer()
            gVariables.current_trial_start_time = timeit.default_timer()
        except:
            pass
        gVariables.current_trial_stage = 3
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
    if (gVariables.dropReleased == 0 and gVariables.trialExecuting == True):
            #print "Release drop of water."
            gVariables.valve1.drop()
            gVariables.logger.debug("Drop of water released.")
            gVariables.successTrialCount+=1
            gVariables.dropReleased = 1
            if (gVariables.current_trial_type == 1) :
                            gVariables.successMovementTrialCount += 1
            else:
                gVariables.successIdleTrialCount += 1

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
    time.sleep(2.3) #to print Instructions after calibration printings.
    printInstructions()


def exitTraining(key):
    #Finalize this training and exits.
    #Should get a comment from user before finishing, for documentation purposes.
    print "Asking user for comments about this training:"
    import pygame
    pygame.event.set_grab(True)
    st = gVariables.display.askUserInput("Write comment on this training:")
    print "Exiting."
    gVariables.logger.info('Exit signal key = %s', key)
    gVariables.logger.info('Comment about this training: %s', st)
    import signal
    os.kill(os.getpid(), signal.SIGINT)
    sys.exit()

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
                elif (key == 'r'):
                    gVariables.logger.info('Reward given manually.')
                    giveReward();
                elif (key == 'R'):
                    gVariables.logger.info('Reward given manually.')
                    giveReward();
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
                elif (key == 'b'):
                    gVariables.toneOneProbability += 0.05
                    if gVariables.toneOneProbability > 1.0 :
			gVariables.toneOneProbability = 1.0
                    print "Tone One Probabilty changed to : " + str(gVariables.toneOneProbability * 100) + " %"
                    printInstructions()
                elif (key == 'B'):
                    gVariables.toneOneProbability -= 0.05
                    if gVariables.toneOneProbability < 0.0 :
			gVariables.toneOneProbability = 0.0
                    print "Tone One Probabilty changed to : " + str(gVariables.toneOneProbability * 100) + " %"
                    printInstructions()
                elif (key == 'e'):
                    gVariables.movementTime += 0.1
                    if gVariables.movementTime > gVariables.maxMovementTime:
                        gVariables.movementTime = gVariables.maxMovementTime
                    gVariables.videoDet.setMovementTimeWindow(gVariables.movementTime )
                    print "Movement Time changed to : " + str(gVariables.movementTime * 1000) + " ms"
                    printInstructions()
                elif (key == 'E'):
                    gVariables.movementTime -= 0.1
                    if gVariables.movementTime < 0.1:
                        gVariables.movementTime = 0.1
                    gVariables.videoDet.setMovementTimeWindow(gVariables.movementTime )
                    print "Movement Time changed to : " + str(gVariables.movementTime * 1000) + " ms"
                    printInstructions()
                elif (key == 'i'):
                    gVariables.idleTime += 0.1
                    if gVariables.idleTime > gVariables.maxIdleTime:
                        gVariables.idleTime = gVariables.maxIdleTime
                    print "Idle Time changed to : " + str(gVariables.idleTime * 1000) + " ms"
                    printInstructions()
                elif (key == 'I'):
                    gVariables.idleTime -= 0.1
                    if gVariables.idleTime < 0.1:
                        gVariables.idleTime = 0.1
                    print "Idle Time changed to : " + str(gVariables.idleTime * 1000) + " ms"
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
                    exitTraining(key)
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
