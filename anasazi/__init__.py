import numpy as np
from pathlib import Path
import pandas as pd
import pkg_resources
from tqdm import tqdm
import anasazi.components as comp

# BIG TODO: revisit this with the goal of writing out the optimal, most sensical way of doing it instead of a working implementattion

# I think the choices of components here illustrate just how not-immune an ECS is to adding logic assumptions into the data
# ....
# what if a thingy has multiple stockpiles (storage locations) e.g. for different goods?
# TODO: we really need a naming convention for components.
# or a namespace...


# TODO: if we want integrate arbitrary models, things like max_grain_stock need to be components
#   or part of the stockpile component
# then, we need some means to efficiently query the stockpile.
def harvest_corn(world, max_grain_stock=1600):
    """All households harvest grain.

    Part of the artificial anasazi model. The annual harvest is sampled from a normal
    distribution where the center is grain_yield['mean'] and scale is grain_yield['var']
    """
    households = world[[corn_stockpile, farmland]]
    land = world[[corn_yield_mean, corn_yield_var]]
    harvest_stats = land.loc[households[farmland], [corn_yield_mean, corn_yield_var]]
    harvest = np.random.normal(
        harvest[corn_yield_mean], harvest[corn_yield_var])
    households[corn_stockpile] += np.clip(harvest, 0, world[max_stockpile])
    world.loc[households.index, corn_stockpile] = households[corn_stockpile]
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
    households = world[[food_needs, corn_stockpile]]
    expects_to_starve = households[food_needs] > (households[corn_stockpile] + harvest)
    # TODO: this assumes that households corresponds to harvest, which is not always guaranteed.
    expects_to_starve = food_needs['grain'] > stockpiles['grain'] + harvest
    # TODO: this is increasingly indicating that these need to be methods of an object,
    #    one with access to world.
    # perhaps world itself.
    move(world, households[expects_to_starve].index())

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

def _move_out(world, movers):
    world[occupying_farms].loc[world.loc[movers, farmland]] -= 1
    world[occupying_homes].loc[world.loc[movers, home]] -= 1
    del world.loc[movers, [farmland, home]]

def _find_farm(world, movers):
    # TODO: we should use numba.njit for this tbh
    # TODO: or a matching algorithm, only then it's not strictly speaking artifical anasazi...
    unoccupied_land = world[[grain_yield, position, ~occupying_houses, ~farmed]].index
    distances = _calculate_distances_matrix(
        world.loc[movers, [position]]
        world.loc[land.index, position])
    enough_to_survive = world.loc[unoccupied_land, mean_corn_yield].values[np.newaxis, ...]\
        >= world.loc[movers, food_needs].values[..., np.newaxis]
    distances[~enough_to_survive] == np.inf

    nearest_farms = []

    for dist in distances:
        if not np.isfinite(dist).any():
            # assert False, "lol, TODO"
            pass
        nearest = np.argmin(dist)
        distances[:, nearest] = np.inf
        nearest_farms.append(unoccupied_land[nearest])
    return movers, nearest_farms


def _start_farm(world, mover_ids, farm_ids):
    world.loc[households, farmland] = farm_ids
    world.loc[farm_ids, farmed] = household_ids


def _find_home(world, mover_ids, farm_ids):
    potential_housing = world[[position, occupying_houses, ~farmed]]
    
    house_to_farm_distance = _calculate_distance_matrix(
        potential_housing[position],
        - world.loc[farm_ids, position].values[..., np.newaxis, :])
    houses = potential_house_positions.iloc[
        np.argmin(house_to_farm_distance, axis=1)
    ]

    house_ids, nhouses = np.unique(houses.index, return_counts=True)
    return houses.index


def _move_in(world, household_ids, house_ids):
    unique_ids, house_counts = np.unique(house_ids, return_counts=True)
    world.loc[unique_ids, occupying_homes] += house_counts
    # there are too many different ways to update the world state
    # this does not make it especially simple
    # getitem is really simple... maybe we should just stick with that?
    world.loc[household_ids, position] = world.loc[house_ids, position]
    world.loc[household_ids, home] = house_ids


def moving_house(world, mover_ids):
    """Moving households seek a home that can feed them."""
    _move_out(world, movers.ids)
    mover_ids, farm_ids = _find_farm(world, mover_ids)
    _start_farm(world, mover_ids, farm_ids)
    _find_home(world, mover_ids, farm_ids)
    _move_in(world, ids, farms, world[comp.position])


def load_terrain(terrain_file, min_year, soil_quality_variance=0.2, coeff_var=0.2):
    print("loading terrain array")
    terrain_array = np.load(terrain_file)
    soil_quality = np.random.normal(1, soil_quality_variance, size=terrain_array[0].shape)
    terrain_array *= soil_quality[np.newaxis, ...]
    dat = []
    print("dataframify")
    for (t, x, y), val in tqdm(np.ndenumerate(terrain_array)):
        dat.append({'year': t + min_year, 'x': x, 'y': y, 'mean': val})
    terrain_data = pd.DataFrame(dat)

    terrain_data['var'] = terrain_data['mean'] * coeff_var
    return terrain_data


def _get_terrain_this_year(world, terrain_data):
    # we should probably have a better way to deal with global vars...
    year = world[comp.time].iloc[0].year
    this_year = terrain_data.set_index('year').loc[year].reset_index()
    return {
        comp.grain_yield: this_year[['mean', 'var']],
        comp.position: this_year[['x', 'y']]
    }


def initialize_terrain(world, terrain_data):
    terrain = world.add_entities(_get_terrain_this_year(world, terrain_data))
    # it would be neat here to be able to simply say: give this cmponent, with all nil values
    # TODO: test
    world.give(terrain, {comp.occupying_farms: {'num occupants': 0},
                         comp.occupying_houses: {'num occupants': 0}})


def update_terrain(world, terrain_data):
    terrain = world[(comp.position, comp.grain_yield)]
    year = world[comp.time].iloc[0].year
    this_year = terrain_data.set_index('year').loc[year].reset_index().set_index(['x', 'y'])
    yields = terrain[comp.grain_yield].assign(**terrain[comp.position]).set_index(['x', 'y'])
    yields[['mean', 'var']] = this_year[['mean', 'var']]
    # TODO: this should give a better error message
    # world.update(yields.set_index(terrain.ids))
    # TODO: i've learned that I'm dissatisfied with my ecs
    world.update({comp.grain_yield: yields.set_index(terrain.ids)})

# naming convention is all over the place
def eat(world, dt):
    # being able to 'set' the values in the filter may be handy
    # their being slices may be counterintuitive.
    # we'd need some way to know that the corresponding world data
    # has not been updated.
    needs, piles = world[(comp.food_needs, comp.stockpile)].data()
    piles -= needs * dt
    world.update({comp.stockpile: piles})


def initialize(world):
    hhlds = world.add_entities({
        comp.position: {'x': range(100), 'y': range(100)},
        # what were the actual parameters again?
        comp.food_needs: {'grain': 800},
        comp.stockpile: {'grain': 800},
        comp.moving: {}})
    world.add_entities(
        {comp.time: {'year': [800]}})

    world.terrain_data = load_terrain(
        pkg_resources.resource_filename("anasazi", "yields 800-1349.npy"),
        min_year=800
    )
    initialize_terrain(world, world.terrain_data)
    moving_house(world)


def step(world):
    update_terrain(world, world.terrain_data)
    eat(world, 1)
    harvest = harvest_grain(world)
    stock_taking(world, harvest)
    moving_house(world)
    world[comp.time]['year'] += 1

from anasazi import ui
