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
    world.give(expects_to_starve.index[expects_to_starve], {comp.moving: {'to_id': np.nan}})

# TODO: a lot of these questions come down to: when should something be passed from function to function, and when should it be stored in the world state.
# Ultimately this depends on whether taht value will be used in the future...
# which depends on other models... ummm

# well, premature optimization is the root of all evil. Cache it all and come up with a method to save on space when it's unused
# for instance, allow world to skip updating particular things, and raise an error when asked for them.

# um no that's utterly fucked.
# you can't create a fresh component for every variable you ever use, that's a nightmare to develop and debug,
# just remember developing harvest, how simple it is and how you would never expect the harvest amount to do anything other than be added to the thing. Make a component for that?
# just make it work for now ok?
