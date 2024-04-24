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

@scenario('common_features.feature', 'steps declared in conftest')
@scenario('dying.feature', 'vacates farm and house on death')
def test_dying():
    pass

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
    assert not np.any(np.isin(
        dying[anasazi.comps.HOME],
        world[anasazi.comps.OCCUPYING_HOMES]))