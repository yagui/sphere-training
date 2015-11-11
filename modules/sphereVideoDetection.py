# -*- coding: utf-8 -*-
# sphereVideoDetection.py
'''
    Programa que detecta movimiento de un flujo de video (webcam o video) configurado en un archivo de configuración:
    En base al video, establece un vector que corresponde a la dirección del movimiento detectado.
    El movimiento se detecta tomando círculos negros en movimiento, comparando posición actual con su
    posición pasada más probable
'''


import timeit
import pygame
import math
import threading
import time
import os
import signal
import cv2
import sys
import logging
logger = logging.getLogger('sphereVideoDetection')
import track_bola_utils



class sphereVideoDetection():
    NoiseFilteringOffVars = track_bola_utils.dummyClass();
    NoiseFilteringOffVars.MAX_CIRCLE_MOVEMENT = -1;
    NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT = -1;
    NoiseFilteringOffVars.WORKING_MIN_CONTOUR_AREA = -1;
    NoiseFilteringOffVars.WORKING_MAX_CONTOUR_AREA = -1;
    NoiseFilteringOffVars.minRadius = -1;
    
    
    NoiseFilteringOnVars = track_bola_utils.dummyClass();
    NoiseFilteringOnVars.MAX_CIRCLE_MOVEMENT = -1;
    NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT = -1;
    NoiseFilteringOnVars.WORKING_MIN_CONTOUR_AREA = -1;
    NoiseFilteringOnVars.WORKING_MAX_CONTOUR_AREA = -1;
    NoiseFilteringOnVars.minRadius = -1;
    
    usingPygameDisplay = False;
    number_of_moving_vectors = 0;
    number_of_standing_vectors = 0;
    sum_of_areas = 0;
    losing_track_cause = ""
    capturedImageWidth = 0;
    capturedImageHeight = 0;
    capturedImageSize = 0;
    
    MIN_CIRCLE_TOTAL_AREA_TO_CONSIDER_TRACKING = 0 ;
    
    def __init__ (self) :
        import track_bola_utils
        import os
        logger.info("Initializing sphereVideoDetection")
        try:
            import configSphereVideoDetection
        except ImportError:
            print "File configSphereVideoDetection.py not found. Generating a new copy..."
            logger.info("File configSphereVideoDetection.py not found. Generating a new copy...")
            a = os.getcwd() + "/"
            print a
            import shutil
            shutil.copyfile(a + "configSphereVideoDetection.py.example", a + "configSphereVideoDetection.py")
            import configSphereVideoDetection
            print "configSphereVideoDetection.py copied and imported successfully."
            logger.info("configSphereVideoDetection.py copied and imported successfully.")
        except:
            print "Error importing configSphereVideoDetection."
            logger.error("Error importing configSphereVideoDetection.")
            os._exit(1)
        # import configSphereVideoDetection
        

        
        self.winName = configSphereVideoDetection.WINDOW_TITLE
        # declare self variables to use.
        self.mustquit = 0
        self.available = True
        self.vectorInstantaneo = track_bola_utils.vectorSimple()  # instant vector, generally regarded as an internal variable.
        self.vectorAcumulado = track_bola_utils.vectorSimple()  # accumulated vector. Keeps adding instant.x and .y since start of program.
        self.vectorPseudoInstantaneo = track_bola_utils.vectorSimple()  # pseudo instant vector. Contains last non-zero instant value
        self.startCalibration = True  # if True, a calibration will be performed
        
        self.firstCalibration = False  # if True, a first calibration was performed.
        
        
        self.usingPygameDisplay = configSphereVideoDetection.pygameDisplay
        self.CV2THRESHOLD = configSphereVideoDetection.CV2_THRESHOLD  # binary threshold. A black pixel is only considered if its color is greater than 160
        
        # variables for keeping track of continuous movement.
        self.noiseFiltering = configSphereVideoDetection.NOISE_FILTERING_INITIAL_VALUE
        self.internalMovementCounter = 0  # counter, amount of cycles over which integration of movement is made.
        
        self.sleepTime = configSphereVideoDetection.MAIN_SLEEP_TIME  # Main loop sleep time in ms
        self.movement_loopNumberSpan = configSphereVideoDetection.MOVEMENT_LOOPS_INTEGRATED  # amount of main loops that movement is integrated into.
        self.movementThreshold = configSphereVideoDetection.MOVEMENT_THRESHOLD_INITIAL_VALUE  # threshold, below this, we consider it noise.
        
        self.movementMethod = configSphereVideoDetection.MOVEMENT_METHOD_INITIAL_VALUE  # Type of movement analysis method used.
        # Current methods: 0=Accumulate time, 1= movementVector, 2=(WIP) movementVectorBinary
        
        
        self.continuousMovementTime = 0  # amount of seconds that a continous movement was detected last time it moved or currently
        self.continuousIdleTime = 0  # amount of seconds that no movement was detected last time it ceased movement or currently
        self.isMoving = False  # if true, it is currently in movement. False => not moving (not necessarily moving)
        self.isIdle = False  # true: it is idle.
        self.isTrackingTemp = True  # temp, very instantaneous tracking boolean.
        self.isTracking = True  # True: is tracking correctly. False: could not keep up with the circles movement
        self.trackingVector = [True, True, True, True, True, True, True, True, True, True]
        self.areasVector = [0,0,0,0,0,0,0,0,0,0]
        
        self.showTrackingFeedback = True  # circles, dots and lines for the user
        self.showUserFeedback = True  # show or hide video window.
        
        self.movementVector = []  # binary vector, each loop adds 1 if moving, 0 otherwise
        
        
        self.movementVectorLength = configSphereVideoDetection.MOVEMENT_VECTOR_LENGTH
        
        self.movementDelayVector = []
        
        self.movementDelayVectorLength = 20
        
        self.movementHistoryVector = [0, 0, 0, 0, 0, 0]  # saves past movements . Helps track interrupted movements
        self.movementDelayHistoryVector = [0, 0, 0, 0, 0, 0]  # saves past delays. Helps track interrupted delays
        
        self.movementTimeWindow = 0.5  # 0.5 seconds for the method movementVector_Binary
        
        self.VECTOR_COUNT_PERCENTAGE = configSphereVideoDetection.VECTOR_COUNT_PERCENTAGE  # percentage of 1's needed for the mvnt.vector. method to consider it "moving"
        self.VECTOR_COUNT_PERCENTAGE_MOVEMENT = configSphereVideoDetection.VECTOR_COUNT_PERCENTAGE_MOVEMENT  #
        self.VECTOR_COUNT_PERCENTAGE_IDLE = configSphereVideoDetection.VECTOR_COUNT_PERCENTAGE_IDLE 
        
        self.MIN_CIRCLE_TOTAL_AREA_TO_CONSIDER_TRACKING = configSphereVideoDetection.MIN_CIRCLE_TOTAL_AREA_TO_CONSIDER_TRACKING
        
        for i in range (0, self.movementVectorLength):
            self.movementVector.append(0)
        
        for i in range (0, self.movementDelayVectorLength):
            self.movementDelayVector.append(0)
        
        self.last_saved_time_idle = timeit.default_timer()  # will be used to check differences in time (determine idle time)
        self.last_saved_time_movement = timeit.default_timer()  # will be used to check differences in time (determine mvnt time)
        self.last_saved_time_gp = timeit.default_timer()  # general purpose time counter
        
        
    
    def initAll(self):
        if self.usingPygameDisplay:
            #pygame init
            pygame.init()
            self.windowWidth = 450
            self.windowHeight = 350
            self.windowSurface = pygame.display.set_mode((self.windowWidth, self.windowHeight), 0, 32)
            pygame.display.set_caption('sphereVideoDetection variables:')
            self.secondaryFont = pygame.font.SysFont(None, 36)
            self.smallFont = pygame.font.SysFont(None, 20)
            self.smallestFont = pygame.font.SysFont(None, 12)
            text1 = self.secondaryFont.render('_', True, (255,255,255))
            textRect1 = text1.get_rect()
            self.windowSurface.blit(text1, textRect1)
            pygame.display.update()
        import threading
        # Create one non-blocking thread for capturing video Stream
        self.fred1 = threading.Thread(target=self.mainVideoDetection, name="VideoDetection")
        self.fred1.start()
    
    def cv_size(self, img):
        return tuple(img.shape[1::-1])
    
    def getAccumulatedVector(self):
        return [self.vectorAcumulado.x, self.vectorAcumulado.y]
    
    def resetX(self):
        self.vectorInstantaneo.x = 0
        self.vectorPseudoInstantaneo.x = 0
        self.vectorAcumulado.x = 0
        self.movEjeX = 0

    def resetY(self):
        self.vectorInstantaneo.y = 0
        self.vectorPseudoInstantaneo.y = 0
        self.vectorAcumulado.y = 0
        self.movEjeY = 0

    def getAccumX(self):
        return self.vectorAcumulado.x

    def getAccumY(self):
        return self.vectorAcumulado.y
    
    def getInstantX(self):
       #return self.vectorInstantaneo.x
       return self.vectorPseudoInstantaneo.x
    
    def getInstantY(self):
        #return self.vectorInstantaneo.y
        return self.vectorPseudoInstantaneo.y

    def calibrateCircle(self):
        self.startCalibration = True
    
    def exit(self):
        # os._exit(0)
        self.mustquit = 1
        self.available = False
    
    def setNoiseFiltering(self, bool):
        # Set Noise FIltering: False if you DON'T want noise filtering , because you consider that your input video has no noise.
        self.noiseFiltering = bool
        if (bool):
            self.MAX_CIRCLE_MOVEMENT = self.NoiseFilteringOnVars.MAX_CIRCLE_MOVEMENT
            self.MIN_CIRCLE_MOVEMENT = self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT
            self.WORKING_MAX_CONTOUR_AREA = self.NoiseFilteringOnVars.WORKING_MAX_CONTOUR_AREA
            self.WORKING_MIN_CONTOUR_AREA = self.NoiseFilteringOnVars.WORKING_MIN_CONTOUR_AREA
        else:
            self.MAX_CIRCLE_MOVEMENT = self.NoiseFilteringOffVars.MAX_CIRCLE_MOVEMENT
            self.MIN_CIRCLE_MOVEMENT = self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT
            self.WORKING_MAX_CONTOUR_AREA = self.NoiseFilteringOffVars.WORKING_MAX_CONTOUR_AREA
            self.WORKING_MIN_CONTOUR_AREA = self.NoiseFilteringOffVars.WORKING_MIN_CONTOUR_AREA
        print "Noise Filtering now set to: %r" % self.noiseFiltering
    
    def getNoiseFiltering(self):
        return self.noiseFiltering
    
    def getMovementTime(self):
        # return the time in seconds that continuous movement was detected:
        # if it is moving, current time it is moving until now.
        # if it has stopped, amount of time it was moving before stopping.
        return self.continuousMovementTime
    
    def getIdleTime(self):
        # return the time in seconds that no movement was detected:
        # if it is moving, amount of time it was not moving before starting to move.
        # if it is not moving now, amount of time it is idle until now.
        return self.continuousIdleTime
    
    def manageCalibrationVariables(self, flag):
        # this method loads calibration variables from file, if the file exists.
        # else: it will create a file where the calibration will be saved.
        
        if (self.firstCalibration == True):
            # A first calibration was executed. So the user is asking for a re-calibration, which means
            # that the calibration file shouldn' be used.
            if (flag == 0):
                return False
        
        self.firstCalibration = True
        
        if (flag == 0):
            # Flag 0: Check whether calibration file exists or not.
            try:
                import calibrationCamera
                self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT = calibrationCamera.MIN_CIRCLE_MOVEMENT
                self.NoiseFilteringOnVars.MAX_CIRCLE_MOVEMENT = calibrationCamera.MAX_CIRCLE_MOVEMENT
                self.NoiseFilteringOnVars.WORKING_MIN_CONTOUR_AREA = calibrationCamera.WORKING_MIN_CONTOUR_AREA
                self.NoiseFilteringOnVars.WORKING_MAX_CONTOUR_AREA = calibrationCamera.WORKING_MAX_CONTOUR_AREA
                
                self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT = calibrationCamera.NF_MIN_CIRCLE_MOVEMENT
                self.NoiseFilteringOffVars.MAX_CIRCLE_MOVEMENT = calibrationCamera.NF_MAX_CIRCLE_MOVEMENT
                self.NoiseFilteringOffVars.WORKING_MIN_CONTOUR_AREA = calibrationCamera.NF_WORKING_MIN_CONTOUR_AREA
                self.NoiseFilteringOffVars.WORKING_MAX_CONTOUR_AREA = calibrationCamera.NF_WORKING_MAX_CONTOUR_AREA
                self.setNoiseFiltering(self.getNoiseFiltering()) #to apply changes.
                return True  # True, calibration file was there (and i already loaded all vars..
            except:
                # probably: file doesn't exist.
                return False  # False, calibration file was not there. A new one will be created AFTER calib. variables are determined"

        if (flag == 1):
            # flag 1: A new calibration file should be created. It will have the calibrated variables just determined.
            try:
                import os
                os.remove("../modules/calibrationCamera.py")
                os.remove("../modules/calibrationCamera.pyc")
                print "Previous calibrationCamera file exists. File erased."
                logger.info("Previous calibrationCamera file exists. File erased.")
            except:
                print "Error erasing previous calibration file. Probably file does not exist."
                logger.error("Error erasing previous calibration file. Probably file does not exist.")
            
            print "Creating new calibration file"
            with open("../modules/calibrationCamera.py", "w") as text_file:
                    text_file.write("#This file has calibration variables for the camera \n")
                    text_file.write("#if this file exists, these values will be used in execution. Else, a new file \n")
                    text_file.write("#with calibration variables will be created and used. \n")
                    text_file.write("# \n")
                    
                    text_file.write("MAX_CIRCLE_MOVEMENT = %d \n" % int(self.NoiseFilteringOnVars.MAX_CIRCLE_MOVEMENT))
                    text_file.write("MIN_CIRCLE_MOVEMENT = %d \n" % int(self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT))
                    text_file.write("WORKING_MIN_CONTOUR_AREA = %d \n" % int(self.NoiseFilteringOnVars.WORKING_MIN_CONTOUR_AREA))
                    text_file.write("WORKING_MAX_CONTOUR_AREA = %d \n" % int(self.NoiseFilteringOnVars.WORKING_MAX_CONTOUR_AREA))
                    
                    text_file.write("# \n")
                    text_file.write("# Noise Filtering variables \n")
                    
                    text_file.write("NF_MAX_CIRCLE_MOVEMENT = %d \n" % int(self.NoiseFilteringOffVars.MAX_CIRCLE_MOVEMENT))
                    text_file.write("NF_MIN_CIRCLE_MOVEMENT = %d \n" % int(self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT))
                    text_file.write("NF_WORKING_MIN_CONTOUR_AREA = %d \n" % int(self.NoiseFilteringOffVars.WORKING_MIN_CONTOUR_AREA))
                    text_file.write("NF_WORKING_MAX_CONTOUR_AREA = %d \n" % int(self.NoiseFilteringOffVars.WORKING_MAX_CONTOUR_AREA))
                    
                    print self.MAX_CIRCLE_MOVEMENT
                    logger.info(str(self.MAX_CIRCLE_MOVEMENT))
                    print self.MIN_CIRCLE_MOVEMENT
                    logger.info(str(self.MIN_CIRCLE_MOVEMENT))
                    print self.WORKING_MIN_CONTOUR_AREA
                    logger.info(str(self.WORKING_MIN_CONTOUR_AREA))
                    print self.WORKING_MAX_CONTOUR_AREA
                    logger.info(str(self.WORKING_MAX_CONTOUR_AREA))
                    
                    print "calibration file overwritten."
                    logger.info("calibration file overwritten.")
                    
                    return True  # True, file was written OK
            return False  # False, file couldn't be written (or it was written and it's status is unknown)
    
    
    def resetMovementTime(self):
        self.continuousMovementTime = 0.0
        self.last_saved_time_movement = timeit.default_timer()
        for i in range(0, len(self.movementVector)):
            self.movementVector[i] = 0
        
        
    def resetIdleTime(self):
        self.continuousIdleTime = 0.0
        self.last_saved_time_idle = timeit.default_timer()
        for i in range(0, len(self.movementVector)):
            self.movementVector[i] = 1
    
    def setMovementThreshold(self, thres):
        # Movement threshold: how much "movement" between two frames should be considered as "movement"
        # Be careful changing this value, it is extremely sensitive.
        self.movementThreshold = int(thres)
    
    def getMovementThreshold(self):
        return int(self.movementThreshold)
    
    def getMovementStatus(self):
        return self.isMoving  # true if right now it is moving, false otherwise.
    
    def getIdleStatus(self):
        return self.isIdle  # true if right now it is idle, false otherwise.
    
    def setTrackingFeedback(self, trc):
        self.showTrackingFeedback = trc
    
    def setUserFeedback(self, fdb):
        self.showUserFeedback = fdb
        if (fdb == False):
            #import cv2
            #cv2.namedWindow(self.winName, cv2.CV_WINDOW_AUTOSIZE)
            #cv2.destroyWindow(self.winName)
            # currently, it is unstable to destroy window as it will generate errors on the processing of the movement
            # So this function will stop feedback and you can minimize the window manually.
            try:
                cv2.resizeWindow(self.winName, 0, 0);
            except:
                pass
            pass
        else:
            try:
                cv2.resizeWindow(self.winName, self.capturedImageWidth, self.capturedImageHeight);
            except:
                pass
            pass
    
    def getTrackingStatus(self):
        return self.isTracking  # true if it is tracking, false if it lost tracking.
    
    def getMovementTimeWindow(self):
        return self.movementTimeWindow
    
    def setMovementTimeWindow(self, wind):
        # This method sets the time window.
        # Especially useful with the movement analysis method: Method_MovementVectorBinary
        # Seconds that will be detected for movement.
        if (wind > 0.0):
            self.movementTimeWindow = wind;
            logger.debug("videoDetection: Movement time window changed to %f seconds." % self.movementTimeWindow)
    
    def Method_MovementVectorBinary(self):
        
        #=======================================================================
        # # Movement Vector Binary (a variant of the non binary method)
        #=======================================================================
        
        # This method will set the movement time in a preset value, and no more or less, only if that much time
        # is detected. For example:
        # If it was moving for 1 second, and the time window in the training
        # files set this module to detect at least 0.5 s, this method will detect movingTIme to 0.5 s
        # If this method does not detect 0.5 s , it will set movingTime to 0 and idle time to 0
        #=======================================================================
        # # Keep track of the time it takes to process the whole loop
        #=======================================================================
        # work in seconds.
        
        # print "MVB Start."
        self.continuousMovementTime = 0.0
        self.continuousIdleTime = 0.0
        timeDif = (timeit.default_timer() - self.last_saved_time_gp)
        self.last_saved_time_gp = timeit.default_timer()
        # sttemp = "Current Loop time (ms): %d" %  int(timeDif * 1000)
        # sttemp += "            "
        
        # DELAY VECTOR: for keeping track of FPS and delay.
        self.movementDelayVector[0:-1] = self.movementDelayVector[1:]
        self.movementDelayVector[self.movementDelayVectorLength - 1] = int(timeDif * 1000)
        # keeping track of delay and estimated FPS:
        average_delay = 0
        for i in range(0, self.movementDelayVectorLength):
            average_delay += self.movementDelayVector[i]
        
        average_delay /= self.movementDelayVectorLength
        
        # logger.debug ( sttemp + ("Average Loop time (ms): %d" % average_delay) )
        
        self.last_saved_time_movement = timeit.default_timer()
        
        # Time window is the amount of time that it is asked to the subject to perform continuous movement
        # For example, timewindow = 0.5 s , so each loop this method will determine if continuous movement
        # is detected for that amount of time, and will return 0.5 if it was detected or 0 if there is not enough 1's.
        
        #=======================================================================
        # process last loop. Appends a 1 or 0 to the movement vector if the amount was above threshold.
        #=======================================================================
        
        self.movementVector[0:-1] = self.movementVector[1:]
        movementAmount = (abs(self.getInstantX() * self.getInstantX()) + 
                           abs(self.getInstantY() * self.getInstantY()))
        # logger.debug( "Amount of movement: %d" % movementAmount)
        # if it surpasses threshold OR if it lost tracking (so it is moving quite fast..)
        
        if (movementAmount >= self.movementThreshold or self.isTracking == False):
                    self.movementVector[self.movementVectorLength - 1] = 1
                    # print "1 appended   ", movementAmount ,"    Thres: ", self.movementThreshold
        else:
                    self.movementVector[self.movementVectorLength - 1] = 0
                    # print "0 appended   ", movementAmount ,"    Thres: ", self.movementThreshold
        
        self.vectorPseudoInstantaneo.x = self.vectorInstantaneo.x
        self.vectorPseudoInstantaneo.y = self.vectorInstantaneo.y
        self.vectorInstantaneo.x = 0
        self.vectorInstantaneo.y = 0
        
        #=======================================================================
        # # Determines if there are enough 1's in the time window (which was already set)
        #=======================================================================
        
        # Calculate the amount of elements that should be checked back, to cover the time window set.
        numElementsToCheck = int((self.movementTimeWindow * 1000) / average_delay) + 1
        ones_count = 0
        ceros_count = 0
        for i in range(0, numElementsToCheck):
            if (self.movementVector[self.movementVectorLength - 1 - i] == 1):
                ones_count += 1
            else:
                ceros_count += 1
        # print "1's: ", ones_count
        # print "0's: ", ceros_count
        if (ones_count * (100.0 / numElementsToCheck) >= self.VECTOR_COUNT_PERCENTAGE_MOVEMENT):
            # More ones than the percentage. This is considered movement along the given time window.
            # return OK
            self.continuousMovementTime = self.movementTimeWindow
            self.continuousIdleTime = 0.0
            self.isMoving = True
            self.isIdle = False
        elif (ceros_count * (100.0 / numElementsToCheck) >= self.VECTOR_COUNT_PERCENTAGE_IDLE):
            self.continuousIdleTime = self.movementTimeWindow
            self.continuousMovementTime = 0.0
            self.isMoving = False
            self.isIdle = True
        else:
            # it is not moving nor staying idle
            self.continuousMovementTime = 0.0
            self.continuousIdleTime = 0.0
            self.isMoving = False
            self.isIdle = False
        # print "MVB end."
        logger.debug(("Idle Time: %r" % self.continuousIdleTime) + ("     Movement Time: %r" % self.continuousMovementTime) + ("   Elements to check: %d" % numElementsToCheck))
        logger.debug ("       isMoving: %r      isTracking: %r" % (self.isMoving , self.isTracking))
        logger.debug ("       isIdle: %r      " % self.isIdle)
        logger.debug("movementVector:%r" %  self.movementVector)
        return
    
    
    
    
    def Method_MovementVector(self):
        # Movement Vector method:
        # Each cycle, an element is added to movement vector.
        # If there are N past 1's in the vector, then it was moving and currently is. (includes certain 0's tolerance)
        # Else: it is idle.
        # This method returns the estimated movement time (how much time it was moving) or idle time.
        # This method does not considers anything different than moving or idle (there is no extra state).
        
        
        
        #=======================================================================
        # # Variables for recognizing changes in state.
        #=======================================================================
        
        current_state_change = 0  # 0: invalid, 1: changed from idle to moving, 2: changed from moving to idle, 3: stays idle, 4: stays moving
        
        #=======================================================================
        # # Keep track of the time it takes to process the whole loop
        #=======================================================================
        
        # work in ms, at the end it passes to s again
        
        timeDif = (timeit.default_timer() - self.last_saved_time_gp)
        self.last_saved_time_gp = timeit.default_timer()
        # sttemp = "Current Loop time (ms): %d" %  int(timeDif * 1000)
        # sttemp += "            "
        
        self.movementDelayVector[0:-1] = self.movementDelayVector[1:]
        self.movementDelayVector[self.movementDelayVectorLength - 1] = int(timeDif * 1000)
        average_delay = 0
        for i in range(0, self.movementDelayVectorLength):
            average_delay += self.movementDelayVector[i]
        
        average_delay /= self.movementDelayVectorLength
        
        # logger.debug ( sttemp + ("Average Loop time (ms): %d" % average_delay) )
        
        self.last_saved_time_movement = timeit.default_timer()
        
        #=======================================================================
        # process new vector entry, appends a 1 or 0 to the movement vector.
        #=======================================================================
        
        self.movementVector[0:-1] = self.movementVector[1:]
        movementAmount = (abs(self.getInstantX() * self.getInstantX()) + abs(self.getInstantY() * self.getInstantY()))
        logger.debug("Amount of movement: %d" % movementAmount)
        if (movementAmount >= self.movementThreshold or self.isTracking == False):
                    self.movementVector[self.movementVectorLength - 1] = 1
        else:
                    self.movementVector[self.movementVectorLength - 1] = 0
        
        #=======================================================================
        # # Check whether this element mantains the previous state or modifies it
        #=======================================================================
        if (self.movementVector[self.movementVectorLength - 1] == 1 and self.isMoving == True):
            # new 1 detected, and it was moving, so it is still moving. Add 1 LOOP TIME to the total movement time.
            self.continuousMovementTime += (timeDif)
            current_state_change = 4
        
        elif (self.movementVector[self.movementVectorLength - 1] == 0 and self.isIdle == True):
            # new 0 detected, and it was idle, so it is still idle. Add 1 LOOP TIME to the total idle time.
            self.continuousIdleTime += (timeDif)
            current_state_change = 3
        
        elif (self.movementVector[self.movementVectorLength - 1] == 0 and self.isMoving == True):
            # cero detected, and was previously moving.
            # It should be checked whether this 0 nullifies the continuous mvmnt. or not
            number_of_elements_to_check = int (int(self.continuousMovementTime * 1000) / average_delay)
            if (number_of_elements_to_check >= self.movementVectorLength):
                # the number of elements to check is too large, better check all the vector
                number_of_elements_to_check = self.movementVectorLength
            else:
                number_of_elements_to_check += 1  # we check all the previous ones + 1 addition.
            
            # a comparisson is made between the last N elements, to see if this new 0 alters the balance
            ones_count = 0
            ceros_count = 0
            for i in range(int(self.movementVectorLength - number_of_elements_to_check) , int (self.movementVectorLength)):
                if (self.movementVector[i] == 1):
                    ones_count += 1
                else:
                    ceros_count += 1
            if ((ones_count * (100 / number_of_elements_to_check)) >= self.VECTOR_COUNT_PERCENTAGE):
                # the ones and ceros were counted, and it is still moving because the 1's are greater than the percentage.
                self.isMoving = True
                self.isIdle = False
                current_state_change = 4
                self.continuousMovementTime += (timeDif)
            else:
                # now that a 0 was found, there are not enough 1's. So it changed from moving to currently idle.
                self.isMoving = False
                self.isIdle = True
                current_state_change = 2
                self.continuousIdleTime = (timeDif)
        
        
        elif (self.movementVector[self.movementVectorLength - 1] == 1 and self.isIdle == True):
            # one detected, and was previously idle.
            # It should be checked whether this 1 nullifies the idle state or not
            number_of_elements_to_check = int(self.continuousMovementTime * 1000) / average_delay
            if (number_of_elements_to_check >= self.movementVectorLength):
                # the number of elements to check is too large, better check all the vector
                number_of_elements_to_check = self.movementVectorLength
            else:
                number_of_elements_to_check += 1  # we check all the previous ones + 1 addition.
            
            # a comparisson is made between the last N elements, to see if this new 1 alters the balance
            ones_count = 0
            ceros_count = 0
            for i in range(int(self.movementVectorLength - number_of_elements_to_check) , int(self.movementVectorLength)):
                if (self.movementVector[i] == 1):
                    ones_count += 1
                else:
                    ceros_count += 1
            if ((ones_count * (100 / number_of_elements_to_check)) >= self.VECTOR_COUNT_PERCENTAGE):
                # the ones and ceros were counted, and it changed, it is now moving because the 1's are greater than the percentage.
                self.isMoving = True
                self.isIdle = False
                current_state_change = 1
                self.continuousMovementTime = (timeDif)
            else:
                # the 1 found does not alter the idle state
                self.isMoving = False
                self.isIdle = True
                current_state_change = 3
                self.continuousIdleTime += (timeDif)
        
        logger.debug(self.movementVector)
        logger.debug(("Idle Time: %r" % self.continuousIdleTime) + ("     Movement Time: %r" % self.continuousMovementTime))
        # logger.debug ( "       isMoving: %r" % self.isMoving)
        
        #=======================================================================
        # # Save history of movements and idle
        #=======================================================================
        # CONTINUAR
        # DEBEN HABER 3 ESTADOS. SE MOVIÓ HACE 0.5 SEGUNDOS, IDLE HACE 0.5 SEGUNDOS, ESTADO INVÁLIDO.
        # Historia de movimiento para saber cuánto suman los movimientos interrumpidos.
        # EJ: [ 0.3 0.5 1.0 0.0 0.1 0.0 ]  suma bastante movimiento en total. Es mejor que preguntar instantáneamente cuanto se está moviendo.
        
        self.vectorPseudoInstantaneo.x = self.vectorInstantaneo.x
        self.vectorPseudoInstantaneo.y = self.vectorInstantaneo.y
        self.vectorInstantaneo.x = 0
        self.vectorInstantaneo.y = 0
    
    
    def Method_AccumulateTime(self):
        # this function analyzes continuous movement. If detected, saves the amount of seconds of the movement so far.
        # if idle is detected, it saves how much time the subject is idle.
        self.internalMovementCounter += 1
        
        if (self.internalMovementCounter > self.movement_loopNumberSpan):
            self.internalMovementCounter = 0
            logger.debug("   ----" + 
                            str(abs(self.vectorInstantaneo.x * self.vectorInstantaneo.x) + 
                abs(self.vectorInstantaneo.y * self.vectorInstantaneo.y)))
            if ((abs(self.vectorInstantaneo.x * self.vectorInstantaneo.x) + 
                    abs(self.vectorInstantaneo.y * self.vectorInstantaneo.y) >= self.movementThreshold)
                or self.isTracking == False):
                    # print "It is currently moving"
                    if (self.isIdle == True):
                        # was idle, now started to move. We erase time movement counter and start from 0 now
                        self.continuousMovementTime = 0
                        self.isMoving = True
                        self.isIdle = False
                        # CHECK SOLUTION FOR THE NEXT LINE.
                        self.last_saved_time_movement = timeit.default_timer()  # this substracts the first loop movement
                    
                    
                    now = timeit.default_timer()
                    timeDif = (now - self.last_saved_time_movement)
                    if (timeDif < 0.001):  # prevent from saving extremely low values (exp-10 etc..)
                        timeDif = 0
                    self.continuousMovementTime = timeDif
                    # self.last_saved_time_movement = timeit.default_timer()
                    self.vectorPseudoInstantaneo.x = self.vectorInstantaneo.x
                    self.vectorPseudoInstantaneo.y = self.vectorInstantaneo.y
                    self.vectorInstantaneo.x = 0
                    self.vectorInstantaneo.y = 0
            else:
                    # print "not moving"
                    if (self.isMoving == True):
                        # was moving and now it is not. We erase the old idle time counter, and we start counting idle time from 0
                        self.isMoving = False
                        self.isIdle = True
                        self.continuousIdleTime = 0
                        self.last_saved_time_idle = timeit.default_timer()
                    now = timeit.default_timer()
                    timeDif = (now - self.last_saved_time_idle)
                    if (timeDif < 0.001):  # prevent from saving extremely low values
                        timeDif = 0
                    self.continuousIdleTime = timeDif
                    # self.last_saved_time_idle = timeit.default_timer()
                    self.vectorPseudoInstantaneo.x = self.vectorInstantaneo.x
                    self.vectorPseudoInstantaneo.y = self.vectorInstantaneo.y
                    self.vectorInstantaneo.x = 0
                    self.vectorInstantaneo.y = 0
            # history of movement mejoraría la performance de este método.
            logger.debug("Continuous: " + str(self.continuousMovementTime) + "  ...  Idle: " + str(self.continuousIdleTime))
    
    def continuousMovementAnalysis(self):
        if (self.movementMethod == 0):
            self.Method_AccumulateTime()
        elif (self.movementMethod == 1):
            self.Method_MovementVector()
        elif (self.movementMethod == 2):
            self.Method_MovementVectorBinary()
        
    def setMovementMethod(self, mthd):
        """set Movement Analysis method. There are:
            0- Accumulate time method (default): 
                For each main cycle, the continuous movement (or idle) time is updated. 
                If the status changes, the counter is restarted.
            1- Movement vector method:
                For each main cycle, an element is added to a vector. 1 if movement detected, 0 else.
                The program returns if there is "movement" and for how much time if the vector contains
                enough 1's and 0's, and considers the case where a nearly smooth movement was detected (1111011111)
            2- Many cycles integration method:
                Similar to 0, it integrates among many cycles, averaging the movement, making less probable
                to have a false negatives, but losses certain precision.
            3- Goodness of fit method:
                A movement vector, with non-binary values, is compared against a statistical model that predicts
                the subject movement. If the movement is similar to the statistical model, then it is moving.
        """
        try:
            methodNumber = int(mthd)
        except:
            return
        self.movementMethod = methodNumber
    
    def getMovementMethod(self):
        return self.movementMethod
    
    def setCalibrationVariables(self, minRadius, maxRadius, expectedValue):
        #setting first "noise filtering on" variables:
        self.NoiseFilteringOnVars.MAX_CIRCLE_MOVEMENT = expectedValue * 1.5
        self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT = expectedValue / 5
        if (self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT > 2 and expectedValue > 15 and expectedValue < 35):
            self.NoiseFilteringOnVars.MIN_CIRCLE_MOVEMENT = 2
        pass
        self.NoiseFilteringOnVars.WORKING_MIN_CONTOUR_AREA = minRadius * minRadius * 3.142 * 0.5
        self.NoiseFilteringOnVars.WORKING_MAX_CONTOUR_AREA = maxRadius * maxRadius * 3.142 * 1.3
        pass
        #now setting "noise filtering off" variables:
        print "No noise filtering set."
        logger.info("No noise filtering set.")
        self.NoiseFilteringOffVars.MAX_CIRCLE_MOVEMENT = expectedValue * 2
        self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT = expectedValue / 8
        self.NoiseFilteringOffVars.minRadius = 1
        minRadius = 1
        if (self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT > 2 and expectedValue > 15 and expectedValue < 35):
            self.NoiseFilteringOffVars.MIN_CIRCLE_MOVEMENT = 2
        pass
        self.NoiseFilteringOffVars.WORKING_MIN_CONTOUR_AREA = minRadius * minRadius * 3.142 * 0.5
        self.NoiseFilteringOffVars.WORKING_MAX_CONTOUR_AREA = maxRadius * maxRadius * 3.142 * 1.3
#         if (self.noiseFiltering == False):
#                             print "No noise filtering set."
#                             logger.info("No noise filtering set.")
#                             self.MAX_CIRCLE_MOVEMENT = expectedValue * 2
#                             self.MIN_CIRCLE_MOVEMENT = expectedValue / 8
#                             minRadius = 1
#                             if (self.MIN_CIRCLE_MOVEMENT > 2 and expectedValue > 15 and expectedValue < 35):
#                                 self.MIN_CIRCLE_MOVEMENT = 2
#         else:
#                              self.MAX_CIRCLE_MOVEMENT = expectedValue * 1.5
#                              self.MIN_CIRCLE_MOVEMENT = expectedValue / 5
#                              if (self.MIN_CIRCLE_MOVEMENT > 2 and expectedValue > 15 and expectedValue < 35):
#                                  self.MIN_CIRCLE_MOVEMENT = 2
#         self.WORKING_MIN_CONTOUR_AREA = minRadius * minRadius * 3.142 * 0.5
#         self.WORKING_MAX_CONTOUR_AREA = maxRadius * maxRadius * 3.142 * 1.3
        pass
        self.setNoiseFiltering(self.getNoiseFiltering()) #to apply changes.
    
    def pygameVisualizationTools(self):
        #visualization tools for helping calibrate camera.
        self.windowSurface.fill((0,0,0))   
        text1 = self.secondaryFont.render('mvnt: %r' % self.getMovementTime(), True, (255,255,255))
        textRect1 = text1.get_rect()
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.secondaryFont.render('idle: %r' % self.getIdleTime(), True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centerx = textRect1.centerx + 150;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render('tracking: %r' % self.trackingVector, True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 40;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render('Is Tracking: %r' % self.isTracking, True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 80;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render('Cause for losing track: %r' % self.losing_track_cause, True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 120;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render('Moving circles: %r' % self.number_of_moving_vectors, True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 160;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render('Standing circles: %r' % self.number_of_standing_vectors, True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 200;
        self.windowSurface.blit(text1, textRect1)
        
        strAreas = ""
        for i in range (0, len(self.areasVector)):
            strAreas += "%.2f , " % (self.areasVector[i]/10000.0)
        text1 = self.smallFont.render("total area of circles/10000: %r" % (strAreas), True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 240;
        self.windowSurface.blit(text1, textRect1)
        
        text1 = self.smallFont.render("Current area of circles: %.2f" % (self.sum_of_areas), True, (255,255,255))
        textRect1 = text1.get_rect()
        textRect1.centery = textRect1.centery + 280;
        self.windowSurface.blit(text1, textRect1)
        
        pygame.display.update()
        pass
    
    def mainVideoDetection(self):
    
        """
            Programa de detección de movimiento:
            Se enciende y configura cámara.
            Por cada ciclo de programa, se compara el fotograma actual con el anterior.
                Si hay diferencias en el movimiento de un círculo particular (comparando
                si son iguales por el hecho de que hay colisión en el espacio 2D-tiempo)
                entonces añadir valor en el vector en el que este círculo se movió.
    """    
        CAM_NUMBER = 0  # cam number, 0 for integrated webcam, 1 for the next detected camera.
        
        # TCP_IP = 'localhost' #ip a donde conecto a socket
        # TCP_PORT = 50007 #puerto del socket
        # variables "de movimiento":
        # CAM_WIDTH = 640
        # CAM_HEIGHT = 480
        MIN_CONTOUR_AREA = 60  # min contour area to be valid, used in calibration
        MAX_CONTOUR_AREA = 2600  # max contour area to be valid , used in calibration
        self.WORKING_MIN_CONTOUR_AREA = 9999  # min contour area to be valid, used in every main loop
        self.WORKING_MAX_CONTOUR_AREA = 0  # max contour area to be valid, used in every main loop
        self.MIN_CIRCLE_MOVEMENT = 3  # mínima diferencia en movimiento del círculo para considerarlo como movimiento
        self.MAX_CIRCLE_MOVEMENT = 35  # máx diferencia en movimiento del círculo para considerarlo como movimiento
        
        # Inicio de programa: se instancia videoSource
        import videoSource
        vs = videoSource.videoSource();
        cam = vs.getVideoSource();
        
        
        
        
        
        cv2.namedWindow(self.winName, cv2.CV_WINDOW_AUTOSIZE)
        
        
        # Se declaran unas imágenes, para inicializar correctamente cámara y variables.
        t_before = cv2.cvtColor(cam.read()[1], cv2.COLOR_RGB2GRAY)
        t_now = cv2.cvtColor(cam.read()[1], cv2.COLOR_RGB2GRAY)
        capturedImage = cam.read()[1]
        
        
        #self.capturedImageWidth, self.capturedImageHeight = cv.GetSize( cv.fromarray(capturedImage) )
        self.capturedImageWidth, self.capturedImageHeight = self.cv_size( capturedImage )
        self.capturedImageSize = capturedImage.size
        print "Size: %r " % self.capturedImageSize
        print "Width: %r " %  self.capturedImageWidth
        print "Height: %r " %  self.capturedImageHeight
        
        time.sleep(0.1)

        self.startCalibration = True
        print "Starting video detection main loop."
        Lnew = []
        while (self.available == True):
                #===============================================================
                # #calibrate if necessary
                #===============================================================
                if (self.startCalibration == True):
                    if (self.manageCalibrationVariables(0) == False):
                        print "Calibration file missing. A new calibration file will be created.."
                        logger.info("Calibration file missing. A new calibration file will be created..")
                        t_calib = cv2.cvtColor(capturedImage, cv2.COLOR_RGB2GRAY)
                        #cv.Smooth(cv.fromarray(t_calib), cv.fromarray(t_calib), cv.CV_BLUR, 3);
                        t_calib = cv2.medianBlur(t_calib, 3)
                        ret, thresh = cv2.threshold(t_calib, self.CV2THRESHOLD, 255, cv2.THRESH_BINARY)
                        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                        # recorro los contornos capturando centros de los contornos cuando son englobados por un círculo
                        circleCenters = []
                        circleRadius = []
                        for cnt in contours:
                            (x, y), radius = cv2.minEnclosingCircle(cnt)
                            center = (int(x), int(y))
                            radius = int(radius)
                            if cv2.contourArea(cnt) > MIN_CONTOUR_AREA and cv2.contourArea(cnt) < MAX_CONTOUR_AREA: 
                                # áreas muy chicas pueden significar ruido que se mueve, mejor ignorarlo..
                                cv2.circle(capturedImage, center, radius, (0, 255, 0), 2)
                                circleCenters.append(center)
                                circleRadius.append(radius)
                        expectedValue = 0
                        minRadius = 9999
                        maxRadius = 0
                        for i in range (0, 10):
                            cv2.imshow(self.winName , capturedImage)
                            time.sleep(0.01)
                            key = cv2.waitKey(10)
                        for i in range(0, len(circleRadius)):
                            expectedValue += circleRadius[i]
                        
                        if len(circleCenters) > 0:
                          expectedValue /= len(circleCenters)
                        else:
                          expectedValue = 1
                        
                        for i in range (0, len(circleCenters)):
                            if (circleRadius[i] > maxRadius and abs(circleRadius[i] - expectedValue) < expectedValue / 2):
                                maxRadius = circleRadius[i]
                            if (circleRadius[i] < minRadius and abs(circleRadius[i] - expectedValue) < expectedValue / 2):
                                minRadius = circleRadius[i]
                        
                        # variables regarding noise filtering will be created wether nf is on or off:
                        self.setCalibrationVariables(minRadius, maxRadius, expectedValue)
                        
                        print "Number of samples: %d" % len(circleCenters)
                        logger.info(str("Number of samples: %d" % len(circleCenters)))
                        print "Radius expected value: %d" % expectedValue
                        logger.info(str("Radius expected value: %d" % expectedValue))
                        print "Minor Radius: %d" % minRadius
                        logger.info(str("Minor Radius: %d" % minRadius))
                        print "Major Radius: %d" % maxRadius
                        logger.info(str("Major Radius: %d" % maxRadius))
                        print "Max Circle Movement: %d" % int(self.MAX_CIRCLE_MOVEMENT)
                        logger.info(str("Max Circle Movement: %d" % int(self.MAX_CIRCLE_MOVEMENT)))
                        print "Min Circle Movement: %d" % int(self.MIN_CIRCLE_MOVEMENT)
                        logger.info(str("Min Circle Movement: %d" % int(self.MIN_CIRCLE_MOVEMENT)))
                        print "Min contour area: %d" % int(self.WORKING_MIN_CONTOUR_AREA)
                        logger.info(str("Min contour area: %d" % int(self.WORKING_MIN_CONTOUR_AREA)))
                        print "Max contour area: %d" % int(self.WORKING_MAX_CONTOUR_AREA)
                        logger.info(str("Max contour area: %d" % int(self.WORKING_MAX_CONTOUR_AREA)))
                        
                        if (self.manageCalibrationVariables(1) == False):
                            print "Error writing and saving calibration file."
                            logger.warning("Error writing and saving calibration file.")
                        else:
                            print "Calibration file saved."
                            logger.info("Calibration file saved.")
                        if (self.showUserFeedback == False):
                            cv2.destroyWindow(self.winName)
                        self.startCalibration = False
                    else:
                        # Calibration file exists, there is no need to calibrate.
                        print " - Calibration file exists. Using calibration file. - "
                        logger.info(str("Max Circle Movement: %d" % int(self.MAX_CIRCLE_MOVEMENT)))
                        # print "Max Circle Movement: %d" % int(self.MAX_CIRCLE_MOVEMENT)
                        logger.info(str("Max Circle Movement: %d" % int(self.MAX_CIRCLE_MOVEMENT)))
                        # print "Min Circle Movement: %d" % int(self.MIN_CIRCLE_MOVEMENT)
                        logger.info(str("Min Circle Movement: %d" % int(self.MIN_CIRCLE_MOVEMENT)))
                        # print "Min contour area: %d" % int(self.WORKING_MIN_CONTOUR_AREA)
                        logger.info(str("Min contour area: %d" % int(self.WORKING_MIN_CONTOUR_AREA)))
                        # print "Max contour area: %d" % int(self.WORKING_MAX_CONTOUR_AREA)
                        logger.info(str("Max contour area: %d" % int(self.WORKING_MAX_CONTOUR_AREA)))
                        self.startCalibration = False
                        pass
                
                #===============================================================
                # # Preparo las imgs antigûa, actual y futura<>
                #===============================================================
                # capturedImage toma una captura para t_now, y para algunas geometrías que se dibujan encima de él.
                capturedImage = cam.read()[1]
                #lo primero que se hace es verificar que se haya podido leer algo. Caso contrario, end of video..
                if (type(capturedImage) == type(None)):
                    logger.info("sphereVideoDetection reached END OF VIDEO . Seeking to the start...")
                    #cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_POS_FRAMES, 0)
                    cam.set( cv2.cv.CV_CAP_PROP_POS_MSEC , 0)
                    cam.set( cv2.cv.CV_CAP_PROP_POS_MSEC , 0)
                    capturedImage = cam.read()[1]
                    #break
                    pass
                
                if capturedImage.size == 0:
                    logger.info("sphereVideoDetection reached END OF VIDEO . Seeking to the start...")
                    #cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_POS_FRAMES, 0)
                    cam.set(cv2.cv.CV_CAP_PROP_POS_MSEC, 0)
                    cam.set(cv2.cv.CV_CAP_PROP_POS_MSEC, 0)
                    capturedImage = cam.read()[1]
                    #break;
                    pass
                pass
                # t_before es el del anterior ciclo, t_now es el recién capturado (procesándolo 1ero..),
                
                # t_before = t_now #saves old matrix; unnecessary since what is important from old matrix is the circle and point matrix
                t_now = cv2.cvtColor(capturedImage, cv2.COLOR_RGB2GRAY)  # current matrix
                
                #cv.Smooth(cv.fromarray(t_now), cv.fromarray(t_now), cv.CV_BLUR, 3);
                t_now = cv2.medianBlur(t_now, 3)
                # cv.Smooth(cv.fromarray(t_now), cv.fromarray(t_now), cv.CV_GAUSSIAN, 3, 0);
                #===============================================================
                # Se guarda la matriz utilizada en el ciclo anterior.
                #===============================================================
                Lbefore = Lnew  # guardo vieja matriz de movimiento; actualizo la nueva
                #===============================================================
                # #Proceso la imagen actual: t_now
                #===============================================================
                ret, thresh = cv2.threshold(t_now, self.CV2THRESHOLD, 255, cv2.THRESH_BINARY)
                contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                #===============================================================
                # #Recorrido de frame actual:
                #===============================================================
                # recorro los contornos para el frame actual, capturando centros.
                Lnew = []
                self.sum_of_areas = 0; #cantidad de área cubierta por todos los círculos siendo trackeados
                # si el área es muy chica respecto de lo que es normal, probablemente ha perdido tracking.
                for cnt in contours:
                    (x, y), radius = cv2.minEnclosingCircle(cnt)
                    center = (int(x), int(y))
                    radius = int(radius)
                    # a continuaciOn, si el contorno tiene suficiente área, pero también si no es TAN grande:
                    if (cv2.contourArea(cnt) > self.WORKING_MIN_CONTOUR_AREA and
                         cv2.contourArea(cnt) < self.WORKING_MAX_CONTOUR_AREA):
                        if (self.showTrackingFeedback):
                            cv2.circle(capturedImage, center, radius, (0, 255, 0), 2)  # visual feedback to user.
                        Lnew.append(center)
                        self.sum_of_areas+= 3.1415 * radius*radius;
                self.areasVector[0:-1] = self.areasVector[1:]
                self.areasVector[-1] = self.sum_of_areas
                #===============================================================
                # #analizo si hay colisiones en el espacio 2D-tiempo
                #===============================================================
                # Si las hubiera, voy sumando contribuciones para ver hacia donde apunta el movimiento medio.
                # Se analizan ambos versores del vector en el plano bidireccional:
                self.movEjeX = 0
                self.movEjeY = 0
                self.number_of_moving_vectors = 0
                self.number_of_standing_vectors = 0
                
                for index in range(len(Lnew)):
                    for jndex in range(index, len(Lbefore)):
                        movement_difference = (Lnew[index][0] - Lbefore[jndex][0]) ** 2 + (Lnew[index][1] - Lbefore[jndex][1]) ** 2
                        if (math.sqrt(movement_difference) >= self.MIN_CIRCLE_MOVEMENT):
                             if (math.sqrt(movement_difference) <= self.MAX_CIRCLE_MOVEMENT):
                                # print "Hay colisión: %d %d" % (index,jndex)
                                # cv2.circle(capturedImage, (Lnew[index][0], Lnew[index][1]),3,(0,0,255),2)
                                if (self.showTrackingFeedback):
                                    cv2.line(capturedImage, (Lnew[index][0], Lnew[index][1]), (Lbefore[jndex][0], Lbefore[jndex][1]), (255, 0, 0), 5)  # user feedback
                                # se suma a todos los desplazamientos (en x, en y).
                                self.movEjeX += Lnew[index][0] - Lbefore[jndex][0]
                                self.movEjeY += Lnew[index][1] - Lbefore[jndex][1]
                                self.number_of_moving_vectors += 1
                        else:
                            # están muy cerca, son probablemente el mismo.
                            self.number_of_standing_vectors += 1
                self.isTrackingTemp = True
                self.losing_track_cause = ""
                if (self.number_of_standing_vectors < len(Lnew) / 3 and self.number_of_moving_vectors < len(Lnew) / 3):  # see docs.
                    if (len(Lnew) > 2):  # else too few circles to determine loss of tracking
                        self.isTrackingTemp = False #on this frame, the tracking has been lost.
                        self.losing_track_cause = "standing_vs_moving_vectors"
                if self.isTrackingTemp == True:
                    # studying lose of track associated with area of circles
                    if (self.sum_of_areas < self.MIN_CIRCLE_TOTAL_AREA_TO_CONSIDER_TRACKING):
                            self.isTrackingTemp = False #less area than expected, it has lost movement tracking
                            self.losing_track_cause = "small_area"
                
                self.trackingVector[0:-1] = self.trackingVector[1:]
                self.trackingVector[-1] = self.isTrackingTemp
                cant_pastframes_tracking = 0
                self.isTracking = True
                for i in range(0, len(self.trackingVector)):
                    if self.trackingVector[i] == True:
                        cant_pastframes_tracking += 1
                if (cant_pastframes_tracking < 8): #from the past 10 tracking frames , 80% or less have lost tracking
                    self.isTracking = False #so consider this as a current lost of track (movement with unknown direction)
                
                
                
                # print cant_pastframes_tracking
                # print self.trackingVector
                # print "Standing vectors ", number_of_standing_vectors
                # print "Moving vectors ", number_of_moving_vectors
                # print "circles " , len(Lnew)
                # print "Tracking : " , self.isTracking
                # print "----"
                
                # we divide each instant vector components by N, to obtain average instant vector.
                if (self.number_of_moving_vectors == 0):
                    self.number_of_moving_vectors = 1
                
                self.movEjeX /= self.number_of_moving_vectors  # movimiento x promedio, ponderación de todos los movimientos en x.
                self.movEjeY /= self.number_of_moving_vectors  # movimiento y promedio, ponderación de todos los movimientos en y.
                
                self.vectorAcumulado.x += self.movEjeX
                self.vectorAcumulado.y += self.movEjeY
                
                self.vectorInstantaneo.x += self.movEjeX  # suma contrib. x en este ciclo (se establece a 0 en otro método)
                self.vectorInstantaneo.y += self.movEjeY  # suma contrib. y en este ciclo (se establece a 0 en otro método)
                
                # se analiza continuidad de movimiento en función:
                self.continuousMovementAnalysis()
                
                # se ejecutan visualization tools de pygame (es opcional)
                if self.usingPygameDisplay:
                    self.pygameVisualizationTools()
                
                #===============================================================
                # se "muestra" el resultado al usuario (feedback)
                #===============================================================
                if (self.showUserFeedback):
                    cv2.imshow(self.winName , capturedImage)  # obs.: NO es estrictamente necesario mostrar la ventana para que funcione
                # (imshow se puede sacar si el CPU es un problema.)
                
                #===============================================================
                # #para finalizar programa, usuario presiona "Escape":
                #===============================================================
                key = cv2.waitKey(self.sleepTime)
                if (key == 27 or key == 1048603 or self.mustquit == 1 or self.available != True):  # escape pressed
                    # end Program.
                    try:
                        cam.release()
                    except:
                        pass
                    cv2.destroyWindow(self.winName)
                    cv2.destroyAllWindows()
                    # cv.DestroyWindow(self.winName)
                    logger.info("Exiting sphereVideoDetection")
                    # os.kill(os.getpid(), signal.SIGINT)
                    #print self.mustquit
                    if (self.mustquit == 0):
                        os._exit(0)
                    return


""
#
#
#===============================================================================
# #Prueba unitaria de la clase si es ejecutada independientemente:
#===============================================================================
if __name__ == '__main__':
    # create a logging format
    dateformat = '%Y/%m/%d %H:%M:%S'
    formatter_str = '%(asctime)s.%(msecs)d - %(name)s - %(levelname)s - %(message)s'
    filename_to_log='logs/sphereVideoDetection.log'
    
    
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
    
    logger.info('Start sphereVideoDetection Test')
    # Crea un objeto de captura de video, imprime tiempo de movimiento continuo o tiempo que permanece quieto.
    videoDet = sphereVideoDetection( )
    videoDet.setNoiseFiltering(True)
    videoDet.setMovementTimeWindow(1.6);
    videoDet.initAll()
    import time
    # time.sleep(2)
    # videoDet.setNoiseFiltering(False)
    # videoDet.calibrate()
    
    while(True):
        # print "x:  "+str(videoDet.getAccumX())
        # print "y:  "+str(videoDet.getAccumY()) #<>
        # print "Continuous movement time: %r    Idle movement time: %r   IsMoving: %r"  % (videoDet.getMovementTime() , videoDet.getIdleTime(), videoDet.getMovementStatus())
        a = str("Continuous movement time: %r    Idle movement time: %r   IsMoving: %r" % 
                 (videoDet.getMovementTime() , videoDet.getIdleTime(), videoDet.getMovementStatus()))
        logger.info(a)
        #print videoDet.movementVector
        time.sleep(0.3)

"""
if __name__ == '__main__':
    #ver http://stackoverflow.com/questions/12376224/python-threading-running-2-different-functions-simultaneously
    #import threading
    #import threading
    # Create two threads, one for video Detection, the other with the game per se.
    #fred1 = threading.Thread(target=mainFunction)
    #fred1.start()
    
    #fred2 = threading.Thread(target=mainVideoDetection)
    #fred2.start()
    print "prueba ejecutada."
    try:
        from configvideo import *
    except ImportError:
        print "No existe el archivo configvideo.py"
    except:
        print "otro error"
    videoDet = sphereVideoDetection(VIDEOSOURCE,CAM_WIDTH, CAM_HEIGHT)
    
    
    import time
    try:
    import valve
    except:
    print "error importing Valve"
    while(True):
    time.sleep(2)
    print "x:  "+str(videoDet.getAccumX())
    print "y:  "+str(videoDet.getAccumY()) #<>
    if (abs(videoDet.getAccumX()) > 100  or abs(videoDet.getAccumY()) > 100):
        #resetear lo acumulado:
        videoDet.resetX()
        videoDet.resetY()
        #abrir la válvula
        print "abro VAlvula"
        val1 = valve.Valve()
        val1.open()
        time.sleep(0.2)
        val1.close()
        time.sleep(0.2)
        print "fin apertura vAlvula"
"""
