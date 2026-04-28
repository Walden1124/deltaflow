import numpy as np
from scipy.stats import norm

def calculate_d1_d2(S, K, T, r, sigma):
  """
  Calculates d1 and d2 parameters for the Black-Scholes model.

  Args:
    S (float): Current stock price
    K (float): Strike price
    T (float): Time to expiration (in years)
    r (float): Risk-free interest rate (annualized)
    sigma (float): Implied volatility (annualized)

  Returns:
    tuple: (d1, d2)
  """
  # Handle the case where T is exactly 0 to avoid division by zero
  if T <= 0.0:
    T = 1e-10

  d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
  d2 = d1 - sigma * np.sqrt(T)
  return d1, d2

def black_scholes_price(option_type, S, K, T, r, sigma):
  """
  Calculates the theoretical price of an option using the Black-Scholes model.

  Args:
    option_type (str): 'call' or 'put'
    S (float): Current stock price
    K (float): Strike price
    T (float): Time to expiration (in years)
    r (float): Risk-free interest rate (annualized)
    sigma (float): Implied volatility (annualized)

  Returns:
    float: Option price
  """
  if T <= 0.0:
    return max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)

  d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
  
  if option_type == 'call':
    price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
  elif option_type == 'put':
    price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
  else:
    raise ValueError("option_type must be 'call' or 'put'")
    
  return price

def calculate_greeks(option_type, S, K, T, r, sigma):
  """
  Calculates the first-order and second-order Greeks.

  Args:
    option_type (str): 'call' or 'put'
    S (float): Current stock price
    K (float): Strike price
    T (float): Time to expiration (in years)
    r (float): Risk-free interest rate (annualized)
    sigma (float): Implied volatility (annualized)

  Returns:
    dict: Dictionary containing Delta, Gamma, Theta, Vega, Rho, Vanna, and Charm.
  """
  if T <= 0.0:
    T = 1e-10

  d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
  
  # Helper components
  N_prime_d1 = norm.pdf(d1)
  N_d1 = norm.cdf(d1)
  N_minus_d1 = norm.cdf(-d1)
  N_d2 = norm.cdf(d2)
  N_minus_d2 = norm.cdf(-d2)
  
  sqrt_T = np.sqrt(T)

  # 1. Delta (Δ)
  if option_type == 'call':
    delta = N_d1
  else:
    delta = N_d1 - 1.0

  # 2. Gamma (Γ) - Same for call and put
  gamma = N_prime_d1 / (S * sigma * sqrt_T)

  # 3. Theta (Θ) - Time decay (annualized, often divided by 365 for daily)
  theta_term1 = -(S * N_prime_d1 * sigma) / (2 * sqrt_T)
  if option_type == 'call':
    theta = theta_term1 - r * K * np.exp(-r * T) * N_d2
  else:
    theta = theta_term1 + r * K * np.exp(-r * T) * N_minus_d2

  # 4. Vega (ν) - Same for call and put (1% change)
  vega = S * N_prime_d1 * sqrt_T / 100.0

  # 5. Rho (ρ) - 1% change
  if option_type == 'call':
    rho = K * T * np.exp(-r * T) * N_d2 / 100.0
  else:
    rho = -K * T * np.exp(-r * T) * N_minus_d2 / 100.0

  # 6. Vanna - Sensitivity of Delta to Volatility
  vanna = -N_prime_d1 * d2 / sigma

  # 7. Charm - Sensitivity of Delta to Time (Delta decay)
  if option_type == 'call':
    charm = -N_prime_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)
  else:
    charm = -N_prime_d1 * (2 * r * T - d2 * sigma * sqrt_T) / (2 * T * sigma * sqrt_T)

  return {
    "delta": delta,
    "gamma": gamma,
    "theta": theta,
    "vega": vega,
    "rho": rho,
    "vanna": vanna,
    "charm": charm
  }
