Feature: moving

    Scenario: moves when not enough food
    Given there is a landscape
    And there are some households 
    And the households each own a farm

    When the households expect their next harvest not to be enough

    Then they move to a new farm

    Scenario: moves to an empty plot with enough food
    Given there is a landscape
    And there are some households
    And the households each own a farm
    And there is some quality farmland available
    
    When some households move

    Then they move to the nearest empty plot with enough yield
    And place a house in the nearest empty spot