import numpy as np
from anasazi import MovingSystem
from pd_ecs import World
from mock import MagicMock
from anasazi import position, stockpile, food_needs, grain_yield, \
    occupying_farms, farmland, occupying_houses


# TODO: should also test that when we move entities they unoccupy their old farm
# TODO: kind of awkward to have to add components to both the world and the system.
def test_moves_after_small_harvest():
    world = World(stockpile, food_needs, position,
                  occupying_farms, farmland, grain_yield,
                  occupying_houses)
    world.events.find_home = MagicMock()
    ms = MovingSystem(world)
    households = world.add_entities({
        stockpile: {'grain': [1, 2, 3, 1]},
        food_needs: {'grain': [2.5, 2.5, 2.5, 2.5]}})
    world.events.harvest(households, [1, 0.1, 0, 2.0])
    arg1, = world.events.find_home.mock_calls[0].args
    assert (arg1 == [0, 1]).all()

# TODO: test move_out and then find_home called
# TODO: test move_out event

def test_moves_to_nearest_habitable_unoccupied():
    """
    When a household moves, it should seek the nearest farm that offers enough
    food to survive.
    They should move into the nearest unfarmed location.

    When multiple households move, the first in the list gets priority.
    """
    world = World(food_needs, grain_yield, position,
                  occupying_farms, farmland, occupying_houses)
    ms = MovingSystem(world)
    households = world.add_entities({
        position: {'x': [0, 0], 'y': [100, 100]},
        food_needs: {'grain': [1, 1]}})
    lands = world.add_entities({
        position: {'x': [0, 0, 0, 0, 0], 'y': [110, 115, 120, 125, 105]},
        occupying_farms: {'num occupants': [1, 0, 0, 0, 0]},
        occupying_houses: {'num occupants': [0, 0, 0, 0, 2]},
        grain_yield: {'mean': [1.0, 0.5, 1.0, 1.0, 1.0]}})
    world.events.find_home(households)

    assert np.allclose(world[farmland].loc[households, 'id'].values,
                       [lands[2], lands[3]])
    assert np.allclose(world[position].loc[households], [[0, 115], [0, 115]])
    print(world[occupying_houses].values)
    print(world[occupying_farms].values)
    assert np.allclose(world[occupying_houses].values[:, 0], [0, 2, 0, 0, 2])
    assert np.allclose(world[occupying_farms].values[:, 0], [1, 0, 1, 1, 0])

# TODO: test move_in event is called
# TODO: test move_in event
