"""All the components for the simulation."""
from pd_ecs import Component
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
# yeah best to stay away from multi-level columns...
POSITION = Component("x", "y", name='position')
# we need to add something to change these things on the fly...
# for isntance from var to cv.
YIELD = Component('mean', 'var', name='yield')
TIME = Component('year', 'month', 'day', name='year')
FOOD_NEEDS = Component('grain', name='yearly food needed (Kg corn)')
STOCKPILE = Component("grain", name='stockpile')
FARMLAND = Component('id', name='farmland')
HOME = Component('id', name='home')
FARMED = Component('is_farmed')
OCCUPYING_HOMES = Component(num='num occupants')
