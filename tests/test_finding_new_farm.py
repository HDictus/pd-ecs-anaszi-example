import numpy as np
from pd_ecs import World
import pandas as pd
from mock import MagicMock
from anasazi import components as comps
import anasazi
import mock


def test_moves_after_small_harvest():
    world = World()
    # TODO: it is better to be able to avoid mocking
    # say we choose to call it something else?
    # it's a little brittle.
    oldmove = anasazi.move
    anasazi.move = mock.MagicMock()
    households = world.add_entities({
        comps.STOCKPILE: {'grain': [1, 2, 3, 2]},
        comps.FOOD_NEEDS: {'grain': [2.5, 2.5, 2.5, 2.5]}})
    anasazi.stock_taking(world, pd.Series([1, 1, 0, 0], index=households))

    assert all(anasazi.move.call_args[0][1] == [0, 3])
    anasazi.move = oldmove


def test_moves_to_nearest_habitable_unoccupied():
    """
    When a household moves, it should seek the nearest farm that offers enough
    food to survive.
    They should move into the nearest unfarmed location.

    When multiple households move, the first in the list gets priority.
    """
    world = World()
    lands = world.add_entities({
        comps.POSITION: {'x': [0, 0, 0, 0, 0, 5, 0], 'y': [100, 100, 110, 115, 120, 120, 105]},
        comps.OCCUPYING_HOMES: {'num occupants': [0, 0, 0, 0, 0, 0, 2]},
        comps.YIELD: {'mean': [0.1, 0.1, 1.0, 0.5, 1.0, 1.0, 0.1]}})
    world.give(lands[:3], {comps.FARMED: {'is_farmed': True}})
    households = world.add_entities({
        comps.POSITION: {'x': [0, 0], 'y': [100, 100]},
        comps.FOOD_NEEDS: {'grain': [1, 1]},
        comps.FARMLAND: {'id': [0, 1]},
        comps.HOME: {'id': [6, 6]},
        })

    anasazi.move(world, households)
    assert all(world[comps.FARMLAND]['id'].values == [lands[4], lands[5]])
    assert all(world[comps.HOME]['id'].values == [lands[3], lands[3]])

    assert all(world[comps.FARMED]['is_farmed'].index
               == [lands[2], lands[4], lands[5]])
    assert np.allclose(
        world[comps.OCCUPYING_HOMES]['num occupants'],
        [0, 0, 0, 2, 0, 0, 0])


def test_if_no_farm_then_die():
    world = World()
    lands = world.add_entities({
        comps.POSITION: {
            'x': [0, 0, 0, 0],
            'y': [1, 2, 3, 4],
        },
        comps.YIELD: {
            'mean': [0.1, 0.1, 0.1, 0.1]
        },
        comps.OCCUPYING_HOMES: {'num occupants': 0}
    })
    household = world.add_entities({
        comps.POSITION: {
            'x': [1],
            'y': [3]
        },
        comps.FOOD_NEEDS: {
            'grain': 0.2
        }
    })
    anasazi.move(world, household)
    assert all(world.loc[household, comps.FARMLAND].values == [lands[2]])


def test_move_works_for_farmless_folks():
    world = World()
    lands = world.add_entities({
        comps.POSITION: {'x': [0, 0, 0, 0, 0, 5, 0], 'y': [100, 100, 110, 115, 120, 120, 105]},
        comps.OCCUPYING_HOMES: {'num occupants': [0, 0, 0, 0, 0, 0, 2]},
        comps.YIELD: {'mean': [0.1, 0.1, 1.0, 0.5, 1.0, 1.0, 0.1]}})
    world.give(lands[:3], {comps.FARMED: {'is_farmed': True}})
    households = world.add_entities({
        comps.POSITION: {'x': [0, 0], 'y': [100, 100]},
        comps.FOOD_NEEDS: {'grain': [1, 1]},
        })

    anasazi.move(world, households)
    assert all(world[comps.FARMLAND]['id'].values == [lands[4], lands[5]])
    assert all(world[comps.HOME]['id'].values == [lands[3], lands[3]])