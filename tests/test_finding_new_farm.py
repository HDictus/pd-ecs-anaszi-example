import numpy as np
from pd_ecs import World
import pandas as pd
from mock import MagicMock
from anasazi.components import position, stockpile, food_needs, grain_yield, \
    occupying_farms, farmland, occupying_houses, home, moving
from anasazi import stock_taking, moving_house


def test_moves_after_small_harvest():
    world = World()
    households = world.add_entities({
        stockpile: {'grain': [1, 2, 3, 2]},
        food_needs: {'grain': [2.5, 2.5, 2.5, 2.5]}})
    stock_taking(world, pd.Series([1, 1, 0, 0], index=households))
    assert all(world[moving].index == [0, 3])


def test_moves_to_nearest_habitable_unoccupied():
    """
    When a household moves, it should seek the nearest farm that offers enough
    food to survive.
    They should move into the nearest unfarmed location.

    When multiple households move, the first in the list gets priority.
    """
    world = World()
    lands = world.add_entities({
        position: {'x': [0, 0, 0, 0, 0, 5, 0], 'y': [100, 100, 110, 115, 120, 120, 105]},
        occupying_farms: {'num occupants': [1, 1, 1, 0, 0, 0, 0]},
        occupying_houses: {'num occupants': [0, 0, 0, 0, 0, 0, 2]},
        grain_yield: {'mean': [0.1, 0.1, 1.0, 0.5, 1.0, 1.0, 0.1]}})
    households = world.add_entities({
        position: {'x': [0, 0], 'y': [100, 100]},
        food_needs: {'grain': [1, 1]},
        farmland: {'id': [0, 1]},
        home: {'id': [6, 6]},
        moving: {},
        })

    moving_house(world)
    assert all(world[farmland]['id'].values == [lands[4], lands[5]])
    assert all(world[home]['id'].values == [lands[3], lands[3]])

    assert all(world[occupying_farms]['num occupants']
               == [0, 0, 1, 0, 1, 1, 0])
    assert all(world[occupying_houses]['num occupants']
               == [0, 0, 0, 2, 0, 0, 0])
