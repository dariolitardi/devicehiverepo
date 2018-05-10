# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================


import glob
import hashlib
import sched
import time 
import threading
from devicehive import Handler
from devicehive import DeviceHive

SERVER_URL = 'http://playground.devicehive.com/api/rest'
SERVER_REFRESH_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJwYXlsb2FkIjp7ImEiOlsyLDMsNCw1LDYsNyw4LDksMTAsMTEsMTIsMTUsMTYsMTddLCJlIjoxNTM5Nzg0NjE5NzUwLCJ0IjowLCJ1IjoxODk1LCJuIjpbIjE4NzYiXSwiZHQiOlsiKiJdfX0.fpeWgw4-MYgG2JQNYHquDNx09S19Fig2jb9SwT1qDWI' # 'PUT_YOUR_REFRESH_TOKEN_HERE'
DEVICE_ID = 'raspi-smartgarden' \
            + hashlib.md5(SERVER_REFRESH_TOKEN.encode()).hexdigest()[0:8]
LED_PIN = 17



sensorValueRain=0
sensorValueHumidity=0
STARTINGTIME=0 #GESTIONE TIMER
TIMEOUTWATER=0 #GESTIONE TIMEOUT (8000Ms = 8 Sec)
pioggia=False
umiditaIniziale=0
umiditaFinale=0
inizioInnaffiamento=""
fineInnaffiamento=""
data=""
TIMEWATER=0 #GESTIONE TIMEOUT (8000Ms = 8 Sec)
START_TIMEWATER=0#GESTIONE TIMEOUT (8000Ms = 8 Sec)
ledVerde = 8
INTERVAL = 120000
DO = 02
D1 = 03
D2 = 04

''' Real or fake GPIO handler.
'''
try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
except ImportError:
    class FakeGPIO(object):
        OUT = "OUT"

        def __init__(self):
            print('Fake gpio initialized')

        def setup(self, io, mode):
            print('Set gpio {0}; Mode: {1};'.format(io, mode))

        def output(self, io, vlaue):
            print('Set gpio {0}; Value: {1};'.format(io, vlaue))

    GPIO = FakeGPIO()


''' Temperature sensor wrapper. Gets temperature readings form file.
'''
def goto(linenum):
        global line
        line = linenum
        
def millis():
    return long(round(time.time() * 1000))    
    
	
class SampleHandler(Handler):
    INTERVAL_SECONDS = 2

    def __init__(self, api, device_id=DEVICE_ID):
        super(SampleHandler, self).__init__(api)
        self._device_id = device_id
        self._device = None
       
        self._scheduler = sched.scheduler(time.time, time.sleep)
        print('DeviceId: ' + self._device_id)
        pioggia = False
        GPIO.setup(DO, GPIO.IN)
        GPIO.setup(D1, GPIO.OUT)
        GPIO.output(D1, GPIO.LOW)        
        

    def _timer_loop(self):
        sensorValueRain = GPIO.input(DO) #Legge il valore digitale
        print (sensorValueRain) #Stampa a schermo il valore
        if sensorValueRain == 0:
                               return;
                               #sta piovendo
        
        umiditaIniziale = sensorValueHumidity = GPIO.input(DO) #Legge il valore digitale
        print (sensorValueHumidity) #Stampa a schermo il valore
        if sensorValueHumidity ==0:
                                    # gia umido
                                    return
        

        STARTINGTIME = millis()
        TIMEOUTWATER =STARTINGTIME+ INTERVAL
        TIMEWATER=0
        START_TIMEWATER=millis()
        pioggia = False
        print( "inizioInnaffiamento")

        GPIO.output(D1, GPIO.HIGH)
        while ((millis() - STARTINGTIME )<= (TIMEOUTWATER -STARTINGTIME)) :
           sensorValueRain =  GPIO.input(DO) #Legge il valore digitale

           if sensorValueRain ==0 :
                print ("stop innaffiamento")
                GPIO.output(D1, GPIO.LOW)

                START_TIMEWATER = millis()
                while (sensorValueRain ==0 and (millis()- STARTINGTIME )<=( TIMEOUTWATER-STARTINGTIME)) :#sta piovendo e non e finito il tempo di innaf.
                    sensorValueRain = GPIO.input(DO)
        
                if (sensorValueRain ==1 and 	(millis() -STARTINGTIME) <= (TIMEOUTWATER-STARTINGTIME )):# non sta piovendo piu ma non e finito il tempo di innaf.
                  print ("ReInizio innaffiamento")
                  TIMEWATER += millis() - START_TIMEWATER
                  pioggia = True
 
                  goto(115)

        
                elif (sensorValueRain == 0 and (millis() - STARTINGTIME) > (TIMEOUTWATER-STARTINGTIME)) : # sta piovendo ma e finito il tempo
                  TIMEWATER += millis() - START_TIMEWATER
                  pioggia = True
                  GPIO.output(D1, GPIO.LOW)

                  break;
        
           else :
    
			  			  if((millis() - STARTINGTIME )>(TIMEOUTWATER -STARTINGTIME)):
							TIMEWATER += millis() - START_TIMEWATER

							#non sta piovendo ed e finito il tempo
							pioggia = False
							GPIO.output(D1, GPIO.LOW) 
							break;

        
        
        
        GPIO.output(D1, GPIO.LOW)
        p=False
        umiditaFinale =  GPIO.input(DO)
        if (pioggia):
          p = True
        else:
          p = False


        print (data);
       
        self._device.send_notification('data', parameters={'pioggia':p, 'durataInnaffiamento':str(TIMEWATER),
        'umiditaIniziale':str(umiditaIniziale), 'umiditaFinale':str(umiditaFinale)})
        self._scheduler.enter(self.INTERVAL_SECONDS, 1, self._timer_loop, ())

    def handle_connect(self):
        self._device = self.api.put_device(self._device_id)
        self._device.subscribe_insert_commands()
        print('Connected')
        self._timer_loop()
        t = threading.Thread(target=self._scheduler.run)
        t.setDaemon(True)
        t.start()

    def handle_command_insert(self, command):
        if command.command == 'led/on':
            GPIO.output(LED_PIN, 1)
            command.status = "Ok"
        elif command.command == 'led/off':
            GPIO.output(LED_PIN, 0)
            command.status = "Ok"
        else:
            command.status = "Unknown command"
        command.save()


dh = DeviceHive(SampleHandler)
dh.connect(SERVER_URL, refresh_token=SERVER_REFRESH_TOKEN)
