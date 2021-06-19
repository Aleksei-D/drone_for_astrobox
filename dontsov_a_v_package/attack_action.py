# -*- coding: utf-8 -*

import math

from robogame_engine.geometry import Point, Vector

from .base_actions import BaseAction
from .constants import DRONE_SPEED, PROJECTILE_SPEED


class AttackBaseAction(BaseAction):
    """
    Класс состояния-действия Атаки.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._base_attack = kwargs.get('base_attack')

    @property
    def base_attack(self):
        return self._base_attack

    @base_attack.setter
    def base_attack(self, new_base_attack):
        self._base_attack = new_base_attack

    def go(self, strategy):
        """
        Действия атаки.

        :param strategy: Класс текущей стратегии
        """
        self.drone.target_attack = self.next_target_attack()

        if self.drone.target_attack:
            self.drone.turn_to(self.drone.target_attack)
            if not self.drone.near(self.drone.my_mothership):
                self.drone.gun.shot(self.drone.target_attack)
            if self.nav.is_need_heal(self.drone):
                strategy.current_action = strategy.recovery_action
        else:
            strategy.current_action = strategy.move_action

    def next_target_attack(self):
        """
        Полуение цели для атаки

        :return: Point or MotherShip
        """
        enemy_drones_alive = self.nav.get_drones(
            filters=[self.nav.get_enemy_drones, self.nav.get_alive_obj]
        )
        enemy_drones_alive = self.nav.get_objects_in_radius_attack(drone=self.drone, objects=enemy_drones_alive)
        if enemy_drones_alive:
            for enemy in sorted(enemy_drones_alive, key=self.drone.distance_to):
                number_attackers = self.get_number_attack(enemy_drones_alive)
                if len([drone for drone in self.drone.teammates if drone.target_attack == enemy]) < number_attackers:
                    return self.get_point_attack(enemy=enemy)

        if self.base_attack:
            if self.sector['mothership'].is_alive and self.nav.is_radius_attack(self.drone, self.sector['mothership']):
                return self.sector['mothership']

    def get_point_attack(self, enemy):
        """
        Получение очки для стрельбы на упреждение, если цель двигается.

        :param enemy: Drone
        :return: Point
        """
        if enemy.is_moving:
            time = (enemy.coord.x - self.drone.coord.x) / (PROJECTILE_SPEED - DRONE_SPEED)
            radian = Vector.to_radian(enemy.vector.direction)
            y = enemy.coord.y + time * DRONE_SPEED * math.sin(radian)
            x = enemy.coord.x + time * DRONE_SPEED * math.cos(radian)
            return Point(x, y)
        else:
            return enemy.coord

    def get_number_attack(self, enemy):
        """
        Получение максимального количества атакующих по одной цели.

        :param enemy: Drone
        :return: int
        """
        if len(enemy) > len([drone for drone in self.drone.teammates if drone.is_alive]):
            return 2
        else:
            return 4

    def is_ready_attack(self):
        """
        Проверка повернут ли дрон к цели (Не используется).

        :return: True
        """
        vec = Vector.from_points(point1=self.drone.coord, point2=self.drone.target_attack)
        vec_direction = vec.direction
        if int(self.drone.direction) == int(vec_direction):
            return True

    def is_not_friendly_fire(self, point_attack):
        """
        Проверка есть ли на линии дружеский дрон (Не используется).

        :param point_attack: Point
        :return: True
        """
        p1x, p1y = self.drone.coord.x, self.drone.coord.y
        p2x, p2y = point_attack.x, point_attack.y
        dx, dy = (p2x - p1x), (p2y - p1y)
        for drone in self.drone.teammates:
            radius = drone.radius + self.drone.gun.projectile.radius * 2
            cx, cy = drone.target_move.x, drone.target_move.y
            dcy, dcx = (cy - p1y), (cx - p1x)
            discriminant = radius ** 2 * (dx ** 2 - dy ** 2) - (dx * dcy - dcx * dy) ** 2
            if discriminant < 0:
                return True
            else:
                intersections = [
                    (dcx * dx + dcy * dy + sign * discriminant ** .5) / (dx ** 2 + dy ** 2)
                    for sign in (-1, 1)
                ]
                intersections = [fraq for fraq in intersections if 0 <= fraq <= 1]
                if intersections:
                    return False
                else:
                    return True
        else:
            return True
