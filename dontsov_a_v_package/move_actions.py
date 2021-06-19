# -*- coding: utf-8 -*-

import math

from robogame_engine.geometry import Point, Vector

from .base_actions import BaseAction
from .constants import HEALING_DISTANCE


class MoveBaseAction(BaseAction):
    """
    Базовый класс действия-состояния движения дрона.
    """

    @staticmethod
    def is_same_points(point1, point2):
        """
        Проверка на равенство координат точек

        :param point1: Point
        :param point2: Point
        :return: True or False
        """
        if point1.x == point2.x and point1.y == point2.y:
            return True
        else:
            return False

    def is_valid_point(self, point):
        """
        Проверка занято ли место дружественным дроном

        :param point: Point
        :return: True or False
        """
        teammates_is_alive = [drone for drone in self.drone.teammates if drone.is_alive]
        for drone in teammates_is_alive:
            if drone.start_position:
                if self.is_same_points(point1=point, point2=drone.start_position):
                    return False
        else:
            return True

    def get_position_on_circle(self, distance, mothership, angle=60):
        """
        Получение позиции вокруг объекта (базы) на заданном расстоянии.

        :param distance: float
        :param mothership: MotherShip
        :param angle: int
        :return: Point
        """
        direction_to_center = self.get_direction_attack(
            start_point=mothership.coord,
            end_point=self.nav.point_center_field)
        direction_to_center = int(direction_to_center)
        number_guard = len([drone for drone in self.drone.teammates if drone.is_alive])
        number_guard = 1 if number_guard == 0 else number_guard
        start_angle = direction_to_center - angle
        end_angle = direction_to_center + angle
        step = int((end_angle - start_angle) / number_guard)
        for direction in range(start_angle, end_angle + 1, step):
            radian = Vector.to_radian(direction)
            y = mothership.coord.y + distance * math.sin(radian)
            x = mothership.coord.x + distance * math.cos(radian)
            point = Point(x=x, y=y)
            if self.is_valid_point(point):
                return point

    @staticmethod
    def get_direction_attack(start_point, end_point):
        """
        Получение направления вектора, заданного точками.

        :param start_point: Point
        :param end_point: Point
        :return: float
        """
        vec = Vector.from_points(point1=start_point, point2=end_point)
        return vec.direction

    def unload_move(self, strategy):
        self.drone.target_move = self.drone.my_mothership
        if not self.drone.near(self.drone.target_move):
            self.drone.move_at(self.drone.target_move)
        strategy.current_action = strategy.unload_action


class MoveDefenderAction(MoveBaseAction):
    """Класс действия-состояния передвижения на позицию защиты базы."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.safe_distance = .88 * HEALING_DISTANCE

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        if not self.drone.is_empty:
            self.unload_move(strategy)
        else:
            self.drone.start_position = self.get_target_move()
            self.drone.target_move = self.drone.start_position
            if self.drone.target_move:
                if not self.drone.near(self.drone.target_move):
                    self.drone.move_at(self.drone.target_move)
                else:
                    strategy.current_action = strategy.attack_action

    def get_target_move(self):
        """
        Получение точки передвижения.

        :return: Point
        """
        return self.get_position_on_circle(
            distance=self.safe_distance,
            mothership=self.drone.my_mothership
        )


class MoveHarvestAction(MoveBaseAction):
    """Класс действи
я-состояния передвижения на точку сбора Элириума."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sector = kwargs.get('sector')
        self._safe_harvest = kwargs.get('safe_harvest')

    @property
    def safe_harvest(self):
        return self._safe_harvest

    @safe_harvest.setter
    def safe_harvest(self, condition):
        self._safe_harvest = condition

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        self.drone.target_move = self.get_target_move()
        if self.drone.target_move is None:
            strategy.current_action = strategy.recovery_action
        else:
            if self.drone.near(self.drone.target_move) and not self.drone.is_moving:
                strategy.current_action = strategy.load_action

            self.drone.move_at(self.drone.target_move)

    def get_target_move(self):
        """
        Получение точки передвижения.

        :return: GameObject
        """
        objects_with_loot = self.nav.get_objects_with_loot(sector=self.sector, safe_harvest=self.safe_harvest)
        if objects_with_loot:
            objects_with_loot_free = [obj for obj in objects_with_loot if self.is_obj_free_for_group(obj)]
            if objects_with_loot_free:
                return min(objects_with_loot_free, key=self.drone.distance_to)

    def is_obj_free_for_solo(self, obj):
        """
        Проверка для фильтрации объектов игры с лутом, для одиночного дрона.

        :param obj: GameObject
        :return: True or False
        """
        for drone in self.drone.teammates:
            if drone.target_move == obj:
                return False
        else:
            return True

    def is_obj_free_for_group(self, obj):
        """
        Проверка для фильтрации объектов игры с лутом, для группового дрона.

        :param obj: GameObject
        :return: True or False
        """
        teammates_alive = [drone for drone in self.drone.teammates if drone.target_move == obj and drone.is_alive]
        if teammates_alive:
            if sum([drone.free_space for drone in teammates_alive]) < obj.payload:
                return True
            else:
                return False
        else:
            return True

    def is_need_drone(self):
        priority_asteroids = self.separated_asteroids['priority_asteroids']
        priority_asteroids_not_empty = [asteroid for asteroid in priority_asteroids if not asteroid.is_empty]
        half_distance = self.drone.distance_to(max(priority_asteroids_not_empty, key=self.drone.distance_to)) / 2
        distant_asteroids = [
            asteroid for asteroid in priority_asteroids_not_empty
            if self.drone.distance_to(asteroid) > half_distance
        ]
        drones_with_first_target = [
            drone.target for drone in self.drone.teammates
            if drone.target in priority_asteroids_not_empty
        ]
        if len(distant_asteroids) > 1.4 * (len(priority_asteroids_not_empty) - len(distant_asteroids)):
            if len(drones_with_first_target) < len(self.drone.teammates) // 2 + 1:
                return True
            else:
                return False
        else:
            if len(drones_with_first_target) < len(self.drone.teammates) // 2:
                return True
            else:
                return False


class MoveToSector(MoveBaseAction):
    """Класс действия-состояния передвижения на позицию атаки боковых баз врага."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drone.target_move = None
        self.drone.start_position = None
        self._start_sector = kwargs.get('start_sector')
        self.current_sector = self.sector
        self.direction_attack = self.get_direction_attack(
            start_point=self.nav.my_mothership.coord
            if self.start_sector is None else self.start_sector['mothership'].coord,
            end_point=self.sector['mothership'].coord
        )

    @property
    def start_sector(self):
        return self._start_sector

    @start_sector.setter
    def start_sector(self, new_sector):
        self._start_sector = new_sector

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        if not self.drone.is_empty:
            self.unload_move(strategy)
        else:
            if self.current_sector['team_name'] != self.sector['team_name']:
                self.reload_attr()

            if self.drone.start_position is None:
                self.drone.start_position = self.get_start_position()
                self.drone.target_move = self.drone.start_position
            else:
                if self.drone.near(self.drone.target_move):
                    self.drone.target_move = self.get_target_move()
                    strategy.current_action = strategy.attack_action
                else:
                    self.drone.move_at(self.drone.target_move)

            if self.drone.start_position is self.drone.my_mothership:
                self.drone.start_position = self.get_start_position()
                self.drone.target_move = self.drone.start_position

    def reload_attr(self):
        """
        Сброс атрибутов класа, при смене направления.

        return: None
        """
        self.direction_attack = self.get_direction_attack(
            start_point=self.nav.my_mothership.coord
            if self.start_sector is None else self.start_sector['mothership'].coord,
            end_point=self.sector['mothership'].coord
        )
        self.drone.start_position = None
        self.current_sector = self.sector

    def get_target_move(self):
        """
        Получение точки передвижения.

        :return: Point
        """
        game_data = self.nav.get_game_data()
        team_name = self.sector['team_name']
        defender_team = next((team for team in game_data if team.get('team_name') == team_name))
        module = 10 if defender_team['number_soldiers'] else 60
        if self.drone.target_move is self.nav.my_mothership:
            return self.drone.target_move
        else:
            return self.drone.target_move + Vector.from_direction(direction=self.direction_attack, module=module)

    def get_start_points(self):
        """
        Получение начальных параметров для расчетов.

        :return: tuple
        """
        team_drones = self.nav.get_drones(filters=[self.nav.get_alive_obj, self.nav.get_team_drones])
        numbers_team = len(team_drones)
        mothership = self.nav.my_mothership if self.start_sector is None else self.start_sector['mothership']
        diagonal = math.sqrt(2 * mothership.radius ** 2)
        diagonal = round(diagonal, 0)
        cathet = 2 * numbers_team * self.drone.radius + self.drone.radius
        dir_from_center = Vector.from_points(point1=self.nav.point_center_field, point2=mothership.coord).direction
        dir_to_center = dir_from_center + 180
        point_start = mothership.coord + Vector.from_direction(direction=dir_from_center, module=diagonal)
        gyp_line = math.sqrt((2.5 * mothership.radius) ** 2 + cathet ** 2)
        point_top = point_start + Vector.from_direction(direction=dir_to_center, module=gyp_line)
        point_bottom = point_start + Vector.from_direction(
            direction=self.direction_attack,
            module=2.5 * mothership.radius)
        return point_start, point_top, point_bottom

    def get_start_position(self):
        """
        Получение начальной точки движения.

        :return: Point
        """
        point_start, point_top, point_bottom = self.get_start_points()
        if int(point_bottom.x) == int(point_start.x):
            point_new = self.get_point_on_axis(
                point_top=point_top, point_bottom=point_bottom,
                attr_main='x', attr_second='y'
            )
            if point_new:
                return point_new

        if int(point_bottom.y) == int(point_start.y):
            point_new = self.get_point_on_axis(
                point_top=point_top, point_bottom=point_bottom,
                attr_main='y', attr_second='x'
            )
            if point_new:
                return point_new

        return self.nav.my_mothership

    def get_point_on_axis(self, point_top, point_bottom, attr_main, attr_second):
        """
        Распределение дронов на линии атаки.

        :param point_top: Point
        :param point_bottom: Point
        :param attr_main: str
        :param attr_second: str
        :return: Point or None
        """
        attr_main_top = getattr(point_top, attr_main)
        attr_main_bottom = getattr(point_bottom, attr_main)
        attr_second_bottom = getattr(point_bottom, attr_second)
        min_coord = min(attr_main_top, attr_main_bottom)
        max_coord = max(attr_main_top, attr_main_bottom)
        step = int(2 * self.drone.radius)
        start_range = int(min_coord + self.drone.radius)
        end_range = int(max_coord)
        for coord_half in range(start_range, end_range, step):
            coord_full = {attr_main: coord_half, attr_second: attr_second_bottom}
            point_new = Point(**coord_full)
            if self.is_valid_point(point_new) and self.nav.is_obj_safe(obj=point_new):
                return point_new
        else:
            return None


class MoveLastSectorAction(MoveBaseAction):
    """Класс действия-состояния передвижения на позицию атаки центральной базы врага."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drone.target_move = None
        self.drone.start_position = None
        self.direction_attack = None
        self.safe_distance = .8 * HEALING_DISTANCE + self.drone.gun.shot_distance

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        if not self.drone.is_empty:
            self.unload_move(strategy)
        else:
            if self.drone.start_position is None:
                self.set_start_attr()
            else:
                if self.drone.near(self.drone.target_move):
                    self.drone.target_move = self.get_target_move()
                    strategy.current_action = strategy.attack_action
                else:
                    self.drone.move_at(self.drone.target_move)

    def get_target_move(self):
        """
        Получение точки передвижения.

        :return: Point
        """
        enemy_alive_drones = self.nav.get_drones(filters=[self.nav.get_alive_obj, self.nav.get_enemy_drones])
        module = 10 if enemy_alive_drones else 70
        return self.drone.target_move + Vector.from_direction(direction=self.direction_attack, module=module)

    def set_start_attr(self):
        """
        Установка первоначальных атрибутов для движения.

        :return: None
        """
        self.drone.start_position = self.get_position_on_circle(
            distance=self.safe_distance,
            mothership=self.sector['mothership'],
            angle=45
        )
        self.direction_attack = self.get_direction_attack(
            start_point=self.drone.start_position,
            end_point=self.sector['mothership'].coord
        )
        self.drone.target_move = self.drone.start_position


class MoveRecoveryAction(MoveBaseAction):
    """Класс действия-состояния передвижения на базу с целью лечения дрона."""

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        self.drone.move_at(self.get_target_move())
        if self.drone.near(self.drone.my_mothership):
            strategy.current_action = strategy.move_action

    def get_target_move(self):
        """
        Получение точки передвижения.

        :return: Point
        """
        return self.drone.my_mothership


class MoveHomeAction(MoveRecoveryAction):
    """Класс действия-состояния передвижения на базу с целью лечения дрона или выгрузки лута."""

    def go(self, strategy):
        """
        Действия движения.

        :param strategy: Класс текущей стратегии
        """
        self.drone.target_move = self.get_target_move()
        self.drone.move_at(self.drone.target_move)
        if self.drone.near(self.drone.target_move):
            strategy.current_action = strategy.unload_action
