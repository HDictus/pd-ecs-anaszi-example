import anasazi
import numpy as np
import pandas as pd
from pytest_bdd import scenario, given, when, then


# TODO: I suspect I could just put these steps in an importable module
@scenario('common_features.feature', 'steps declared in conftest')
@scenario('moving.feature', 'moves when not enough food')
def test_move_when_food():
    return

@scenario('common_features.feature', 'steps declared in conftest')
@scenario("moving.feature", "moves to an empty plot with enough food")
def test_move_to_close():
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


@given("there is some quality farmland available")
def good_farmland(world):
    households = world[[anasazi.comps.FOOD_NEEDS] + anasazi.comps.POSITION]
    food_needs = households[anasazi.comps.FOOD_NEEDS]
    mins = households[anasazi.comps.POSITION].min().values
    maxs = households[anasazi.comps.POSITION].max().values
    world.add_entities(
        pd.DataFrame({
            anasazi.comps.X: np.random.uniform(mins[0], maxs[0], size=40),
            anasazi.comps.Y: np.random.uniform(mins[1], maxs[1], size=40),
            anasazi.comps.MEAN_YIELD: food_needs.max() * 2,
            anasazi.comps.VAR_YIELD: 5,
        })
    )

@when("some households move", target_fixture='original_positions')
def household_moves(world, households):
    movers = households[:3]
    original_positions = world.loc[movers, anasazi.comps.POSITION + [anasazi.comps.FOOD_NEEDS]]
    anasazi.move(world, movers)
    return original_positions


@then('they move to the nearest empty plot with enough yield')
def household_movers(world, original_positions):
    previous_position = original_positions[anasazi.comps.POSITION]
    movers = original_positions.index
    target_farms = world[anasazi.comps.POSITION + [anasazi.comps.MEAN_YIELD]]#, ~anasazi.comps.FARMED]]
    # TODO: manage farmed land in other test cases
    expected = []
    for mover, posn in previous_position.iterrows():
        need = original_positions.loc[mover, anasazi.comps.FOOD_NEEDS]
        ok = target_farms[target_farms[anasazi.comps.MEAN_YIELD] >= need]
        distances = np.linalg.norm(ok[anasazi.comps.POSITION] - posn, axis=1)
        nearest = ok.index[np.argmin(distances)]
        target_farms = target_farms[target_farms.index != nearest]
        expected.append(nearest)

    assert np.isin(movers, world.index).all()
    farms = world.loc[movers, anasazi.comps.FARMLAND]
    assert all(farms == expected)
