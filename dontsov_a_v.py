# -*- coding: utf-8 -*-

import math

from astrobox.core import Drone, GameObject
from robogame_engine.geometry import Point, Vector

from hangar_2021.dontsov_a_v_package import HEALING_DISTANCE, FIELD_HEIGHT, FIELD_WIDTH, RADIUS_ATTACK, \
    DefenderStrategy, SabotageStrategy, HarvestStrategy, LastBattleStrategy


class DontsovDrone(Drone):
    """
    Дочерний класс Drone
    """
    command_center = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strategy = None
        self.target_attack = None
        self.start_position = None
        self.target_move = None

    def on_born(self):
        if DontsovDrone.command_center is None:
            DontsovDrone.command_center = CommandCenter(my_mothership=self.my_mothership, space_field=self.scene)
        self.command_center.run(drone=self)
        self.next_action()

    def on_stop_at_asteroid(self, asteroid):
        self.next_action()

    def on_stop_at_point(self, target):
        self.next_action()

    def on_load_complete(self):
        self.next_action()

    def on_stop_at_mothership(self, mothership):
        self.next_action()

    def on_unload_complete(self):
        self.next_action()

    def on_wake_up(self):
        self.strategy.action()

    def on_heartbeat(self):
        self.next_action()

    def next_action(self):
        self.command_center.analyzing(drone=self)
        self.strategy.action()


class CommandCenter:
    """
    Класс выбора стратегии дрона в зависимости от событий.
    """
    def __init__(self, my_mothership, space_field):
        self.space_field = space_field
        self.my_mothership = my_mothership
        self.init_strategy = HarvestStrategy
        self.sectors = None
        self.total_ellirium = 0
        self.events = [
            self.harvest_in_begin_event,
            self.harvest_in_alien_sector_event,
            self.home_under_threat_event,
            self.attack_sector_without_soldiers_event,
            self.attack_sector_without_base_event,
            self.attack_sector_without_defenders_event,
            self.knight_move_event,
            self.safe_harvest_event,
            self.attack_near_sector_with_risk_event,
        ]

    def run(self, drone):
        """
        Уставновление стартовой стратегии.
        """
        self.start_navigation()
        drone.strategy = self.init_strategy(drone=drone)
        self.total_ellirium = sum([asteroid.payload for asteroid in self.space_field.asteroids])

    def start_navigation(self):
        """
        Запуск навигации
        """
        self.sectors = self.get_sorted_sectors()

    def analyzing(self, drone):
        """
        Совешение действия дроном и выбор следующей стратегии.
        """
        next_strategy, strategy_param = self.get_next_strategy()
        self.transition_strategy(drone=drone, strategy=next_strategy, **strategy_param)

    def get_next_strategy(self):
        """
        Получение следующие стратегии.

        :return: tuple
        """
        for event in self.events:
            next_strategy_param = event()
            if next_strategy_param:
                return next_strategy_param
        else:
            return DefenderStrategy, {}

    def home_under_threat_event(self):
        """
        Событие, которые возвращает tuple с стратегией Обороны домашнего сектора.

        :return: tuple
        """
        enemy_drones = self.get_drones(filters=[self.get_enemy_drones, self.get_alive_obj])
        enemy_drones_in_radius_attack = [drone for drone in enemy_drones if self.is_base_radius_attack(drone)]
        if enemy_drones_in_radius_attack:
            return DefenderStrategy, {}

    def knight_move_event(self):
        """
        Событие, которые возвращает tuple с стратегией нападения по кромке карты.

        :return: tuple
        """
        enemy_sectors = [sector for sector in self.sectors if not sector['home_sector'] and not sector['front']]
        for sector in enemy_sectors:
            game_data = self.get_game_data()
            number_soldiers = next(
                (team['number_soldiers'] for team in game_data if team.get('team_name') == sector['team_name']), False)
            if sector['mothership']:
                if not sector['mothership'].is_alive and number_soldiers == 0:
                    front_sector = next((sector for sector in self.sectors if sector['front']), False)
                    if front_sector['mothership'] and front_sector['mothership'].is_alive:
                        enemy_defenders = self.get_base_defender(
                            team_name=front_sector['team_name'],
                            mothership=front_sector['mothership'],
                        )
                        if self.is_risk_game() or len(enemy_defenders) <= 1:
                            return SabotageStrategy, {
                                'sector': front_sector,
                                'start_sector': sector,
                                'base_attack': True
                            }

    def last_battle_event(self):  # не используется
        """
        Событие, которые возвращает tuple с стратегией Атаки дальнего сектора.

        :return: tuple
        """
        near_sectors = [sector for sector in self.sectors if not sector['front'] and not sector['home_sector']]
        near_motherships_alive = [
            sector['mothership'] for sector in near_sectors
            if sector['mothership'] and sector['mothership'].is_alive
        ]
        if len(near_motherships_alive) == 0:
            front_sector = next((sector for sector in self.sectors if sector['front']), False)
            if front_sector['mothership'] and front_sector['mothership'].is_alive:
                teammates = self.get_drones(filters=[self.get_alive_obj, self.get_team_drones])
                game_data = self.get_game_data()
                number_enemy_soldiers = next((
                    team['number_soldiers'] for team in game_data
                    if team.get('team_name') == front_sector['team_name']
                ), False)

                if self.is_risk_game() or number_enemy_soldiers + 3 <= len(teammates):
                    return LastBattleStrategy, {'sector': front_sector, 'base_attack': True}

    def attack_sector_without_soldiers_event(self):
        """
        Событие, которые возвращает tuple с стратегией Вторжения в боковой сектор, в котором дроны комманды уничтожены.

        :return: tuple
        """
        game_data = [
            team for team in self.get_game_data()
            if team['team_name'] != self.my_mothership.team and team['number_soldiers'] == 0
        ]
        front_sector = next((sector for sector in self.sectors if sector['front']), False)
        for team in game_data:
            if team['team_name'] != front_sector['team_name']:
                sector_attack = next(
                    (
                        sector for sector in self.sectors
                        if team['team_name'] == sector['team_name'] and sector['mothership'].is_alive
                    ),
                    False
                )
                if sector_attack:
                    return SabotageStrategy, {'sector': sector_attack, 'base_attack': True}

    def attack_sector_without_defenders_event(self):
        """
        Событие, которые возвращает tuple с стратегией Вторжения в боковой сектор,
        в котором дроны комманды не охраняют базу.

        :return: tuple
        """
        game_data = [
            team for team in self.get_game_data()
            if team['team_name'] != self.my_mothership.team and team['defenders'] == 0
        ]
        front_sector = next((sector for sector in self.sectors if sector['front']), False)
        for team in game_data:
            if team['team_name'] != front_sector['team_name']:
                sector_attack = next(
                    (
                        sector for sector in self.sectors
                        if team['team_name'] == sector['team_name'] and sector['mothership'].is_alive
                    ),
                    False
                )
                if sector_attack:
                    return SabotageStrategy, {'sector': sector_attack, 'base_attack': True}

    def attack_sector_without_base_event(self):
        """
        Событие, которые возвращает tuple с стратегией Вторжения в боковой сектор,
        чтобы добить дронов без базы.

        :return: tuple
        """
        enemy_sectors = [sector for sector in self.sectors if not sector['home_sector'] and not sector['front']]
        for sector in enemy_sectors:
            if sector['mothership'] and not sector['mothership'].is_alive:
                enemy_team_data = next(
                    (
                        team for team in self.get_game_data()
                        if team['team_name'] == sector['team_name'] and team['defenders'] != 0

                    ),
                    False
                )
                if enemy_team_data:
                    return SabotageStrategy, {'sector': sector, 'base_attack': True}

    def attack_near_sector_with_risk_event(self):
        """
        Событие, которые возвращает tuple с стратегией Вторжения в боковые сектора.

        :return: tuple
        """
        game_data = [
            team for team in self.get_game_data()
            if team['team_name'] != self.my_mothership.team
        ]
        game_data_sorted = sorted(game_data, key=lambda x: x['defenders'])
        front_sector = next((sector for sector in self.sectors if sector['front']), False)
        teammates = self.get_drones(filters=[self.get_alive_obj, self.get_team_drones])
        for team in game_data_sorted:
            if team['team_name'] != front_sector['team_name']:
                if team['defenders'] + 3 <= len(teammates) or self.is_risk_game():
                    sector_attack = next(
                        (
                            sector for sector in self.sectors
                            if team['team_name'] == sector['team_name'] and sector['mothership'].is_alive
                        ),
                        False
                    )
                    if sector_attack:
                        return SabotageStrategy, {'sector': sector_attack, 'base_attack': True}

    def harvest_in_alien_sector_event(self):
        """
        Событие, которые возвращает tuple с стратегией Сбора в чужих секторах.

        :return: tuple
        """
        enemy_sectors = [sector for sector in self.sectors if not sector['home_sector']]
        for sector in enemy_sectors:
            if self.get_objects_with_loot(sector=sector):
                if not sector['mothership']:
                    return HarvestStrategy, {'sector': sector}
                else:
                    team_name = sector['team_name']
                    game_data = self.get_game_data()
                    enemy_team = next((team for team in game_data if team.get('team_name') == team_name), False)
                    number_enemy_drones = enemy_team['number_soldiers']
                    if number_enemy_drones == 0:
                        return HarvestStrategy, {'sector': sector}

    def harvest_in_begin_event(self):
        """
        Событие, которые возвращает tuple с стратегией Сбора в начале игры.

        :return: tuple
        """
        if self.is_start_game():
            return HarvestStrategy, {}

    def safe_harvest_event(self):
        """
        Событие, которые возвращает dict с стратегией Сбора безупасного лута.

        :return: Dict
        """
        if self.get_objects_with_loot(safe_harvest=True):
            return HarvestStrategy, {'safe_harvest': True}

    def transition_strategy(self, drone, strategy, **kwargs):
        """
        Переход в новую стратегии или обновлении текущей стратегии.
        """
        if not isinstance(drone.strategy, strategy):
            drone.strategy = strategy(drone=drone, **kwargs)
        else:
            drone.strategy.update(**kwargs)

    def get_base_defender(self, team_name, mothership):
        """
        Получения списка дронов которые находятся в зоне хила у своей базы.

        :param team_name: str
        :param mothership: Mothership
        :return: List
        """
        enemy_drones = self.get_drones(filters=[self.get_alive_obj, self.get_enemy_drones])
        enemy_team = [drone for drone in enemy_drones if drone.set_team_name == team_name]
        base_defender = [drone for drone in enemy_team if drone.distance_to(mothership) <= HEALING_DISTANCE]
        return base_defender

    def get_sorted_sectors(self):
        """
        Возврат словаря с параметрами каждого сектора.

        :return: Dict
        """
        sectors = []
        vector_to_center = Vector.from_points(point1=self.my_mothership.coord, point2=self.point_center_field)
        direction_to_center = vector_to_center.direction
        diagonal = math.sqrt(FIELD_WIDTH ** 2 + FIELD_HEIGHT ** 2)
        vec = Vector.from_direction(direction=direction_to_center, module=.7 * diagonal)
        point_in_front_sector = self.my_mothership.coord + vec
        for sector in self.unsorted_sectors:
            front_sector = True if self.is_enter_in_sector(sector_coord=sector, obj=point_in_front_sector) else False
            mship = self.get_mship_in_sector(sector)
            sectors.append(
                {
                    'front': front_sector,
                    'home_sector': True if mship is self.my_mothership else False,
                    'team_name': mship.team if mship else None,
                    'mothership': mship,
                    'coord': sector
                }
            )
        return sectors

    def get_game_data(self):
        """
        Получение состояния армии противников

        :return: Dict
        """
        game_data = []
        for drone in self.get_drones():
            team = next((team for team in game_data if team.get('team_name') == drone.set_team_name), False)
            if not team:
                team = {'team_name': drone.set_team_name}
                game_data.append(team)

            if drone.is_alive:
                team['number_soldiers'] = team.get('number_soldiers', 0) + 1
                team['elirium'] = team.get('elirium', 0) + drone.payload
            else:
                team['number_soldiers'] = team.get('number_soldiers', 0)
                team['elirium'] = team.get('elirium', 0)

        for mship in self.space_field.motherships:
            team = next((team for team in game_data if team.get('team_name') == mship.team), False)
            if mship.is_alive:
                if not team:
                    team = {'team_name': mship.team}
                    game_data.append(team)
                team['elirium'] = team.get('elirium', 0) + mship.payload
            team['defenders'] = len(self.get_base_defender(team_name=mship.team, mothership=mship))
        return game_data

    def get_mship_in_sector(self, sector_coord):
        """
        Проверка распложения Базы в соот-щем секторе.

        :param sector_coord: список с углами (точками) сектора
        :return: None or MotherShip
        """
        for mship in self.space_field.motherships:
            if self.is_enter_in_sector(sector_coord=sector_coord, obj=mship):
                return mship
        else:
            return None

    def get_drones_in_sector(self, sector_coord):
        """
        Получение дронов в соот-щем секторе (в проекте не используется).

        :param sector_coord:  список с углами (точками) сектора
        :return: список дронов
        """
        enemy_drones = self.get_drones(filters=[self.get_enemy_drones, self.get_alive_obj])
        drones_in_sector = [
            drone for drone in enemy_drones
            if self.is_enter_in_sector(sector_coord=sector_coord, obj=drone)
        ]
        return drones_in_sector

    def get_drones(self, filters=None):
        """
        Получение дронов с заданными фильрами

        :param filters: Список с функциями фильтрами
        :return: List
        """
        drones = []
        for team_name, teammates in self.space_field.teams.items():
            for drone in teammates:
                drones.append(drone)
        if filters:
            for add_filter in filters:
                drones = add_filter(drones)
        return drones

    def get_enemy_motherships(self, filters=None):
        """
        Получение списка вражеских баз

        :param filters: Список с функциями фильтрами
        :return: List
        """
        enemy_motherships = []
        for mothership in self.space_field.motherships:
            if mothership.team != 'DontsovDrone':
                enemy_motherships.append(mothership)
        if filters:
            for add_filter in filters:
                enemy_motherships = add_filter(enemy_motherships)
        return enemy_motherships

    @property
    def point_center_field(self):
        """
        Возврат центр поля.

        :return: Point
        """
        x_half = int(FIELD_WIDTH / 2)
        y_half = int(FIELD_HEIGHT / 2)
        return Point(x_half, y_half)

    @property
    def unsorted_sectors(self):
        """
        Возврат списка секторов с координатами.

        :return: List
        """
        return [
            [
                Point(0, 0),
                Point(FIELD_WIDTH / 2, 0),
                self.point_center_field,
                Point(0, FIELD_HEIGHT / 2)
            ],
            [
                Point(0, FIELD_HEIGHT / 2),
                self.point_center_field,
                Point(FIELD_WIDTH / 2, FIELD_HEIGHT),
                Point(0, FIELD_HEIGHT)
            ],
            [
                Point(FIELD_WIDTH / 2, 0),
                Point(FIELD_WIDTH, 0),
                Point(FIELD_WIDTH, FIELD_HEIGHT / 2),
                self.point_center_field
            ],
            [
                self.point_center_field,
                Point(FIELD_WIDTH, FIELD_HEIGHT / 2),
                Point(FIELD_WIDTH, FIELD_HEIGHT),
                Point(FIELD_WIDTH / 2, FIELD_HEIGHT)
            ]
        ]

    @staticmethod
    def is_enter_in_sector(sector_coord, obj):
        """
        Проверка распложения объекта игры в соот-щем секторе.

        :param sector_coord:  список с углами (точками) сектора
        :param obj: объект игры или точка
        :return: True or False
        """
        if isinstance(obj, GameObject):
            obj = obj.coord
        min_x = (min(sector_coord, key=lambda obj: obj.x)).x
        max_x = (max(sector_coord, key=lambda obj: obj.x)).x
        min_y = (min(sector_coord, key=lambda obj: obj.y)).y
        max_y = (max(sector_coord, key=lambda obj: obj.y)).y
        if min_x <= obj.x <= max_x and min_y <= obj.y <= max_y:
            return True
        else:
            return False

    @staticmethod
    def get_alive_obj(objects):
        """
        Возвращает список живых объектов.

        :param objects: Список объектов игры
        :return: List
        """
        return [obj for obj in objects if obj.is_alive]

    @staticmethod
    def get_not_alive_obj(objects):
        """
        Возвращает список живых объектов.

        :param objects: Список объектов игры
        :return: List
        """
        return [obj for obj in objects if not obj.is_alive]

    @staticmethod
    def filter_is_not_empty(objects):
        """
        Возвращает список объектов с элириумом.

        :param objects: Список объектов игры
        :return: List
        """
        return [obj for obj in objects if not obj.is_empty]

    @staticmethod
    def get_enemy_drones(objects):
        """
        Возвращает список вражеских дронов.

        :param objects: Список дронов
        :return: List
        """
        return [obj for obj in objects if not isinstance(obj, DontsovDrone)]

    @staticmethod
    def get_team_drones(objects):
        """
        Возвращает список дружеских дронов.

        :param objects: Список дронов
        :return: List
        """
        return [obj for obj in objects if isinstance(obj, DontsovDrone)]

    def get_objects_in_radius_attack(self, drone, objects):
        """
        Возвращает список объектов, которые находятся в радиусе атаки дрона.

        :param objects: Список объектов игры
        :param drone: DontsovDrone
        :return: List
        """
        return [obj for obj in objects if self.is_radius_attack(drone, obj)]

    def get_objects_with_loot(self, sector=None, safe_harvest=False, bait=True):
        """
        Получение списка объектов игры с элириума и фильтрация по секторам.

        :param sector: список с углами (точками) сектора
        :param safe_harvest: Boolean
        :return: List
        """
        objects_with_loot = [aster for aster in self.space_field.asteroids if not aster.is_empty]
        drones_with_loot = self.get_drones(filters=[self.get_not_alive_obj, self.filter_is_not_empty])
        objects_with_loot.extend(drones_with_loot)
        enemy_mships_with_loot = self.get_enemy_motherships(
            filters=[self.get_not_alive_obj, self.filter_is_not_empty])
        objects_with_loot.extend(enemy_mships_with_loot)
        if safe_harvest:
            objects_with_loot = self.get_safe_obj(objects_with_loot)
        if sector:
            objects_with_loot = [
                obj for obj in objects_with_loot
                if self.is_enter_in_sector(sector_coord=sector['coord'], obj=obj)
            ]
        return objects_with_loot

    def get_safe_obj(self, objects):
        """
        Получение списка игровых объектов, которые находятся вне зоны поражения.

        :param objects: Список объектов игры
        :return: List
        """
        return [obj for obj in objects if self.is_obj_safe(obj)]

    def is_radius_attack(self, drone, enemy):
        """
        Проверка нахождения объекта в радиусе атака.

        :param enemy: объект игры
        :param drone: DontsovDrone
        :return: True
        """
        if RADIUS_ATTACK >= drone.distance_to(enemy):
            return True

    def is_base_radius_attack(self, obj):
        """
        Проверка нахождения объекта в радиусе угрозе Базы.

        :param obj: объект игры
        :return: True
        """
        if RADIUS_ATTACK + self.my_mothership.radius >= self.my_mothership.distance_to(obj):
            return True

    def is_need_heal(self, drone):
        """
        Проверка на необходимость лечения дрона.

        :param drone: DontsovDrone
        :return: True or False
        """
        if drone.health < 60:
            return True
        else:
            return False

    def is_obj_safe(self, obj):
        """
        Проверка нахождения точки или объекта игры вне зоны поражения.

        :param obj: объект игры
        :return: True or False
        """
        enemy_alive_drones = self.get_drones(filters=[self.get_enemy_drones, self.get_alive_obj])
        enemy_alive_drones_stay = [drone for drone in enemy_alive_drones if not drone.is_moving]
        for drone in enemy_alive_drones_stay:
            if drone.distance_to(obj) < RADIUS_ATTACK:
                return False
        else:
            return True

    def is_risk_game(self):
        """
        Определение необходимости риска в игре.

        :return: Boolean
        """
        number_place = 0
        game_data = self.get_game_data()
        game_data = sorted(game_data, key=lambda x: x['elirium'], reverse=True)
        for number_place, team in enumerate(game_data):
            if team['team_name'] == 'DontsovDrone':
                break
        teammates = self.get_drones(filters=[self.get_alive_obj, self.get_team_drones])

        if number_place > 1 and len(teammates) >= 4:
            return True

    def is_start_game(self):
        """
         проверка для евента сбора в начле игры.

        :return: Boolean
        """
        objects_with_loot = [mship.payload for mship in self.space_field.motherships]
        objects_with_loot.extend([drone.payload for drone in self.get_drones()])
        total_tank = sum(objects_with_loot)
        if total_tank < .9 * self.total_ellirium:
            return True
        return False


drone_class = DontsovDrone
