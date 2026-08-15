import anasazi
import pandas as pd
import pd_ecs
from pathlib import Path
from pytest_bdd import given


@given("there is a landscape", target_fixture='world')
def initialize_world():
    world = pd_ecs.World()
    anasazi.initialize_terrain(
        world, 
        anasazi.load_terrain(Path(__file__).parent / 'data' / 'yields 800-805.npy', 800))
    return world

@given("there are some households", target_fixture='households')
def init_households(world):
    return anasazi.initialize_households(world, 10)
     
@given("the households each own a farm",  target_fixture='farms')
def own_farms(world, households):
    farms = world[anasazi.comps.MEAN_YIELD].index[:len(households)]
    print(households, farms)
    anasazi._start_farm(world, households, farms)
    print(world[anasazi.comps.FARMLAND])
    return farms


@given("the households each have a house", target_fixture='homes')
def own_house(world, households):
    land_ids = world[anasazi.comps.MEAN_YIELD].index
    home_ids = land_ids.difference(anasazi.farmed_land_ids(world))[:len(households)]
    anasazi._move_in(world, households, home_ids)
    return anasazi.home_occupancy(world).reindex(home_ids)