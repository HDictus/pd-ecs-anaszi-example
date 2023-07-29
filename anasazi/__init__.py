import numpy as np
from pathlib import Path
import pandas as pd
import anasazi.components as comp

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
    households = world[(comp.stockpile, comp.farmland)]
    land = world[comp.grain_yield]
    harvest_statistics = land.loc[households[comp.farmland]['id']]
    harvest = np.random.normal(
        harvest_statistics['mean'].values, harvest_statistics['var'].values)
    grain_stockpile = households[comp.stockpile]
    grain_stockpile['grain'] = np.clip(
        grain_stockpile['grain'] + harvest, 0, max_grain_stock)
    world.update({comp.stockpile: grain_stockpile})
    return pd.Series(harvest, index=grain_stockpile.index)


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
    food_needs, stockpiles = world[(comp.food_needs, comp.stockpile)].data()
    # TODO: this assumes that households corresponds to harvest, which is not always guaranteed.
    expects_to_starve = food_needs['grain'] > stockpiles['grain'] + harvest
    world.give(expects_to_starve.index[expects_to_starve], {comp.moving: {}})

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

def _move_out(world, home_ids, farm_ids):
    farms = farm_ids['id'].value_counts()
    homes = home_ids['id'].value_counts()
    world[comp.occupying_farms].loc[farms.index, 'num occupants'] -=\
        farms.values
    world[comp.occupying_houses].loc[homes.index, 'num occupants'] -=\
        homes.values


def _find_home(mover_positions, mover_needs, arable_land):
    positions, yields, occupation, houses = arable_land.data()
    unoccupied = np.logical_and(
        occupation['num occupants'] == 0,
        houses['num occupants'] == 0)
    positions = positions[unoccupied]
    yields = yields[unoccupied]
    displacements = (
        positions.values[np.newaxis, ...]
        - mover_positions.values[..., np.newaxis, :]
    )
    distances = np.linalg.norm(displacements, axis=-1)
    enough_to_survive = (
        yields['mean'].values[np.newaxis, ...]
        >= mover_needs['grain'].values[..., np.newaxis]
    )
    distances[~enough_to_survive] = np.inf
    nearest_farms = []
    for dist in distances:
        if not np.isfinite(dist).any():
            assert False, "lol, TODO"
        nearest = np.argmin(dist)
        distances[:, nearest] = np.inf
        nearest_farms.append(positions.index[nearest])
    return mover_needs.index, nearest_farms


def _move_in(world, household_ids, farm_ids, farm_positions):
    world.give(household_ids, {comp.farmland: {'id': farm_ids}})
    world[comp.occupying_farms].loc[farm_ids] += 1
    # TODO: there is a repeated operation here I should abstract away
    # TODO: should there maybe be a filter???
    positions = farm_positions.loc[farm_ids]
    potential_housing = world[(comp.position, comp.occupying_houses, comp.occupying_farms)]
    house_posns, occupants, farmed = potential_housing.data()

    potential_house_positions = house_posns[farmed['num occupants'] == 0]

    house_to_farm_distance = np.linalg.norm(
        potential_house_positions.values[np.newaxis, ...]
        - positions.loc[farm_ids].values[..., np.newaxis, :],
        axis=-1
        )
    houses = potential_house_positions.iloc[
        np.argmin(house_to_farm_distance, axis=1)]

    house_ids, nhouses = np.unique(houses.index, return_counts=True)
    occupants.loc[house_ids, 'num occupants'] += nhouses
    # there are too many different ways to update the world state
    # this does not make it especially simple
    # getitem is really simple... maybe we should just stick with that?

    world[comp.position].loc[household_ids] = house_posns.loc[house_ids].values
    world.give(household_ids, {comp.home: {'id': house_ids}})
    world.update({comp.occupying_houses: occupants})


def moving_house(world):
    """Moving households seek a home that can feed them."""
    # TODO: I can't entirely explain why, but I have a feeling that it would be a good
    # practice to not have helper functions push changes.
    movers = world[
        (comp.home, comp.farmland, comp.food_needs, comp.moving, comp.position)
    ]
    home_ids, farm_ids, needs, moving, position = movers.data()
    # move out: see this is a fairly generic operation that many systems will need...
    _move_out(world, home_ids, farm_ids)
    arable_land = world[
        (comp.position, comp.grain_yield,
         comp.occupying_farms, comp.occupying_houses)
    ]
    ids, farms = _find_home(position, needs, arable_land)
    _move_in(world, ids, farms, world[comp.position])
