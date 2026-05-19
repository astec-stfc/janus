from math import floor, log10

def round_it(x, sig):
    """Round a numeric value to a given number of significant digits.

    Parameters
    ----------
    x : Any
        The value to round.
    sig : int
        The number of significant digits to preserve.

    Returns
    -------
    float
        The rounded value, or ``0.0`` for ``None`` or zero values.
    """
    if x is None:
        return 0.0
    if float(x) == 0.0:
        return 0.0
    return round(x, sig - int(floor(log10(abs(x)))) - 1)