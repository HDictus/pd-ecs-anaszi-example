Feature: moving

    Scenario: moves when not enough food
    Given there is a landscape
    Given there are some households 
    And the households each own a farm

    When the households expect their next harvest not to be enough

    Then they move to a new farm

