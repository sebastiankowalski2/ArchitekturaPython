# -*- coding: utf-8 -*-
"""Testy unittest dla klasy Product -- uzupelnij metody testowe!

Uruchomienie: python -m unittest test_product_unittest -v
"""

import unittest
from product import Product


class TestProduct(unittest.TestCase):

    def setUp(self):
        """Przygotuj instancje Product do testow."""
        self.product = Product("Laptop", 2999.99, 10)

    # --- Testy add_stock ---

    def test_add_stock_positive(self):
        """Sprawdz, czy dodanie towaru zwieksza quantity."""
        self.product.add_stock(5)
        self.assertEqual(self.product.quantity, 15)

    def test_add_stock_negative_raises(self):
        """Sprawdz, czy ujemna wartosc rzuca ValueError."""
        with self.assertRaises(ValueError):
            self.product.add_stock(-1)

    # --- Testy remove_stock ---

    def test_remove_stock_positive(self):
        """Sprawdz, czy usuniecie towaru zmniejsza quantity."""
        self.product.remove_stock(3)
        self.assertEqual(self.product.quantity, 7)

    def test_remove_stock_too_much_raises(self):
        """Sprawdz, czy proba usuniecia wiecej niz jest dostepne rzuca ValueError."""
        with self.assertRaises(ValueError):
            self.product.remove_stock(11)

    def test_remove_stock_negative_raises(self):
        """Sprawdz, czy ujemna wartosc rzuca ValueError."""
        with self.assertRaises(ValueError):
            self.product.remove_stock(-2)

    # --- Testy is_available ---

    def test_is_available_when_in_stock(self):
        """Sprawdz, czy produkt z quantity > 0 jest dostepny."""
        self.assertTrue(self.product.is_available())

    def test_is_not_available_when_empty(self):
        """Sprawdz, czy produkt z quantity == 0 nie jest dostepny."""
        empty_product = Product("Mysz", 99.99, 0)
        self.assertFalse(empty_product.is_available())

    # --- Testy total_value ---

    def test_total_value(self):
        """Sprawdz, czy total_value zwraca price * quantity."""
        self.assertEqual(self.product.total_value(), 2999.99 * 10)


if __name__ == "__main__":
    unittest.main()