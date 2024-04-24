import anasazi
from pytest_bdd import scenario, given, when, then


# TODO: I suspect I could just put these steps in an importable module
@scenario('common_features.feature', 'steps declared in conftest')
@scenario('moving.feature', 'moves when not enough food')
def test_moving():
    return


@then('they move to a new farm')
def assert_moved(households, movers):
    assert all(households == movers)


@when('the households expect their next harvest not to be enough', target_fixture='movers')
def harvest_happens(world, households):
    needs = world.loc[households, anasazi.comps.FOOD_NEEDS]
    world.loc[households, anasazi.comps.STOCKPILE] = 0
    harvest =  needs / 4
    movers = anasazi.decide_whether_to_move(world, harvest)
    return movers
