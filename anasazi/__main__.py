from pd_ecs import World, System, Component
import numpy as np

# for now we just do farming on a random map with random changes

YEARS_PER_SECOND = 100

position = Component("X", "Y")
grain_stockpile = Component("grain")

def initalize_households(world, n_households, initial_grain=20):
    x = np.random.choice(range(world.mapsize[0]), n_households, replace=False)
    y = np.random.choice(range(world.mapsize[1]), n_households, replace=False)
    grain = np.ones((n_households, )) * initial_grain
    world.add_entiies(position=dict(x=x, y=y), grain_stockpile=dict(grain))
    return


class YearSystem(System):
    time = 0
    seconds_to_years = YEARS_PER_SECOND

    @property
    def year(self):
        return self.time * self.seconds_to_years

    def update(self, dt):
        yearbefore = int(np.floor(self.year))
        self.time += dt
        yearafter = int(np.floor(self.year))
        for i in range(yearafter - yearbefore):
            self.world.events.year_passes()


class HarvestSystem(System):

    households = [position, grain_stockpile]

    def __init__(self, world):
        super().__init__(self)
        self.yield_mean = np.random.uniform(0, 10, size=world.mapsize)
        self.yield_std = np.random.uniform(0, 5, size=world.mapsize)

    def calculate_yield(self, x, y):
        means = self.yield_mean[x, y]
        std = self.yield_std[x, y]
        actual = np.random.normal(means, stds)
        actual[actual < 0] = 0
        return actual

    def year_passes(self):
        households = self.households
        harvests = self.calculate_yield(households[position.X], households[position.Y])
        self.households[grain_stockpile.grain] += harvests
        return

class EatingSystem(System):

    households = [position, grain_stockpile]

    food_requirement = 0.5 * YEARS_PER_SECOND

    def update(dt):
        self.households.grain_stockpile.grain -= food_requirement * dt

world = World()
world.mapsize = (100, 100)

EatingSystem(world)
HarvestSystem(world)

initialize_households(world)


import time

prevt = time.clock()
while True:
    currt = time.clock()
    world.update(currt-prevt)
    prevt = currtg
