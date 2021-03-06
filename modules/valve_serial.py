from serial import *
import time
import track_bola_utils
import logging
logger = logging.getLogger('valveserial')

DropTime = .1


class multiproc_Valve():
    def __init__(self, jobl):
        self.displayJobList = jobl
        
        import deviceSerial
        self.innerDeviceSerial = deviceSerial.deviceSerial();
        if (self.innerDeviceSerial.using_dummy):
            #using dummy, means that it was not well initialized. Retrying:
            print "Not using serial device. Retrying device creation.."
            time.sleep(0.5)
            self.innerDeviceSerial.initDevice()
            if (self.innerDeviceSerial.using_dummy):
                print "Still not using serial device. Retrying device creation.."
                time.sleep(0.5)
                self.innerDeviceSerial.initDevice()
        devStatusMessage = "Device created successfully. Device type: "
        if (self.innerDeviceSerial.using_dummy):
            devStatusMessage = devStatusMessage + " dummy device"
        else:
            devStatusMessage = devStatusMessage + " serial device"
        print devStatusMessage
    
    def checkJobList(self):
        if (self.displayJobList.qsize() > 0 or self.displayJobList.empty() == False ):
                try:
                        tempvar = self.displayJobList.get()
                        self.displayJobList.task_done()
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
                if (index == "open"):
                    self.open()
                elif (index == "drop"):
                    self.drop()
                elif (index == "close"):
                    self.close()
        pass
    
    def open(self) :
         logger.debug('Valve opened')
         retmsg = self.innerDeviceSerial.writeToSerial('o')
         return retmsg

    def close(self) :
         logger.debug('Valve closed')
         retmsg = self.innerDeviceSerial.writeToSerial('c')
         return retmsg

    def drop(self) :
         logger.debug('Valve drop')
         retmsg = self.innerDeviceSerial.writeToSerial('o')
         time.sleep(DropTime)
         retmsg = self.innerDeviceSerial.writeToSerial('c')
         return retmsg
     


if __name__ == '__main__':
    # create a logging format
    dateformat = '%Y/%m/%d %H:%M:%S'
    formatter_str = '%(asctime)s.%(msecs)d - %(name)s - %(levelname)s - %(message)s'
    filename_to_log='logs/valve.log'
    
    
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
    
    logger.info('Start Valve Test1')
    time.sleep(0.3)
    v1 = Valve()
    v1.open()
    time.sleep(2)
    v1.close()
    time.sleep(2)
    v1.drop()
    time.sleep(2)
    print v1
    v2 = Valve()
    v2.open()
    time.sleep(2)
    v2.close()
    print v2
    
    logger.info('End Valve Test')
    v1.exit()
