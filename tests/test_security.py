import pytest
from decimal import Decimal
from app.utils import money

def test_money_is_decimal_and_rejects_negative():
    assert money("1000")==Decimal("1000.00")
    with pytest.raises(ValueError): money("-1")
