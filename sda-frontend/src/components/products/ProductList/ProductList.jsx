import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import ProductCard from '../ProductCard/ProductCard'
import { apiClient, API_ENDPOINTS } from '../../../services/api'
import './ProductList.css'

function ProductList() {
  const { category } = useParams()
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Enhanced filters
  const [sortBy, setSortBy] = useState('name-asc') // 'name-asc', 'name-desc', 'price-asc', 'price-desc'
  const [stockStatus, setStockStatus] = useState('all') // 'all', 'in-stock', 'out-of-stock'
  const [maxPrice, setMaxPrice] = useState('')

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // Build URL based on whether category is provided
        let url
        if (category) {
          // Use category-specific endpoint: /api/products/category/{category}/
          url = `http://localhost:8000/api/products/category/${category}/`
        } else {
          // Use general list endpoint
          url = API_ENDPOINTS.PRODUCTS.LIST
        }
        
        console.log('Fetching from:', url)
        const data = await apiClient.get(url)
        console.log('API Response:', data)
        console.log('First product:', data[0] || (Array.isArray(data) ? 'empty array' : data))
        
        // Handle paginated or direct response
        const productList = Array.isArray(data) ? data : data.results || data.products || []
        console.log('Products to display:', productList)
        productList.forEach((p, i) => {
          console.log(`Product ${i}:`, { id: p.id, name: p.name, image: p.image, image_url: p.image_url })
        })
        
        setProducts(productList)
      } catch (err) {
        const errorMsg = err.message || 'Failed to fetch products'
        console.error('Error fetching products:', errorMsg, err)
        setError(errorMsg)
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [category])

  return (
    <div className="product-list-container">
      <h1>{category ? `${category.toUpperCase()} - Products` : 'All Products'}</h1>
      
      {loading && <p className="loading-text">Loading products...</p>}
      {error && <p className="error-text">Error: {error}</p>}
      
      {!loading && products.length === 0 && (
        <p className="no-products">No products found</p>
      )}
      
      {!loading && products.length > 0 && (
        <>
          <div className="product-filters">
            <div className="filter-group">
              <label>Sort By:</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="name-asc">Name (A-Z)</option>
                <option value="name-desc">Name (Z-A)</option>
                <option value="price-asc">Price: Low to High</option>
                <option value="price-desc">Price: High to Low</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Stock Status:</label>
              <select value={stockStatus} onChange={(e) => setStockStatus(e.target.value)}>
                <option value="all">All Products</option>
                <option value="in-stock">In Stock</option>
                <option value="out-of-stock">Out of Stock</option>
              </select>
            </div>

            <div className="filter-group price-filter">
              <label>Max Price: <span className="price-value">Rs {maxPrice || '∞'}</span></label>
              <input 
                type="range" 
                min="0" 
                max="50000" 
                step="100" 
                value={maxPrice || 50000} 
                onChange={(e) => setMaxPrice(e.target.value === '50000' ? '' : e.target.value)}
                className="price-slider"
              />
            </div>

            <div className="filter-results">
              {(() => {
                let list = [...products]
                if (stockStatus === 'in-stock') {
                  list = list.filter(p => Number(p.stock || 0) > 0)
                } else if (stockStatus === 'out-of-stock') {
                  list = list.filter(p => Number(p.stock || 0) === 0)
                }
                if (maxPrice !== '' && !isNaN(Number(maxPrice))) {
                  list = list.filter(p => Number(p.price || 0) <= Number(maxPrice))
                }
                return `Showing ${list.length} of ${products.length} products`
              })()}
            </div>
          </div>

          <div className="products-grid">
            {(() => {
              // Apply filters and sorting
              let list = [...products]
              
              // Filter by stock status
              if (stockStatus === 'in-stock') {
                list = list.filter(p => Number(p.stock || 0) > 0)
              } else if (stockStatus === 'out-of-stock') {
                list = list.filter(p => Number(p.stock || 0) === 0)
              }
              
              // Filter by max price
              if (maxPrice !== '' && !isNaN(Number(maxPrice))) {
                list = list.filter(p => Number(p.price || 0) <= Number(maxPrice))
              }
              
              // Apply sorting
              if (sortBy === 'name-asc') {
                list.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
              } else if (sortBy === 'name-desc') {
                list.sort((a, b) => (b.name || '').localeCompare(a.name || ''))
              } else if (sortBy === 'price-asc') {
                list.sort((a, b) => Number(a.price || 0) - Number(b.price || 0))
              } else if (sortBy === 'price-desc') {
                list.sort((a, b) => Number(b.price || 0) - Number(a.price || 0))
              }

              if (list.length === 0) {
                return <p className="no-products-filtered">No products match your filters</p>
              }

              return list.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))
            })()}
          </div>
        </>
      )}
    </div>
  )
}

export default ProductList
