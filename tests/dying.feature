Feature: Dying

    Scenario: vacates farm and house on death
        Given there is a landscape
        And there are some households
        And the households each own a farm
        And the households each have a house

        When some of them die

        Then their farms should be vacant
        And their house should be vacant