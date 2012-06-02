

class Entity():
    """
    Class to represent an antity used to hold the information for debtor and
        creditor

    @ivar _name: Entity name
    @type _name: string
    @ivar _address_lines: List of address lines for the entity (max 5 lines)
    @type _address_lines: string
    @ivar _country: Country
    @type _country: string

    """

    def __init__(self, name, country, *adr_lines):
        """
        @param name: string
        @type name: Name of the entity
        @param country: string
        @type country: Entity's country
        @param *adr_lines: Maximum of 5 address-lines. First add street address, then postal code
        @type *adr_lines: string

        @raise IndexError: If the number of address lines passed is over 5
        """
        self._name = name
        self._country = country
        self._address_lines = []
        if len(adr_lines) <= 5:
            for x in adr_lines:
                self._address_lines.append(x)
        else:
            raise IndexError('Too many address lines, maximum allowed is 5')
