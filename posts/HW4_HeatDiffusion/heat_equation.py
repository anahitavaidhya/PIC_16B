import numpy as np
import scipy.sparse as sp
import jax.numpy as jnp
from jax import jit
from jax.experimental import sparse

@jit
def advance_time_matvecmul(A, u, epsilon):
    """Advances the simulation by one timestep, using matrix-vector multiplication
    
    Args:
        A: The 2d finite difference matrix, N^2 x N^2. 
        u: N x N grid state at timestep k.
        epsilon: stability constant.

    Returns:
        N x N Grid state at timestep k+1.
    """
    
    N = u.shape[0]
    u = u + epsilon * (A @ u.flatten()).reshape((N, N))
    return u

def get_A(N):
    """
    Constructs the 2D finite difference matrix A for the heat equation.
    
    Args:
        N (int): Grid size (NxN).
        
    Returns:
        A (numpy.ndarray): Finite difference matrix of size (N^2 x N^2).
    """
    # Total number of points in the grid
    n = N * N  
    diagonals = [
        -4 * np.ones(n),
        np.ones(n - 1),
        np.ones(n - 1),
        np.ones(n - N),
        np.ones(n - N)
    ]
    
    # Set zero at the right boundary to avoid wrap-around
    diagonals[1][(N-1)::N] = 0
    diagonals[2][(N-1)::N] = 0
    
    # Construct the matrix
    A = (
        np.diag(diagonals[0]) + 
        np.diag(diagonals[1], 1) + np.diag(diagonals[2], -1) +  
        np.diag(diagonals[3], N) + np.diag(diagonals[4], -N)
    )
    
    return A

def get_sparse_A(N):
    """
    Returns the finite difference matrix A in a sparse format compatible 
    with JAX.
    
    Args:
        N (int): The size of the grid (NxN).
        
    Returns:
        A_sp_matrix: The sparse finite difference matrix A in BCOO format,  
                     which is efficient for sparse matrix operations in JAX.
    """
    dense_matrix = jnp.array(get_A(N))

    # Convert to sparse BCOO format
    A_sp_matrix = sparse.BCOO.fromdense(dense_matrix)
    
    return A_sp_matrix


def advance_time_numpy(u, epsilon):
    """
    Advances the simulation of heat diffusion by one timestep using 
    explicit indexing and zero-padding.
    
    Args:
        u (numpy.ndarray): N x N grid state at timestep k.
        epsilon (float): Stability constant.
    
    Returns:
        numpy.ndarray: N x N Grid state at timestep k+1.
    """
    # Pad the input array with zeros (1 layer around the grid)
    padded = np.pad(u, pad_width=1, mode='constant', constant_values=0)

    # Compute the Laplacian
    laplacian = (
        # Shift down
        padded[2:, 1:-1] +  
        # Shift up
        padded[0:-2, 1:-1] +  
        # Shift right
        padded[1:-1, 2:] +  
        # Shift left
        padded[1:-1, 0:-2] -
        # Center
        4 * u  
    )

    # Update
    u_new = u + epsilon * laplacian

    return u_new

@jit
def advance_time_jax(u, epsilon):
    """
    Advances the heat equation using jax.numpy with explicit slicing.
    
    Args:
        u (jax.numpy.ndarray): N x N grid state at timestep k.
        epsilon (float): Stability constant.
    
    Returns:
        jax.numpy.ndarray: N x N Grid state at timestep k+1.
    """
    # Pad the input array with zeros
    padded = jnp.pad(u, pad_width=1, mode='constant', constant_values=0)

    # Compute the Laplacian using slicing
    laplacian = (
        padded[2:, 1:-1] +  # Shift down
        padded[0:-2, 1:-1] +  # Shift up
        padded[1:-1, 2:] +  # Shift right
        padded[1:-1, 0:-2] -  # Shift left
        4 * u  # Center
    )

    # Update with forward Euler step
    u_new = u + epsilon * laplacian

    return u_new