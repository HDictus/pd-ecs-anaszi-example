import numpy as np
from pathlib import Path
import pandas as pd
import pkg_resources
from tqdm import tqdm
import anasazi.components as comps

# BIG TODO: revisit this with the goal of writing out the optimal, most sensical way of doing it instead of a working implementattion

# I think the choices of components here illustrate just how not-immune an ECS is to adding logic assumptions into the data
# ....
# what if a thingy has multiple stockpiles (storage locations) e.g. for different goods?
# TODO: we really need a naming convention for components.
# or a namespace...


# TODO: if we want integrate arbitrary models, things like max_grain_stock need to be components
#   or part of the stockpile component
# then, we need some means to efficiently query the stockpile.
def harvest_grain(world, max_grain_stock=1600):
    """All households harvest grain.

    Part of the artificial anasazi model. The annual harvest is sampled from a normal
    distribution where the center is grain_yield['mean'] and scale is grain_yield['var']
    """
    households = world[[comps.STOCKPILE.grain, comps.FARMLAND.id]]
    farms = world[comps.YIELD].loc[households[comps.FARMLAND.id]]
    harvest = np.random.normal(
        farms[comps.YIELD.mean[1]].values, farms[comps.YIELD.var[1]].values)
    households[comps.STOCKPILE.grain] += np.maximum(harvest, 0)
    households[comps.STOCKPILE.grain] = np.minimum(households[comps.STOCKPILE.grain], max_grain_stock)
    world.loc[households.index, comps.STOCKPILE.grain] = households[comps.STOCKPILE.grain]
    return pd.Series(harvest, index=households.index)

# We run into a problem: stock-taking can depend on e.g. last harvest
# which is not something that harvest_grain does not necessarily need to add to state...
# as a feature, it is spanned between the two.
# it calculates it, but writing it as a state is not necessary for it.
# that's kinda meaningless.
# the previous way of doing it: an event that calls eg. a move event is not right either
# too much entanglement
def stock_taking(world, harvest):
    """All households predict whether they will have enough food to survive.

    Those which do not expect a large enough harvest next year will move.

    harvest: a series containing the size of the last harvest
    """
    households = world[[comps.FOOD_NEEDS, comps.STOCKPILE]]
    expected_food = households[comps.STOCKPILE.grain] + harvest
    expects_to_starve = households[comps.FOOD_NEEDS.grain]\
          > expected_food
    # TODO: this is increasingly indicating that these need to be methods of an object,
    #    one with access to world.
    # perhaps world itself.
    move(world, households[expects_to_starve].index)

# TODO: a lot of these questions come down to: when should something be passed from function to function, and when should it be stored in the world state.
# Ultimately this depends on whether taht value will be used in the future...
# which depends on other models... ummm

# well, premature optimization is the root of all evil. Cache it all and come up with a method to save on space when it's unused
# for instance, allow world to skip updating particular things, and raise an error when asked for them.

# um no that's utterly fucked.
# you can't create a fresh component for every variable you ever use, that's a nightmare to develop and debug,
# just remember developing harvest, how simple it is and how you would never expect the harvest amount to do anything other than be added to the thing. Make a component for that?
# just make it work for now ok?

# there will be operations here that do not involve any "game logic", that just adjust the other components that need to change when an entity moves house...

def _calculate_distances_matrix(positions1, positions2):
    displacements = (
        positions1[..., np.newaxis, :]
        - positions2[np.newaxis,]
    )
    return np.linalg.norm(np.float32(displacements), axis=-1)

def _move_out(world, movers):
    have_farm = world[comps.FARMLAND].index.intersection(movers)
    if len(have_farm) > 0:
        del world.loc[world.loc[have_farm, comps.FARMLAND.id], comps.FARMED]
    have_home = world[comps.HOME].index.intersection(movers)
    if len(have_home) == 0:
        return
    unique_homes, counts = np.unique(
        world.loc[have_home, comps.HOME.id],
        return_counts=True)
    world.loc[unique_homes, comps.OCCUPYING_HOMES.num] -= counts
    del world.loc[have_home, comps.HOME]


def _find_farm(world, movers):
    # TODO: we should use numba.njit for this tbh
    # TODO: or a matching algorithm, only then it's not strictly speaking artifical anasazi...
    land = world[[comps.YIELD, comps.POSITION, comps.OCCUPYING_HOMES, ~comps.FARMED]]
    unoccupied_land = land[
        land[comps.OCCUPYING_HOMES.num] == 0]

    distances = _calculate_distances_matrix(
        world.loc[movers, comps.POSITION].values,
        unoccupied_land[comps.POSITION].values)
    enough_to_survive = world.loc[movers, comps.FOOD_NEEDS.grain].values[..., np.newaxis]\
        <= unoccupied_land[comps.YIELD.mean].values[np.newaxis]
    
    distances[~enough_to_survive] = np.inf

    nearest_farms = []

    for dist in distances:
        if not np.isfinite(dist).any():
            # assert False, "lol, TODO"
            pass
        nearest = np.argmin(dist)
        distances[:, nearest] = np.inf
        nearest_farms.append(unoccupied_land.index[nearest])
    return movers, nearest_farms


def _start_farm(world, mover_ids, farm_ids):
    # TODO: would be cooler if we could 'give' with .loc
    world.give(mover_ids, {
        comps.FARMLAND: {comps.FARMLAND.id[1]: farm_ids}})
    world.give(farm_ids, {comps.FARMED: {'is_farmed': True}})


def _find_home(world, mover_ids, farm_ids):
    # TODO: go back to component negation later
    potential_housing = world[
        [comps.POSITION, comps.OCCUPYING_HOMES, ~comps.FARMED]]

    house_to_farm_distance = _calculate_distances_matrix(
        potential_housing[comps.POSITION].values,
        world.loc[farm_ids, comps.POSITION].values)
    houses = potential_housing.iloc[
        np.argmin(house_to_farm_distance, axis=0)
    ]

    return houses.index


def _move_in(world, household_ids, house_ids):
    unique_ids, house_counts = np.unique(house_ids, return_counts=True)
    world.loc[unique_ids, comps.OCCUPYING_HOMES.num] += house_counts
    # there are too many different ways to update the world state
    # this does not make it especially simple
    # getitem is really simple... maybe we should just stick with that?
    world.loc[household_ids, comps.POSITION] = world.loc[house_ids, comps.POSITION]
    world.give(household_ids, {comps.HOME: {'id': house_ids}})


def move(world, mover_ids):
    """Moving households seek a home that can feed them."""
    if len(mover_ids) == 0:
        return
    _move_out(world, mover_ids)
    mover_ids, farm_ids = _find_farm(world, mover_ids)
    _start_farm(world, mover_ids, farm_ids)
    home_ids = _find_home(world, mover_ids, farm_ids)
    _move_in(world, mover_ids, home_ids)


def load_terrain(terrain_file, min_year, soil_quality_variance=0.2, coeff_var=0.2, transpose=True):
    print("loading terrain array")
    terrain_array = np.load(terrain_file)
    soil_quality = np.random.normal(1, soil_quality_variance, size=terrain_array[0].shape)
    terrain_array *= soil_quality[np.newaxis, ...]
    dat = []
    print("dataframify")
    for (t, x, y), val in tqdm(np.ndenumerate(terrain_array)):
        dat.append({'year': t + min_year, 'x': x, 'y': y, 'mean': val})
    terrain_data = pd.DataFrame(dat)
    if transpose:
        terrain_data[['x', 'y']] = terrain_data[['y', 'x']]
    terrain_data['var'] = terrain_data['mean'] * coeff_var
    return terrain_data


def _get_terrain_this_year(world, terrain_data):
    # we should probably have a better way to deal with global vars...
    year = world[comps.TIME].iloc[0].year
    this_year = terrain_data.set_index('year').loc[year].reset_index()
    return {
        comps.YIELD: this_year[['mean', 'var']],
        comps.POSITION: this_year[['x', 'y']]
    }


def initialize_terrain(world, terrain_data):
    terrain = world.add_entities(_get_terrain_this_year(world, terrain_data))
    # it would be neat here to be able to simply say: give this cmponent, with all nil values
    # TODO: test
    world.give(terrain, {comps.OCCUPYING_HOMES: {'num occupants': 0}})


def update_terrain(world, terrain_data):
    terrain = world[(comps.POSITION, comps.YIELD)]
    year = world[comps.TIME].iloc[0].year
    this_year = terrain_data.set_index('year').loc[year].reset_index().set_index(['x', 'y'])
    yields = terrain[comps.YIELD].assign(**terrain[comps.POSITION]).set_index(['x', 'y'])
    yields[['mean', 'var']] = this_year[['mean', 'var']]
    # TODO: this should give a better error message
    # world.update(yields.set_index(terrain.ids))
    # TODO: i've learned that I'm dissatisfied with my ecs
    world.update({comps.YIELD: yields.set_index(terrain.ids)})

# naming convention is all over the place
def eat(world, dt):
    # being able to 'set' the values in the filter may be handy
    # their being slices may be counterintuitive.
    # we'd need some way to know that the corresponding world data
    # has not been updated.
    needs, piles = world[(comps.FOOD_NEEDS, comps.STOCKPILE)].data()
    piles -= needs * dt
    world.update({comps.STOCKPILE: piles})


def initialize(world):
    hhlds = world.add_entities({
        comps.POSITION: {'x': range(100), 'y': range(100)},
        # what were the actual parameters again?
        comps.FOOD_NEEDS: {'grain': 800},
        comps.STOCKPILE: {'grain': 800},})
    world.add_entities(
        {comps.TIME: {'year': [800]}})

    world.terrain_data = load_terrain(
        pkg_resources.resource_filename("anasazi", "yields 800-1349.npy"),
        min_year=800
    )
    initialize_terrain(world, world.terrain_data)
    move(world, hhlds)


def step(world):
    update_terrain(world, world.terrain_data)
    eat(world, 1)
    harvest = harvest_grain(world)
    stock_taking(world, harvest)
    world[comps.TIME]['year'] += 1

from anasazi import ui
