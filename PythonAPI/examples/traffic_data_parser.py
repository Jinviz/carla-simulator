import xml.etree.ElementTree as ET
import re
import time
import os

class PaseTrafficXmlData:
    def __init__(self, file_name, index):
        # self.tree = ET.parse('./traffic_data/'+file_name)
        self.tree = ET.parse(file_name)
        # self.group_num =int(file_name[0:2])
        self.group_num = index
        self.root = self.tree.getroot()
        self.Traffic_Signal_Controller =[]
        self.Meta=[]
        self.TrafficPhases=[]
        self.TrafficPhase_list=[]
        self.Duration=[]
        #self.State = {}
        self.State_list=[]
        self.TrafficLights=[]

        for child in self.root:
            self.Traffic_Signal_Controller.append(child) # Meta, TrafficPhases 구분

        for i in self.Traffic_Signal_Controller[0]:
            self.Meta.append(i)                      #Name , Version, RoadType, Location, TrafficLights구분


        for i in self.Traffic_Signal_Controller[1]:
            self.TrafficPhases.append(i)             #phase 구분
            self.Duration.append(int(i.attrib.get("Duration"))) #phase별 Duration 가져오기

        for TrafficLights in self.Meta[4]:
            self.TrafficLights.append(TrafficLights.attrib.get("TrafficSignalID"))


        for idx in range(len(self.TrafficPhases)):
            State={}
            cnt=0
            for TrafficPhase in self.TrafficPhases[idx]:
                State[TrafficPhase.attrib.get("TrafficSignalID")]=TrafficPhase.attrib.get('State') #ID에 해당하는 State Dict
                cnt=cnt+1
                if cnt == len(self.Meta[4]):
                    self.State_list.append(State)


