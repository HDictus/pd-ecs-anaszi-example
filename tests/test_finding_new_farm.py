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
        comps.STOCKPILE: [1, 2, 3, 2],
        comps.FOOD_NEEDS: [2.5, 2.5, 2.5, 2.5]})
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
        comps.X: [0, 0, 0, 0, 0, 5, 0], 
        comps.Y: [100, 100, 110, 115, 120, 120, 105],
        comps.MEAN_YIELD: [0.1, 0.1, 1.0, 0.5, 1.0, 1.0, 0.1]})
    world.add_entities({comps.FARMLAND: lands[2:3]})

    households = world.add_entities({
        comps.X: [0, 0], 
        comps.Y: [100, 100],
        comps.FOOD_NEEDS: [1, 1],
        comps.FARMLAND: [0, 1],
        comps.HOME: [6, 6],
    })

    anasazi.move(world, households)
    assert all(world.loc[households, comps.FARMLAND].values == [lands[4], lands[5]])
    assert all(world[comps.HOME].values == [lands[3], lands[3]])

    assert all(world[comps.FARMED].index
               == [lands[2], lands[4], lands[5]])
    pd.testing.assert_series_equal(
        world[comps.OCCUPYING_HOMES],
        pd.Series([2], index=[3], name=comps.OCCUPYING_HOMES))


def test_if_no_farm_then_die():
    world = World()
    lands = world.add_entities({
        comps.X: [0, 0, 0, 0],
        comps.Y: [1, 2, 3, 4],
        comps.MEAN_YIELD:  [0.1, 0.1, 0.1, 0.1],
    })
    household = world.add_entities({
        comps.X: [1],
        comps.Y: [3],
        comps.FOOD_NEEDS:  0.2
    })
    anasazi.move(world, household)
    assert len(world.index.intersection(household)) == 0


def test_move_works_for_farmless_folks():
    world = World()
    lands = world.add_entities({
        comps.X: [0, 0, 0, 0, 0, 5, 0], 
        comps.Y: [100, 100, 110, 115, 120, 120, 105],
        comps.MEAN_YIELD: [0.1, 0.1, 1.0, 0.5, 1.0, 1.0, 0.1]})
    world.add_entities({comps.FARMLAND: lands[:3]})
    households = world.add_entities({
        comps.X: [0, 0],
        comps.Y: [100, 100],
        comps.FOOD_NEEDS: [1, 1],
    })

    anasazi.move(world, households)
    assert all(world.loc[households, comps.FARMLAND].values == [lands[4], lands[5]])
    assert all(world[comps.HOME].values == [lands[3], lands[3]])