from anasazi import MovingSystem
from pd_ecs import World
from mock import MagicMock
from anasazi import position, stockpile, food_needs, grain_yield, \
    occupying_farms, farmland


# TODO: should also test that when we move entities they unoccupy their old farm
def test_moves_after_small_harvest():
    world = World(stockpile, food_needs, position,
                  occupying_farms, farmland, grain_yield)
    world.events.find_home = MagicMock()
    ms = MovingSystem(world)
    households = world.add_entities({
        stockpile: {'grain': [1, 2, 3, 1]},
        food_needs: {'grain': [2.5, 2.5, 2.5, 2.5]}})
    world.events.harvest(households, [1, 0.1, 0, 2.0])
    arg1, = world.events.find_home.mock_calls[0].args
    assert (arg1 == [0, 1]).all()

def test_moves_to_nearest_habitable_unoccupied():
    world = World(food_needs, grain_yield, position, occupying_farms, farmland)
    ms = MovingSystem(world)
    households = world.add_entities({
        position: {'x': [0], 'y': [100]},
        food_needs: {'grain': [1]}})
    lands = world.add_entities({
        position: {'x': [0, 0, 0, 0], 'y': [110, 115, 120, 125]},
        occupying_farms: {'num occupants': [1, 0, 0, 0]},
        grain_yield: {'mean': [1.0, 0.5, 1.0, 1.0]}})
    world.events.find_home([0])
    assert world[farmland].loc[0, 'id'] == lands[2]
