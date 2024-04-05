#!/usr/bin/python3

mq_host = "localhost"
mq_chan = "rpi4-001101"
THRESH_L=5 #currently set to THRESH*avgerage_of_array(avg_prev).Can be std/pstd
THRESH_H=5000 #removes erroneous sensor spikes as normals readings are max 1000

import paho.mqtt.client as mqtt
import signal,errno,sys,time,os
import psutil #pip3 install psutil for rpi: pip-3.2 install psutil worked
import json, pyaudio, wave
from datetime import datetime
import math 
import statistics as st
import numpy as np
from gpiozero import CPUTemperature

###### Functions #######
def signal_handling(signum,frame):           
    global terminate                         
    terminate = True                         
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(mq_chan)
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("msg received")
    #print("msg topic: "+msg.topic+" msg: "+str(msg.payload))
def on_publish(client,userdata,result): #create function for callback
    print("data published \n")
    pass
def RMS(lst):
    squared_sum = sum([num**2 for num in lst])
    return math.sqrt(squared_sum/len(lst))
def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()
def readSoundcard(stream):
    data = stream.read(CHUNK,exception_on_overflow=False)
    decoded = wave.struct.unpack("%dh"%(CHUNK),data) #tuple
    #decoded = wave.struct.unpack("%iB"%(CHUNK),data) #tuple
    suba = [[i] for i in decoded] #convert to sublist as tuples can't be del
    a_flt = [item for sublist in suba for item in sublist] #flatten it
    a = [abs(ele) for ele in a_flt] #convert to absolute values
    return(a)
def get_cpu_temp():
    cpu = CPUTemperature()
    return cpu.temperature
#######################

sys.path.append('/home/src/mqtt') # if modules ever get put here

terminate = False                            

client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.on_publish = on_publish 
client.connect(mq_host, 1883, 60)
client.loop_start()
time.sleep(1)

signal.signal(signal.SIGINT,signal_handling) 

######## Soundcard read setup #############
FORMAT = pyaudio.paInt16
SAMPLEFREQ = 44100 #lowest valid sample frequency
FRAMESIZE = 1024 #number of values in the decoded list
NOFFRAMES = 640 #approx 14.86 sec of data capture 
#NOFFRAMES = 100  
CHUNK = FRAMESIZE*NOFFRAMES
DEV_INDEX = 1 # mic one
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,channels=1,rate=SAMPLEFREQ,input=True,input_device_index = DEV_INDEX,frames_per_buffer=FRAMESIZE)
a=[]
#######################################
x=1                                          
while True:                                  
    if terminate: 
        print("Oh-o gotta go...")
        break 

    #print("Processing #",x,"started...")

    # Create message
    myts=str(int((time.time() + 0.5) * 1000))
    mydev="\""+str(os.uname()[1])+"\""

    a=readSoundcard(stream) #load mic readings in a[]
    mysen=json.dumps(a) #message type 1 with full array sent
    print("size of full message array a:",len(a))

    # Some calcs for msg option 2
    a_dict = {}
    std_a = (st.stdev(a)+0.0)
    avg_a = (st.mean(a)+0.0)
    med_a = (st.median(a)+0.0)
    max_a = (max(a)+0.0)
    smax_a = (softmax(a)+0.0) #outputs array can't go st into dict
    a_sorted = sorted(a,reverse=True) # then pick first say N items
    #rmstN_a = RMS(a_sorted[:20]) #use RMS value
    #rmstN_a = st.median(a_sorted[:20]) #look for central value in high end
    #rmstN_a = min(a_sorted[:20]) #take the least of top N values
    rmstN_a = get_cpu_temp() # get rpi4's cpu temperature for ambient temp
    for variable in ["std_a","rmstN_a","avg_a","med_a","max_a"]:
        a_dict[variable] = eval(variable)
    #Create version 2 message
    mysen2=json.dumps(a_dict)
 
    #Assembled MQTT message (ready to send):
    #msg='{"ts":'+myts+',"dev":'+mydev+',"mag":'+mysen+'}'
    msg='{"ts":'+myts+',"dev":'+mydev+',"mag":'+mysen2+'}'
    avg_prev=avg_a
    #sys.exit("debug exit")


    # Filter out usual low end noise
    #if (max_a < THRESH_L*avg_prev) or (max_a > THRESH_H): #don't want an error spike
       #print("low max_a:",max_a,"for avg_prev:",avg_prev,"pstedev:",std_a,datetime.fromtimestamp(int(myts)/1000).strftime("%H:%M:%S"))
    #   del a[:]
    #   continue

    ret=client.publish(mq_chan,msg,qos=2)
    #print(msg,"prevAvg:",int(avg_prev+0.5),"max:",max(a))
    #print("(STATUS,#):",ret,"Std:",int(std_a+.5),"Avg:",int(avg_prev+0.5),
    #  "max:",max_a,"ts:",
    #   datetime.fromtimestamp(int(myts)/1000).strftime("%H:%M:%S"),"len:",len(a))
    print("(STATUS,#)",ret,msg,
          datetime.fromtimestamp(int(myts)/1000).strftime("%H:%M:%S"))
    #time.sleep(20)
    del a[:]
    x+=1 
    if terminate: 
        print("Oh-o gotta go...")
        break 
print("Cya")
print("iters: ",x)
stream.stop_stream()
stream.close()
p.terminate()
client.loop_stop()
#1 For wave unpack denisb411/plot_mic_fft.py :
# https://gist.github.com/denisb411/cbe1dce9bc01e770fa8718e4f0dc7367
