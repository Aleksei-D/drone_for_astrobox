# -*- coding: utf-8 -*-

from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE, DRONE_SPEED, PROJECTILE_SPEED
from astrobox.guns import PlasmaProjectile
from robogame_engine.theme import theme

DRONE_SPEED = DRONE_SPEED
HEALING_DISTANCE = MOTHERSHIP_HEALING_DISTANCE
PROJECTILE_SPEED = PROJECTILE_SPEED
RADIUS_ATTACK = PlasmaProjectile.max_distance + PlasmaProjectile.radius * 4
FIELD_WIDTH = theme.FIELD_WIDTH
FIELD_HEIGHT = theme.FIELD_HEIGHT
