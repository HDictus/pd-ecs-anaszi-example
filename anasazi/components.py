"""All the components for the simulation."""
from pd_ecs import Component

position = Component("x", "y", name='position')
grain_yield = Component('mean', 'var', name='yield')
food_needs = Component('grain', name='yearly food needed (Kg corn)')
stockpile = Component("grain", name='stockpile')
farmland = Component('id', name='farmland')
home = Component('id', name='home')
occupying_farms = Component('num occupants')
occupying_houses = Component('num occupants')
moving = Component(name="moving")
