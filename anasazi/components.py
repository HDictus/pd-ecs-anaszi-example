"""All the components for the simulation."""
import pandas as pd
from pd_ecs import Component, gets, sets


# TODO: should I really group things together like this, or would it be best to
#   have each component be on its own?
# we should make first positional argument name, then all kwargs can be e.g. POSITION.X which gives us the tuple
# these should not be grouped together per se...
# hoever this is way more concise....
# maybe strings is enough??????
# like terms... then it ca register whenever something is off???
# aaarrrgghhhh!!!
# which one is simpler?
# it is pretty neat to have position, x and y grouped together s.t. you can do position += velocity...
# but that can be just as easily addressed with POSITION=[POSITION_X, POSITION_Y].
# What about properties that can/should be calculated together from other properties?
#   well, we just need the ability to specify setters/getters for multiple properties together.
# yeah best to stay away from multi-level columns...
X = Component('x', int)
Y = Component('y', int)
POSITION = [X, Y]
# we need to add something to change these things on the fly...
# for isntance from var to cv.
MEAN_YIELD = Component('mean_yeild', float)
VAR_YIELD = Component('var yield', float)
YIELD = [MEAN_YIELD, VAR_YIELD]

YEAR = Component('year', int)
FOOD_NEEDS = Component('corn needed (Kg)')
STOCKPILE = Component("corn stockpike (Kg)")
FARMLAND = Component('farm owned', int)
HOME = Component('home', int)

FARMED = Component('is_farmed')

WATER_SOURCE = Component("water source id")

@gets(FARMED)
def farmed_by_a_farmer(world):
    return pd.Series(True, index=world[FARMLAND], name=FARMED)


@sets(FARMED)
def farmers_that_just_farm(world, index, values):
    world.add_entities({FARMLAND: index})


OCCUPYING_HOMES = Component('occupying homes')
@gets(OCCUPYING_HOMES)
def occupied_by_household(world):
    series = world[HOME].value_counts()
    return pd.Series(
        series.values,
        index=series.index.values,
        name=OCCUPYING_HOMES
    )


AGE = Component('age (years)')
