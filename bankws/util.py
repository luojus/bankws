''' Util module contains some simple utility functions

Check is account number valid IBAN number:
    >>> is_valid_iban(account_number)

Get account number and branch from Finnish account number
    >>> parse_account_number(account_number)

Check is last char correct in means of Luhn modulus 10.
    >>> check_luhn_modulo10(key)
'''
import re


def is_valid_iban(account_number):
    """ Checks if account number is valid IBAN number

    @type  account_number: string
    @param account_number: IBAN account number
    @rtype: boolean
    @return: Is account number valid.
    """
    # Valid (finnish) IBAN number contains 18 numbers
    if len(account_number) != 18:
        return False
    # Add F=15 I=18 00 to string
    number = account_number[4:] + "151800"
    # number should contain only numbers
    if not number.isdigit():
        return False
    # Check number is 98 - number mod 97
    check = "{:0>2}".format(98 - (int(number) % 97))
    # Check that check number is correct.
    if check != account_number[2:4]:
        return False
    return True


def parse_account_number(account_number):
    """ Parses Finnish BBAN and IBAN account number

    @type  account_number: string
    @param account_number: Account number in IBAN or BBAN format
    @rtype: tuple(string, string)
    @return: Returns tuple that contains branch and account number
    @raise ValueError: If account number is not valid.
    """
    if account_number.startswith("FI"):
        # IBAN number
        if not is_valid_iban(account_number):
            raise ValueError("This is not valid IBAN account number.")
        # Drop country code and check number
        account_number = account_number[4:]
    # valid =  [1,2,31,33,34,36,37,38,39,4,5,6,8]
    pat = re.compile(r"""
            (^[^3,7,9]     # String may not start with 3,7,9
            \d{5})         # After first char 5 more digits
            -?             # There can be '-'
            (\d{2,8}$)     # Account number is from 2 to 8 digits
            |              # or
            (^3[^2,5]      # If string starts with it can't cont. with 2 or 5
            \d{4})         # 4 more digits
            -?             # There can be '-'
            (\d{2,8}$)     # 2 to 8 digits
            """, re.VERBOSE)

    match = pat.match(account_number)
    if match is None:
        raise ValueError("Unsupported account number.")

    branch = match.group(1)
    account = match.group(2)
    #fill with zeros
    if branch[0] in ['4', '5']:
        # Banks whose branch starts with 4 and 5.
        # Zero fill is put after 1 character of account number
        account = "{}{:0>7}".format(account[0], account[1:])
    else:
        # Rest banks put zeroes first and then account number
        account = "{:0>8}".format(account)
    if check_luhn_modulo10(branch + account):
        return (branch, account)
    else:
        raise ValueError("Invalid account number: Luhn 10 failed")


def check_luhn_modulo10(key):
    """Calculates luhns modulo 10

    Luhn modulo10 http://en.wikipedia.org/wiki/Luhn_algorithm
    @type  key: string
    @param key: string of numbers.
    @rtype: boolean
    @return: Is key in luhn's modulo 10
    """
    key = str(key)
    try:
        numbers = [int(x) for x in key]  # Convert key to number list
    except ValueError:
        return False
    odd = numbers[::-2]
    even = [sum(divmod(d * 2, 10)) for d in numbers[-2::-2]]
    result = sum(odd + even)
    return (result % 10 == 0)
