from pd_ecs import World, System, Component
import numpy as np
from scipy.ndimage import gaussian_filter

# for now we just do farming on a random map with random changes

YEARS_PER_SECOND = 20

# TODO: better as kwargs name: type?
position = Component("x", "y")
stockpile = Component("grain")


def initialize_households(world, n_households, initial_grain=1600):
    x = np.random.choice(range(world.mapsize[0]), n_households, replace=False)
    y = np.random.choice(range(world.mapsize[1]), n_households, replace=False)
    grain = np.ones((n_households, )) * initial_grain
    households_data = {position: dict(x=x, y=y),
                       stockpile: dict(grain=grain),
                       age: dict(age=np.zeros(x.shape))}
    world.add_entities(
        households_data)
    return


class YearSystem(System):
    time = 0

    def __init__(self, world, start_year=800):
        self.time = start_year / YEARS_PER_SECOND
        super().__init__(world)

    @property
    def year(self):
        return self.time * YEARS_PER_SECOND

    def update(self, dt):
        yearbefore = int(np.floor(self.year))
        self.time += dt
        yearafter = int(np.floor(self.year))
        for i in range(yearafter - yearbefore):
            self.world.events.year_passes()


# TODO: consider systems in isolation, for the needed parameters, what are they to that system?
#    where should they come from?
#    e.g. globals provided at init...
#    or provided to world?


class HarvestSystem(System):

    filters = dict(households = [position, stockpile])

    # min_yield = 0
    # max_yield = 1650

    def __init__(self, world):
        super().__init__(world)
        # self.yield_mean = np.random.uniform(self.min_yield, self.max_yield, size=world.mapsize)
        # self.yield_mean = gaussian_filter(self.yield_mean, sigma=2)
        # self.yield_std = np.random.uniform(0, 100, size=world.mapsize)
        self.yield_by_year = np.load("yields 800-1349.npy")
        self.yield_by_year *= 1 + (np.random.normal(
            0, 0.4, size=self.yield_by_year.shape[1:]))  # TODO: parameterize

    @property
    def yield_mean(self):
        year = int(np.floor(self.world.systems[YearSystem].year))
        start_year = 800  # TODO: more example of mixing responsibilities
        yld = self.yield_by_year[year - 800]
        return yld

    def calculate_yield(self, x, y):
        x = np.int32(np.floor(x))
        y = np.int32(np.floor(y))
        means = self.yield_mean[(x, y)]
        # stds = self.yield_std
        # actual = np.random.normal(means, stds)
        # actual[actual < 0] = 0
        return means

    def mutate_yield(self):
        self.yield_mean += np.random.normal(size=self.yield_mean.shape, scale=0.1)
        # normalized_yield = self.yield_mean - self.yield_mean.mean()
        # self.yield_mean = gaussian_filter(self.yield_mean, sigma=0.01)
        # self.yield_mean += (
        #     0.05 * gaussian_filter(normalized_yield, sigma=0.75)
        #     - 0.01 * normalized_yield**2)
        self.yield_mean[self.yield_mean < 0] = 0

    def year_passes(self):
        # TODO: this could be made better. Ideally we want to only access declared groups.
        # TODO: this is definitely an awkward way to do this. maybe system will automatically refresh after each function call?
        households = self.households.ids
        x = self.world[position].loc[households, 'x']
        y = self.world[position].loc[households, 'y']
        harvests = self.calculate_yield(x, y)
        self.world.events.harvest(harvests)
        # self.mutate_yield()

    def harvest(self, harvests):
        households = self.households.ids
        self.world[stockpile].loc[households, 'grain'] +=\
            harvests
        return


class MovingSystem(System):

    # TODO: can have a maximum distance traveled to keep efficient
    filters=dict(households = [position, stockpile])


    def harvest(self, harvest):
        households = self.households.ids
        need = self.world.systems[EatingSystem].yearly_consumption

        expectation = harvest
        grain = self.world[stockpile].loc[households, 'grain']
        harvest_needed = need - grain
        moving = expectation < harvest_needed
        moving_households = households[moving]
        new_positions = self.new_farmlands(
            moving_households, harvest_needed[moving])
        self.world.events.households_move(moving_households, new_positions)

    def new_farmlands(self, moving_households, harvest_needed):
        yieldmeans = self.world.systems[HarvestSystem].yield_mean
        unoccupied_yields = yieldmeans.copy()
        unoccupied_yields[self.occupation] = -np.inf
        adequate_squares = unoccupied_yields > self.world.systems[EatingSystem].yearly_consumption
        newposns = []
        for harvest_needed, household in zip(
                harvest_needed, moving_households):
            # TODO: I know how to fix
            if adequate_squares.any():
                newposns.append(self.move_to_nearest_adequate(
                    adequate_squares, household, yieldmeans,
                    unoccupied_yields))
            else:
                newposns.append(self.move_to_nearest_adequate(
                    unoccupied_yields > -np.inf,
                    household, yieldmeans,
                    unoccupied_yields))
        return newposns

    def move_to_nearest_adequate(self, adequate_squares, household, yieldmeans,
                                 unoccupied_yields):
        posns = np.transpose(np.nonzero(adequate_squares))
        # TODO: bit of a long way to get components...
        #   ideally we wouldn't need to.
        oldposition = self.world[position].loc[household, ['x', 'y']].values
        dists = np.linalg.norm(np.float32(posns - oldposition), axis=1)
        nearest_posn = posns[np.argmin(dists)]
        self.world[position].loc[household, ['x', 'y']] = nearest_posn
        unoccupied_yields[tuple(oldposition)] = yieldmeans[tuple(oldposition)]
        unoccupied_yields[tuple(nearest_posn)] = -np.inf


class
    @property
    def occupation(self):
        occu = np.zeros(self.world.mapsize, dtype=bool)
        positions = self.world[position].loc[self.households.ids]
        occu[(np.int32(positions['x']), np.int32(positions['y']))] = True
        return occu


class EatingSystem(System):

    filters = dict(households = [position, stockpile])

    yearly_consumption = 160 * 5  # 160 kg of grain p.p., avg 5 per household

    def update(self, dt):
        current_stockpile = self.world[stockpile].loc[self.households.ids, 'grain']
        new_stockpile = current_stockpile - self.yearly_consumption * (dt * YEARS_PER_SECOND)
        starving = current_stockpile.index[new_stockpile < 0]
        self.world[stockpile].loc[self.households.ids, 'grain'] = new_stockpile
        self.world.remove_entities(starving)


import time
import matplotlib.pyplot as plt


# class DeathSystem(System):

#     return


age = Component("age")


class AgeSystem(System):

    filters = dict(ages=[age],
                   households=[age, stockpile])

    move_out_age = 16

    # TODO: fertility, fertility ends age
    death_age = 40
    fertility = 0.155  # chance of having a baby each year

    def year_passes(self):
        """
        Assumptions:
           each household has one child each year after it is established
           every child moves out at 16 years of age
           the child establishes their own household (asexual reproduction)
           every household provides one third of its corn stockpile to the child
           every household dies after exactly 40 years of existing
        # TODO: these various things do not belong in the same system
        #  I would say: fertility age, death age are managed here
        """

        aging_entities = self.ages.ids
        self.world[age].loc[aging_entities, 'age'] += 1
        # TODO: there has to be a way to make the below smoother
        # it shouldn't belong to agesystem
        households = self.households.ids
        moving_out = np.logical_and(
            np.random.uniform(0, 1, size=len(households)) < self.fertility,
            self.world[age].loc[households, 'age'] >= self.move_out_age)
            # self.world[age].loc[households, 'age'] >= self.move_out_age
        # moveout = np.random.uniform(0, 1, size=moving_out) >
        moving_out_ids = self.world[age].loc[households].index[moving_out]

        self.world.events.children_move_out(moving_out_ids)
        too_old = self.world[age].loc[aging_entities, 'age'] >= self.death_age
        too_old_ids = self.world[age].loc[aging_entities].index[too_old]
        self.world.events.death(too_old_ids)

    def death(self, dying):
        self.world.remove_entities(dying)


class MoveOutSystem(System):

    stockpile_gift_fraction = 0.33333

    # TODO: what is actually the best way to handle the creation of new entities?
    #   there may be aspects of a particular type of entity which are determined
    #   independent of any single system...
    def children_move_out(self, moving_out_ids):
        gift = self.world[stockpile].loc[moving_out_ids, 'grain']\
            * self.stockpile_gift_fraction
        self.world[stockpile].loc[moving_out_ids, 'grain'] -= gift
        newdata = {position: self.world[position].loc[moving_out_ids],
                   stockpile: dict(grain=gift),
                   age: dict(age=np.zeros(gift.shape))}
        new = world.add_entities(newdata)

        self.world.events.households_move(new, self.world.systems[EatingSystem].yearly_consumption - gift)




# TODO: best practices for proper separatiion between systems
#


# def scatter_posns(x, y):
#     return -y, x



# TODO: this should be a sysem
# TODO: LOL code duplication between this and next
def plot_world(world):
    # this may be a little confusing wrt the name v.s. the actual column...
    fig = plt.figure()
    ax = fig.gca()
    im = ax.imshow(world.systems[HarvestSystem].yield_mean.transpose(), cmap='RdYlGn')
    scatter = ax.scatter(x=world[position].x,
                         y=world[position].y,
                         s=(world[stockpile].grain / 1500))
    fig.show()
    return fig, ax, scatter, im


def update_plot(fig, ax, scatter, im, world):
    # TODO: we can be more efficient by updating imshow only each year, by making this a system
    im.set(data=world.systems[HarvestSystem].yield_mean.transpose())
    scatter.remove()
    scatter = ax.scatter(x=world[position].x,
                         y=world[position].y,
                         s=world[stockpile].grain / 800,
                         c='b')
    # scatter.set_offsets(np.concatenate([x, y], axis=1))
    # scatter.set_sizes(world.components.stockpile.grain)
    ax.set_title(str(world.systems[YearSystem].year))
    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    return fig, ax, scatter, im


# some duplication here... can we just declare components as Component(name, *things/**things:type)?
world = World(position, stockpile, age)
world.mapsize = (80, 120)

YearSystem(world)
HarvestSystem(world)
EatingSystem(world)
MovingSystem(world)
AgeSystem(world)
MoveOutSystem(world)

initialize_households(world, 80)

plotinfo = plot_world(world)
prevt = time.time()
initt = prevt
while True:
    currt = time.time()
    world.events.update(currt - prevt)
    prevt = currt
    if np.floor(world.systems[YearSystem].year) % 16 == 0:
        plotinfo = update_plot(*plotinfo, world)
        print("population:", world[position].shape[0])
        fields = np.zeros(world.mapsize)
        for _, posn in world[position].iterrows():
            fields[posn['x'], posn['y']] += 1
        print(np.max(fields))

# TODO: parameterize step size
