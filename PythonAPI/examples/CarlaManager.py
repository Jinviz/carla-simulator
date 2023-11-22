import glob
import os
import sys
import argparse
import logging

from Data.weather_data import UI_DATA
import Data.ui_input_module as ui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic, QtWidgets
import WeatherManager
import random
import time
import traffic_data_parser
import multiprocessing
import ego_vehicle_control as EgoVehicle

try:
    # 파이썬에서 참조할 모듈의 경로 및 설정
    sys.path.append(glob.glob('carla-0.9.11*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])

except IndexError:
    pass

import carla
from carla import VehicleLightState as vls


# UI파일 연결
# 단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.
form_class = uic.loadUiType("Carla_UI.ui")[0]

class NPC_Manager(object):

    def __init__(self, world, client, args, target, carla_package):
        """
        :param world:
        :param client:
        :param args:
        :param target:
        :param carla_package: [SpawnActor, SetAutopilot, SetVehicleLightState, FutureActor, DestroyActor]
        """
        self.world = world
        self.client = client
        self.args = args
        self.target = target
        self.vehicles_list = []
        self.walkers_list = []
        self.all_id = []
        self.carla_package = carla_package
        self.synchronous_master = False


        # Traffic Manager Init
        self.traffic_manager = client.get_trafficmanager(self.args.tm_port)
        self.traffic_manager.set_global_distance_to_leading_vehicle(1.0)    #차량과 차량 사이의 거리 미터단위
        if self.args.hybrid:
            self.traffic_manager.set_hybrid_physics_mode(True)

        if self.args.sync:
            settings = self.world.get_settings()
            self.traffic_manager.set_synchronous_mode(True)
            if not settings.synchronous_mode:   #클라이언트와 서버 간의 동기화
                self.synchronous_master = True
                settings.synchronous_mode = True    #true 설정 틱을 기다림
                settings.fixed_delta_seconds = 0.05 #서버(언리얼)와 클라이언트(메뉴얼컨트롤) 사이의 시간
                self.world.apply_settings(settings)
            else:
                self.synchronous_master = False

        # Blueprint Setting
        _blueprints = self.world.get_blueprint_library().filter("vehicle.*")    #액터 블루프린트를 월드에 쉽게 스폰하는데 사용할 수 있는 액터 블루프린트 목록 반환
        self.blueprintsWalkers = self.world.get_blueprint_library().filter("walker.pedestrian.*")   #필터를 통해 일치하는 액터 목록을 매칭 * << 모든 것과 일치

        self.blueprints = [x for x in _blueprints if int(x.get_attribute('number_of_wheels')) == 4 if   #get_attribute() : 액터의 속성 반환
                           not x.id.endswith('cybertruck') if not x.id.endswith('carlacola')]   #endswith() : 접미사로 찾기
        self.spawn_points = self.world.get_map().get_spawn_points() #get_map() : 서버에 맵 파일이 포함된 xodr을 요청하고 이를 carla.map으로 구문 분석하여 반환
        # get_spawn_points() : 차량의 스폰 지점으로 사용할 지도 작성자의 권장 사항 목록을 반환
        self.number_of_spawn_points = len(self.spawn_points)

    #ui npc 숫자 입력 함수
    def ui_world_npc_walker(self, input_number):
        SpawnActor = self.carla_package[0]
        DestroyActor = self.carla_package[4]


        if len(self.walkers_list) >= 1:  # 생성된 워커 제거
            self.client.apply_batch([DestroyActor(x) for x in self.all_id])
            self.all_id = []
            self.walkers_list = []
            time.sleep(0.5) #time라이브러리를 사용하여 프로세스 0.5초 일시정지

        if input_number > 0:
            percentagePedestriansRunning = 0.0  # how many pedestrians will run
            percentagePedestriansCrossing = 0.0  # how many pedestrians will walk through the road

            # 1. take all the random locations to spawn
            spawn_points = []
            for i in range(input_number):
                spawn_point = carla.Transform()
                loc = self.world.get_random_location_from_navigation() #여기서안됨
                if (loc != None):
                    spawn_point.location = loc
                    spawn_points.append(spawn_point)

            # 2. we spawn the walker object
            batch = []
            walker_speed = []
            for spawn_point in spawn_points:
                walker_bp = random.choice(self.blueprintsWalkers)
                # set as not invincible
                if walker_bp.has_attribute('is_invincible'):
                    walker_bp.set_attribute('is_invincible', 'false')
                # set the max speed
                if walker_bp.has_attribute('speed'):
                    if (random.random() > percentagePedestriansRunning):
                        # walking
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
                    else:
                        # running
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])
                else:
                    print("Walker has no speed")
                    walker_speed.append(0.0)
                batch.append(SpawnActor(walker_bp, spawn_point))
            results = self.client.apply_batch_sync(batch, True)
            walker_speed2 = []
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    self.walkers_list.append({"id": results[i].actor_id})
                    walker_speed2.append(walker_speed[i])
            walker_speed = walker_speed2
            # 3. we spawn the walker controller
            batch = []
            walker_controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
            for i in range(len(self.walkers_list)):
                batch.append(SpawnActor(walker_controller_bp, carla.Transform(), self.walkers_list[i]["id"]))
            results = self.client.apply_batch_sync(batch, True)
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    self.walkers_list[i]["con"] = results[i].actor_id
            # 4. we put altogether the walkers and controllers id to get the objects from their id
            for i in range(len(self.walkers_list)):
                self.all_id.append(self.walkers_list[i]["con"])
                self.all_id.append(self.walkers_list[i]["id"])
            all_actors = self.world.get_actors(self.all_id)

            if not self.args.sync or not self.synchronous_master:
                self.world.wait_for_tick()
            else:
                self.world.tick()

            # 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
            # set how many pedestrians can cross the road
            self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
            for i in range(0, len(self.all_id), 2):
                # start walker
                all_actors[i].start()
                # set walk to random point
                all_actors[i].go_to_location(self.world.get_random_location_from_navigation())
                # max speed
                all_actors[i].set_max_speed(float(walker_speed[int(i / 2)]))

            # wait for a tick to ensure client receives the last transform of the walkers we have just created


            print('spawned %d walkers, press Ctrl+C to exit.' % (len(self.walkers_list)))
    #npc차량설정
    def ui_world_npc_vehicle(self, input_number):
        SpawnActor = self.carla_package[0]
        SetAutopilot = self.carla_package[1]
        SetVehicleLightState = self.carla_package[2]    #차량조명상태설정
        FutureActor = self.carla_package[3]
        DestroyActor = self.carla_package[4]

        if len(self.vehicles_list) >= 1:  # 생성된 차량 제거
            self.client.apply_batch([DestroyActor(x) for x in self.vehicles_list])  #차량의 리스트 갯수만큼 반복해서 차량제거
            self.vehicles_list = [] #차량제거 후 리스트 비우기
            time.sleep(0.5) #0.5초 일시정지

        if input_number > 0:
            # --------------
            # Spawn vehicles
            # --------------

            for n, transform in enumerate(self.spawn_points):
                batch = []

                if n >= input_number:
                    break
                blueprint = random.choice(self.blueprints)
                if blueprint.has_attribute('color'):    #블루프린트 안에 color
                    color = random.choice(blueprint.get_attribute('color').recommended_values)  #랜덤 색깔 반환
                    blueprint.set_attribute('color', color) #색깔 설정
                if blueprint.has_attribute('driver_id'):
                    driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                    blueprint.set_attribute('driver_id', driver_id)
                blueprint.set_attribute('role_name', 'autopilot')

                # prepare the light state of the cars to spawn 스폰할 자동차의 조명 상태를 준비합니다
                light_state = vls.NONE
                # autopilot vehicle right on
                light_state = vls.Position | vls.LowBeam | vls.LowBeam

                # spawn the cars and set their autopilot and light state all together
                batch.append(SpawnActor(blueprint, transform)
                             .then(SetAutopilot(FutureActor, True, self.traffic_manager.get_port()))
                             .then(SetVehicleLightState(FutureActor, light_state)))

                for response in self.client.apply_batch_sync(batch, self.synchronous_master):
                    if response.error:
                        logging.error(response.error)
                    else:
                        self.traffic_manager.global_percentage_speed_difference(10.0)  # 제한 속도의 10% 속도로 주행
                        self.vehicles_list.append(response.actor_id)

            time.sleep(0.5)
            print('spawned %d vehicle, press Ctrl+C to exit.' % (len(self.vehicles_list)))


# 화면을 띄우는데 사용되는 Class 선언
class WindowClass(QMainWindow, form_class):
    def __init__(self, ui_data):
        super().__init__()
        self.ui_data = ui_data
        self.setupUi(self)

        # Variable for vehicle settings
        self.player = list()
        self.process = list()
        self.queue = list()
        self.player_info = list()  # player 정보 string

        # Variable for vehicle location viewing
        self.location = list()  # 각 차량의 위치 정보
        for n in range(99):
            self.location.append(list())
        self.timerVar = QTimer()  # 차량 위치 주기적 출력을 위한 QTimer 클래스 인스턴스
        self.timerVar.setInterval(1000)  # 주기적 출력의 인터벌 설정
        self.timerVar.timeout.connect(self.location_monitoring)  # 인터벌마다 출력 함수 호출
        self.timerVar.start()

        # Variable for traffic sign data
        self.data_list = list()  # 신호등 데이터 파일 리스트
        self.xml_data = list()
        self.trafficLightDict = list()
        self.Before_traffic_group = list()
        self._tls = dict()
        self.Is_In_group = dict()
        self.Result_Tl_Group = list()
        self.traffic_list = list()

        # -- 1. Setting
        # 차량 모니터
        self.VehicleTextBrowser.append('')
        # 선택 차량 경로 설정
        self.pushButton_route_Vehicle.clicked.connect(lambda: self.route_settings("Route"))   # 경로 설정 차량 소환
        self.pushButton_autopilot_vehicle.clicked.connect(lambda: self.route_settings("Autopilot"))
        # 경로설정 & 초기화
        self.pushButton_spawn_Vehicle.clicked.connect(lambda: self.set_vehicle("Spawn"))   # 경로 설정 차량 소환
        self.pushButton_initialize_Vehicle.clicked.connect(lambda: self.set_vehicle("Initialize"))  # 경로 설정 차량 제거

        # -- 2. Location
        # 위치 모니터
        self.LocationTextBrowser.append('')
        # 이전 & 다음
        self.LocationComboBox.currentIndexChanged.connect(self.change_monitoring)

        # -- 3. Traffic sign
        # 신호 모니터
        self.trafficSignTextBrowser.append('')
        # 추가 & 초기화
        self.pushButton_add_Sign.clicked.connect(lambda: self.set_traffic_sign("Add"))
        self.pushButton_apply_Sign.clicked.connect(lambda: self.set_traffic_sign("Apply"))
        self.pushButton_remove_Sign.clicked.connect(lambda: self.set_traffic_sign("Remove All"))

        # -- 4. Configuration
        # NPC 설정
        self.pushButton_NPC_Spawn.clicked.connect(self.NPC_Spawn)

        # 시간 변경 radio 버튼
        self.radioButton_1.clicked.connect(self.groupbox_Time_Function)
        self.radioButton_2.clicked.connect(self.groupbox_Time_Function)
        self.radioButton_3.clicked.connect(self.groupbox_Time_Function)

        # 날씨 번경 Slider and checkbox
        self.horizontalSlider_fog.sliderReleased.connect(self.show_Slider_weather)
        self.horizontalSlider_rain.sliderReleased.connect(self.show_Slider_weather)
        self.horizontalSlider_wind.sliderReleased.connect(self.show_Slider_weather)
        self.horizontalSlider_clouds.sliderReleased.connect(self.show_Slider_weather)

        # Carla Init
        argparser = argparse.ArgumentParser(description="설정값")
        argparser.add_argument(
            '--hybrid',
            action='store_true',
            help='Enanble')
        argparser.add_argument(
            '--sync',
            action='store_true',
            help='Synchronous mode execution')
        argparser.add_argument(
            '--host',
            metavar='H',
            default='127.0.0.1',
            help='호스트 서버의 아이피 주소 입력.')
        argparser.add_argument(
            '--port',
            metavar='P',
            default=2000,
            type=int,
            help='호스트 서버의 TCP포트 입력.')
        argparser.add_argument(
            '--tm-port',
            metavar='P',
            default=8000,
            type=int,
            help='트래픽매니저 전용 rpc 포트 (default: 8000)')
        argparser.add_argument(
            '-t', '--target_id',
            metavar='N',
            default=0,
            type=int,
            help='센서수집을 위한 대상 차량 actor_id')
        argparser.add_argument(
            '-v', '--verbose',
            action='store_true',
            dest='debug',
            help='Print debug information')
        argparser.add_argument(
            '--res',
            metavar='WIDTHxHEIGHT',
            default='1280x720',
            help='Window resolution (default: 1280x720)')
        argparser.add_argument(
            '--filter',
            metavar='PATTERN',
            default='vehicle.*',
            help='Actor filter (default: "vehicle.*")')
        argparser.add_argument(
            '--generation',
            metavar='G',
            default='2',
            help='restrict to certain actor generation (values: "1","2","All" - default: "2")')
        argparser.add_argument(
            '-l', '--loop',
            action='store_true',
            dest='loop',
            help='Sets a new random destination upon reaching the previous one (default: False)')
        argparser.add_argument(
            "-a", "--agent", type=str,
            choices=["Behavior", "Basic", "Constant"],
            help="select which agent to run",
            default="Basic")
        argparser.add_argument(
            '-b', '--behavior', type=str,
            choices=["cautious", "normal", "aggressive"],
            help='Choose one of the possible agent behaviors (default: normal) ',
            default='normal')
        argparser.add_argument(
            '-s', '--seed',
            help='Set seed for repeating executions (default: None)',
            default=None,
            type=int)

        self.args = argparser.parse_args()
        self.args.width, self.args.height = [int(x) for x in self.args.res.split('x')]

        log_level = logging.DEBUG if self.args.debug else logging.INFO
        logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

        logging.info('listening to server %s:%s', self.args.host, self.args.port)
        print(self.args.target_id)

        # @todo cannot import these directly.
        SpawnActor = carla.command.SpawnActor
        SetAutopilot = carla.command.SetAutopilot
        SetVehicleLightState = carla.command.SetVehicleLightState
        FutureActor = carla.command.FutureActor
        DestroyActor = carla.command.DestroyActor

        self.carla_package = [SpawnActor, SetAutopilot, SetVehicleLightState, FutureActor, DestroyActor]

        self.client = carla.Client(self.args.host, 2000)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.map = self.world.get_map()
        self.target = self.world.get_actor(self.args.target_id)  # 타겟 차량 Actor_id
        self._weather = WeatherManager.Weather(self.world.get_weather(), self.world)
        self._npc = NPC_Manager(self.world, self.client, self.args, self.target, self.carla_package)
        self._sun_set = None
        self._weather_set = None

    def set_vehicle(self, btn):
        if btn == "Spawn":
            queue = multiprocessing.Queue()
            self.process.append(multiprocessing.Process(target=EgoVehicle.game_loop, args=(self.args, queue)))
            self.process[-1].start()
            self.queue.append(queue)

            player_id = self.queue[-1].get()  # 소환된 차량 id 공유 메모리를 통해 접근
            player = self.world.get_actor(player_id)  # 차량 id로 월드에 있는 차량 정보 반환
            self.player.append(player)  # 차량 정보
            self.player_info.append(str(self.player[-1]))  # 차량 정보 문자열
            self.LocationComboBox.addItem(self.player_info[-1])
            self.SelectVehicleComboBox.addItem(self.player_info[-1])

        # 초기화 버튼이 눌렸을 때
        elif btn == "Initialize":
            for n, process in enumerate(self.process):
                process.terminate()
                self.player[n].destroy()

            self.player.clear()
            self.process.clear()
            self.queue.clear()
            self.player_info.clear()

            self.SelectVehicleComboBox.clear()
            self.LocationComboBox.clear()

        # 스폰된 차량 리스트 출력
        self.VehicleTextBrowser.clear()
        for info in self.player_info:
            self.VehicleTextBrowser.append(info)

    def route_settings(self, btn):
        select = self.SelectVehicleComboBox.currentIndex()  # 콤보박스에서 선택된 차량 인덱스

        if btn == "Route":
            # 적용 버튼이 눌렸을 때
            filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')
            coords = []  # 파싱 데이터를 저장하기 위한 리스트 생성
            if filename[0]:
                print("파일 위치: ", filename[0])
                with open(filename[0], 'r') as f:
                    route_data = f.read()
                    print("##### 업로드된 경로 파일 ##### \n", route_data)

                data = route_data.split("),(")  # 각 좌표의 구분
                for crds in data:
                    crds = crds.replace("(", "").replace(")", "")  # 첫번째 좌표와 마지막 좌표 데이터 처리
                    parts = crds.split(",")  # 각 좌표의 xyz 요소 구분
                    if len(parts) == 3:
                        coords.append((float(parts[0]), float(parts[1]), float(parts[2])))
                        print("경로가 설정되었습니다")
                    else:
                        print("데이터 형식이 잘못되었습니다")

                self.queue[select].put(coords)

            else:
                print("경로가 설정되지 않았습니다")

        elif btn == "Autopilot":
            self.queue[select].put("Autopilot Mode")

    def change_monitoring(self):
        index = self.LocationComboBox.currentIndex()
        if index != -1:
            self.LocationTextBrowser.clear()
            location = self.location[index]
            for xyz in location:
                self.LocationTextBrowser.append(xyz)

    # 차량 위치 모니터링
    def location_monitoring(self):
        # 플레이어의 주행 위치 정보 저장 리스트
        for n in range(len(self.player)):
            location = str(self.player[n].get_location())
            x_val = location.split('x=')[1].split(',')[0]
            y_val = location.split('y=')[1].split(',')[0]
            z_val = location.split('z=')[1].split(')')[0]
            f_location = f"x={x_val}, y={y_val}, z={z_val}"

            self.location[n].append(f_location)

        index = self.LocationComboBox.currentIndex()

        # 위치 정보 모니터 출력
        if index != -1:
            self.LocationTextBrowser.append(self.location[index][-1])

        else:
            self.LocationTextBrowser.clear()


    def set_traffic_sign(self, btn):
        # 추가 버튼이 눌렸을 때
        if btn == "Add":
            add_file = QtWidgets.QFileDialog.getOpenFileNames(self, 'Select one or more files to open', "", "*.xml")[0]
            if add_file:
                self.data_list.extend(add_file)
                self.trafficSignTextBrowser.clear()
                for data in self.data_list:
                    self.trafficSignTextBrowser.append(data)
                    self.trafficSignTextBrowser.append('')

        # 적용 버튼이 눌렸을 때
        elif btn == "Apply":
            for count, i in enumerate(self.data_list):   # count(=index)값 추가
                self.xml_data.append(traffic_data_parser.PaseTrafficXmlData(i, count))  # XmlData Paser 객체들
            group_per_duration = []
            for i in self.xml_data:
                group_per_duration.append(i.Duration)
            for i in self.xml_data:
                for j in i.State_list:
                    print(j)
            for i in group_per_duration:
                print(i)

            ############### Get Traffic Light Group & TrafficLights  ######################
            try:
                for landmark in self.map.get_all_landmarks_of_type('1000001'):
                    if landmark.id != '':
                        traffic_light = self.world.get_traffic_light(landmark)
                        if traffic_light is not None:
                            self._tls[landmark.id] = traffic_light
                        else:
                            logging.warning('Landmark %s is not linked to any traffic light', landmark.id)
                self.traffic_list = list(self._tls.values())
                for i in range(len(self.traffic_list)):
                    self.Before_traffic_group.append(list(self.traffic_list[i].get_group_traffic_lights()))
                for i in self.traffic_list:
                    self.Is_In_group[str(i)] = False
                for traffic in self.traffic_list:
                    str_traffic = str(traffic)
                    for group in self.Before_traffic_group:
                        for idx in range(len(group)):
                            if self.Is_In_group[str_traffic] == True:
                                break
                            if str_traffic == str(group[idx]):
                                for group_idx in range(len(group)):
                                    self.Is_In_group[str(group[group_idx])] = True
                                self.Result_Tl_Group.append(traffic.get_group_traffic_lights())
                ##################################### Xml_Data_Parsing #################################################
                for idx, data in enumerate(self.xml_data):  # 1, 2, ... n번째 xml data
                    self.trafficLightDict.append({})
                    group_num = data.group_num
                    if group_num < len(self.Result_Tl_Group):  # 인덱스 범위 확인
                        for i in range(len(self.Result_Tl_Group[group_num])):
                            self.trafficLightDict[idx][data.TrafficLights[i]] = self.Result_Tl_Group[group_num][i]
                for group in self.Result_Tl_Group:
                    for j in group:
                        j.set_state(carla.TrafficLightState.Red)
                if self.trafficLightDict[0]:
                    first_traffic_light = list(self.trafficLightDict[0].values())[0]
                    first_traffic_light.freeze(True)  # TrafficLight 객체의 freeze 함수를 True로 설정
                self.trafficSignTextBrowser.append("# ======================================")
                self.trafficSignTextBrowser.append("# -- Xml Parsing Success----------------")
                self.trafficSignTextBrowser.append("# ======================================")

            except ValueError as ve:
                # ValueError 예외를 처리하는 코드
                print("ValueError occurred: ", ve)
                self.trafficSignTextBrowser.append("# ValueError occurred: ", ve)
            except FileNotFoundError as fne:
                # FileNotFoundError 예외를 처리하는 코드
                print("FileNotFoundError occurred: ", fne)
                self.trafficSignTextBrowser.append("# FileNotFoundError occurred: ", fne)
            except Exception as e:
                # 기타 모든 예외를 처리하는 코드
                print("Some other Exception occurred: ", e)
                self.trafficSignTextBrowser.append("# Some other Exception occurred: ", e)

        # 초기화 버튼이 눌렸을 때
        elif btn == "Remove All":
            self.data_list = []  # 신호등 데이터 파일 리스트
            self.xml_data = []
            self.trafficLightDict = []
            self.Before_traffic_group = []
            self._tls = {}
            self.Is_In_group = {}
            self.Result_Tl_Group = []
            self.traffic_list = []
            self.trafficSignTextBrowser.clear()

    # NPC 버튼 클릭 후 값 가져오기
    def NPC_Spawn(self):
        people = int(self.Edit_People.text())
        vehicle = int(self.Edit_Vehicle.text())
        self.ui_data.set_NPC_Spawn(people, vehicle)
        self._npc.ui_world_npc_vehicle(self.ui_data.A_vehicle)
        self._npc.ui_world_npc_walker(self.ui_data.A_people)
        print("Spawn Complete")

    # 시간 변경 radio 버튼 함수
    def groupbox_Time_Function(self):
        elapsed_time = 0
        if self.radioButton_1.isChecked():
            self.ui_data.B_sun_type = "midday"
        elif self.radioButton_2.isChecked():
            self.ui_data.B_sun_type = "sunset"
        elif self.radioButton_3.isChecked():
            self.ui_data.B_sun_type = "midnight"
        self._weather_set = ui.UI_INPUT_CONTROL().return_weather(clouds=self.ui_data.C_cloud, rain=self.ui_data.C_rain,
                                                                 wetness=self.ui_data.C_rain * 5,
                                                                 puddles=self.ui_data.C_rain, wind=self.ui_data.C_wind,
                                                                 fog=self.ui_data.C_fog)
        self._sun_set = ui.UI_INPUT_CONTROL().return_sun_type(sun_type=self.ui_data.B_sun_type)
        timestamp = self.world.wait_for_tick().timestamp
        elapsed_time += timestamp.delta_seconds
        self._weather.tick(elapsed_time, self._weather_set, self._sun_set)

    # 날씨 번경 Slider
    def show_Slider_weather(self):
        elapsed_time = 0
        self.ui_data.C_fog = self.horizontalSlider_fog.value()
        self.ui_data.C_rain = self.horizontalSlider_rain.value()
        self.ui_data.C_wind = self.horizontalSlider_wind.value()
        self.ui_data.C_cloud = self.horizontalSlider_clouds.value()
        self._weather_set = ui.UI_INPUT_CONTROL().return_weather(clouds=self.ui_data.C_cloud, rain=self.ui_data.C_rain,
                                                                 wetness=self.ui_data.C_rain * 5,
                                                                 puddles=self.ui_data.C_rain, wind=self.ui_data.C_wind,
                                                                 fog=self.ui_data.C_fog)
        self._sun_set = ui.UI_INPUT_CONTROL().return_sun_type(sun_type=self.ui_data.B_sun_type)
        timestamp = self.world.wait_for_tick().timestamp
        elapsed_time += timestamp.delta_seconds
        self._weather.tick(elapsed_time, self._weather_set, self._sun_set)




if __name__ == "__main__":
    ui_data = UI_DATA()
    app = QApplication(sys.argv)
    myWindow = WindowClass(ui_data)
    myWindow.show()
    app.exec_()
