# -*- coding: utf-8 -*-
"""Testy pytest dla klasy Product.

Uruchomienie: pytest test_product_pytest.py -v
"""

import pytest
from product import Product


# --- Fixture ---

@pytest.fixture
def product():
    """Tworzy instancje Product do testow (odpowiednik setUp)."""
    return Product("Laptop", 2999.99, 10)


# --- Testy z fixture ---

def test_is_available(product):
    assert product.is_available() == True


def test_total_value(product):
    assert product.total_value() == 2999.99 * 10


# --- Testy z parametryzacja ---

@pytest.mark.parametrize("amount, expected_quantity", [
    (5, 15),
    (0, 10),
    (100, 110),
])
def test_add_stock_parametrized(product, amount, expected_quantity):
    product.add_stock(amount)
    assert product.quantity == expected_quantity


# --- Testy bledow ---

def test_remove_stock_too_much_raises(product):
    with pytest.raises(ValueError):
        product.remove_stock(11)


def test_add_stock_negative_raises(product):
    with pytest.raises(ValueError):
        product.add_stock(-1)


# --- Testy apply_discount ---

@pytest.mark.parametrize("percent, expected_price", [
    (0,   100.0),
    (50,   50.0),
    (100,   0.0),
    (25,   75.0),
])
def test_apply_discount(percent, expected_price):
    p = Product("Test", 100.0, 1)
    p.apply_discount(percent)
    assert p.price == expected_price


@pytest.mark.parametrize("bad_percent", [-1, 101, -100])
def test_apply_discount_invalid_raises(bad_percent):
    p = Product("Test", 100.0, 1)
    with pytest.raises(ValueError):
        p.apply_discount(bad_percent)
