import anasazi
import pd_ecs
import numpy as np
from pathlib import Path
from pytest_bdd import scenario, given, when, then

# TODO: we're facing an issue here, with this.
#  the lack of specificity in the scenario causes us some difficulty
#  if we controlled the specifics of the test case a little more, it would be easier to
#  write this test.
#  however, I think that the idea is that this pays off by making reusable phrases for other tests.
#  let's endure and see.

@scenario('dying.feature', 'vacates farm and house on death')
def test_dying():
    pass

@given("there is a landscape", target_fixture='world')
def initialize_world():
    world = pd_ecs.World()
    anasazi.initialize_terrain(
        world, 
        anasazi.load_terrain(Path(__file__).parent / 'data' / 'yields 800-805.npy', 800))
    return world

@given("there are some households", target_fixture='households')
def init_households(world):
    return anasazi.initialize_households(world, 10)
     
@given("the households each own a farm",  target_fixture='farms')
def own_farms(world, households):
    farms = world[anasazi.comps.MEAN_YIELD].index[:len(households)]
    anasazi._start_farm(world, households, farms)
    return farms


@given("the households each have a house", target_fixture='homes')
def own_house(world, households):
    homes = world[[anasazi.comps.MEAN_YIELD,anasazi.comps.OCCUPYING_HOMES,  ~anasazi.comps.FARMED]].iloc[:len(households)]
    anasazi._move_in(world, households, homes.index)
    return world.loc[homes.index, [anasazi.comps.OCCUPYING_HOMES]]

@when('some of them die', target_fixture="dying")
def some_die(world, households):
    num_dying=2
    dying = world.loc[households[:num_dying], [
        anasazi.comps.FARMLAND, anasazi.comps.HOME]]
    anasazi.die(world, dying.index)
    return dying

@then('their farms should be vacant')
def farms_vacant(world, dying, farms):
    farms = dying[anasazi.comps.FARMLAND]
    assert not any(np.isin(farms, world[anasazi.comps.FARMED].index))


@then('their house should be vacant')
def houses_vacant(world, dying, homes):
    print("!!")
    print(world[[anasazi.comps.MEAN_YIELD, ~anasazi.comps.FARMED, anasazi.comps.OCCUPYING_HOMES]])
    new = world.loc[dying[anasazi.comps.HOME], anasazi.comps.OCCUPYING_HOMES]
    print(world[[anasazi.comps.MEAN_YIELD, ~anasazi.comps.FARMED, anasazi.comps.OCCUPYING_HOMES]])

    assert all(new.values == homes.loc[new.index, anasazi.comps.OCCUPYING_HOMES].values - 1)