import unittest
import numpy as np
from engine.calculator import black_scholes_price, calculate_greeks

class TestOptionsCalculator(unittest.TestCase):
    """Test suite for the Options Calculator engine to ensure mathematical accuracy."""

    def setUp(self):
        # Static benchmark inputs
        # Stock: 100, Strike: 100, Time: 1 year, Rate: 5%, Volatility: 20%
        self.S = 100.0
        self.K = 100.0
        self.T = 1.0
        self.r = 0.05
        self.sigma = 0.20

    def test_black_scholes_call_pricing(self):
        """Test Black-Scholes Call option pricing against benchmark."""
        price = black_scholes_price('call', self.S, self.K, self.T, self.r, self.sigma)
        # Expected value approx 10.4506
        self.assertAlmostEqual(price, 10.45058, places=4)

    def test_black_scholes_put_pricing(self):
        """Test Black-Scholes Put option pricing against benchmark."""
        price = black_scholes_price('put', self.S, self.K, self.T, self.r, self.sigma)
        # Expected value approx 5.5735
        self.assertAlmostEqual(price, 5.57352, places=4)

    def test_call_greeks(self):
        """Test Call Greeks calculations against benchmark."""
        greeks = calculate_greeks('call', self.S, self.K, self.T, self.r, self.sigma)
        
        # Benchmark values
        self.assertAlmostEqual(greeks['delta'], 0.63683, places=4)
        self.assertAlmostEqual(greeks['gamma'], 0.01876, places=4)
        self.assertAlmostEqual(greeks['vega'], 0.37524, places=4)
        self.assertAlmostEqual(greeks['rho'], 0.53232, places=4)
        
        # Theta can vary based on whether it's daily or annualized. 
        # The calculator returns annualized theta.
        self.assertAlmostEqual(greeks['theta'], -6.4140, places=3)

    def test_put_greeks(self):
        """Test Put Greeks calculations against benchmark."""
        greeks = calculate_greeks('put', self.S, self.K, self.T, self.r, self.sigma)
        
        self.assertAlmostEqual(greeks['delta'], -0.36317, places=4)
        self.assertAlmostEqual(greeks['gamma'], 0.01876, places=4)
        self.assertAlmostEqual(greeks['vega'], 0.37524, places=4)
        self.assertAlmostEqual(greeks['rho'], -0.41890, places=4)

    def test_zero_dte_handling(self):
        """Test the corner case of 0 days to expiration."""
        price = black_scholes_price('call', 105.0, 100.0, 0.0, self.r, self.sigma)
        self.assertEqual(price, 5.0)  # Intrinsic value
        
        price_out_of_money = black_scholes_price('call', 95.0, 100.0, 0.0, self.r, self.sigma)
        self.assertEqual(price_out_of_money, 0.0)

if __name__ == '__main__':
    unittest.main()
