import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [view, setView] = useState('home'); // home, create, trace
  const [formData, setFormData] = useState({
    producerName: '',
    producerType: 'vegetable_farmer',
    producerLocation: '',
    producerContact: '',
    productName: '',
    quantityKg: '',
    harvestDate: new Date().toISOString().split('T')[0],
  });
  const [traceId, setTraceId] = useState('');
  const [traceData, setTraceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const createHarvest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // First, register producer
      const producerRes = await axios.post('/api/producer/register', {
        name: formData.producerName,
        type: formData.producerType,
        location: formData.producerLocation,
        contact: formData.producerContact,
      });

      const producerId = producerRes.data.producer_id;

      // Then create harvest
      const harvestRes = await axios.post('/api/harvest/create', {
        producer_id: producerId,
        product_name: formData.productName,
        quantity_kg: parseFloat(formData.quantityKg),
        harvest_date: formData.harvestDate,
      });

      setSuccess(`✓ Harvest created: ${harvestRes.data.harvest_id}\nQR: ${harvestRes.data.qr}`);
      setFormData({
        producerName: '',
        producerType: 'vegetable_farmer',
        producerLocation: '',
        producerContact: '',
        productName: '',
        quantityKg: '',
        harvestDate: new Date().toISOString().split('T')[0],
      });
      setTimeout(() => setView('home'), 2000);
    } catch (err) {
      setError(err.response?.data?.error || 'Error creating harvest');
    } finally {
      setLoading(false);
    }
  };

  const traceHarvest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await axios.get(`/api/harvest/${traceId}/trace`);
      setTraceData(res.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Harvest not found');
      setTraceData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🥬 Trasabilitate</h1>
        <p>Loose Produce Traceability</p>
      </header>

      <main className="container">
        {/* Navigation */}
        <nav className="nav">
          <button
            className={`nav-btn ${view === 'home' ? 'active' : ''}`}
            onClick={() => setView('home')}
          >
            Home
          </button>
          <button
            className={`nav-btn ${view === 'create' ? 'active' : ''}`}
            onClick={() => setView('create')}
          >
            New Harvest
          </button>
          <button
            className={`nav-btn ${view === 'trace' ? 'active' : ''}`}
            onClick={() => setView('trace')}
          >
            Trace Harvest
          </button>
        </nav>

        {/* Error/Success Messages */}
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Home View */}
        {view === 'home' && (
          <div className="view">
            <h2>Welcome to Trasabilitate</h2>
            <p>Track loose vegetables and fruits from harvest to market.</p>
            <div className="features">
              <div className="feature">
                <h3>📱 Simple Tracking</h3>
                <p>Log harvests and sales in seconds.</p>
              </div>
              <div className="feature">
                <h3>🔍 Full Traceability</h3>
                <p>Track produce from farmer to buyer.</p>
              </div>
              <div className="feature">
                <h3>📊 Compliance Ready</h3>
                <p>EU 178/2002 compliant 1-step forward/back tracking.</p>
              </div>
            </div>
          </div>
        )}

        {/* Create Harvest View */}
        {view === 'create' && (
          <div className="view">
            <h2>Create New Harvest</h2>
            <form onSubmit={createHarvest} className="form">
              <fieldset>
                <legend>Producer Info</legend>
                <input
                  type="text"
                  name="producerName"
                  placeholder="Producer Name"
                  value={formData.producerName}
                  onChange={handleInputChange}
                  required
                />
                <select
                  name="producerType"
                  value={formData.producerType}
                  onChange={handleInputChange}
                >
                  <option value="vegetable_farmer">Vegetable Farmer</option>
                  <option value="fruit_farmer">Fruit Farmer</option>
                  <option value="mixed_farmer">Mixed Farmer</option>
                </select>
                <input
                  type="text"
                  name="producerLocation"
                  placeholder="Location"
                  value={formData.producerLocation}
                  onChange={handleInputChange}
                  required
                />
                <input
                  type="email"
                  name="producerContact"
                  placeholder="Email/Phone"
                  value={formData.producerContact}
                  onChange={handleInputChange}
                  required
                />
              </fieldset>

              <fieldset>
                <legend>Harvest Info</legend>
                <input
                  type="text"
                  name="productName"
                  placeholder="Product (e.g., Tomato, Apple)"
                  value={formData.productName}
                  onChange={handleInputChange}
                  required
                />
                <input
                  type="number"
                  name="quantityKg"
                  placeholder="Quantity (kg)"
                  value={formData.quantityKg}
                  onChange={handleInputChange}
                  step="0.1"
                  required
                />
                <input
                  type="date"
                  name="harvestDate"
                  value={formData.harvestDate}
                  onChange={handleInputChange}
                  required
                />
              </fieldset>

              <button type="submit" disabled={loading} className="btn btn-primary">
                {loading ? 'Creating...' : 'Create Harvest'}
              </button>
            </form>
          </div>
        )}

        {/* Trace Harvest View */}
        {view === 'trace' && (
          <div className="view">
            <h2>Trace Harvest</h2>
            <form onSubmit={traceHarvest} className="form">
              <input
                type="text"
                placeholder="Harvest ID (e.g., 260308-TOMATO-500KG)"
                value={traceId}
                onChange={(e) => setTraceId(e.target.value)}
                required
              />
              <button type="submit" disabled={loading} className="btn btn-primary">
                {loading ? 'Searching...' : 'Trace'}
              </button>
            </form>

            {traceData && (
              <div className="trace-result">
                <div className="harvest-info">
                  <h3>{traceData.harvest.product_name}</h3>
                  <p><strong>Harvest ID:</strong> {traceData.harvest.harvest_id}</p>
                  <p><strong>Quantity:</strong> {traceData.harvest.quantity_kg} kg</p>
                  <p><strong>Date:</strong> {traceData.harvest.harvest_date}</p>
                  <p><strong>Producer:</strong> {traceData.harvest.name}</p>
                  <p><strong>Location:</strong> {traceData.harvest.location}</p>
                </div>

                {traceData.sales && traceData.sales.length > 0 && (
                  <div className="sales-info">
                    <h3>Sales & Deliveries</h3>
                    {traceData.sales.map((sale, idx) => (
                      <div key={idx} className="sale">
                        <p><strong>{sale.buyer_type.toUpperCase()}</strong>: {sale.buyer_name}</p>
                        <p>{sale.quantity_kg} kg @ €{sale.price_per_kg}/kg</p>
                        <p>Delivered: {sale.delivery_date} to {sale.delivery_location}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        <p>© 2026 Trasabilitate — Loose Produce Traceability</p>
      </footer>
    </div>
  );
}

export default App;
