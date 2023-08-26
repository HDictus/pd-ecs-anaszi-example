import pd_ecs
import anasazi
from anasazi import components as comps


def test_fission_randomly_at_reproductive_ages():
    world = pd_ecs.World()
    world.add_entities(
        {comps.POSITION: {'x': [1, 2, 3, 4],
                          'y': [1, 2, 3, 4]},
         comps.AGE: {'years': [15, 16, 40, 41]},
         comps.STOCKPILE: {'grain': [40, 20, 50, 60]}}
    )
    
    new = anasazi.households_fission(
        world, min_age=16, max_age=40,
        fertility=1)
    assert len(world[comps.POSITION]) == 6
    assert all(world.loc[new, comps.STOCKPILE.grain] == [10, 25])
    assert all(world.loc[new, comps.AGE.years] == [0, 0])