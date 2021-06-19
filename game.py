# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField

from dontsov import DontsovDrone

NUMBER_OF_DRONES = 5

if __name__ == '__main__':
    scene = SpaceField(
        speed=3,
        asteroids_count=10,
    )
    [DontsovDrone() for _ in range(NUMBER_OF_DRONES)]
    scene.go()

# Первый этап: зачёт!
# Второй этап: зачёт!
