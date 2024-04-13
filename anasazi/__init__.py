import numpy as np
from pathlib import Path
import pandas as pd
import pkg_resources
from tqdm import tqdm
import scipy
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
    households = world[[comps.STOCKPILE, comps.FARMLAND]]
    farms = world[comps.YIELD].loc[households[comps.FARMLAND]]
    harvest = np.random.normal(
        farms[comps.MEAN_YIELD].values, farms[comps.VAR_YIELD].values)
    households[comps.STOCKPILE] += np.maximum(harvest, 0)
    households[comps.STOCKPILE] = np.minimum(households[comps.STOCKPILE], max_grain_stock)
    world.loc[households.index, comps.STOCKPILE] = households[comps.STOCKPILE]
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
    expected_food = households[comps.STOCKPILE] + harvest
    expects_to_starve = households[comps.FOOD_NEEDS]\
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
    del world.loc[have_farm, comps.FARMLAND]
    have_home = world[comps.HOME].index.intersection(movers)
    if len(have_home) == 0:
        return
    del world.loc[have_home, comps.HOME]


def _find_farm(world, movers):
    # TODO: we should use numba.njit for this tbh
    # TODO: or a matching algorithm, only then it's not strictly speaking artifical anasazi...
    # TODO: scipy.kdtree would speed things up too.
    # TODO: I think I understand now the logic of grouping multiple events into system objects
    #  say we wanted to use a KDTree here for efficiency - and say that it were most efficient
    #  to add/remove from the KDTree whenever a piece of land becomes occupied/unoccupied
    #  Then the logic of the e.g. 'die' event becomes entangled with the implementation of 
    #  the _find_farm method, and so it makes sense to separate the parts relating to that
    #  implementation in their own object.
    # TODO: The issue I see however, is that this makes the implementation dictate the usage
    #   of a given system. Now we have to initialize and object and register and call its various
    #   events. 
    # TODO: we could instead make use of the data abstraction capabilities of pd_ecs
    #   In the same module as farm finding we can register a 'setter' method that registers when
    #   farmland becomes available and adds it to the kdtree.
    #   But for this we need to be able to register multiple 'setters' for a given object
    #   and this should only be added if the system is actually to be run, which leads us to the same problems
    # TODO: Another option might be to only use the most efficient implementation that preserves ideal usage
    #   indeed, we do not know a priori if it is faster to add things to the KDTree all the time, or only
    #   when we are about to use it. To complicate the usage in general, throughout the program, for a 'maybe'
    #   is a shame. Even if we try it and find the less user-friendly implementation is faster, we do not know
    #   for sure that a more user-friendly, faster implementation will occur to us in the future.
    # TODO: the following line is bugged in pd_ecs - identify and fix
    # unoccupied_land = world[comps.POSITION + [~comps.OCCUPYING_HOMES, comps.MEAN_YIELD, ~comps.FARMED]]
    unoccupied_land = world[comps.POSITION + [comps.MEAN_YIELD, ~comps.OCCUPYING_HOMES, ~comps.FARMED]]
    tree = scipy.spatial.KDTree(unoccupied_land[comps.POSITION].values)
    mover_positions = world.loc[movers, comps.POSITION]
    dists, nearest = tree.query(mover_positions.values, min(50, len(unoccupied_land)))
    mover_needs = world.loc[movers, comps.FOOD_NEEDS]
    nearest_yields = unoccupied_land.iloc[nearest.flatten()][comps.MEAN_YIELD].values.reshape(nearest.shape)
    enough_to_survive = nearest_yields >= mover_needs.values[:, np.newaxis]
    
    already_taken = set()
    farm_nums = pd.Series({})
    for mover, farms, enough in zip(movers, nearest, enough_to_survive):
        farm_num = _first_free_farm(mover, farms[enough], already_taken)
        farm_nums[mover] = farm_num
    
    going_to_die = farm_nums.index[farm_nums == -1]
    farm_nums = farm_nums[farm_nums != -1]
    farm_ids = pd.Series(unoccupied_land.index[farm_nums], index=farm_nums.index)

    world.remove_entities(going_to_die)
    return farm_ids.index, farm_ids.values

def _first_free_farm(mover, farm_nums, already_taken: set):
    for farm_num in farm_nums:
        if farm_num not in already_taken:
            already_taken.add(farm_num)
            return farm_num
    return -1

def _start_farm(world, mover_ids, farm_ids):
    # TODO: would be cooler if we could 'give' with .loc
    world.give(mover_ids, {
        comps.FARMLAND: farm_ids})

def _find_home(world, mover_ids, farm_ids):
    potential_housing = world[
        comps.POSITION + [~comps.FARMED]]

    house_to_farm_distance = _calculate_distances_matrix(
        potential_housing[comps.POSITION].values,
        world.loc[farm_ids, comps.POSITION].values)
    houses = potential_housing.iloc[
        np.argmin(house_to_farm_distance, axis=0)
    ]
    incorner = np.logical_and(
        houses[comps.X] < 10,
        houses[comps.Y] < 10
    )
    return houses.index


def _move_in(world, household_ids, house_ids):
    unique_ids, house_counts = np.unique(house_ids, return_counts=True)
    # there are too many different ways to update the world state
    # this does not make it especially simple
    # getitem is really simple... maybe we should just stick with that?
    world.loc[household_ids, comps.POSITION] = world.loc[house_ids, comps.POSITION].values
    world.give(household_ids, {comps.HOME: house_ids})


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
    soil_quality = np.maximum(0, np.random.normal(
        1, soil_quality_variance, terrain_array[0].shape))
    terrain_array *= soil_quality[np.newaxis]
    flat_mean = terrain_array.flatten()
    t, x, y = np.unravel_index(
        np.arange(len(flat_mean)), terrain_array.shape)
    dataframe = pd.DataFrame({
        'mean': flat_mean,
        'var': flat_mean * coeff_var,
        'year': t + 800,
        'x': x,
        'y': y
    })
    return dataframe.set_index(['year', 'x', 'y'])

def initialize_terrain(world, terrain_data, year=800):
    xy = terrain_data.loc[year].reset_index()[['x', 'y']]
    terrain_state = pd.DataFrame(
        {
        comps.X: xy['x'],
        comps.Y: xy['y'],
        comps.MEAN_YIELD: terrain_data.loc[year, 'mean'].values,
        comps.VAR_YIELD: terrain_data.loc[year, 'var'].values,
    })
    terrain = world.add_entities(terrain_state)
    return terrain


def update_terrain(world, terrain_data):
    # TODO: it would be way better to use the historical rainfall data
    #  directly and convert that to annual yield in this process.
    terrain = world[comps.POSITION +  comps.YIELD]
    year = world[comps.YEAR].iloc[0]
    this_year = terrain_data.loc[year]
    yields = terrain[comps.YIELD].assign(x=terrain[comps.X], y=terrain[comps.Y]).set_index(['x', 'y'])
    yields[[comps.MEAN_YIELD, comps.VAR_YIELD]] = this_year[['mean', 'var']]
    # TODO: this should give a better error message
    # world.update(yields.set_index(terrain.ids))
    # TODO: i've learned that I'm dissatisfied with my ecs
    world.update(yields.set_index(terrain.index))

# naming convention is all over the place
def eat(world, dt):
    # being able to 'set' the values in the filter may be handy
    # their being slices may be counterintuitive.
    # we'd need some way to know that the corresponding world data
    # has not been updated.
    needs, piles = world[comps.FOOD_NEEDS], world[comps.STOCKPILE]
    piles -= needs * dt
    world.update({comps.STOCKPILE: piles})


def starve(world):
    stockpiles = world[[comps.FOOD_NEEDS, comps.STOCKPILE]]
    world.remove_entities(
        stockpiles.index[
            stockpiles[comps.FOOD_NEEDS] 
            > stockpiles[comps.STOCKPILE]]
    )


def die(world, households):
    farmland = world.loc[households, comps.FARMLAND]
    homes = world.loc[households, comps.HOME]
    del world.loc[households]
    # TODO: allow using del instead of remove
    # del world.loc[farmland, comps.FARMED]


def households_fission(
    world,
    min_age=16, 
    max_age=40, 
    fertility=0.1
):
    # TODO: assemble event from sub-events pre-initialized with parameters.
    fissions = choose_fissioning_households(world, min_age=min_age, max_age=max_age, fertility=fertility)
    new = households_started(world, parents=fissions)
    return new


def choose_fissioning_households(world, min_age=16, max_age=40, fertility=0.1):
    households_of_age = _households_between_ages(world, min_age, max_age)
    fissions = households_of_age[
        np.random.uniform(0, 1, len(households_of_age)) < fertility]
    world.loc[fissions.index, comps.STOCKPILE] /= 2
    return fissions.index


def _households_between_ages(world, min_age, max_age):
    households = world[[
        comps.AGE, comps.X, comps.Y, comps.STOCKPILE
        ]]
    households_of_age = households[
        np.logical_and(
            households[comps.AGE] >= min_age,
            households[comps.AGE] <= max_age
        )
    ]
    return households_of_age


def households_started(world, parents):
    new = world.add_entities({
        comps.X: world.loc[parents, comps.X],
        comps.Y: world.loc[parents, comps.Y],
        comps.AGE: 0,
        comps.STOCKPILE: world.loc[parents, comps.STOCKPILE] / 2,
        comps.FOOD_NEEDS: world.loc[parents, comps.FOOD_NEEDS]
    })
    world.loc[parents, comps.STOCKPILE] /= 2
    return new


def initialize(world):
  
    world.add_entities({comps.YEAR: [800]})

    world.terrain_data = load_terrain(
        pkg_resources.resource_filename("anasazi", "yields 800-1349.npy"),
        min_year=800
    )
    initialize_terrain(world, world.terrain_data)

    N = 100
    hhlds = initialize_households(world, N)
    move(world, hhlds)


def initialize_households(world, N):
    minp = world[comps.POSITION].min()
    maxp = world[comps.POSITION].max()
    hhlds = world.add_entities({
        comps.X: np.random.uniform(minp[comps.X], maxp[comps.X], size=N),
        comps.Y: np.random.uniform(minp[comps.Y], maxp[comps.Y], size=N),
        # what were the actual parameters again?
        comps.AGE: np.random.uniform(0, 50, size=N),
        comps.FOOD_NEEDS: 800,
        comps.STOCKPILE:  800})
    return hhlds


def step(world):
    update_terrain(world, world.terrain_data)
    harvest = harvest_grain(world)
    stock_taking(world, harvest)
    starve(world)
    eat(world, 1)
    new = households_fission(world)
    move(world, new)
    years = world[comps.YEAR]
    world.loc[years.index, comps.YEAR] = years + 1
    ages = world[comps.AGE]
    world.loc[ages.index, comps.AGE] = ages + 1
    # TODO: this should be ok to do IMO
    # world[comps.YEAR] += 1
    # world[comps.AGE] += 1

    world.remove_entities(
        world[comps.AGE].index[world[comps.AGE] > 60]
    )


from anasazi import ui
