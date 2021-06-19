# -*- coding: utf-8 -*

class BaseAction:
    """
    Класс базового состояния-действия.
    """
    def __init__(self, **kwargs):
        self._drone = kwargs['drone']
        self._nav = self.drone.command_center
        self._sector = kwargs.get('sector')

    def go(self, strategy):
        """
        Совершения действия дроном.
        """
        pass

    @property
    def drone(self):
        return self._drone

    @property
    def nav(self):
        return self._nav

    @property
    def sector(self):
        return self._sector

    @sector.setter
    def sector(self, new_sector):
        self._sector = new_sector


class LoadAction(BaseAction):
    """
    Класс состояния-действия Загрузки с объекта Элирума.
    """
    def go(self, strategy):
        """
        Действия загрузки Элирума.

        :param strategy: Класс текущей стратегии
        """
        if not self.drone.is_full and not self.drone.target_move.is_empty:
            enemy_drones = self.nav.get_drones(filters=[self.nav.get_enemy_drones, self.nav.get_alive_obj])
            victim = next((drone for drone in enemy_drones if self.drone.near(drone) and not drone.is_moving), None)
            target_load = victim if victim else self.drone.target_move
            self.drone.load_from(target_load)
        else:
            if self.drone.is_full:
                strategy.current_action = strategy.recovery_action
            else:
                strategy.current_action = strategy.move_action

        if self.nav.is_need_heal(self.drone):
            strategy.current_action = strategy.recovery_action


class UnloadAction(BaseAction):
    """
    Класс состояния-действия Разгрузки Элирума.
    """
    def go(self, strategy):
        """
        Действия разгрузки Элирума.

        :param strategy: Класс текущей стратегии
        """
        self.drone.unload_to(self.drone.my_mothership)
        if self.drone.is_empty:
            strategy.current_action = strategy.move_action
