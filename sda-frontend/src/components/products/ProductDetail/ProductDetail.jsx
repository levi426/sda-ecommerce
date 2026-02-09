
import React, { useState, useEffect, useContext, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient, API_ENDPOINTS } from '../../../services/api';
import { AuthContext } from '../../../services/AuthService';
import ProductReviews from '../ProductReviews/ProductReviews';
import AddReview from '../AddReview/AddReview';
import './ProductDetail.css';

function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const { isAuthenticated } = useContext(AuthContext);
  const infoRef = useRef(null);
  // Default to true so product details are visible immediately.
  // IntersectionObserver will keep it true on scroll (no flicker).
  const [infoVisible, setInfoVisible] = useState(true);

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true);
        const url = `http://localhost:8000/api/products/${id}/`;
        const data = await apiClient.get(url);
        setProduct(data);
        console.debug('Product loaded:', data);
      } catch (err) {
        setError(err.message || 'Failed to fetch product');
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchProduct();
  }, [id]);

  useEffect(() => {
    if (!infoRef.current) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) setInfoVisible(true);
      });
    }, { threshold: 0.15 });
    io.observe(infoRef.current);
    return () => io.disconnect();
  }, [infoRef]);

  if (loading) return <div className="product-detail-container"><p>Loading product...</p></div>;
  if (error) return <div className="product-detail-container"><p className="error-text">Error: {error}</p></div>;
  if (!product) return <div className="product-detail-container"><p>Product not found</p></div>;

  const imageUrl = product?.image_url || product?.image;

  const handleAddToCart = async () => {
    if (!isAuthenticated) return setMessage('Please login to add items to cart');
    try {
      setMessage(null);
      const res = await apiClient.post(API_ENDPOINTS.CART.ADD, { product_id: product.id, quantity: 1 });
      setMessage(res?.error || 'Added to cart');
    } catch {
      setMessage('Failed to add to cart');
    }
  };

  const handleAddToWishlist = async () => {
    if (!isAuthenticated) return setMessage('Please login to add items to wishlist');
    try {
      setMessage(null);
      const res = await apiClient.post(API_ENDPOINTS.WISHLIST.ADD, { product_id: product.id });
      setMessage(res?.message || res?.error || 'Added to wishlist');
    } catch {
      setMessage('Failed to add to wishlist');
    }
  };

  return (
    <div className="product-detail-container">
      <div className="product-detail-flex">
        <div className="product-detail-image-col">
          {imageUrl ? (
            <img src={imageUrl} alt={product.name} className="product-detail-img" />
          ) : (
            <div className="image-placeholder-large">No Image</div>
          )}
        </div>
        <div ref={infoRef} className={`product-detail-info-col ${infoVisible ? 'visible' : 'hidden'}`}>
          <h1 className="product-title">{product.name}</h1>
          <div className="product-price">Rs {parseFloat(product.price).toFixed(2)}</div>
          <div className="product-meta">
            <span className="category-badge">{product.category_display || product.category}</span>
            <span className="stock-badge">{product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}</span>
          </div>
          <h3 className="desc-label">Product Description</h3>
          <p className="product-description">{product.description}</p>
          <div className="product-actions">
            <button className="btn-add-cart" disabled={product.stock === 0} onClick={handleAddToCart}>Add to Cart</button>
            <button className="btn-add-wishlist" onClick={handleAddToWishlist}>Add to Wishlist</button>
          </div>
          {message && <div className="success-text">{message}</div>}
          <div className="product-details-table">
            <h3>Product Details</h3>
            <table>
              <tbody>
                <tr><td>Category</td><td>{product.category_display || product.category}</td></tr>
                <tr><td>Price</td><td>Rs {parseFloat(product.price).toFixed(2)}</td></tr>
                <tr><td>Stock</td><td>{product.stock}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div className="product-detail-reviews-col">
        <ProductReviews productId={id} reviews={product.reviews} />
        <AddReview productId={id} onReviewAdded={async () => {
          try {
            const data = await apiClient.get(`http://localhost:8000/api/products/${id}/`);
            setProduct(data);
          } catch {}
        }} />
      </div>
    </div>
  );
}

export default ProductDetail;

