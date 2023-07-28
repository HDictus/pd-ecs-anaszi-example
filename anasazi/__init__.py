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
def harvest(world, max_grain_stock=1600):
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


def stock_taking(world):
    """All households predict whether they will have enough food to survive.

    Those which do not expect a large enough harvest next year will move.
    """
    pass
