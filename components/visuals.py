import plotly.graph_objects as go
import numpy as np

def create_pl_stress_test(current_price: float, strike_price: float, premium: float, option_type: str = 'call'):
    """
    Creates a P/L stress testing line chart for the Volatility Lab.
    """
    price_range = np.linspace(current_price * 0.7, current_price * 1.3, 100)
    
    if option_type.lower() == 'call':
        payoff = np.maximum(price_range - strike_price, 0) - premium
    else:
        payoff = np.maximum(strike_price - price_range, 0) - premium

    fig = go.Figure()
    
    # Plot the P/L line
    fig.add_trace(go.Scatter(
        x=price_range, 
        y=payoff, 
        mode='lines',
        name='P/L',
        line=dict(color='#00ffcc', width=3)
    ))
    
    # Add horizontal zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Breakeven")
    
    # Add vertical line for current price
    fig.add_vline(x=current_price, line_dash="dot", line_color="white", annotation_text="Current Price")

    fig.update_layout(
        title="P/L Stress Test",
        xaxis_title="Underlying Price at Expiration",
        yaxis_title="Profit / Loss",
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def create_volatility_surface(surface_data: list, current_price: float):
    """
    Creates an interactive 3D Volatility Surface from real market data.
    """
    if not surface_data:
        return create_volatility_surface_placeholder()

    import pandas as pd
    from scipy.interpolate import griddata

    df = pd.DataFrame(surface_data)
    
    # Filter for strikes near the money for a better visual
    df = df[(df['strike'] > current_price * 0.7) & (df['strike'] < current_price * 1.3)]
    
    # Create a grid
    ti = np.linspace(df['dte'].min(), df['dte'].max(), 30)
    ki = np.linspace(df['strike'].min(), df['strike'].max(), 30)
    T, K = np.meshgrid(ti, ki)
    
    # Interpolate IV onto the grid
    Zi = griddata((df['dte'], df['strike']), df['iv'], (T, K), method='linear')

    fig = go.Figure(data=[go.Surface(
        z=Zi, x=T, y=K, 
        colorscale='Viridis',
        colorbar_title="IV"
    )])
    
    fig.update_layout(
        title="Live Implied Volatility Surface",
        scene=dict(
            xaxis_title="Time to Expiration (Years)",
            yaxis_title="Strike Price",
            zaxis_title="Implied Volatility",
            xaxis=dict(backgroundcolor="rgb(20, 20, 20)", gridcolor="gray", showbackground=True),
            yaxis=dict(backgroundcolor="rgb(20, 20, 20)", gridcolor="gray", showbackground=True),
            zaxis=dict(backgroundcolor="rgb(20, 20, 20)", gridcolor="gray", showbackground=True),
        ),
        template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

def create_volatility_smile(surface_data: list, current_price: float):
    """
    Creates a 2D Volatility Smile plot for the nearest expiration.
    """
    if not surface_data:
        return go.Figure()

    import pandas as pd
    df = pd.DataFrame(surface_data)
    
    # Get the nearest expiration (minimum DTE)
    min_dte = df['dte'].min()
    df_near = df[df['dte'] == min_dte]
    
    # Filter near the money
    df_near = df_near[(df_near['strike'] > current_price * 0.8) & (df_near['strike'] < current_price * 1.2)]
    df_near = df_near.sort_values('strike')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_near['strike'], 
        y=df_near['iv'], 
        mode='lines+markers',
        line=dict(color='#00ffcc', width=3),
        name=f"Smile ({min_dte*365:.0f} DTE)"
    ))

    fig.update_layout(
        title=f"Volatility Smile: {min_dte*365:.0f} Days to Expiration",
        xaxis_title="Strike Price",
        yaxis_title="Implied Volatility",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_volatility_surface_placeholder():
    """
    Creates a placeholder 3D Volatility Surface plot.
    """
    # Generate dummy data for the placeholder
    x = np.linspace(0.1, 1.0, 20)  # Time to expiration
    y = np.linspace(0.8, 1.2, 20)  # Moneyness (K/S)
    xGrid, yGrid = np.meshgrid(x, y)
    
    # Simulating an implied volatility smile/skew
    z = 0.2 + 0.1 * (yGrid - 1.0)**2 + 0.05 * np.exp(-xGrid)
    
    fig = go.Figure(data=[go.Surface(z=z, x=xGrid, y=yGrid, colorscale='Viridis')])
    
    fig.update_layout(
        title="Implied Volatility Surface (Placeholder)",
        scene=dict(
            xaxis_title="Time to Expiration (Years)",
            yaxis_title="Moneyness (K/S)",
            zaxis_title="Implied Volatility"
        ),
        template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig
