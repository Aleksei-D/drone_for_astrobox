# -*- coding: utf-8 -*-

from .attack_action import AttackBaseAction
from .base_actions import LoadAction, UnloadAction
from .move_actions import MoveHarvestAction, MoveRecoveryAction, MoveDefenderAction, \
    MoveToSector, MoveHomeAction, MoveLastSectorAction


class BaseStrategy:
    """
    Базовый класс стратегии.
    """
    def __init__(self, **kwargs):
        self._drone = kwargs['drone']
        self.recovery_action = MoveRecoveryAction(**kwargs)
        self.unload_action = UnloadAction(**kwargs)
        self.move_action = None
        self.current_action = None

    @property
    def drone(self):
        return self._drone

    def action(self):
        """
        Действие дрона.
        """
        self.current_action.go(strategy=self)

    def update(self, **kwargs):
        """
        Обновление атрибутов стратегии.
        """
        pass


class DefenderStrategy(BaseStrategy):
    """
    Стратегия защиты базы.

    :return: Dict
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_action = MoveDefenderAction(**kwargs)
        self.attack_action = AttackBaseAction(**kwargs)
        self.current_action = self.move_action


class HarvestStrategy(BaseStrategy):
    """
    Стратегия защиты базы.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_action = MoveHarvestAction(**kwargs)
        self.load_action = LoadAction(**kwargs)
        self.unload_action = UnloadAction(**kwargs)
        self.recovery_action = MoveHomeAction(**kwargs)
        self.current_action = self.move_action

    def update(self, **kwargs):
        """
         Обновление атрибутов стратегии.
        """
        self.move_action.sector = kwargs.get('sector')
        self.move_action.safe_harvest = kwargs.get('safe_harvest')


class SabotageStrategy(BaseStrategy):
    """
    Стратегия вторжения в сектор по безопасной траектории.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_action = MoveToSector(**kwargs)
        self.attack_action = AttackBaseAction(**kwargs)
        self.current_action = self.move_action

    def update(self, **kwargs):
        """
         Обновление атрибутов стратегии.
        """
        self.move_action.sector = kwargs.get('sector')
        self.move_action.start_sector = kwargs.get('start_sector')
        self.attack_action.base_attack = kwargs.get('base_attack')
        self.attack_action.sector = kwargs.get('sector')


class LastBattleStrategy(BaseStrategy):
    """
    Стратегия нападения в центральный сектор.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_action = MoveLastSectorAction(**kwargs)
        self.attack_action = AttackBaseAction(**kwargs)
        self.current_action = self.move_action

    def update(self, **kwargs):
        """
         Обновление атрибутов стратегии.
        """
        self.move_action.sector = kwargs.get('sector')
