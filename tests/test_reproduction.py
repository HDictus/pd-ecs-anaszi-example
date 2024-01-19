import pd_ecs
import numpy as np
import anasazi
from anasazi import components as comps
from mock import patch


# TODO: I'm trying to figure something out here about testing behavior.
#   the households_fission event calls the households_started event
#   I should be able to test the former's behavior independent of the latter
#   but in the end, what i get out of calling households_fission (an aspect of its behavior)
#   depends on households_started
#   What I want to test below is which households become parents
#   how many children they have or what properties they get is a separate test.

# TODO: when it comes to the dependency inversion principle, to which extent does using other
#   methods as a part of a given method violate that at the function level?
#   say we wanted to be able to replace the households_fission event to behave differently

# TODO: we build a kind of domain-specific language that abstracts e.g. the creation of households
#   the components that make up a household are kind of set here, and if an event needs new components to act on them we just add them
#   but say we separately test an event for creating households and an event for choosing households to fission
#   we make a households abstraction for each of these units
#   this doesn't guarantee they'll work together
#   wtf am I trying to say here?

# TODO: this is most likely an argument for using a separate event manager through which you call events
#  that way you can check that a given event is called with particular arguments.

# TODO: I suppose the question is: are is the households_started event a part of households_fission or not?
#   Arguably, there are two separate events here: choosing parents and creating offspring
#   these always occur together however, and so there should be an extra abstraction that does both.


def test_fission_randomly_at_reproductive_ages():
    """
    Given that there are some households in the valid age range
    When the households_fission event occurs
    Then those households will be parents of new households
    """
    world = pd_ecs.World()
    hhlds = households_of_ages(
        world,
        [15, 16, 40, 41]
    )

    with assert_households_started() as ae:
        new = anasazi.households_fission(
            world, min_age=16, max_age=40,
            fertility=1)
        assert list(ae.parents) == list(hhlds[1:-1])


def test_fission_no_births():
    world = pd_ecs.World()
    households_of_ages(
        world,
        [10, 10, 50, 50]
    )
    with assert_households_started() as ae:
        assert len(ae.call_logger.calls) == 0


def test_children_age_0():
    world = pd_ecs.World()
    hhld = households_of_ages(world, [19])
    child = anasazi.households_started(world, hhld)
    assert np.allclose(world.loc[child, comps.AGE.years].values, 0)


def test_children_keep_food_needs():
    world = pd_ecs.World()
    hhld = households_of_ages(world, [19])
    child = anasazi.households_started(world, hhld)
    assert np.allclose(world.loc[child, comps.FOOD_NEEDS].values, 
                       world.loc[hhld, comps.FOOD_NEEDS].values)


def test_children_get_half_stockpile():
    world = pd_ecs.World()
    hhld = households_of_ages(world, [19])
    hhld_stockpile = world.loc[hhld, comps.STOCKPILE]
    child = anasazi.households_started(world, hhld)
    assert np.allclose(world.loc[hhld, comps.STOCKPILE], hhld_stockpile / 2)
    assert np.allclose(world.loc[child, comps.STOCKPILE], hhld_stockpile / 2)


class _CallLogger:
    
    def __init__(self, mocked):
        self.calls = []
        self.mocked = mocked
    
    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        self.mocked(*args, **kwargs)


def assert_households_started():
    """Tool to check whether and how the households_started event is used"""

    class _AssrtHHLDs:

        mocked = None
        call_logger = None

        def __enter__(self):
            self.mocked = anasazi.households_started
            self.call_logger = _CallLogger(self.mocked)
            anasazi.households_started = self.call_logger
            return self

        def __exit__(self, err, instance, traceback):
            anasazi.households_started = self.mocked
            if err:
                raise instance

        @property
        def parents(self):
            return self.call_logger.calls[0][1]['parents']

    return _AssrtHHLDs()


def households_of_ages(world, ages):
    """Create households of given ages. Other properties are random."""
    new = world.add_entities(
        {comps.AGE: {'years': ages},
         comps.POSITION: {'x': range(len(ages)),
                          'y': range(len(ages))},
         comps.STOCKPILE: {'grain': np.ones(len(ages)) * 10},
         comps.FOOD_NEEDS: {'grain': np.ones(len(ages))}}
    )
    return new